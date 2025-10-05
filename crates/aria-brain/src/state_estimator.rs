//! State Estimator: Kalman/particle filter

use aria_domain::{IStateEstimator, State, Pose, Twist, RobotMode};
use chrono::Utc;
use nalgebra::{Vector3, UnitQuaternion};

pub struct StateEstimator {
    state: State,
    process_noise: f32,
}

impl StateEstimator {
    pub fn new() -> Self {
        Self {
            state: State {
                timestamp: Utc::now(),
                pose: Pose {
                    position: Vector3::zeros(),
                    orientation: UnitQuaternion::identity(),
                    covariance: None,
                },
                velocity: Twist {
                    linear: Vector3::zeros(),
                    angular: Vector3::zeros(),
                },
                battery_percent: 100.0,
                mode: RobotMode::Idle,
                custom_state: std::collections::HashMap::new(),
            },
            process_noise: 0.01,
        }
    }
}

impl IStateEstimator for StateEstimator {
    fn predict(&mut self, dt: f32) {
        // Predict next state using motion model
        self.state.pose.position += self.state.velocity.linear * dt;
        self.state.timestamp = Utc::now();
    }
    
    fn update(&mut self, measurement: &State) {
        // Kalman update (simplified)
        let alpha = 0.7;
        self.state.pose.position = self.state.pose.position * (1.0 - alpha) + measurement.pose.position * alpha;
        self.state.velocity = measurement.velocity;
        self.state.battery_percent = measurement.battery_percent;
    }
    
    fn get_state(&self) -> State {
        self.state.clone()
    }
}
