//! Forward Error Correction using Reed-Solomon

use aria_domain::{AriaError, AriaResult, IFEC};
use reed_solomon_erasure::galois_8::ReedSolomon;

pub struct ReedSolomonFec;

impl IFEC for ReedSolomonFec {
    fn encode(&self, data: &[u8], k: usize, m: usize) -> AriaResult<Vec<Vec<u8>>> {
        let rs = ReedSolomon::new(k, m)
            .map_err(|e| AriaError::Fec(format!("Failed to create RS encoder: {:?}", e)))?;
        
        // Calculate shard size
        let shard_size = (data.len() + k - 1) / k;
        let padded_size = shard_size * k;
        
        // Pad data
        let mut padded = data.to_vec();
        padded.resize(padded_size, 0);
        
        // Split into shards
        let mut shards: Vec<Vec<u8>> = padded
            .chunks(shard_size)
            .map(|chunk| chunk.to_vec())
            .collect();
        
        // Add empty parity shards
        for _ in 0..m {
            shards.push(vec![0u8; shard_size]);
        }
        
        // Encode
        rs.encode(&mut shards)
            .map_err(|e| AriaError::Fec(format!("Failed to encode: {:?}", e)))?;
        
        Ok(shards)
    }
    
    fn decode(&self, fragments: &[Option<Vec<u8>>], k: usize, m: usize) -> AriaResult<Vec<u8>> {
        let rs = ReedSolomon::new(k, m)
            .map_err(|e| AriaError::Fec(format!("Failed to create RS decoder: {:?}", e)))?;
        
        // Convert to format expected by reed-solomon-erasure
        let mut shards: Vec<_> = fragments
            .iter()
            .map(|opt| opt.as_ref().map(|v| v.as_slice()))
            .collect();
        
        // Reconstruct
        rs.reconstruct(&mut shards)
            .map_err(|e| AriaError::Fec(format!("Failed to reconstruct: {:?}", e)))?;
        
        // Concatenate data shards
        let data: Vec<u8> = shards[..k]
            .iter()
            .filter_map(|s| s.map(|sl| sl.to_vec()))
            .flatten()
            .collect();
        
        Ok(data)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_fec_no_loss() {
        let fec = ReedSolomonFec;
        let original = b"Hello, World! This is a test message.";
        
        let k = 4;
        let m = 2;
        let shards = fec.encode(original, k, m).unwrap();
        assert_eq!(shards.len(), k + m);
        
        // No loss: use all shards
        let fragments: Vec<Option<Vec<u8>>> = shards.into_iter().map(Some).collect();
        let decoded = fec.decode(&fragments, k, m).unwrap();
        
        assert_eq!(&decoded[..original.len()], original);
    }
    
    #[test]
    fn test_fec_with_loss() {
        let fec = ReedSolomonFec;
        let original = b"Hello, World! This is a test message.";
        
        let k = 4;
        let m = 2;
        let shards = fec.encode(original, k, m).unwrap();
        
        // Simulate loss: drop 2 shards
        let mut fragments: Vec<Option<Vec<u8>>> = shards.into_iter().map(Some).collect();
        fragments[1] = None;
        fragments[3] = None;
        
        let decoded = fec.decode(&fragments, k, m).unwrap();
        assert_eq!(&decoded[..original.len()], original);
    }
    
    #[test]
    fn test_fec_too_much_loss() {
        let fec = ReedSolomonFec;
        let original = b"Hello, World!";
        
        let k = 4;
        let m = 2;
        let shards = fec.encode(original, k, m).unwrap();
        
        // Drop too many shards (more than m)
        let mut fragments: Vec<Option<Vec<u8>>> = shards.into_iter().map(Some).collect();
        fragments[0] = None;
        fragments[1] = None;
        fragments[2] = None;
        
        let result = fec.decode(&fragments, k, m);
        assert!(result.is_err());
    }
}
