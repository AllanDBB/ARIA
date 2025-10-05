//! Delta encoding for sequential data compression

use aria_domain::{AriaError, AriaResult, IDeltaCodec};

pub struct SimpleDeltaCodec {
    previous: Option<Vec<u8>>,
}

impl SimpleDeltaCodec {
    pub fn new() -> Self {
        Self { previous: None }
    }
}

impl IDeltaCodec for SimpleDeltaCodec {
    fn encode(&mut self, current: &[u8], previous: Option<&[u8]>) -> AriaResult<Vec<u8>> {
        match previous.or(self.previous.as_deref()) {
            Some(prev) => {
                // Simple XOR delta
                let delta: Vec<u8> = current
                    .iter()
                    .zip(prev.iter().chain(std::iter::repeat(&0)))
                    .map(|(c, p)| c ^ p)
                    .collect();
                
                self.previous = Some(current.to_vec());
                Ok(delta)
            }
            None => {
                // First frame: no delta, send as-is
                self.previous = Some(current.to_vec());
                Ok(current.to_vec())
            }
        }
    }
    
    fn decode(&mut self, delta: &[u8], previous: Option<&[u8]>) -> AriaResult<Vec<u8>> {
        match previous.or(self.previous.as_deref()) {
            Some(prev) => {
                let current: Vec<u8> = delta
                    .iter()
                    .zip(prev.iter().chain(std::iter::repeat(&0)))
                    .map(|(d, p)| d ^ p)
                    .collect();
                
                self.previous = Some(current.clone());
                Ok(current)
            }
            None => {
                // First frame
                self.previous = Some(delta.to_vec());
                Ok(delta.to_vec())
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_delta_roundtrip() {
        let mut encoder = SimpleDeltaCodec::new();
        let mut decoder = SimpleDeltaCodec::new();
        
        let frame1 = b"Hello World";
        let frame2 = b"Hello Rust!";
        
        let delta1 = encoder.encode(frame1, None).unwrap();
        let delta2 = encoder.encode(frame2, None).unwrap();
        
        let decoded1 = decoder.decode(&delta1, None).unwrap();
        let decoded2 = decoder.decode(&delta2, None).unwrap();
        
        assert_eq!(frame1.as_slice(), decoded1.as_slice());
        assert_eq!(frame2.as_slice(), decoded2.as_slice());
    }
    
    #[test]
    fn test_delta_compression() {
        let mut codec = SimpleDeltaCodec::new();
        
        let frame1 = vec![1, 2, 3, 4, 5];
        let frame2 = vec![1, 2, 3, 4, 6]; // Only last byte changed
        
        let delta1 = codec.encode(&frame1, None).unwrap();
        let delta2 = codec.encode(&frame2, None).unwrap();
        
        // Delta should reflect only the change
        assert_eq!(delta1, frame1); // First is full
        assert!(delta2.iter().take(4).all(|&b| b == 0)); // First 4 bytes are same
    }
}
