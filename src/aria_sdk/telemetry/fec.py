"""
ARIA SDK - Telemetry FEC (Forward Error Correction) Module

Provides Reed-Solomon error correction for lossy channels.
"""

from typing import List, Optional
import reedsolo

from aria_sdk.domain.protocols import IFEC


class ReedSolomonFEC(IFEC):
    """
    Reed-Solomon forward error correction.
    
    Can recover from up to (m) erasures or (m/2) errors.
    Example: RS(4,2) can recover 2 lost packets from 6 total (4 data + 2 parity).
    """
    
    def __init__(self, k: int = 4, m: int = 2):
        """
        Initialize Reed-Solomon FEC.
        
        Args:
            k: Number of data symbols (packets)
            m: Number of parity symbols (packets)
            
        Total packets sent: k + m
        Can recover from up to m losses
        """
        if k < 1 or m < 1:
            raise ValueError(f"Invalid RS parameters: k={k}, m={m} (must be >= 1)")
        
        self.k = k
        self.m = m
        self.total = k + m
        
        # Create Reed-Solomon codec
        # nsym = number of error correction symbols (bytes of parity)
        # We'll work at packet level, so we'll use byte-level RS
        self.rs = reedsolo.RSCodec(m)
    
    def encode(self, packets: List[bytes]) -> List[bytes]:
        """
        Encode data packets with FEC parity.
        
        Args:
            packets: List of k data packets
            
        Returns:
            List of k+m packets (original data + parity)
            
        Raises:
            ValueError: If number of packets doesn't match k
        """
        if len(packets) != self.k:
            raise ValueError(f"Expected {self.k} packets, got {len(packets)}")
        
        # Ensure all packets same size (pad if needed)
        max_len = max(len(p) for p in packets)
        padded_packets = [p + b'\x00' * (max_len - len(p)) for p in packets]
        
        # Encode each byte position across packets
        encoded_packets = list(padded_packets)  # Start with data packets
        
        # Generate parity packets
        for byte_idx in range(max_len):
            # Extract byte column across all data packets
            data_bytes = bytes([padded_packets[i][byte_idx] for i in range(self.k)])
            
            # Encode with RS
            encoded = self.rs.encode(data_bytes)
            
            # Parity bytes are at the end
            parity_bytes = encoded[self.k:]
            
            # Distribute parity bytes to parity packets
            for parity_idx, parity_byte in enumerate(parity_bytes):
                if parity_idx >= len(encoded_packets) - self.k:
                    # Create new parity packet
                    encoded_packets.append(bytearray())
                encoded_packets[self.k + parity_idx].append(parity_byte) if isinstance(encoded_packets[self.k + parity_idx], bytearray) else None
        
        # Create m parity packets by transposing parity data
        parity_packets = []
        for parity_idx in range(self.m):
            parity_packet = bytearray()
            for byte_idx in range(max_len):
                data_bytes = bytes([padded_packets[i][byte_idx] for i in range(self.k)])
                encoded = self.rs.encode(data_bytes)
                parity_packet.append(encoded[self.k + parity_idx])
            parity_packets.append(bytes(parity_packet))
        
        return list(packets) + parity_packets
    
    def decode(self, packets: List[Optional[bytes]], erasure_positions: List[int]) -> List[bytes]:
        """
        Decode packets with FEC recovery.
        
        Args:
            packets: List of k+m packets (None for lost packets)
            erasure_positions: Indices of lost packets
            
        Returns:
            Recovered k data packets
            
        Raises:
            RuntimeError: If too many packets lost to recover
        """
        if len(packets) != self.total:
            raise ValueError(f"Expected {self.total} packets, got {len(packets)}")
        
        if len(erasure_positions) > self.m:
            raise RuntimeError(
                f"Cannot recover: {len(erasure_positions)} packets lost, "
                f"FEC can only recover {self.m} losses"
            )
        
        if not erasure_positions:
            # No losses - return data packets
            return [p for p in packets[:self.k] if p is not None]
        
        # Determine packet size
        available_packets = [p for p in packets if p is not None]
        if not available_packets:
            raise RuntimeError("No packets available for recovery")
        
        packet_len = len(available_packets[0])
        
        # Decode byte-by-byte
        recovered_packets = [bytearray() for _ in range(self.k)]
        
        for byte_idx in range(packet_len):
            # Extract byte column
            encoded_bytes = []
            for i in range(self.total):
                if packets[i] is not None and byte_idx < len(packets[i]):
                    encoded_bytes.append(packets[i][byte_idx])
                else:
                    encoded_bytes.append(0)  # Placeholder for lost byte
            
            # Decode with erasure positions
            try:
                decoded = self.rs.decode(bytes(encoded_bytes), erase_pos=erasure_positions)
                # Extract data bytes (first k)
                for i in range(self.k):
                    recovered_packets[i].append(decoded[0][i])
            except reedsolo.ReedSolomonError as e:
                raise RuntimeError(f"FEC decode failed at byte {byte_idx}: {e}") from e
        
        return [bytes(p) for p in recovered_packets]
    
    def get_overhead(self) -> float:
        """
        Get FEC overhead ratio.
        
        Returns:
            Overhead as ratio (e.g., 0.5 for 50% overhead)
        """
        return self.m / self.k


class AdaptiveFEC:
    """
    Adaptive FEC that adjusts redundancy based on channel conditions.
    """
    
    def __init__(self, min_m: int = 1, max_m: int = 4, k: int = 4):
        """
        Initialize adaptive FEC.
        
        Args:
            min_m: Minimum parity packets
            max_m: Maximum parity packets
            k: Number of data packets (fixed)
        """
        self.min_m = min_m
        self.max_m = max_m
        self.k = k
        self.current_m = min_m
        self.fec = ReedSolomonFEC(k, self.current_m)
        
        # Loss tracking
        self.recent_loss_rate: float = 0.0
    
    def update_loss_rate(self, loss_rate: float):
        """
        Update loss rate estimate and adjust FEC.
        
        Args:
            loss_rate: Observed packet loss rate (0.0-1.0)
        """
        self.recent_loss_rate = loss_rate
        
        # Adjust m based on loss rate
        # Target: m > loss_rate * (k + m) to handle losses
        # Solve: m > loss_rate * k / (1 - loss_rate)
        if loss_rate > 0.01:
            target_m = int((loss_rate * self.k) / (1 - loss_rate)) + 1
            target_m = max(self.min_m, min(self.max_m, target_m))
        else:
            target_m = self.min_m
        
        if target_m != self.current_m:
            self.current_m = target_m
            self.fec = ReedSolomonFEC(self.k, self.current_m)
            print(f"[AdaptiveFEC] Adjusted m={self.current_m} for loss_rate={loss_rate:.2%}")
    
    def encode(self, packets: List[bytes]) -> List[bytes]:
        """Encode with current FEC parameters."""
        return self.fec.encode(packets)
    
    def decode(self, packets: List[Optional[bytes]], erasure_positions: List[int]) -> List[bytes]:
        """Decode with current FEC parameters."""
        return self.fec.decode(packets, erasure_positions)
