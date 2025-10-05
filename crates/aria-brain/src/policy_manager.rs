//! Policy Manager: skill selection

use aria_domain::{IPolicyManager, AriaResult, Task, State, Policy, IWorldModel, AriaError};
use std::collections::HashMap;
use uuid::Uuid;

pub struct PolicyManager {
    policies: HashMap<String, Policy>,
}

impl PolicyManager {
    pub fn new() -> Self {
        Self {
            policies: HashMap::new(),
        }
    }
}

impl IPolicyManager for PolicyManager {
    fn select_skill(&self, task: &Task, state: &State, world: &dyn IWorldModel) -> AriaResult<String> {
        // Match task to skill based on policies
        Ok(task.skill_name.clone())
    }
    
    fn register_policy(&mut self, policy: Policy) {
        self.policies.insert(policy.name.clone(), policy);
    }
}
