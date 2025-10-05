#!/usr/bin/env python3
"""
ARIA SDK - Brain Demo

Demonstrate cognitive loop with mock sensors.
"""

import asyncio
import click
from datetime import datetime, timezone
from uuid import uuid4
import numpy as np

from aria_sdk.domain.entities import Goal, Action, Detection, BoundingBox, State
from aria_sdk.brain.world_model import WorldModel
from aria_sdk.brain.state_estimator import StateEstimator
from aria_sdk.brain.safety_supervisor import SafetySupervisor, SafetyLimits
from aria_sdk.brain.goal_manager import GoalManager
from aria_sdk.brain.action_synthesizer import ActionSynthesizer


@click.command()
@click.option('--duration', '-d', default=30, help='Demo duration (seconds)')
@click.option('--rate', '-r', default=10, help='Update rate (Hz)')
def main(duration: int, rate: int):
    """Run cognitive loop demo."""
    asyncio.run(run_demo(duration, rate))


async def run_demo(duration: int, rate: int):
    """Run cognitive demo loop."""
    click.echo(f"🧠 ARIA Brain Demo (duration={duration}s, rate={rate}Hz)")
    
    # Initialize modules
    world_model = WorldModel()
    state_estimator = StateEstimator()
    safety_limits = SafetyLimits(
        max_linear_velocity=2.0,
        max_angular_velocity=1.5,
        max_linear_accel=1.0,
        max_angular_accel=0.8
    )
    safety = SafetySupervisor(safety_limits)
    goal_mgr = GoalManager()
    action_synth = ActionSynthesizer()
    
    # Add initial goal
    goal = Goal(
        id=uuid4(),
        timestamp=datetime.now(timezone.utc),
        goal_type="navigate",
        target={"position": [10.0, 0.0, 0.0]},
        priority=1
    )
    goal_mgr.add_goal(goal)
    
    click.echo("✅ Initialized cognitive modules")
    click.echo(f"🎯 Goal: Navigate to [10, 0, 0]\n")
    
    # Run loop
    dt = 1.0 / rate
    steps = int(duration * rate)
    
    for step in range(steps):
        t = step * dt
        
        # Simulate detections (mock objects)
        detections = []
        if step % 20 == 0:  # Every 2 seconds
            detection = Detection(
                id=uuid4(),
                timestamp=datetime.now(timezone.utc),
                sensor_id="mock_yolo",
                object_class="obstacle",
                confidence=0.9,
                bounding_box=BoundingBox(x=100, y=100, w=50, h=50)
            )
            detections.append(detection)
            world_model.update_from_detections(detections)
        
        # State estimation
        current_state = state_estimator.get_state()
        
        # Get active goal
        active_goal = goal_mgr.get_next_goal()
        
        if active_goal:
            # Synthesize action
            action = action_synth.synthesize(active_goal, current_state, world_model)
            
            # Safety supervision
            safe_action = safety.supervise(action, current_state)
            
            # Log
            if step % (rate * 2) == 0:  # Every 2 seconds
                pos = current_state.pose.position
                vel = safe_action.values.get('vx', 0.0)
                click.echo(f"[{t:5.1f}s] Pos: [{pos[0]:5.2f}, {pos[1]:5.2f}, {pos[2]:5.2f}] | "
                          f"Vel: {vel:4.2f} m/s | "
                          f"Entities: {len(world_model.get_entities())}")
            
            # Simulate motion (update state)
            new_pos = np.array(current_state.pose.position) + np.array([safe_action.values.get('vx', 0.0) * dt, 0.0, 0.0])
            state_estimator.update_pose(new_pos.tolist(), current_state.pose.orientation)
            
            # Check goal completion
            target = active_goal.target.get('position', [0, 0, 0])
            distance = np.linalg.norm(new_pos - np.array(target))
            if distance < 0.5:
                goal_mgr.complete_goal(active_goal.id)
                click.echo(f"\n🎉 Goal reached at t={t:.1f}s!")
                break
        
        await asyncio.sleep(dt)
    
    click.echo(f"\n✅ Demo completed")
    click.echo(f"📊 Final stats:")
    click.echo(f"  Position: {state_estimator.get_state().pose.position}")
    click.echo(f"  Entities tracked: {len(world_model.get_entities())}")
    click.echo(f"  Safety violations: {len(safety.get_violations())}")


if __name__ == '__main__':
    main()
