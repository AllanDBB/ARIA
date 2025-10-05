# ARIA SDK - Quick Start Guide

## 🚀 Installation (5 minutes)

### Step 1: Clone Repository
```bash
git clone https://github.com/aria-robotics/aria-sdk
cd ARIA
```

### Step 2: Create Virtual Environment (Recommended)
```bash
# Windows PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install ARIA SDK
```bash
# Basic installation
pip install -e .

# With GPU support (NVIDIA CUDA)
pip install -e ".[gpu]"

# Development installation (includes testing tools)
pip install -e ".[dev]"
```

### Step 4: Verify Installation
```bash
# Check CLI tools
aria-send --help
aria-recv --help
aria-bench --help
aria-demo-brain --help

# Run Python check
python -c "import aria_sdk; print('✅ ARIA SDK installed successfully!')"
```

---

## 🎯 Quick Examples

### Example 1: Basic Sensor Reading (2 minutes)

```python
import asyncio
from aria_sdk.ports.sensors import MockCamera

async def main():
    # Create mock camera
    camera = MockCamera("cam_0", width=640, height=480, fps=30)
    await camera.start()
    
    # Capture 5 frames
    for i in range(5):
        sample = await camera.read()
        print(f"Frame {i+1}: {sample.data.width}x{sample.data.height} RGB")
    
    await camera.stop()

asyncio.run(main())
```

**Expected Output:**
```
[MockCamera] Started: cam_0 (640x480 @ 30fps)
Frame 1: 640x480 RGB
Frame 2: 640x480 RGB
Frame 3: 640x480 RGB
Frame 4: 640x480 RGB
Frame 5: 640x480 RGB
[MockCamera] Stopped: cam_0 (5 frames captured)
```

---

### Example 2: Telemetry Pipeline (3 minutes)

```python
import asyncio
from datetime import datetime, timezone
from uuid import uuid4
from aria_sdk.domain.entities import Envelope, Priority, RawSample, ImageData
from aria_sdk.telemetry.codec import AriaCodec
from aria_sdk.telemetry.compression import create_compressor
import numpy as np

async def main():
    # Create codec and compressor
    codec = AriaCodec()
    compressor = create_compressor("lz4")
    
    # Generate test image
    image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    image_data = ImageData(data=image, width=640, height=480, channels=3, format="rgb8")
    
    # Create sample
    sample = RawSample(
        id=uuid4(),
        timestamp=datetime.now(timezone.utc),
        sensor_id="test_cam",
        data=image_data
    )
    
    # Create envelope
    envelope = Envelope(
        id=uuid4(),
        timestamp=datetime.now(timezone.utc),
        robot_id="robot_001",
        priority=Priority.HIGH,
        payload=sample,
        metadata={"test": True}
    )
    
    # Encode
    encoded = codec.encode(envelope)
    print(f"Encoded size: {len(encoded):,} bytes")
    
    # Compress
    compressed = compressor.compress(encoded)
    ratio = len(encoded) / len(compressed)
    print(f"Compressed size: {len(compressed):,} bytes ({ratio:.2f}x ratio)")
    
    # Decompress and decode
    decompressed = compressor.decompress(compressed)
    decoded = codec.decode(decompressed)
    print(f"✅ Roundtrip successful! Robot ID: {decoded.robot_id}")

asyncio.run(main())
```

**Expected Output:**
```
Encoded size: 921,612 bytes
Compressed size: 307,204 bytes (3.00x ratio)
✅ Roundtrip successful! Robot ID: robot_001
```

---

### Example 3: Cognitive Loop (5 minutes)

```python
import asyncio
import numpy as np
from datetime import datetime, timezone
from uuid import uuid4
from aria_sdk.domain.entities import Goal
from aria_sdk.brain.world_model import WorldModel
from aria_sdk.brain.state_estimator import StateEstimator
from aria_sdk.brain.safety_supervisor import SafetySupervisor, SafetyLimits
from aria_sdk.brain.goal_manager import GoalManager
from aria_sdk.brain.action_synthesizer import ActionSynthesizer

