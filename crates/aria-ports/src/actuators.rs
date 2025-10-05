//! Actuator ports

use aria_domain::{IActuatorPort, AriaResult, Command, Ack};
use async_trait::async_trait;
use chrono::Utc;

pub struct MockMotor {
    actuator_id: String,
}

impl MockMotor {
    pub fn new(actuator_id: String) -> Self {
        Self { actuator_id }
    }
}

#[async_trait]
impl IActuatorPort for MockMotor {
    async fn open(&mut self) -> AriaResult<()> {
        tracing::info!("Mock motor {} opened", self.actuator_id);
        Ok(())
    }
    
    async fn close(&mut self) -> AriaResult<()> {
        tracing::info!("Mock motor {} closed", self.actuator_id);
        Ok(())
    }
    
    async fn send(&mut self, command: Command) -> AriaResult<Ack> {
        tracing::debug!("Mock motor {} executing: {:?}", self.actuator_id, command.action);
        
        Ok(Ack {
            command_id: command.id,
            timestamp: Utc::now(),
            success: true,
            error_code: None,
            message: Some("OK".into()),
        })
    }
    
    fn actuator_id(&self) -> &str {
        &self.actuator_id
    }
}
