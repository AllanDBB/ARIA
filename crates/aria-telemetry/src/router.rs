//! Telemetry Router: merges sensor and brain telemetry

use aria_domain::{AriaResult, Envelope};
use tokio::sync::mpsc;

pub struct TelemetryRouter {
    sensor_rx: Option<mpsc::Receiver<Envelope>>,
    brain_rx: Option<mpsc::Receiver<Envelope>>,
    output_tx: Option<mpsc::Sender<Envelope>>,
}

impl TelemetryRouter {
    pub fn new() -> Self {
        Self {
            sensor_rx: None,
            brain_rx: None,
            output_tx: None,
        }
    }
    
    pub async fn route(&mut self) -> AriaResult<()> {
        // Merge streams based on priority and topic
        Ok(())
    }
}