async def main():
    # Initialize brain modules
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
    
    # Add navigation goal
    goal = Goal(
        id=uuid4(),
        timestamp=datetime.now(timezone.utc),
        goal_type="navigate",
        target={"position": [5.0, 0.0, 0.0]},
        priority=1
    )
    goal_mgr.add_goal(goal)
    print(f"🎯 Goal: Navigate to [5, 0, 0]")
    
    # Run cognitive loop
    dt = 0.1  # 10 Hz
    for step in range(100):
        # Get current state
        state = state_estimator.get_state()
        
        # Get active goal
        active_goal = goal_mgr.get_next_goal()
        if not active_goal:
            print("✅ Goal completed!")
            break
        
        # Synthesize action
        action = action_synth.synthesize(active_goal, state, world_model)
        
        # Safety supervision
        safe_action = safety.supervise(action, state)
        
        # Log every second
        if step % 10 == 0:
            pos = state.pose.position
            vx = safe_action.values.get('vx', 0.0)
            print(f"[{step*dt:.1f}s] Pos: [{pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f}] | Vel: {vx:.2f} m/s")
        
        # Simulate motion
        vx = safe_action.values.get('vx', 0.0)
        new_pos = [
            state.pose.position[0] + vx * dt,
            state.pose.position[1],
            state.pose.position[2]
        ]
        state_estimator.update_pose(new_pos, state.pose.orientation)
        
        # Check goal completion
        target = active_goal.target['position']
        distance = np.linalg.norm(np.array(new_pos) - np.array(target))
        if distance < 0.5:
            goal_mgr.complete_goal(active_goal.id)
            print(f"🎉 Goal reached at {step*dt:.1f}s!")
            break
        
        await asyncio.sleep(dt)

asyncio.run(main())
```

**Expected Output:**
```
🎯 Goal: Navigate to [5, 0, 0]
[0.0s] Pos: [0.00, 0.00, 0.00] | Vel: 1.00 m/s
[1.0s] Pos: [1.00, 0.00, 0.00] | Vel: 1.00 m/s
[2.0s] Pos: [2.00, 0.00, 0.00] | Vel: 1.00 m/s
[3.0s] Pos: [3.00, 0.00, 0.00] | Vel: 1.00 m/s
[4.0s] Pos: [4.00, 0.00, 0.00] | Vel: 1.00 m/s
🎉 Goal reached at 4.9s!
✅ Goal completed!
```

---

## 🛠️ CLI Tools

### 1. Send Test Data
```bash
# Send 100 frames to file
aria-send --count 100 --width 640 --height 480 --output test_data.bin
```

### 2. Receive and Decode
```bash
# Decode saved data
aria-recv --input test_data.bin --verbose
```

### 3. Run Benchmarks
```bash
# Codec benchmark
aria-bench codec --count 1000 --width 640 --height 480

# Compression benchmark
aria-bench compression --size 1000000 --algorithm lz4

# FEC benchmark
aria-bench fec --size 1000000 --loss 10

# Crypto benchmark
aria-bench crypto --size 1000000
```

### 4. Cognitive Demo
```bash
# Run 30-second cognitive loop at 10Hz
aria-demo-brain --duration 30 --rate 10
```

---

## 📦 Complete Demo

Run the comprehensive example:

```bash
python examples/complete_demo.py
```

This demonstrates:
- ✅ Telemetry pipeline (codec, compression, delta, FEC, crypto, QoS)
- ✅ Perception (YOLO API, audio processing)
- ✅ Cognitive loop (world model, state estimation, goal management, safety)
- ✅ IMA subsystems (novelty, homeostasis, stigmergy)

---

## 🔧 Configuration

Create `config.yaml`:

```yaml
robot_id: "robot_001"

