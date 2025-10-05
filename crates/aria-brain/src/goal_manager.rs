//! Goal Manager

use aria_domain::{IGoalManager, MissionGoal};
use uuid::Uuid;
use std::collections::HashMap;

pub struct GoalManager {
    goals: HashMap<Uuid, MissionGoal>,
}

impl GoalManager {
    pub fn new() -> Self {
        Self {
            goals: HashMap::new(),
        }
    }
}

impl IGoalManager for GoalManager {
    fn add_goal(&mut self, goal: MissionGoal) {
        self.goals.insert(goal.id, goal);
    }
    
    fn get_active_goals(&self) -> Vec<MissionGoal> {
        self.goals.values().cloned().collect()
    }
    
    fn complete_goal(&mut self, goal_id: Uuid) {
        self.goals.remove(&goal_id);
    }
}
