//! Action Synthesizer

use aria_domain::{IActionSynthesizer, AriaResult, Command, State, ActuatorAction, AriaError};
use chrono::Utc;
use uuid::Uuid;
use nalgebra::Vector3;
use std::collections::HashMap;

pub struct ActionSynthesizer;

impl ActionSynthesizer {
    pub fn new() -> Self {
        Self
    }
}

impl IActionSynthesizer for ActionSynthesizer {
    fn synthesize(&self, skill_name: &str, parameters: &HashMap<String, f32>, state: &State) -> AriaResult<Command> {
        let action = match skill_name {
            "navigate" => {
                let vx = parameters.get("vx").copied().unwrap_or(0.0);
                let vy = parameters.get("vy").copied().unwrap_or(0.0);
                let wz = parameters.get("wz").copied().unwrap_or(0.0);
                
                ActuatorAction::Motion {
                    velocity: Vector3::new(vx, vy, 0.0),
                    angular: Vector3::new(0.0, 0.0, wz),
                }
            },
            "stop" => ActuatorAction::Motion {
                velocity: Vector3::zeros(),
                angular: Vector3::zeros(),
            },
            _ => return Err(AriaError::Planning(format!("Unknown skill: {}", skill_name))),
        };
        
        Ok(Command {
            id: Uuid::new_v4(),
            timestamp: Utc::now(),
            actuator_id: "base".into(),
            action,
            justification: Some(format!("Skill: {}", skill_name)),
        })
    }
}
