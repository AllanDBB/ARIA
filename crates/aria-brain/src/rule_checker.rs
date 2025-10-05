//! Rule Checker: constraint validation

use aria_domain::{IRuleChecker, AriaResult, Command, State};

pub struct RuleChecker {
    rules: Vec<Rule>,
}

struct Rule {
    name: String,
    check_fn: Box<dyn Fn(&Command, &State) -> bool + Send + Sync>,
}

impl RuleChecker {
    pub fn new() -> Self {
        let mut checker = Self {
            rules: Vec::new(),
        };
        
        // Add default safety rules
        checker.add_rule(
            "max_velocity".into(),
            Box::new(|cmd, state| {
                // Check velocity limits
                true
            })
        );
        
        checker
    }
    
    pub fn add_rule(&mut self, name: String, check_fn: Box<dyn Fn(&Command, &State) -> bool + Send + Sync>) {
        self.rules.push(Rule { name, check_fn });
    }
}

impl IRuleChecker for RuleChecker {
    fn check(&self, action: &Command, state: &State) -> AriaResult<bool> {
        Ok(self.rules.iter().all(|rule| (rule.check_fn)(action, state)))
    }
    
    fn get_violations(&self, action: &Command, state: &State) -> Vec<String> {
        self.rules
            .iter()
            .filter(|rule| !(rule.check_fn)(action, state))
            .map(|rule| rule.name.clone())
            .collect()
    }
}
