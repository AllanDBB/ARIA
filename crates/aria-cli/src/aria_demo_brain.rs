//! aria-demo-brain - Goal→action loop with mocked sensors/actuators

use aria_sdk::*;
use aria_domain::*;
use aria_brain::*;
use aria_ports::*;
use clap::Parser;
use nalgebra::Vector3;
use std::collections::HashMap;

#[derive(Parser, Debug)]
#[command(name = "aria-demo-brain")]
#[command(about = "Demonstrate brain cognitive loop", long_about = None)]
struct Args {
    /// Number of cycles to run
    #[arg(short = 'n', long, default_value = "10")]
    cycles: usize,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    aria_sdk::init();
    
    let args = Args::parse();
    
    tracing::info!("ARIA Brain Demo starting...");
    
    // Initialize components
    let mut world_model = WorldModel::new();
    let mut state_estimator = StateEstimator::new();
    let goal_manager = GoalManager::new();
    let mut task_planner = TaskPlanner::new();
    let mut scheduler = Scheduler::new();
    let policy_manager = PolicyManager::new();
    let rule_checker = RuleChecker::new();
    let safety_supervisor = SafetySupervisor::new();
    let action_synthesizer = ActionSynthesizer::new();
    let action_justifier = ActionJustifier::new();
    
    // Create mock sensors and actuators
    let mut camera = MockCamera::new("cam0".into(), 640, 480);
    let mut motor = MockMotor::new("motor0".into());
    
    camera.start().await?;
    motor.open().await?;
    
    tracing::info!("Running {} cognitive cycles", args.cycles);
    
    for cycle in 0..args.cycles {
        tracing::info!("--- Cycle {} ---", cycle);
        
        // 1. Sense
        let sample = camera.read().await?;
        tracing::debug!("Read sensor: {}", sample.sensor_id);
        
        // 2. Perceive (placeholder)
        let observation = Observation {
            timestamp: sample.timestamp,
            source: sample.sensor_id.clone(),
            entities: vec![],
        };
        
        // 3. Update world model
        world_model.update(observation);
        
        // 4. Estimate state
        state_estimator.predict(0.1);
        let state = state_estimator.get_state();
        
        // 5. Plan (if goal exists)
        // For demo: create a simple navigation task
        let mut params = HashMap::new();
        params.insert("vx".into(), 0.5);
        params.insert("wz".into(), 0.1);
        
        // 6. Synthesize action
        let action = action_synthesizer.synthesize("navigate", &params, &state)?;
        
        // 7. Rule check
        let rules_ok = rule_checker.check(&action, &state)?;
        tracing::debug!("Rules check: {}", rules_ok);
        
        // 8. Safety supervision
        let safe_action = safety_supervisor.supervise(action, &state)?;
        
        // 9. Justify
        let justification = action_justifier.justify(&safe_action, "demo cycle");
        tracing::info!("{}", justification);
        
        // 10. Act
        let ack = motor.send(safe_action).await?;
        tracing::debug!("Actuator ack: {}", ack.success);
        
        tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
    }
    
    camera.stop().await?;
    motor.close().await?;
    
    tracing::info!("Brain demo completed successfully");
    
    Ok(())
}
