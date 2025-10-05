//! QoS: Priority queues with token bucket rate limiting

use aria_domain::{AriaResult, Envelope, IQoSShaper, Priority, QoSPolicy};
use async_trait::async_trait;
use std::collections::{HashMap, VecDeque};
use std::time::{Duration, Instant};

pub struct QoSShaper {
    queues: HashMap<Priority, PriorityQueue>,
    policies: HashMap<String, QoSPolicy>,
}

struct PriorityQueue {
    queue: VecDeque<Envelope>,
    token_bucket: TokenBucket,
    max_depth: usize,
}

struct TokenBucket {
    capacity: f32,
    tokens: f32,
    refill_rate: f32,
    last_refill: Instant,
}

impl TokenBucket {
    fn new(capacity: f32, refill_rate: f32) -> Self {
        Self {
            capacity,
            tokens: capacity,
            refill_rate,
            last_refill: Instant::now(),
        }
    }
    
    fn refill(&mut self) {
        let now = Instant::now();
        let elapsed = now.duration_since(self.last_refill).as_secs_f32();
        self.tokens = (self.tokens + elapsed * self.refill_rate).min(self.capacity);
        self.last_refill = now;
    }
    
    fn try_consume(&mut self, count: f32) -> bool {
        self.refill();
        if self.tokens >= count {
            self.tokens -= count;
            true
        } else {
            false
        }
    }
}

impl QoSShaper {
    pub fn new() -> Self {
        let mut shaper = Self {
            queues: HashMap::new(),
            policies: HashMap::new(),
        };
        
        // Default policies for each priority
        let default_policy = QoSPolicy {
            max_rate_per_sec: 1000.0,
            burst_size: 100,
            max_queue_depth: 1000,
        };
        
        for priority in [Priority::P0, Priority::P1, Priority::P2, Priority::P3] {
            shaper.queues.insert(
                priority,
                PriorityQueue {
                    queue: VecDeque::new(),
                    token_bucket: TokenBucket::new(
                        default_policy.burst_size as f32,
                        default_policy.max_rate_per_sec,
                    ),
                    max_depth: default_policy.max_queue_depth,
                },
            );
        }
        
        shaper
    }
    
    pub fn enqueue(&mut self, envelope: Envelope) -> AriaResult<()> {
        let queue = self.queues.get_mut(&envelope.priority).unwrap();
        
        if queue.queue.len() >= queue.max_depth {
            // Drop oldest if queue full (tail drop)
            queue.queue.pop_front();
        }
        
        queue.queue.push_back(envelope);
        Ok(())
    }
    
    pub fn dequeue(&mut self) -> Option<Envelope> {
        // Try priorities in order: P0 -> P1 -> P2 -> P3
        for priority in [Priority::P0, Priority::P1, Priority::P2, Priority::P3] {
            if let Some(queue) = self.queues.get_mut(&priority) {
                if queue.token_bucket.try_consume(1.0) {
                    if let Some(envelope) = queue.queue.pop_front() {
                        return Some(envelope);
                    }
                }
            }
        }
        
        None
    }
}

#[async_trait]
impl IQoSShaper for QoSShaper {
    async fn shape(&mut self, envelope: Envelope) -> AriaResult<Envelope> {
        self.enqueue(envelope.clone())?;
        
        // Immediate dequeue for simplicity; in production, use async queue
        if let Some(env) = self.dequeue() {
            Ok(env)
        } else {
            Ok(envelope)
        }
    }
    
    fn set_policy(&mut self, topic: &str, policy: QoSPolicy) {
        self.policies.insert(topic.to_string(), policy);
    }
    
    fn can_send(&self, priority: Priority) -> bool {
        self.queues.get(&priority).map_or(false, |q| !q.queue.is_empty())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use aria_domain::*;
    use chrono::Utc;
    use uuid::Uuid;
    
    fn make_envelope(priority: Priority, seq: u64) -> Envelope {
        Envelope {
            id: Uuid::new_v4(),
            timestamp: Utc::now(),
            schema_id: 1,
            priority,
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
    fn test_priority_ordering() {
        let mut shaper = QoSShaper::new();
        
        shaper.enqueue(make_envelope(Priority::P3, 1)).unwrap();
        shaper.enqueue(make_envelope(Priority::P0, 2)).unwrap();
        shaper.enqueue(make_envelope(Priority::P2, 3)).unwrap();
        
        // P0 should come first
        let first = shaper.dequeue().unwrap();
        assert_eq!(first.priority, Priority::P0);
    }
    
    #[test]
    fn test_token_bucket() {
        let mut bucket = TokenBucket::new(10.0, 5.0);
        
        assert!(bucket.try_consume(5.0));
        assert!(bucket.try_consume(5.0));
        assert!(!bucket.try_consume(1.0)); // Exhausted
        
        std::thread::sleep(Duration::from_millis(200));
        bucket.refill();
        assert!(bucket.try_consume(1.0)); // Refilled
    }
    
    #[test]
    fn test_queue_depth_limit() {
        let mut shaper = QoSShaper::new();
        
        // Set low depth for testing
        shaper.queues.get_mut(&Priority::P3).unwrap().max_depth = 5;
        
        // Enqueue more than max
        for i in 0..10 {
            shaper.enqueue(make_envelope(Priority::P3, i)).unwrap();
        }
        
        let queue = &shaper.queues[&Priority::P3];
        assert_eq!(queue.queue.len(), 5);
    }
}
