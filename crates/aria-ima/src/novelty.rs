//! Novelty Detection

use aria_domain::{INoveltyDetector, Observation};
use std::collections::HashMap;

pub struct NoveltyDetector {
    seen_classes: HashMap<String, usize>,
}

impl NoveltyDetector {
    pub fn new() -> Self {
        Self {
            seen_classes: HashMap::new(),
        }
    }
}

impl INoveltyDetector for NoveltyDetector {
    fn compute_novelty(&mut self, observation: &Observation) -> f32 {
        let mut novelty = 0.0;
        
        for entity in &observation.entities {
            let count = self.seen_classes.entry(entity.class_name.clone()).or_insert(0);
            
            // Novelty decreases with frequency
            novelty += 1.0 / (*count as f32 + 1.0);
            *count += 1;
        }
        
        novelty / observation.entities.len().max(1) as f32
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use aria_domain::*;
    use chrono::Utc;
    use nalgebra::{Vector3, UnitQuaternion};
    
    #[test]
    fn test_novelty_decreases() {
        let mut detector = NoveltyDetector::new();
        
        let entity = Entity {
            id: "e1".into(),
            class_name: "person".into(),
            pose: Pose {
                position: Vector3::zeros(),
                orientation: UnitQuaternion::identity(),
                covariance: None,
            },
            properties: std::collections::HashMap::new(),
        };
        
        let obs = Observation {
            timestamp: Utc::now(),
            source: "cam".into(),
            entities: vec![entity.clone()],
        };
        
        let nov1 = detector.compute_novelty(&obs);
        let nov2 = detector.compute_novelty(&obs);
        
        assert!(nov1 > nov2);
    }
}
