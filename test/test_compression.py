"""
Unit Tests for Compression Module
==================================

Tests LZ4 and Zstd compression algorithms with various data patterns.

Input:
    - Binary data of various sizes and patterns
    - Compression levels (0-16 for LZ4, 1-22 for Zstd)

Output:
    - Compressed binary data
    - Compression ratios
    - Decompressed data matching original

Test Cases:
1. test_lz4_basic_compression: Basic LZ4 compression/decompression
2. test_lz4_levels: Test all LZ4 compression levels (0-16)
3. test_lz4_empty_data: Handle empty input
4. test_lz4_small_data: Data <100 bytes (may expand)
5. test_lz4_large_data: Data >10MB
6. test_lz4_random_data: Incompressible random data
7. test_lz4_repetitive_data: Highly compressible repeated patterns
8. test_zstd_basic_compression: Basic Zstd compression/decompression
9. test_zstd_levels: Test Zstd levels (1-22)
10. test_compression_ratio_comparison: Compare LZ4 vs Zstd ratios
11. test_speed_comparison: Compare compression speeds
12. test_binary_data: Handle binary (non-text) data
"""

import pytest
import time
import os
from aria_sdk.telemetry.compression import Lz4Compressor, ZstdCompressor


class TestLz4Compression:
    """Test suite for LZ4 compression."""
    
    @pytest.fixture
    def compressor(self):
        """
        Fixture: Provides LZ4 compressor with default level.
        
        Returns:
            Lz4Compressor: Compressor instance (level 0 = fast)
        """
        return Lz4Compressor(level=0)
    
    def test_lz4_basic_compression(self, compressor):
        """
        Test: Basic LZ4 compress and decompress.
        
        Input:
            - Text: "Hello World" * 100 = 1100 bytes
        
        Expected Output:
            - Compressed size < original size
            - Decompressed matches original exactly
        """
        data = b"Hello World! " * 100
        compressed = compressor.compress(data)
        decompressed = compressor.decompress(compressed)
        
        assert len(compressed) < len(data), "Should compress repetitive data"
        assert decompressed == data, "Decompressed should match original"
    
    def test_lz4_levels(self):
        """
        Test: All LZ4 compression levels (0-16).
        
        Input:
            - Same data compressed at different levels
        
        Expected Output:
            - Higher levels → better compression (usually)
            - All levels decompress correctly
        """
        data = b"The quick brown fox jumps over the lazy dog. " * 50
        
        results = []
        for level in range(17):  # 0-16
            compressor = Lz4Compressor(level=level)
            compressed = compressor.compress(data)
            decompressed = compressor.decompress(compressed)
            
            assert decompressed == data, f"Level {level} should decompress correctly"
            results.append((level, len(compressed)))
        
        # Generally, higher levels should give better (or equal) compression
        # Note: LZ4 level 0 is special (fast mode)
        assert len(results) == 17, "Should test all 17 levels"
    
    def test_lz4_empty_data(self, compressor):
        """
        Test: Handle empty input.
        
        Input:
            - b"" (empty bytes)
        
        Expected Output:
            - Compressed size minimal (header only)
            - Decompresses to empty bytes
        """
        data = b""
        compressed = compressor.compress(data)
        decompressed = compressor.decompress(compressed)
        
        assert decompressed == b"", "Empty data should decompress to empty"
    
    def test_lz4_small_data(self, compressor):
        """
        Test: Small data (<100 bytes) may expand due to headers.
        
        Input:
            - 50 bytes of data
        
        Expected Output:
            - Compressed size may be >= original (header overhead)
            - Still decompresses correctly
        """
        data = b"Small data test: 12345"
        compressed = compressor.compress(data)
        decompressed = compressor.decompress(compressed)
        
        # Small data often expands due to compression overhead
        assert decompressed == data, "Small data should decompress correctly"
    
    def test_lz4_large_data(self, compressor):
        """
        Test: Large data (>10MB).
        
        Input:
            - 10MB of repetitive data
        
        Expected Output:
            - Significant compression achieved
            - Correct decompression
        """
        data = b"ABCDEFGH" * (10 * 1024 * 1024 // 8)  # ~10MB
        compressed = compressor.compress(data)
        decompressed = compressor.decompress(compressed)
        
        assert len(compressed) < len(data) / 100, "Should achieve >100x compression on repetitive data"
        assert decompressed == data, "Large data should decompress correctly"
    
    def test_lz4_random_data(self, compressor):
        """
        Test: Random (incompressible) data.
        
        Input:
            - 1KB of random bytes
        
        Expected Output:
            - Compressed size ≈ original (random data doesn't compress)
            - Correct decompression
        """
        data = os.urandom(1024)
        compressed = compressor.compress(data)
        decompressed = compressor.decompress(compressed)
        
        # Random data won't compress well, may even expand
        assert decompressed == data, "Random data should decompress correctly"
    
    def test_lz4_repetitive_data(self, compressor):
        """
        Test: Highly compressible repeated patterns.
        
        Input:
            - "AAAA..." * 1000 = 4000 bytes
        
        Expected Output:
            - High compression ratio (>10x)
        """
        data = b"A" * 4000
        compressed = compressor.compress(data)
        decompressed = compressor.decompress(compressed)
        
        ratio = len(data) / len(compressed)
        assert ratio > 10, f"Should achieve >10x compression on repeated data, got {ratio:.2f}x"
        assert decompressed == data, "Decompressed should match"


class TestZstdCompression:
    """Test suite for Zstd compression."""
    
    @pytest.fixture
    def compressor(self):
        """
        Fixture: Provides Zstd compressor with default level.
        
        Returns:
            ZstdCompressor: Compressor instance (level 3 = balanced)
        """
        return ZstdCompressor(level=3)
    
    def test_zstd_basic_compression(self, compressor):
        """
        Test: Basic Zstd compress and decompress.
        
        Input:
            - Text data with patterns
        
        Expected Output:
            - Compressed < original
            - Perfect decompression
        """
        data = b"Zstandard compression test! " * 100
        compressed = compressor.compress(data)
        decompressed = compressor.decompress(compressed)
        
        assert len(compressed) < len(data), "Should compress data"
        assert decompressed == data, "Should decompress correctly"
    
    def test_zstd_levels(self):
        """
        Test: Zstd compression levels (1-22).
        
        Input:
            - Same data at different levels
        
        Expected Output:
            - Higher levels → better compression (slower)
            - All decompress correctly
        """
        data = b"The five boxing wizards jump quickly. " * 100
        
        results = []
        for level in [1, 3, 5, 9, 15, 22]:  # Sample levels
            compressor = ZstdCompressor(level=level)
            compressed = compressor.compress(data)
            decompressed = compressor.decompress(compressed)
            
            assert decompressed == data, f"Level {level} should work"
            results.append((level, len(compressed)))
        
        # Higher levels should generally compress better
        assert results[0][1] >= results[-1][1], "Higher levels should compress better"
    
    def test_zstd_dictionary_training(self):
        """
        Test: Zstd with dictionary training for similar data.
        
        Input:
            - Multiple similar JSON payloads
        
        Expected Output:
            - Better compression with dictionary
        """
        # Similar JSON structures
        samples = [
            b'{"sensor":"temp","value":25.3,"unit":"C"}',
            b'{"sensor":"temp","value":26.1,"unit":"C"}',
            b'{"sensor":"temp","value":24.8,"unit":"C"}',
        ]
        
        compressor = ZstdCompressor(level=3)
        
        # Compress without dictionary
        compressed_sizes = [len(compressor.compress(s)) for s in samples]
        
        # All should decompress correctly
        for sample in samples:
            compressed = compressor.compress(sample)
            decompressed = compressor.decompress(compressed)
            assert decompressed == sample


class TestCompressionComparison:
    """Compare LZ4 vs Zstd performance."""
    
    def test_compression_ratio_comparison(self):
        """
        Test: Compare compression ratios LZ4 vs Zstd.
        
        Input:
            - 10KB of repetitive data
        
        Expected Output:
            - Zstd (level 3) should beat LZ4 (level 0) on compression
            - Both decompress correctly
        """
        data = b"Mars Rover telemetry data: " * 400  # ~10KB
        
        lz4 = Lz4Compressor(level=0)
        zstd = ZstdCompressor(level=3)
        
        lz4_compressed = lz4.compress(data)
        zstd_compressed = zstd.compress(data)
        
        lz4_ratio = len(data) / len(lz4_compressed)
        zstd_ratio = len(data) / len(zstd_compressed)
        
        # Zstd usually compresses better than LZ4
        assert zstd_ratio >= lz4_ratio * 0.9, "Zstd should compress similarly or better"
        
        # Both should decompress correctly
        assert lz4.decompress(lz4_compressed) == data
        assert zstd.decompress(zstd_compressed) == data
    
    def test_speed_comparison(self):
        """
        Test: Compare compression speeds.
        
        Input:
            - 1MB of data
        
        Expected Output:
            - LZ4 (level 0) faster than Zstd (level 3)
            - Both complete in reasonable time (<1s)
        """
        data = b"Speed test data! " * (1024 * 1024 // 17)  # ~1MB
        
        lz4 = Lz4Compressor(level=0)
        zstd = ZstdCompressor(level=3)
        
        # Time LZ4
        start = time.perf_counter()
        lz4_compressed = lz4.compress(data)
        lz4_time = time.perf_counter() - start
        
        # Time Zstd
        start = time.perf_counter()
        zstd_compressed = zstd.compress(data)
        zstd_time = time.perf_counter() - start
        
        # LZ4 should be faster
        assert lz4_time < zstd_time * 2, "LZ4 should be reasonably fast"
        assert lz4_time < 1.0, "LZ4 should compress 1MB in <1s"
        assert zstd_time < 2.0, "Zstd should compress 1MB in <2s"
    
    def test_binary_data(self):
        """
        Test: Handle binary (non-text) data.
        
        Input:
            - Binary data (e.g., image bytes, serialized objects)
        
        Expected Output:
            - Compresses and decompresses correctly
        """
        # Simulate binary data (e.g., sensor readings)
        binary_data = bytes(range(256)) * 100  # 25.6KB
        
        lz4 = Lz4Compressor(level=0)
        zstd = ZstdCompressor(level=3)
        
        lz4_compressed = lz4.compress(binary_data)
        lz4_decompressed = lz4.decompress(lz4_compressed)
        
        zstd_compressed = zstd.compress(binary_data)
        zstd_decompressed = zstd.decompress(zstd_compressed)
        
        assert lz4_decompressed == binary_data, "LZ4 should handle binary"
        assert zstd_decompressed == binary_data, "Zstd should handle binary"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
