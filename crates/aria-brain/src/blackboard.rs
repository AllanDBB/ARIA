//! Blackboard: shared memory for inter-module communication

use std::collections::HashMap;
use std::any::Any;

pub struct Blackboard {
    data: HashMap<String, Box<dyn Any + Send + Sync>>,
}

impl Blackboard {
    pub fn new() -> Self {
        Self {
            data: HashMap::new(),
        }
    }
    
    pub fn write<T: Any + Send + Sync>(&mut self, key: String, value: T) {
        self.data.insert(key, Box::new(value));
    }
    
    pub fn read<T: Any + Send + Sync>(&self, key: &str) -> Option<&T> {
        self.data.get(key).and_then(|v| v.downcast_ref::<T>())
    }
}
