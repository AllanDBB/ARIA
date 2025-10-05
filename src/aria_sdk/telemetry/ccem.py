"""
ARIA SDK - Telemetry CCEM (Channel Conditioning and Error Management) Module

Provides TX jitter smoothing, RX de-jitter/reorder, and drift compensation.
"""

import asyncio
import time
from typing import Optional, Dict
from collections import deque
from dataclasses import dataclass
import numpy as np

from aria_sdk.domain.entities import Envelope


@dataclass
class TimingStats:
    """Statistics for timing analysis."""
    mean_interval: float = 0.0
    jitter: float = 0.0
    drift: float = 0.0
    samples: int = 0


class TxConditioner:
    """
    Transmit conditioner - smooths outgoing packet timing.
    
    Reduces jitter by maintaining constant send rate.
    """
    
    def __init__(self, target_interval: float = 0.01):
        """
        Initialize TX conditioner.
        
        Args:
            target_interval: Target time between packets (seconds). Default: 10ms = 100Hz
        """
        self.target_interval = target_interval
        self.last_send_time: Optional[float] = None
    
    async def condition(self, envelope: Envelope) -> Envelope:
        """
        Condition envelope transmission timing.
        
        Args:
            envelope: Envelope to send
            
        Returns:
            Same envelope (after timing adjustment)
        """
        now = time.monotonic()
        
        if self.last_send_time is not None:
            elapsed = now - self.last_send_time
            if elapsed < self.target_interval:
                # Sleep to maintain target rate
                await asyncio.sleep(self.target_interval - elapsed)
        
        self.last_send_time = time.monotonic()
        return envelope


class RxDeJitter:
    """
    Receive de-jitter buffer - reorders and smooths incoming packets.
    
    Uses playout buffer to absorb network jitter.
    """
    
    def __init__(self, buffer_size: int = 10, max_wait: float = 0.1):
        """
        Initialize RX de-jitter buffer.
        
        Args:
            buffer_size: Number of packets to buffer
            max_wait: Maximum wait time for late packets (seconds)
        """
        self.buffer_size = buffer_size
        self.max_wait = max_wait
        self.buffer: Dict[int, Envelope] = {}
        self.next_seq: int = 0
        self.arrival_times: Dict[int, float] = {}
    
    async def dejitter(self, envelope: Envelope, seq_num: int) -> Optional[Envelope]:
        """
        Add envelope to de-jitter buffer and try to output.
        
        Args:
            envelope: Received envelope
            seq_num: Sequence number
            
        Returns:
            Envelope ready for processing, or None if buffering
        """
        arrival_time = time.monotonic()
        
        # Store in buffer
        self.buffer[seq_num] = envelope
        self.arrival_times[seq_num] = arrival_time
        
        # Try to output next expected packet
        if self.next_seq in self.buffer:
            # Next packet available
            out_envelope = self.buffer.pop(self.next_seq)
            self.arrival_times.pop(self.next_seq, None)
            self.next_seq += 1
            return out_envelope
        
        # Check if we should wait or skip
        if seq_num > self.next_seq + self.buffer_size:
            # Too far ahead - assume loss, skip to this packet
            gap = seq_num - self.next_seq
            print(f"[RxDeJitter] Detected {gap} lost packets, skipping to seq={seq_num}")
            self.next_seq = seq_num
            out_envelope = self.buffer.pop(seq_num)
            self.arrival_times.pop(seq_num, None)
            return out_envelope
        
        # Buffer and wait
        return None
    
    def get_stats(self) -> TimingStats:
        """Get timing statistics from buffer."""
        if len(self.arrival_times) < 2:
            return TimingStats()
        
        times = sorted(self.arrival_times.values())
        intervals = np.diff(times)
        
        return TimingStats(
            mean_interval=float(np.mean(intervals)),
            jitter=float(np.std(intervals)),
            samples=len(intervals)
        )


class DriftCompensator:
    """
    Clock drift compensator - adjusts for sender/receiver clock skew.
    
    Uses linear regression to estimate and compensate drift.
    """
    
    def __init__(self, window_size: int = 100):
        """
        Initialize drift compensator.
        
        Args:
            window_size: Number of samples for drift estimation
        """
        self.window_size = window_size
        self.sender_timestamps: deque = deque(maxlen=window_size)
        self.receiver_timestamps: deque = deque(maxlen=window_size)
        self.drift_rate: float = 1.0  # Multiplicative factor
        self.offset: float = 0.0  # Additive offset
    
    def update(self, sender_ts: float, receiver_ts: float):
        """
        Update drift estimate with new timestamp pair.
        
        Args:
            sender_ts: Timestamp from sender (seconds)
            receiver_ts: Local receive timestamp (seconds)
        """
        self.sender_timestamps.append(sender_ts)
        self.receiver_timestamps.append(receiver_ts)
        
        if len(self.sender_timestamps) >= 10:
            # Estimate drift using linear regression
            x = np.array(self.sender_timestamps)
            y = np.array(self.receiver_timestamps)
            
            # y = drift_rate * x + offset
            # Use least squares: [drift_rate, offset] = (X^T X)^-1 X^T y
            X = np.column_stack([x, np.ones_like(x)])
            params = np.linalg.lstsq(X, y, rcond=None)[0]
            
            self.drift_rate = params[0]
            self.offset = params[1]
    
    def compensate(self, sender_ts: float) -> float:
        """
        Compensate timestamp for drift.
        
        Args:
            sender_ts: Original sender timestamp
            
        Returns:
            Compensated timestamp in receiver's timebase
        """
        return self.drift_rate * sender_ts + self.offset
    
    def get_drift_info(self) -> tuple[float, float]:
        """
        Get current drift parameters.
        
        Returns:
            Tuple of (drift_rate, offset_seconds)
        """
        return (self.drift_rate, self.offset)
