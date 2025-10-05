//! Action Justifier: explanations for actions

use aria_domain::{IActionJustifier, Command};

pub struct ActionJustifier;

impl ActionJustifier {
    pub fn new() -> Self {
        Self
    }
}

impl IActionJustifier for ActionJustifier {
    fn justify(&self, action: &Command, context: &str) -> String {
        format!(
            "[{}] Action {} for actuator '{}': {:?} | Context: {} | Reason: {:?}",
            action.timestamp,
            action.id,
            action.actuator_id,
            action.action,
            context,
            action.justification
        )
    }
}
