//! Stigmergy: pheromone traces

use aria_domain::{IStigmergy, Trace, BoundingBox};
use chrono::Utc;
use nalgebra::Vector3;

pub struct StigmergySystem {
    traces: Vec<Trace>,
    decay_rate: f32,
}

impl StigmergySystem {
    pub fn new(decay_rate: f32) -> Self {
        Self {
            traces: Vec::new(),
            decay_rate,
        }
    }
    
    pub fn decay(&mut self, dt: f32) {
        for trace in &mut self.traces {
            trace.intensity *= (1.0 - self.decay_rate * dt).max(0.0);
        }
        
        self.traces.retain(|t| t.intensity > 0.01);
    }
}

impl IStigmergy for StigmergySystem {
    fn leave_trace(&mut self, location: Vector3<f32>, trace_type: &str, intensity: f32) {
        self.traces.push(Trace {
            location,
            trace_type: trace_type.into(),
            intensity,
            timestamp: Utc::now(),
        });
    }
    
    fn read_traces(&self, region: &BoundingBox) -> Vec<Trace> {
        self.traces
            .iter()
            .filter(|t| {
                t.location.x >= region.min.x && t.location.x <= region.max.x &&
                t.location.y >= region.min.y && t.location.y <= region.max.y &&
                t.location.z >= region.min.z && t.location.z <= region.max.z
            })
            .cloned()
            .collect()
    }
}
