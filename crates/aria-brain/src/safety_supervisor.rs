//! Safety Supervisor: override/veto unsafe actions

use aria_domain::{ISafetySupervisor, AriaResult, Command, State, ActuatorAction};
use chrono::Utc;
use uuid::Uuid;
use nalgebra::Vector3;

pub struct SafetySupervisor {
    emergency_stop_enabled: bool,
}

impl SafetySupervisor {
    pub fn new() -> Self {
        Self {
            emergency_stop_enabled: false,
        }
    }
}

impl ISafetySupervisor for SafetySupervisor {
    fn supervise(&self, mut action: Command, state: &State) -> AriaResult<Command> {
        if self.emergency_stop_enabled {
            return Ok(self.emergency_stop());
        }
        
        // Clamp velocities to safe limits
        if let ActuatorAction::Motion { ref mut velocity, ref mut angular } = action.action {
            let max_vel = 2.0;
            if velocity.norm() > max_vel {
                *velocity = velocity.normalize() * max_vel;
            }
        }
        
        Ok(action)
    }
    
    fn emergency_stop(&mut self) -> Command {
        self.emergency_stop_enabled = true;
        
        Command {
            id: Uuid::new_v4(),
            timestamp: Utc::now(),
            actuator_id: "all".into(),
            action: ActuatorAction::Motion {
                velocity: Vector3::zeros(),
                angular: Vector3::zeros(),
            },
            justification: Some("Emergency stop".into()),
        }
    }
}
