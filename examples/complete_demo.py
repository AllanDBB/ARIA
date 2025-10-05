"""
ARIA SDK - Complete Example

Demonstrates full telemetry pipeline with cognitive loop.
"""

import asyncio
import numpy as np
from datetime import datetime, timezone
from uuid import uuid4

# Domain
from aria_sdk.domain.entities import Envelope, Priority, Goal, Action

# Ports
from aria_sdk.ports.sensors import MockCamera, MockImu
from aria_sdk.ports.actuators import MockMotor

# Telemetry
from aria_sdk.telemetry.codec import AriaCodec
from aria_sdk.telemetry.compression import create_compressor
from aria_sdk.telemetry.delta import AdaptiveDeltaCodec
from aria_sdk.telemetry.fec import AdaptiveFEC
from aria_sdk.telemetry.crypto import CryptoBox
from aria_sdk.telemetry.qos import QoSShaper

# Perception
from aria_sdk.perception.yolo import YoloDetector

# Brain
from aria_sdk.brain.world_model import WorldModel
from aria_sdk.brain.state_estimator import StateEstimator
from aria_sdk.brain.safety_supervisor import SafetySupervisor, SafetyLimits
from aria_sdk.brain.goal_manager import GoalManager
from aria_sdk.brain.action_synthesizer import ActionSynthesizer

# IMA
from aria_sdk.ima.novelty import NoveltyDetector
from aria_sdk.ima.homeostasis import HomeostasisController
from aria_sdk.ima.stigmergy import StigmergySystem


async def telemetry_demo():
    """Demonstrate telemetry pipeline."""
    print("=" * 60)
    print("TELEMETRY PIPELINE DEMO")
    print("=" * 60)
    
    # Create sensor
    camera = MockCamera("cam_0", width=640, height=480, fps=30)
    await camera.start()
    
    # Create pipeline
    codec = AriaCodec()
    compressor = create_compressor("lz4")
    delta_codec = AdaptiveDeltaCodec()
    fec = AdaptiveFEC(k=10, m=4)
    
    # Generate keys for crypto
    from nacl.public import PrivateKey
    sender_key = PrivateKey.generate()
    receiver_key = PrivateKey.generate()
    crypto = CryptoBox(sender_key.encode(), receiver_key.public_key.encode())
    
    qos = QoSShaper()
    
    print("\n📸 Capturing and processing frames...")
    
    for i in range(5):
        # Capture
        sample = await camera.read()
        print(f"\n[Frame {i+1}]")
        print(f"  Captured: {sample.data.width}x{sample.data.height} RGB")
        
        # Create envelope
        envelope = Envelope(
            id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            robot_id="demo_robot",
            priority=Priority.HIGH,
            payload=sample,
            metadata={"frame": i}
        )
        
        # Encode
        encoded = codec.encode(envelope)
        print(f"  Encoded: {len(encoded):,} bytes")
        
        # Compress
        compressed = compressor.compress(encoded)
        print(f"  Compressed: {len(compressed):,} bytes ({len(encoded)/len(compressed):.2f}x)")
        
        # Delta encode
        delta_encoded = delta_codec.encode(compressed)
        print(f"  Delta: {len(delta_encoded):,} bytes")
        
        # FEC
        fec_shards = fec.encode(delta_encoded)
        print(f"  FEC: {len(fec_shards)} shards")
        
        # Encrypt
        encrypted = crypto.encrypt(delta_encoded)
        print(f"  Encrypted: {len(encrypted):,} bytes")
        
        # QoS enqueue
        await qos.enqueue(encrypted, envelope.priority)
        print(f"  Queued with priority: {envelope.priority.name}")
    
    await camera.stop()
    print("\n✅ Telemetry demo complete")


