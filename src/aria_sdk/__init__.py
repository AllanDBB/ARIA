"""
ARIA SDK - Production-Grade Robot Autonomy SDK

On-device telemetry, perception, cognitive core, and intrinsic motivation
for autonomous robots running on edge hardware (Jetson, Raspberry Pi, x86_64).

Why Python?
- Rapid prototyping and iteration
- Rich ML/perception ecosystem (ONNX Runtime, OpenCV, NumPy)
- Easy integration with ROS 2, hardware drivers
- Strong typing with type hints (Python 3.10+)
- Async/await for concurrent I/O
- Native C extensions where needed (NumPy, cryptography)

Performance Considerations:
- Use NumPy for numerical operations (vectorized C code)
- ONNX Runtime with hardware acceleration (CUDA, TensorRT)
- Async I/O with asyncio (non-blocking network/sensors)
- C extensions for hot paths (optional: Cython, numba)
"""

__version__ = "0.1.0"
__author__ = "ARIA Robotics Team"

from aria_sdk import domain, telemetry, perception, brain, ima, ports

__all__ = [
    "domain",
    "telemetry",
    "perception",
    "brain",
    "ima",
    "ports",
]
