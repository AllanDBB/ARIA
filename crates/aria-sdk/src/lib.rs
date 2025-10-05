//! ARIA SDK - Main Library
//! 
//! Production-grade, robot-side SDK for autonomous systems.
//! Integrates telemetry, perception, cognitive core (brain), IMA, and sensor/actuator ports.

pub use aria_domain as domain;
pub use aria_telemetry as telemetry;
pub use aria_perception as perception;
pub use aria_brain as brain;
pub use aria_ima as ima;
pub use aria_ports as ports;

use tracing_subscriber;

/// Initialize the ARIA SDK with logging
pub fn init() {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::from_default_env()
                .add_directive("aria=info".parse().unwrap())
        )
        .init();
    
    tracing::info!("ARIA SDK initialized");
}

/// SDK version
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_init() {
        // Test that SDK can be initialized
        assert!(!VERSION.is_empty());
    }
}
