"""
ARIA SDK - Telemetry Compression Module

Provides LZ4 and Zstd compression for telemetry payloads.
"""

from typing import Optional
import lz4.frame
import zstandard as zstd

from aria_sdk.domain.protocols import ICompressor


class Lz4Compressor(ICompressor):
    """
    LZ4 compression - optimized for speed and low latency.
    
    Best for: Real-time telemetry, high-frequency sensors
    Compression ratio: ~2-3x
    Speed: Very fast (~500 MB/s)
    """
    
    def __init__(self, level: int = 0):
        """
        Initialize LZ4 compressor.
        
        Args:
            level: Compression level (0-16). 0=fast, 16=max compression
        """
        self.level = level
    
    def compress(self, data: bytes) -> bytes:
        """
        Compress data using LZ4.
        
        Args:
            data: Raw bytes to compress
            
        Returns:
            Compressed bytes
            
        Raises:
            RuntimeError: If compression fails
        """
        try:
            return lz4.frame.compress(
                data,
                compression_level=self.level,
                block_size=lz4.frame.BLOCKSIZE_MAX1MB,
            )
        except Exception as e:
            raise RuntimeError(f"LZ4 compression failed: {e}") from e
    
    def decompress(self, data: bytes) -> bytes:
        """
        Decompress LZ4 data.
        
        Args:
            data: Compressed bytes
            
        Returns:
            Decompressed bytes
            
        Raises:
            RuntimeError: If decompression fails
        """
        try:
            return lz4.frame.decompress(data)
        except Exception as e:
            raise RuntimeError(f"LZ4 decompression failed: {e}") from e


class ZstdCompressor(ICompressor):
    """
    Zstandard compression - balanced speed and compression ratio.
    
    Best for: Batch telemetry, recorded data, archival
    Compression ratio: ~3-5x
    Speed: Fast (~250 MB/s)
    """
    
    def __init__(self, level: int = 3):
        """
        Initialize Zstd compressor.
        
        Args:
            level: Compression level (1-22). 3=default, 22=max compression
        """
        self.level = max(1, min(22, level))
        self.cctx = zstd.ZstdCompressor(level=self.level)
        self.dctx = zstd.ZstdDecompressor()
    
    def compress(self, data: bytes) -> bytes:
        """
        Compress data using Zstd.
        
        Args:
            data: Raw bytes to compress
            
        Returns:
            Compressed bytes
            
        Raises:
            RuntimeError: If compression fails
        """
        try:
            return self.cctx.compress(data)
        except Exception as e:
            raise RuntimeError(f"Zstd compression failed: {e}") from e
    
    def decompress(self, data: bytes) -> bytes:
        """
        Decompress Zstd data.
        
        Args:
            data: Compressed bytes
            
        Returns:
            Decompressed bytes
            
        Raises:
            RuntimeError: If decompression fails
        """
        try:
            return self.dctx.decompress(data)
        except Exception as e:
            raise RuntimeError(f"Zstd decompression failed: {e}") from e


def get_compressor(algo: str, level: Optional[int] = None) -> ICompressor:
    """
    Factory function to create compressor instances.
    
    Args:
        algo: Compression algorithm ('lz4' or 'zstd')
        level: Compression level (None=default)
        
    Returns:
        Compressor instance
        
    Raises:
        ValueError: If algorithm is unknown
    """
    algo = algo.lower()
    
    if algo == 'lz4':
        return Lz4Compressor(level if level is not None else 0)
    elif algo == 'zstd':
        return ZstdCompressor(level if level is not None else 3)
    else:
        raise ValueError(f"Unknown compression algorithm: {algo}. Use 'lz4' or 'zstd'")
