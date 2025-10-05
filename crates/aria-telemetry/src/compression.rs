//! Compression implementations (LZ4, Zstd)

use aria_domain::{AriaError, AriaResult, ICompressor};

pub struct Lz4Compressor {
    level: u32,
}

impl Lz4Compressor {
    pub fn new(level: u32) -> Self {
        Self { level }
    }
}

impl ICompressor for Lz4Compressor {
    fn compress(&self, data: &[u8]) -> AriaResult<Vec<u8>> {
        lz4::block::compress(data, Some(lz4::block::CompressionMode::FAST(self.level as i32)), false)
            .map_err(|e| AriaError::Compression(e.to_string()))
    }
    
    fn decompress(&self, data: &[u8]) -> AriaResult<Vec<u8>> {
        lz4::block::decompress(data, None)
            .map_err(|e| AriaError::Compression(e.to_string()))
    }
    
    fn name(&self) -> &str {
        "LZ4"
    }
}

pub struct ZstdCompressor {
    level: i32,
}

impl ZstdCompressor {
    pub fn new(level: i32) -> Self {
        Self { level }
    }
}

impl ICompressor for ZstdCompressor {
    fn compress(&self, data: &[u8]) -> AriaResult<Vec<u8>> {
        zstd::encode_all(data, self.level)
            .map_err(|e| AriaError::Compression(e.to_string()))
    }
    
    fn decompress(&self, data: &[u8]) -> AriaResult<Vec<u8>> {
        zstd::decode_all(data)
            .map_err(|e| AriaError::Compression(e.to_string()))
    }
    
    fn name(&self) -> &str {
        "Zstd"
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_lz4_roundtrip() {
        let compressor = Lz4Compressor::new(1);
        let original = b"Hello, World! This is a test message that should compress well.";
        let compressed = compressor.compress(original).unwrap();
        let decompressed = compressor.decompress(&compressed).unwrap();
        assert_eq!(original.as_slice(), decompressed.as_slice());
    }
    
    #[test]
    fn test_zstd_roundtrip() {
        let compressor = ZstdCompressor::new(3);
        let original = b"Hello, World! This is a test message that should compress well.";
        let compressed = compressor.compress(original).unwrap();
        let decompressed = compressor.decompress(&compressed).unwrap();
        assert_eq!(original.as_slice(), decompressed.as_slice());
    }
    
    #[test]
    fn test_compression_ratio() {
        let compressor = ZstdCompressor::new(9);
        let original = vec![0u8; 1024]; // Highly compressible
        let compressed = compressor.compress(&original).unwrap();
        assert!(compressed.len() < original.len());
    }
}