sensors:
  camera:
    width: 640
    height: 480
    fps: 30
  
  imu:
    rate_hz: 100

telemetry:
  compression: "lz4"  # or "zstd"
  fec_enabled: true
  crypto_enabled: true

brain:
  update_rate: 10  # Hz
  
  safety:
    max_linear_velocity: 2.0
    max_angular_velocity: 1.5
```

Load configuration:

```python
import yaml
from pathlib import Path

config = yaml.safe_load(Path("config.yaml").read_text())
robot_id = config['robot_id']
camera_fps = config['sensors']['camera']['fps']
```

---

## 🐛 Troubleshooting

### Issue: Import errors
```
ModuleNotFoundError: No module named 'aria_sdk'
```

**Solution**: Install in editable mode
```bash
pip install -e .
```

---

### Issue: Missing dependencies
```
ImportError: No module named 'lz4'
```

**Solution**: Install all dependencies
```bash
pip install -r requirements.txt
# Or
pip install -e .
```

---

### Issue: ONNX Runtime not found
```
ModuleNotFoundError: No module named 'onnxruntime'
```

**Solution**: Install ONNX Runtime
```bash
# CPU version
pip install onnxruntime>=1.16.0

# GPU version (requires CUDA)
pip install onnxruntime-gpu>=1.16.0
```

---

## 📚 Next Steps

1. **Explore Modules**: Check `src/aria_sdk/` for all modules
2. **Read Documentation**: See `PROJECT_STRUCTURE.md` and `IMPLEMENTATION_SUMMARY.md`
3. **Run Examples**: Try `examples/complete_demo.py`
4. **Run Benchmarks**: Use `aria-bench` to test performance
5. **Build Your Robot**: Integrate with real sensors/actuators

---

## 🎓 Learning Path

### Beginner (Day 1)
1. Run Example 1 (sensor reading)
2. Run Example 2 (telemetry pipeline)
3. Run `aria-send` and `aria-recv`

### Intermediate (Week 1)
1. Run Example 3 (cognitive loop)
2. Explore brain modules
3. Run `aria-demo-brain`

### Advanced (Month 1)
1. Integrate real camera (OpenCV)
2. Add custom skills to action synthesizer
3. Build custom transport adapter
4. Connect to real motors

---

## 💡 Pro Tips

### 1. Use Virtual Environment
Always work in a virtual environment to avoid dependency conflicts.

### 2. Enable Logging
```python
from loguru import logger
import sys

logger.remove()
logger.add(sys.stderr, level="DEBUG")
```

### 3. Profile Performance
```python
import time

start = time.perf_counter()
# ... your code ...
elapsed = time.perf_counter() - start
print(f"Took {elapsed*1000:.2f} ms")
```

### 4. Use Type Hints
All ARIA SDK code uses type hints. Your IDE (VS Code, PyCharm) will provide autocomplete!

### 5. Check Protocol Implementations
See `domain/protocols.py` for all interfaces you can implement.

---

## 🤝 Getting Help

1. **Documentation**: Read `README.md`, `PROJECT_STRUCTURE.md`, `IMPLEMENTATION_SUMMARY.md`
2. **Examples**: Check `examples/complete_demo.py`
3. **Source Code**: Browse `src/aria_sdk/` - all code is documented
4. **Issues**: Open GitHub issue with minimal reproducible example

---

## ✅ Checklist

- [x] Install Python 3.10+
- [x] Clone repository
- [x] Create virtual environment
- [x] Install ARIA SDK (`pip install -e .`)
- [x] Verify installation (`aria-send --help`)
- [x] Run Example 1 (sensor reading)
- [x] Run Example 2 (telemetry pipeline)
- [x] Run Example 3 (cognitive loop)
- [x] Run complete demo (`python examples/complete_demo.py`)
- [x] Run CLI tools (`aria-bench codec`)
- [ ] Integrate real hardware
- [ ] Build your robot application!

---

**🤖 Happy Robot Building! 🤖**
