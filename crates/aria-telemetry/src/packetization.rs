//! Packetization: fragmentation and defragmentation

use aria_domain::{AriaError, AriaResult, Envelope, FragmentInfo};
use std::collections::HashMap;
use std::time::{Duration, Instant};

const DEFAULT_MTU: usize = 1400;

pub struct Packetizer {
    mtu: usize,
}

impl Packetizer {
    pub fn new(mtu: usize) -> Self {
        Self { mtu }
    }
    
    pub fn fragment(&self, mut envelope: Envelope) -> AriaResult<Vec<Envelope>> {
        let payload_size = envelope.payload.len();
        
        if payload_size <= self.mtu {
            // No fragmentation needed
            return Ok(vec![envelope]);
        }
        
        let num_fragments = (payload_size + self.mtu - 1) / self.mtu;
        let mut fragments = Vec::with_capacity(num_fragments);
        
        for i in 0..num_fragments {
            let start = i * self.mtu;
            let end = std::cmp::min(start + self.mtu, payload_size);
            let fragment_payload = envelope.payload[start..end].to_vec();
            
            let mut fragment = envelope.clone();
            fragment.id = uuid::Uuid::new_v4();
            fragment.payload = fragment_payload;
            fragment.metadata.fragment_info = Some(FragmentInfo {
                fragment_id: i as u32,
                total_fragments: num_fragments as u32,
                fragment_offset: start,
            });
            
            fragments.push(fragment);
        }
        
        Ok(fragments)
    }
}

pub struct Defragmenter {
    buffers: HashMap<uuid::Uuid, FragmentBuffer>,
    timeout: Duration,
}

struct FragmentBuffer {
    fragments: HashMap<u32, Vec<u8>>,
    total_fragments: u32,
    original_envelope: Envelope,
    last_update: Instant,
}

impl Defragmenter {
    pub fn new(timeout: Duration) -> Self {
        Self {
            buffers: HashMap::new(),
            timeout,
        }
    }
    
    pub fn add_fragment(&mut self, envelope: Envelope) -> Option<Envelope> {
        let frag_info = match &envelope.metadata.fragment_info {
            Some(info) => info,
            None => return Some(envelope), // Not a fragment
        };
        
        let parent_id = envelope.id;
        
        let buffer = self.buffers.entry(parent_id).or_insert_with(|| {
            FragmentBuffer {
                fragments: HashMap::new(),
                total_fragments: frag_info.total_fragments,
                original_envelope: envelope.clone(),
                last_update: Instant::now(),
            }
        });
        
        buffer.fragments.insert(frag_info.fragment_id, envelope.payload);
        buffer.last_update = Instant::now();
        
        // Check if we have all fragments
        if buffer.fragments.len() == buffer.total_fragments as usize {
            // Reassemble
            let mut payload = Vec::new();
            for i in 0..buffer.total_fragments {
                if let Some(frag) = buffer.fragments.get(&i) {
                    payload.extend_from_slice(frag);
                }
            }
            
            let mut complete = buffer.original_envelope.clone();
            complete.payload = payload;
            complete.metadata.fragment_info = None;
            
            self.buffers.remove(&parent_id);
            return Some(complete);
        }
        
        None
    }
    
    pub fn gc_expired(&mut self) {
        let now = Instant::now();
        self.buffers.retain(|_, buffer| {
            now.duration_since(buffer.last_update) < self.timeout
        });
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use aria_domain::*;
    use chrono::Utc;
    
    fn make_envelope(size: usize) -> Envelope {
        Envelope {
            id: uuid::Uuid::new_v4(),
            timestamp: Utc::now(),
            schema_id: 1,
            priority: Priority::P2,
            topic: "test".into(),
            payload: vec![0u8; size],
            metadata: EnvelopeMetadata {
                source_node: "test".into(),
                sequence_number: 0,
                fragment_info: None,
                fec_info: None,
                crypto_info: None,
                qos_class: "default".into(),
            },
        }
    }
    
    #[test]
    fn test_no_fragmentation() {
        let packetizer = Packetizer::new(1400);
        let envelope = make_envelope(1000);
        
        let fragments = packetizer.fragment(envelope.clone()).unwrap();
        assert_eq!(fragments.len(), 1);
        assert_eq!(fragments[0].payload.len(), 1000);
    }
    
    #[test]
    fn test_fragmentation() {
        let packetizer = Packetizer::new(1400);
        let envelope = make_envelope(3000);
        
        let fragments = packetizer.fragment(envelope).unwrap();
        assert_eq!(fragments.len(), 3);
        assert_eq!(fragments[0].payload.len(), 1400);
        assert_eq!(fragments[1].payload.len(), 1400);
        assert_eq!(fragments[2].payload.len(), 200);
    }
    
    #[test]
    fn test_defragmentation() {
        let packetizer = Packetizer::new(1400);
        let mut defragmenter = Defragmenter::new(Duration::from_secs(10));
        
        let original = make_envelope(3000);
        let original_payload = original.payload.clone();
        
        let fragments = packetizer.fragment(original).unwrap();
        
        // Add fragments in order
        for (i, frag) in fragments.iter().enumerate() {
            let result = defragmenter.add_fragment(frag.clone());
            if i < fragments.len() - 1 {
                assert!(result.is_none());
            } else {
                let complete = result.unwrap();
                assert_eq!(complete.payload, original_payload);
            }
        }
    }
    
    #[test]
    fn test_defragmentation_out_of_order() {
        let packetizer = Packetizer::new(1400);
        let mut defragmenter = Defragmenter::new(Duration::from_secs(10));
        
        let original = make_envelope(3000);
        let original_payload = original.payload.clone();
        
        let fragments = packetizer.fragment(original).unwrap();
        
        // Add fragments out of order
        let result1 = defragmenter.add_fragment(fragments[2].clone());
        assert!(result1.is_none());
        
        let result2 = defragmenter.add_fragment(fragments[0].clone());
        assert!(result2.is_none());
        
        let result3 = defragmenter.add_fragment(fragments[1].clone());
        assert!(result3.is_some());
        
        let complete = result3.unwrap();
        assert_eq!(complete.payload, original_payload);
    }
}
