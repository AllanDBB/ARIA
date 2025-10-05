//! World Model: spatial/temporal state representation

use aria_domain::{IWorldModel, Observation, Entity, Belief, BoundingBox, Pose};
use std::collections::HashMap;
use chrono::{DateTime, Utc};

pub struct WorldModel {
    entities: HashMap<String, EntityState>,
}

struct EntityState {
    entity: Entity,
    belief: Belief,
    history: Vec<Observation>,
}

impl WorldModel {
    pub fn new() -> Self {
        Self {
            entities: HashMap::new(),
        }
    }
}

impl IWorldModel for WorldModel {
    fn update(&mut self, observation: Observation) {
        for entity in observation.entities {
            let state = self.entities.entry(entity.id.clone()).or_insert_with(|| {
                EntityState {
                    entity: entity.clone(),
                    belief: Belief {
                        entity_id: entity.id.clone(),
                        pose: entity.pose.clone(),
                        uncertainty: 1.0,
                        last_seen: observation.timestamp,
                    },
                    history: Vec::new(),
                }
            });
            
            state.entity = entity.clone();
            state.belief.pose = entity.pose;
            state.belief.last_seen = observation.timestamp;
            state.belief.uncertainty *= 0.9; // Reduce uncertainty with observation
            state.history.push(observation.clone());
        }
    }
    
    fn query_region(&self, bbox: &BoundingBox) -> Vec<Entity> {
        self.entities
            .values()
            .filter(|state| {
                let pos = &state.entity.pose.position;
                pos.x >= bbox.min.x && pos.x <= bbox.max.x &&
                pos.y >= bbox.min.y && pos.y <= bbox.max.y &&
                pos.z >= bbox.min.z && pos.z <= bbox.max.z
            })
            .map(|state| state.entity.clone())
            .collect()
    }
    
    fn get_belief(&self, entity_id: &str) -> Option<Belief> {
        self.entities.get(entity_id).map(|state| state.belief.clone())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use nalgebra::{Vector3, UnitQuaternion};
    
    #[test]
    fn test_world_model_update() {
        let mut world = WorldModel::new();
        
        let entity = Entity {
            id: "obj1".into(),
            class_name: "person".into(),
            pose: Pose {
                position: Vector3::new(1.0, 2.0, 0.0),
                orientation: UnitQuaternion::identity(),
                covariance: None,
            },
            properties: HashMap::new(),
        };
        
        let obs = Observation {
            timestamp: Utc::now(),
            source: "camera".into(),
            entities: vec![entity.clone()],
        };
        
        world.update(obs);
        assert!(world.get_belief("obj1").is_some());
    }
}
