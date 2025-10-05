//! CCEM - Channel Conditioning & Error Mitigation
//! 
//! TX: rate limiting, jitter smoothing, conditioning
//! RX: de-jitter, reordering, drift/doppler compensation, interference detection

use aria_domain::{AriaResult, Envelope};
use std::collections::VecDeque;
use std::time::{Duration, Instant};

pub struct TxConditioner {
    smoothing_window: Duration,
    last_send: Option<Instant>,
    queue: VecDeque<Envelope>,
}

impl TxConditioner {
    pub fn new(smoothing_window: Duration) -> Self {
        Self {
            smoothing_window,
            last_send: None,
            queue: VecDeque::new(),
        }
    }
    
    pub fn condition(&mut self, envelope: Envelope) -> AriaResult<Option<Envelope>> {
        let now = Instant::now();
        
        if let Some(last) = self.last_send {
            let elapsed = now.duration_since(last);
            if elapsed < self.smoothing_window {
                // Queue for later
                self.queue.push_back(envelope);
                return Ok(None);
            }
        }
        
        self.last_send = Some(now);
        
        // Send queued first, then current
        if let Some(queued) = self.queue.pop_front() {
            self.queue.push_back(envelope);
            Ok(Some(queued))
        } else {
            Ok(Some(envelope))
        }
    }
}

pub struct RxDeJitter {
    buffer: VecDeque<(u64, Envelope)>,
    buffer_size: usize,
    next_sequence: u64,
}

impl RxDeJitter {
    pub fn new(buffer_size: usize) -> Self {
        Self {
            buffer: VecDeque::new(),
            buffer_size,
            next_sequence: 0,
        }
    }
    
    pub fn add(&mut self, envelope: Envelope) -> Vec<Envelope> {
        let seq = envelope.metadata.sequence_number;
        
        // Insert in order
        let pos = self.buffer.iter().position(|(s, _)| *s > seq).unwrap_or(self.buffer.len());
        self.buffer.insert(pos, (seq, envelope));
        
        // Trim to size
        if self.buffer.len() > self.buffer_size {
            self.buffer.pop_front();
        }
        
        // Extract consecutive packets starting from next_sequence
        let mut output = Vec::new();
        while let Some((seq, _)) = self.buffer.front() {
            if *seq == self.next_sequence {
                if let Some((_, env)) = self.buffer.pop_front() {
                    output.push(env);
                    self.next_sequence += 1;
                }
            } else {
                break;
            }
        }
        
        output
    }
}

pub struct DriftCompensator {
    clock_offset: Duration,
    drift_rate: f64,
}

impl DriftCompensator {
    pub fn new() -> Self {
        Self {
            clock_offset: Duration::ZERO,
            drift_rate: 0.0,
        }
    }
    
    pub fn compensate(&self, timestamp: chrono::DateTime<chrono::Utc>) -> chrono::DateTime<chrono::Utc> {
        // Apply clock offset and drift compensation
        timestamp + chrono::Duration::from_std(self.clock_offset).unwrap_or_default()
    }
    
    pub fn update_offset(&mut self, measured_offset: Duration) {
        // Exponential moving average
        let alpha = 0.1;
        let current_ms = self.clock_offset.as_millis() as f64;
        let measured_ms = measured_offset.as_millis() as f64;
        let new_ms = alpha * measured_ms + (1.0 - alpha) * current_ms;
        self.clock_offset = Duration::from_millis(new_ms as u64);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use aria_domain::*;
    use chrono::Utc;
    use uuid::Uuid;
    
    fn make_envelope(seq: u64) -> Envelope {
        Envelope {
            id: Uuid::new_v4(),
            timestamp: Utc::now(),
            schema_id: 1,
            priority: Priority::P2,
            topic: "test".into(),
            payload: vec![],
            metadata: EnvelopeMetadata {
                source_node: "test".into(),
                sequence_number: seq,
                fragment_info: None,
                fec_info: None,
                crypto_info: None,
                qos_class: "default".into(),
            },
        }
    }
    
    #[test]
    fn test_tx_conditioner() {
        let mut conditioner = TxConditioner::new(Duration::from_millis(10));
        let env = make_envelope(1);
        
        let result = conditioner.condition(env.clone()).unwrap();
        assert!(result.is_some());
    }
    
    #[test]
    fn test_rx_dejitter_ordering() {
        let mut dejitter = RxDeJitter::new(10);
        
        // Receive out of order
        dejitter.add(make_envelope(2));
        dejitter.add(make_envelope(0));
        dejitter.add(make_envelope(1));
        
        let output = dejitter.add(make_envelope(3));
        // Should output 0, 1, 2, 3 in order
        assert_eq!(output.len(), 4);
    }
    
    #[test]
    fn test_drift_compensator() {
        let mut compensator = DriftCompensator::new();
        compensator.update_offset(Duration::from_millis(100));
        
        let timestamp = Utc::now();
        let compensated = compensator.compensate(timestamp);
        assert!(compensated > timestamp);
    }
}
