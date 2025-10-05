"""
ARIA SDK - Homeostasis Controller Module

Adaptive parameter controller for maintaining system health.
"""

from typing import Dict, Optional
from dataclasses import dataclass

from aria_sdk.domain.protocols import IHomeostasis


@dataclass
class HomeostasisState:
    """Current homeostatic state."""
    bandwidth_utilization: float = 0.5
    packet_loss_rate: float = 0.0
    latency_ms: float = 50.0
    cpu_load: float = 0.5
    memory_usage: float = 0.5
    temperature: float = 60.0


class HomeostasisController(IHomeostasis):
    """
    Adaptive controller that adjusts system parameters to maintain health.
    
    Monitors:
    - Network conditions (bandwidth, loss, latency)
    - Compute resources (CPU, memory)
    - Hardware (temperature)
    
    Adjusts:
    - FEC level
    - Compression level
    - Codec quality
    - Sensor rates
    """
    
    def __init__(
        self,
        target_bandwidth: float = 0.7,
        target_loss_rate: float = 0.01,
        target_cpu_load: float = 0.6
    ):
        """
        Initialize homeostasis controller.
        
        Args:
            target_bandwidth: Target bandwidth utilization (0-1)
            target_loss_rate: Target packet loss rate (0-1)
            target_cpu_load: Target CPU load (0-1)
        """
        self.target_bandwidth = target_bandwidth
        self.target_loss_rate = target_loss_rate
        self.target_cpu_load = target_cpu_load
        
        self.state = HomeostasisState()
        
        # Recommended parameters
        self.recommendations: Dict[str, any] = {
            'fec_level': 2,
            'compression_level': 1,
            'sensor_rate_scale': 1.0,
        }
    
    def update(
        self,
        bandwidth_utilization: Optional[float] = None,
        packet_loss_rate: Optional[float] = None,
        latency_ms: Optional[float] = None,
        cpu_load: Optional[float] = None,
        memory_usage: Optional[float] = None,
        temperature: Optional[float] = None
    ):
        """
        Update homeostatic state.
        
        Args:
            bandwidth_utilization: Current bandwidth usage (0-1)
            packet_loss_rate: Current packet loss rate (0-1)
            latency_ms: Current latency (milliseconds)
            cpu_load: Current CPU load (0-1)
            memory_usage: Current memory usage (0-1)
            temperature: Current temperature (Celsius)
        """
        # Update state
        if bandwidth_utilization is not None:
            self.state.bandwidth_utilization = bandwidth_utilization
        if packet_loss_rate is not None:
            self.state.packet_loss_rate = packet_loss_rate
        if latency_ms is not None:
            self.state.latency_ms = latency_ms
        if cpu_load is not None:
            self.state.cpu_load = cpu_load
        if memory_usage is not None:
            self.state.memory_usage = memory_usage
        if temperature is not None:
            self.state.temperature = temperature
        
        # Recompute recommendations
        self._adapt_parameters()
    
    def _adapt_parameters(self):
        """Adapt parameters based on current state."""
        
        # Adapt FEC based on packet loss
        if self.state.packet_loss_rate > self.target_loss_rate * 2:
            # High loss - increase FEC
            self.recommendations['fec_level'] = min(4, self.recommendations['fec_level'] + 1)
        elif self.state.packet_loss_rate < self.target_loss_rate * 0.5:
            # Low loss - decrease FEC to save bandwidth
            self.recommendations['fec_level'] = max(1, self.recommendations['fec_level'] - 1)
        
        # Adapt compression based on bandwidth
        if self.state.bandwidth_utilization > self.target_bandwidth:
            # Over bandwidth - increase compression
            self.recommendations['compression_level'] = min(9, self.recommendations['compression_level'] + 1)
        elif self.state.bandwidth_utilization < self.target_bandwidth * 0.5:
            # Plenty of bandwidth - decrease compression for less CPU
            self.recommendations['compression_level'] = max(0, self.recommendations['compression_level'] - 1)
        
        # Adapt sensor rates based on CPU
        if self.state.cpu_load > self.target_cpu_load:
            # High CPU - reduce sensor rates
            self.recommendations['sensor_rate_scale'] = max(0.5, self.recommendations['sensor_rate_scale'] - 0.1)
        elif self.state.cpu_load < self.target_cpu_load * 0.5:
            # Low CPU - can increase sensor rates
            self.recommendations['sensor_rate_scale'] = min(1.5, self.recommendations['sensor_rate_scale'] + 0.1)
        
        # Emergency throttling if temperature too high
        if self.state.temperature > 80.0:
            self.recommendations['sensor_rate_scale'] = 0.5
            self.recommendations['compression_level'] = 0  # Disable compression to reduce CPU
            print("[Homeostasis] THERMAL THROTTLING ACTIVE")
    
    def get_recommendation(self, param_name: str) -> Optional[any]:
        """
        Get recommended parameter value.
        
        Args:
            param_name: Parameter name ('fec_level', 'compression_level', 'sensor_rate_scale')
            
        Returns:
            Recommended value, or None if unknown parameter
        """
        return self.recommendations.get(param_name)
    
    def get_all_recommendations(self) -> Dict[str, any]:
        """Get all recommendations."""
        return dict(self.recommendations)
    
    def get_state(self) -> HomeostasisState:
        """Get current homeostatic state."""
        return self.state
    
    def get_health_score(self) -> float:
        """
        Compute overall system health score.
        
        Returns:
            Health score (0-1, higher=healthier)
        """
        # Compute deviations from targets
        bw_dev = abs(self.state.bandwidth_utilization - self.target_bandwidth)
        loss_dev = abs(self.state.packet_loss_rate - self.target_loss_rate)
        cpu_dev = abs(self.state.cpu_load - self.target_cpu_load)
        
        # Temperature penalty
        temp_penalty = max(0, (self.state.temperature - 70) / 20)  # Penalty above 70°C
        
        # Combine into health score
        health = 1.0 - (bw_dev + loss_dev * 10 + cpu_dev + temp_penalty) / 4
        
        return max(0.0, min(1.0, health))