async def cognitive_demo():
    """Demonstrate cognitive loop."""
    print("\n" + "=" * 60)
    print("COGNITIVE LOOP DEMO")
    print("=" * 60)
    
    # Initialize brain
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
    
    # Initialize IMA
    novelty = NoveltyDetector()
    homeostasis = HomeostasisController()
    stigmergy = StigmergySystem()
    
    # Initialize motor
    motor = MockMotor("motor_0")
    await motor.open()
    
    # Add goal
    goal = Goal(
        id=uuid4(),
        timestamp=datetime.now(timezone.utc),
        goal_type="navigate",
        target={"position": [5.0, 0.0, 0.0]},
        priority=1
    )
    goal_mgr.add_goal(goal)
    
    print(f"\n🎯 Goal: Navigate to {goal.target['position']}")
    print("\n🔄 Running cognitive loop...")
    
    dt = 0.1  # 10 Hz
    steps = 50
    
    for step in range(steps):
        t = step * dt
        
        # World model update
        current_state = state_estimator.get_state()
        
        # Get active goal
        active_goal = goal_mgr.get_next_goal()
        
        if not active_goal:
            print("\n✅ All goals completed!")
            break
        
        # Synthesize action
        action = action_synth.synthesize(active_goal, current_state, world_model)
        
        # Safety supervision
        safe_action = safety.supervise(action, current_state)
        
        # Novelty detection
        observation = np.random.bytes(64)
        novelty_score = novelty.detect(observation)
        
        # Homeostasis
        homeostasis.update(
            bandwidth_utilization=0.5,
            packet_loss_rate=0.01,
            latency_ms=50.0,
            cpu_load=0.4,
            memory_usage=0.6,
            temperature=55.0
        )
        
        # Stigmergy
        pos = current_state.pose.position
        stigmergy.deposit(pos, intensity=1.0, decay_rate=0.1, robot_id="demo_robot")
        gradient = stigmergy.get_gradient(pos, radius=2.0)
        
        # Execute action (convert to command)
        from aria_sdk.domain.entities import Command
        command = Command(
            id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            robot_id="demo_robot",
            action=safe_action,
            deadline=None
        )
        
        ack = await motor.send(command)
        
        # Log progress
        if step % 10 == 0:
            print(f"\n[t={t:.1f}s]")
            print(f"  Position: {current_state.pose.position}")
            print(f"  Action: {safe_action.action_type} {safe_action.values}")
            print(f"  Novelty: {novelty_score:.3f}")
            print(f"  Health: {homeostasis.get_health_score():.3f}")
            print(f"  Gradient: {gradient}")
        
        # Simulate motion
        vx = safe_action.values.get('vx', 0.0)
        new_pos = [
            current_state.pose.position[0] + vx * dt,
            current_state.pose.position[1],
            current_state.pose.position[2]
        ]
        state_estimator.update_pose(new_pos, current_state.pose.orientation)
        
        # Check goal completion
        target = active_goal.target.get('position', [0, 0, 0])
        distance = np.linalg.norm(np.array(new_pos) - np.array(target))
        if distance < 0.5:
            goal_mgr.complete_goal(active_goal.id)
            print(f"\n🎉 Goal reached at t={t:.1f}s!")
            break
        
        await asyncio.sleep(dt)
    
    await motor.close()
    print("\n✅ Cognitive demo complete")


async def perception_demo():
    """Demonstrate perception."""
    print("\n" + "=" * 60)
    print("PERCEPTION DEMO")
    print("=" * 60)
    
    # Note: This requires an actual YOLO model file
    # For demo purposes, we'll just show the API
    
    print("\n🔍 YOLO Detector API:")
    print("  detector = YoloDetector('model.onnx')")
    print("  detections = detector.detect(image)")
    print("  → Returns: List[Detection] with bounding boxes")
    
    from aria_sdk.perception.audio import AudioProcessor
    
    print("\n🎤 Audio Processor:")
    audio_proc = AudioProcessor(sample_rate=16000, frame_size=512)
    
    # Generate test audio
    audio_data = np.random.randn(16000).astype(np.float32)  # 1 second
    
    # VAD
    vad_result = audio_proc.voice_activity_detection(audio_data)
    print(f"  Voice Activity: {vad_result}")
    
    # SED
    sed_result = audio_proc.sound_event_detection(audio_data)
    print(f"  Sound Event: {sed_result}")
    
    print("\n✅ Perception demo complete")


async def main():
    """Run all demos."""
    print("\n" + "🤖" * 30)
    print("ARIA SDK - COMPLETE DEMO")
    print("🤖" * 30)
    
    await telemetry_demo()
    await perception_demo()
    await cognitive_demo()
    
    print("\n" + "=" * 60)
    print("ALL DEMOS COMPLETE ✅")
    print("=" * 60)


if __name__ == '__main__':
    asyncio.run(main())
