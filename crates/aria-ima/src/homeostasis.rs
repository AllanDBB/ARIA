//! Homeostasis

use aria_domain::{IHomeostasis, SystemMetrics, HomeostasisAdvice};

pub struct HomeostasisController {
    target_latency: f32,
    target_loss_rate: f32,
}

impl HomeostasisController {
    pub fn new() -> Self {
        Self {
            target_latency: 50.0,
            target_loss_rate: 0.05,
        }
    }
}

impl IHomeostasis for HomeostasisController {
    fn advise(&mut self, metrics: &SystemMetrics) -> HomeostasisAdvice {
        let mut advice = HomeostasisAdvice {
            adjust_rate: None,
            adjust_fec: None,
            adjust_codec: None,
        };
        
        if metrics.latency_ms > self.target_latency * 1.5 {
            advice.adjust_rate = Some(0.8); // Reduce rate
            advice.adjust_codec = Some("LZ4".into()); // Faster codec
        }
        
        if metrics.packet_loss_rate > self.target_loss_rate {
            advice.adjust_fec = Some((4, 2)); // More redundancy
        }
        
        advice
    }
}
