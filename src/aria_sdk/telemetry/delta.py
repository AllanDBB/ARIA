"""
ARIA SDK - Telemetry Delta Encoding Module

Provides delta encoding for reducing bandwidth on similar consecutive payloads.
"""

from typing import Optional
import numpy as np

from aria_sdk.domain.protocols import IDeltaCodec


class SimpleDeltaCodec(IDeltaCodec):
    """
    Simple XOR-based delta encoding.
    
    Useful for sensor data where consecutive readings are similar.
    Stores the XOR difference between current and previous payload.
    """
    
    def __init__(self):
        """Initialize delta codec with empty state."""
        self.previous: Optional[bytes] = None
    
    def encode(self, data: bytes) -> tuple[bytes, bool]:
        """
        Encode data as delta from previous.
        
        Args:
            data: Current payload bytes
            
        Returns:
            Tuple of (encoded_bytes, is_delta)
            - If is_delta=True, encoded_bytes is XOR difference
            - If is_delta=False, encoded_bytes is full payload (first frame or size mismatch)
        """
        if self.previous is None or len(data) != len(self.previous):
            # First frame or size changed - send full payload
            self.previous = data
            return (data, False)
        
        # Compute XOR delta
        prev_array = np.frombuffer(self.previous, dtype=np.uint8)
        curr_array = np.frombuffer(data, dtype=np.uint8)
        delta_array = np.bitwise_xor(curr_array, prev_array)
        
        self.previous = data
        return (delta_array.tobytes(), True)
    
    def decode(self, data: bytes, is_delta: bool) -> bytes:
        """
        Decode delta-encoded data.
        
        Args:
            data: Encoded bytes (delta or full)
            is_delta: True if data is delta, False if full payload
            
        Returns:
            Decoded full payload
            
        Raises:
            RuntimeError: If delta decoding fails (missing previous)
        """
        if not is_delta:
            # Full payload - update state
            self.previous = data
            return data
        
        if self.previous is None:
            raise RuntimeError("Cannot decode delta without previous frame")
        
        if len(data) != len(self.previous):
            raise RuntimeError(
                f"Delta size mismatch: got {len(data)}, expected {len(self.previous)}"
            )
        
        # Apply XOR delta to previous
        prev_array = np.frombuffer(self.previous, dtype=np.uint8)
        delta_array = np.frombuffer(data, dtype=np.uint8)
        curr_array = np.bitwise_xor(prev_array, delta_array)
        
        self.previous = curr_array.tobytes()
        return self.previous
    
    def reset(self):
        """Reset codec state (clear previous frame)."""
        self.previous = None


class AdaptiveDeltaCodec(IDeltaCodec):
    """
    Adaptive delta codec that only uses delta when beneficial.
    
    Falls back to full payload if delta would be larger.
    """
    
    def __init__(self, threshold: float = 0.9):
        """
        Initialize adaptive delta codec.
        
        Args:
            threshold: Ratio threshold (0-1). Use delta if delta_size/full_size < threshold
        """
        self.threshold = threshold
        self.previous: Optional[bytes] = None
    
    def encode(self, data: bytes) -> tuple[bytes, bool]:
        """
        Encode adaptively - use delta only if beneficial.
        
        Args:
            data: Current payload bytes
            
        Returns:
            Tuple of (encoded_bytes, is_delta)
        """
        if self.previous is None or len(data) != len(self.previous):
            self.previous = data
            return (data, False)
        
        # Compute delta
        prev_array = np.frombuffer(self.previous, dtype=np.uint8)
        curr_array = np.frombuffer(data, dtype=np.uint8)
        delta_array = np.bitwise_xor(curr_array, prev_array)
        
        # Count non-zero bytes (measure of difference)
        non_zero_count = np.count_nonzero(delta_array)
        ratio = non_zero_count / len(delta_array)
        
        if ratio < self.threshold:
            # Delta is beneficial
            self.previous = data
            return (delta_array.tobytes(), True)
        else:
            # Too much change - send full payload
            self.previous = data
            return (data, False)
    
    def decode(self, data: bytes, is_delta: bool) -> bytes:
        """Decode adaptively."""
        if not is_delta:
            self.previous = data
            return data
        
        if self.previous is None:
            raise RuntimeError("Cannot decode delta without previous frame")
        
        prev_array = np.frombuffer(self.previous, dtype=np.uint8)
        delta_array = np.frombuffer(data, dtype=np.uint8)
        curr_array = np.bitwise_xor(prev_array, delta_array)
        
        self.previous = curr_array.tobytes()
        return self.previous
    
    def reset(self):
        """Reset codec state."""
        self.previous = None
