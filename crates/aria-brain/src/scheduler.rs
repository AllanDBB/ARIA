//! Scheduler

use aria_domain::{IScheduler, Task};

pub struct Scheduler {
    queue: Vec<Task>,
}

impl Scheduler {
    pub fn new() -> Self {
        Self {
            queue: Vec::new(),
        }
    }
}

impl IScheduler for Scheduler {
    fn schedule(&mut self, tasks: Vec<Task>) -> Vec<Task> {
        self.queue.extend(tasks.clone());
        tasks
    }
    
    fn next_task(&mut self) -> Option<Task> {
        if !self.queue.is_empty() {
            Some(self.queue.remove(0))
        } else {
            None
        }
    }
}
