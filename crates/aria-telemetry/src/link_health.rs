//! Link Health Controller: monitors channel and advises adjustments

use aria_domain::{HomeostasisAdvice, SystemMetrics};

pub struct LinkHealthController {
    metrics: SystemMetrics,
}

impl LinkHealthController {
    pub fn new() -> Self {
        Self {
            metrics: SystemMetrics {
                packet_loss_rate: 0.0,
                latency_ms: 0.0,
                cpu_usage: 0.0,
                memory_mb: 0.0,
                bandwidth_mbps: 0.0,
            },
        }
    }
    
    pub fn update_metrics(&mut self, metrics: SystemMetrics) {
        self.metrics = metrics;
    }
    
    pub fn advise(&self) -> HomeostasisAdvice {
        let mut advice = HomeostasisAdvice {
            adjust_rate: None,
            adjust_fec: None,
            adjust_codec: None,
        };
        
        // Adapt based on conditions
        if self.metrics.packet_loss_rate > 0.1 {
            advice.adjust_fec = Some((4, 2)); // Increase FEC redundancy
        }
        
        if self.metrics.bandwidth_mbps < 1.0 {
            advice.adjust_codec = Some("LZ4".into()); // Use faster codec
        }
        
        advice
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_link_health_advises_fec() {
        let mut controller = LinkHealthController::new();
        let mut metrics = SystemMetrics {
            packet_loss_rate: 0.15,
            latency_ms: 50.0,
            cpu_usage: 30.0,
            memory_mb: 512.0,
            bandwidth_mbps: 5.0,
        };
        
        controller.update_metrics(metrics);
        let advice = controller.advise();
        
        assert!(advice.adjust_fec.is_some());
    }
}
