# ARIA SDK Python - Quick Reference

## 🎯 Current Status: Foundation Complete

### ✅ What's Working Now
- ✅ Project structure with pyproject.toml
- ✅ Domain layer: 30+ dataclasses, 25+ Protocol interfaces
- ✅ Telemetry codec with encode/decode + tests
- ✅ All dependencies installed (numpy, lz4, onnxruntime, etc.)

### ⏳ What's Next
Build these modules in order:
1. **Telemetry**: compression.py, delta.py, crypto.py, qos.py, transport.py
2. **Perception**: yolo.py, audio.py
3. **Brain**: world_model.py, state_estimator.py, planner.py, safety_supervisor.py
4. **CLI**: aria-send.py, aria-recv.py, aria-demo-brain.py

---

## 📦 File Structure

```
ARIA/
├── pyproject.toml                 # ✅ Project config
├── README_PYTHON.md               # ✅ User guide
├── PYTHON_IMPLEMENTATION_STATUS.md # ✅ Roadmap
├── GETTING_STARTED.md             # ✅ Quick start
│
├── src/aria_sdk/
│   ├── __init__.py               # ✅ Package init
│   ├── domain/
│   │   ├── entities.py           # ✅ All dataclasses
│   │   └── protocols.py          # ✅ All interfaces
│   ├── telemetry/
│   │   ├── __init__.py           # ✅ Exports
│   │   ├── codec.py              # ✅ ProtobufCodec
│   │   ├── compression.py        # ⏳ TODO
│   │   ├── delta.py              # ⏳ TODO
│   │   ├── fec.py                # ⏳ TODO
│   │   ├── crypto.py             # ⏳ TODO
│   │   ├── qos.py                # ⏳ TODO
│   │   └── transport.py          # ⏳ TODO
│   ├── perception/               # ⏳ TODO (yolo.py, audio.py)
│   ├── brain/                    # ⏳ TODO (11 modules)
│   ├── ima/                      # ⏳ TODO (3 modules)
│   ├── ports/                    # ⏳ TODO (sensors.py, actuators.py)
│   └── cli/                      # ⏳ TODO (4 CLI tools)
│
└── tests/
    └── test_codec.py             # ✅ Codec tests
```

---

## 🚀 Quick Commands

### Setup
```powershell
cd C:\Users\allan\Documents\GitHub\ARIA
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### Run Tests
```powershell
pytest tests/test_codec.py -v              # Run codec tests
pytest --cov=aria_sdk --cov-report=html   # Coverage report
```

### Code Quality
```powershell
black src/ tests/       # Format code
ruff check src/ tests/  # Lint
mypy src/               # Type check
```

### Try It
```powershell
python
>>> from aria_sdk.telemetry.codec import ProtobufCodec
>>> from aria_sdk.domain.entities import Envelope, Priority
>>> from datetime import datetime, timezone
>>> from uuid import uuid4
>>> 
>>> codec = ProtobufCodec()
>>> env = Envelope(uuid4(), datetime.now(timezone.utc), Priority.P1_HIGH, "test", b"data", None)
>>> encoded = codec.encode(env)
>>> decoded = codec.decode(encoded)
>>> print(decoded.topic, decoded.priority)
```

---

## 🎨 Code Templates

### New Module Template
```python
"""
Module description.
"""

from typing import List, Optional
from aria_sdk.domain.protocols import ISomeProtocol


class MyClass(ISomeProtocol):
    """Brief description."""
    
    def __init__(self, param: int):
        self.param = param
    
    def some_method(self, data: bytes) -> bytes:
        """Method description."""
        # Implementation
        return data
```

### New Test Template
```python
"""
Tests for my_module.
"""

import pytest
from aria_sdk.my_package.my_module import MyClass


class TestMyClass:
    """Test suite for MyClass."""
    
    @pytest.fixture
    def instance(self):
        """Create instance for testing."""
        return MyClass(param=42)
    
    def test_some_method(self, instance):
        """Test that method works correctly."""
        result = instance.some_method(b"test")
        assert isinstance(result, bytes)
