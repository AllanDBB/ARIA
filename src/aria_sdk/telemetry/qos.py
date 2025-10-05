"""
ARIA SDK - Telemetry QoS (Quality of Service) Module

Provides priority queues and token bucket rate limiting.
"""

import asyncio
import time
from typing import Optional, Dict
from dataclasses import dataclass
from collections import deque

from aria_sdk.domain.entities import Envelope, Priority
from aria_sdk.domain.protocols import IQoSShaper


@dataclass
class QoSConfig:
    """QoS configuration per priority level."""
    max_rate: float  # Maximum packets/second
    burst_size: int  # Maximum burst size (packets)
    queue_size: int  # Maximum queue length


class TokenBucket:
    """
    Token bucket rate limiter.
    
    Allows bursts up to burst_size while maintaining average rate.
    """
    
    def __init__(self, rate: float, burst_size: int):
        """
        Initialize token bucket.
        
        Args:
            rate: Token generation rate (tokens/second)
            burst_size: Maximum tokens in bucket
        """
        self.rate = rate
        self.burst_size = burst_size
        self.tokens = float(burst_size)
        self.last_update = time.monotonic()
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens available, False otherwise
        """
        # Refill tokens based on elapsed time
        now = time.monotonic()
        elapsed = now - self.last_update
        self.tokens = min(self.burst_size, self.tokens + elapsed * self.rate)
        self.last_update = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    async def wait_for_tokens(self, tokens: int = 1):
        """
        Wait until tokens available.
        
        Args:
            tokens: Number of tokens needed
        """
        while not self.consume(tokens):
            # Calculate wait time
            needed = tokens - self.tokens
            wait_time = needed / self.rate
            await asyncio.sleep(min(wait_time, 0.1))  # Cap at 100ms


class QoSShaper(IQoSShaper):
    """
    Multi-priority QoS shaper with token bucket rate limiting.
    
    Priorities (highest to lowest):
    - P0_CRITICAL: Emergency, safety-critical
    - P1_HIGH: Important telemetry, commands
    - P2_NORMAL: Standard sensor data
    - P3_LOW: Logs, diagnostics
    """
    
    def __init__(self, config: Optional[Dict[Priority, QoSConfig]] = None):
        """
        Initialize QoS shaper.
        
        Args:
            config: Per-priority QoS configuration (uses defaults if None)
        """
        if config is None:
            # Default configuration
            config = {
                Priority.P0_CRITICAL: QoSConfig(max_rate=1000.0, burst_size=100, queue_size=1000),
                Priority.P1_HIGH: QoSConfig(max_rate=500.0, burst_size=50, queue_size=500),
                Priority.P2_NORMAL: QoSConfig(max_rate=200.0, burst_size=20, queue_size=200),
                Priority.P3_LOW: QoSConfig(max_rate=50.0, burst_size=10, queue_size=100),
            }
        
        self.config = config
        
        # Priority queues
        self.queues: Dict[Priority, deque] = {
            p: deque(maxlen=cfg.queue_size) for p, cfg in config.items()
        }
        
        # Token buckets per priority
        self.buckets: Dict[Priority, TokenBucket] = {
            p: TokenBucket(cfg.max_rate, cfg.burst_size) for p, cfg in config.items()
        }
        
        # Statistics
        self.stats = {
            'enqueued': {p: 0 for p in Priority},
            'dequeued': {p: 0 for p in Priority},
            'dropped': {p: 0 for p in Priority},
        }
    
    async def enqueue(self, envelope: Envelope) -> bool:
        """
        Enqueue envelope with priority.
        
        Args:
            envelope: Envelope to enqueue
            
        Returns:
            True if enqueued, False if dropped (queue full)
        """
        priority = envelope.priority
        queue = self.queues[priority]
        
        if len(queue) >= self.config[priority].queue_size:
            # Queue full - drop
            self.stats['dropped'][priority] += 1
            return False
        
        queue.append(envelope)
        self.stats['enqueued'][priority] += 1
        return True
    
    async def dequeue(self) -> Optional[Envelope]:
        """
        Dequeue highest-priority envelope that has tokens.
        
        Returns:
            Envelope, or None if all queues empty or rate-limited
        """
        # Try priorities in order (highest first)
        for priority in [Priority.P0_CRITICAL, Priority.P1_HIGH, Priority.P2_NORMAL, Priority.P3_LOW]:
            queue = self.queues[priority]
            bucket = self.buckets[priority]
            
            if queue and bucket.consume(1):
                envelope = queue.popleft()
                self.stats['dequeued'][priority] += 1
                return envelope
        
        return None
    
    async def dequeue_wait(self, timeout: Optional[float] = None) -> Optional[Envelope]:
        """
        Dequeue with wait for tokens or timeout.
        
        Args:
            timeout: Maximum wait time (None=infinite)
            
        Returns:
            Envelope, or None if timeout
        """
        start_time = time.monotonic()
        
        while True:
            # Try dequeue
            envelope = await self.dequeue()
            if envelope:
                return envelope
            
            # Check timeout
            if timeout and (time.monotonic() - start_time) >= timeout:
                return None
            
            # Wait a bit
            await asyncio.sleep(0.01)
    
    def get_stats(self) -> Dict:
        """
        Get QoS statistics.
        
        Returns:
            Dict with enqueued/dequeued/dropped counts per priority
        """
        return {
            'enqueued': dict(self.stats['enqueued']),
            'dequeued': dict(self.stats['dequeued']),
            'dropped': dict(self.stats['dropped']),
            'queue_lengths': {p: len(q) for p, q in self.queues.items()},
        }
    
    def get_queue_length(self, priority: Priority) -> int:
        """Get current queue length for priority."""
        return len(self.queues[priority])
    
    def clear(self, priority: Optional[Priority] = None):
        """
        Clear queues.
        
        Args:
            priority: Specific priority to clear (None=all)
        """
        if priority:
            self.queues[priority].clear()
        else:
            for q in self.queues.values():
                q.clear()


class AdaptiveQoS:
    """
    Adaptive QoS that adjusts rates based on channel conditions.
    """
    
    def __init__(self, base_shaper: QoSShaper):
        """
        Initialize adaptive QoS.
        
        Args:
            base_shaper: Base QoS shaper to adapt
        """
        self.shaper = base_shaper
        self.base_rates = {
            p: cfg.max_rate for p, cfg in base_shaper.config.items()
        }
        self.scaling_factor = 1.0
    
    def update_channel_capacity(self, bandwidth_bps: float, avg_packet_size: int = 1000):
        """
        Update rate limits based on available bandwidth.
        
        Args:
            bandwidth_bps: Available bandwidth (bits/second)
            avg_packet_size: Average packet size (bytes)
        """
        # Calculate packets per second from bandwidth
        packets_per_second = bandwidth_bps / (8 * avg_packet_size)
        
        # Calculate scaling factor
        total_base_rate = sum(self.base_rates.values())
        if total_base_rate > 0:
            self.scaling_factor = packets_per_second / total_base_rate
            self.scaling_factor = max(0.1, min(2.0, self.scaling_factor))  # Clamp [0.1, 2.0]
        
        # Update token bucket rates
        for priority, base_rate in self.base_rates.items():
            new_rate = base_rate * self.scaling_factor
            self.shaper.buckets[priority].rate = new_rate
        
        print(f"[AdaptiveQoS] Scaled rates by {self.scaling_factor:.2f} (BW={bandwidth_bps/1e6:.2f} Mbps)")
    
    async def enqueue(self, envelope: Envelope) -> bool:
        """Enqueue via wrapped shaper."""
        return await self.shaper.enqueue(envelope)
    
    async def dequeue(self) -> Optional[Envelope]:
        """Dequeue via wrapped shaper."""
        return await self.shaper.dequeue()