```

---

## 📚 Key Concepts

### Domain Layer
- **Entities** (`entities.py`): Dataclasses for data structures
- **Protocols** (`protocols.py`): Interfaces for dependency injection
- **Pure Python**: No external dependencies in domain layer

### Telemetry Pipeline
```
Sensor → Codec → Compress → Delta → FEC → Packetize → Encrypt → QoS → Transport → Network
```

### Cognitive Loop
```
Goals → Planner → Scheduler → Policy Manager → Safety → Synthesizer → Actuators
```

### Testing Strategy
- **Unit tests**: Each module isolated
- **Integration tests**: Full pipeline TX/RX
- **Property tests**: Invariants with Hypothesis
- **Benchmarks**: Performance with pytest-benchmark

---

## 🔧 Dependencies

Already installed via pyproject.toml:

| Package | Purpose | Used In |
|---------|---------|---------|
| numpy | Numerical ops | All modules |
| protobuf | Serialization | codec.py |
| lz4 | Fast compression | compression.py |
| zstandard | High-ratio compression | compression.py |
| pynacl | NaCl crypto | crypto.py |
| aioquic | QUIC transport | transport.py |
| onnxruntime | ML inference | yolo.py |
| opencv-python | Image processing | yolo.py |
| scipy | Signal processing | audio.py |
| click | CLI framework | cli/*.py |
| pytest | Testing | tests/*.py |

---

## 💡 Implementation Tips

### Use Type Hints Everywhere
```python
def process(data: bytes, count: int = 10) -> List[Detection]:
    """Always annotate parameters and return types."""
    ...
```

### Async for I/O
```python
async def read_sensor(self) -> RawSample:
    """Use async/await for non-blocking operations."""
    data = await self._read_async()
    return RawSample(...)
```

### NumPy for Speed
```python
import numpy as np

def apply_filter(signal: np.ndarray) -> np.ndarray:
    """Vectorized operations are fast (C backend)."""
    return np.convolve(signal, kernel, mode='same')
```

### Protocols for Interfaces
```python
from typing import Protocol

class ICodec(Protocol):
    """Use Protocol for structural subtyping."""
    def encode(self, env: Envelope) -> bytes: ...
    def decode(self, data: bytes) -> Envelope: ...
```

---

## 📖 Documentation Links

- **User Guide**: `README_PYTHON.md` - Architecture, features, benchmarks
- **Roadmap**: `PYTHON_IMPLEMENTATION_STATUS.md` - What to build next
- **Quick Start**: `GETTING_STARTED.md` - Installation, first steps
- **This File**: `QUICK_REFERENCE.md` - Command cheat sheet

---

## 🎯 Next Immediate Steps

### Step 1: Add Compression (30 minutes)
```powershell
# Create file
New-Item src\aria_sdk\telemetry\compression.py

# Implement Lz4Compressor and ZstdCompressor (see GETTING_STARTED.md for template)

# Test
New-Item tests\test_compression.py
pytest tests/test_compression.py -v
```

### Step 2: Add Delta Encoding (20 minutes)
```powershell
New-Item src\aria_sdk\telemetry\delta.py
# Implement SimpleDeltaCodec (XOR-based)
pytest tests/test_delta.py -v
```

### Step 3: Add QoS (40 minutes)
```powershell
New-Item src\aria_sdk\telemetry\qos.py
# Implement QoSShaper with priority queues + token bucket
pytest tests/test_qos.py -v
```

---

## 🐛 Common Issues

### ModuleNotFoundError
```powershell
# Solution: Install in editable mode
pip install -e .
```

### Import Errors in Tests
```powershell
# Solution: Make sure pytest can find src/
# Add conftest.py to tests/ with sys.path manipulation if needed
```

### Type Errors
```powershell
# Solution: Install type stubs
pip install types-protobuf types-pyyaml
```

---

## ✅ Completion Checklist

Use this to track progress:

- [x] Project setup (pyproject.toml)
- [x] Domain layer (entities + protocols)
- [x] Telemetry codec (ProtobufCodec)
- [ ] Telemetry compression (Lz4, Zstd)
- [ ] Telemetry delta (SimpleDeltaCodec)
- [ ] Telemetry FEC (ReedSolomonFEC)
- [ ] Telemetry crypto (CryptoBox)
- [ ] Telemetry QoS (QoSShaper)
- [ ] Telemetry transport (QuicTransport)
- [ ] Perception YOLO (YoloDetector)
- [ ] Perception audio (AudioProcessor)
- [ ] Brain world model (WorldModel)
- [ ] Brain state estimator (StateEstimator)
- [ ] Brain planner (Planner)
- [ ] Brain safety (SafetySupervisor)
- [ ] IMA novelty (NoveltyDetector)
- [ ] IMA homeostasis (HomeostasisController)
- [ ] Ports sensors (MockCamera, MockImu)
- [ ] Ports actuators (MockMotor)
- [ ] CLI aria-send
- [ ] CLI aria-recv
- [ ] CLI aria-demo-brain
- [ ] Integration tests
- [ ] Documentation update
- [ ] CI/CD workflow

---

**Last Updated**: After completing foundation (codec + tests)  
**Next Focus**: Telemetry compression module
