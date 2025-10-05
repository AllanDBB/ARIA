"""
ARIA SDK - Sensor Adapters Module

Mock and real sensor implementations.
"""

import asyncio
import numpy as np
from typing import Optional
from datetime import datetime, timezone
from uuid import uuid4

from aria_sdk.domain.entities import RawSample, ImageData, ImuData
from aria_sdk.domain.protocols import ISensorAdapter


class MockCamera(ISensorAdapter):
    """
    Mock camera sensor for testing.
    
    Generates synthetic images with optional noise.
    """
    
    def __init__(self, sensor_id: str, width: int = 640, height: int = 480, fps: int = 30):
        """
        Initialize mock camera.
        
        Args:
            sensor_id: Sensor identifier
            width: Image width
            height: Image height
            fps: Frames per second
        """
        self.sensor_id = sensor_id
        self.width = width
        self.height = height
        self.fps = fps
        self.frame_interval = 1.0 / fps
        
        self.running = False
        self.frame_count = 0
    
    async def start(self):
        """Start sensor."""
        self.running = True
        self.frame_count = 0
        print(f"[MockCamera] Started: {self.sensor_id} ({self.width}x{self.height} @ {self.fps}fps)")
    
    async def read(self) -> RawSample:
        """
        Read sensor data.
        
        Returns:
            Image sample
        """
        if not self.running:
            raise RuntimeError("Sensor not started")
        
        # Generate synthetic image (moving gradient)
        x = np.linspace(0, 1, self.width)
        y = np.linspace(0, 1, self.height)
        xx, yy = np.meshgrid(x, y)
        
        # Animated pattern
        t = self.frame_count * 0.1
        pattern = np.sin(xx * 10 + t) * np.cos(yy * 10 + t)
        pattern = ((pattern + 1) * 127.5).astype(np.uint8)
        
        # Create RGB image
        image = np.stack([pattern, pattern, pattern], axis=-1)
        
        # Add noise
        noise = np.random.randint(0, 10, image.shape, dtype=np.uint8)
        image = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        self.frame_count += 1
        
        # Create sample
        image_data = ImageData(
            data=image,
            width=self.width,
            height=self.height,
            channels=3,
            format="rgb8"
        )
        
        sample = RawSample(
            id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            sensor_id=self.sensor_id,
            data=image_data
        )
        
        # Simulate frame rate
        await asyncio.sleep(self.frame_interval)
        
        return sample
    
    async def stop(self):
        """Stop sensor."""
        self.running = False
        print(f"[MockCamera] Stopped: {self.sensor_id} ({self.frame_count} frames captured)")


class MockImu(ISensorAdapter):
    """
    Mock IMU sensor for testing.
    
    Generates synthetic accelerometer and gyroscope data.
    """
    
    def __init__(self, sensor_id: str, rate_hz: int = 100):
        """
        Initialize mock IMU.
        
        Args:
            sensor_id: Sensor identifier
            rate_hz: Sample rate (Hz)
        """
        self.sensor_id = sensor_id
        self.rate_hz = rate_hz
        self.sample_interval = 1.0 / rate_hz
        
        self.running = False
        self.sample_count = 0
    
    async def start(self):
        """Start sensor."""
        self.running = True
        self.sample_count = 0
        print(f"[MockImu] Started: {self.sensor_id} @ {self.rate_hz}Hz")
    
    async def read(self) -> RawSample:
        """
        Read IMU data.
        
        Returns:
            IMU sample
        """
        if not self.running:
            raise RuntimeError("Sensor not started")
        
        # Generate synthetic IMU data
        t = self.sample_count * self.sample_interval
        
        # Accelerometer: gravity + noise
        accel = np.array([
            np.random.normal(0, 0.1),
            np.random.normal(0, 0.1),
            9.81 + np.random.normal(0, 0.1)  # Gravity on Z
        ], dtype=np.float32)
        
        # Gyroscope: slight rotation + noise
        gyro = np.array([
            np.sin(t) * 0.1 + np.random.normal(0, 0.01),
            np.cos(t) * 0.1 + np.random.normal(0, 0.01),
            np.random.normal(0, 0.01)
        ], dtype=np.float32)
        
        self.sample_count += 1
        
        # Create sample
        imu_data = ImuData(
            accel_x=float(accel[0]),
            accel_y=float(accel[1]),
            accel_z=float(accel[2]),
            gyro_x=float(gyro[0]),
            gyro_y=float(gyro[1]),
            gyro_z=float(gyro[2]),
            mag_x=0.0,
            mag_y=0.0,
            mag_z=0.0
        )
        
        sample = RawSample(
            id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            sensor_id=self.sensor_id,
            data=imu_data
        )
        
        # Simulate sample rate
        await asyncio.sleep(self.sample_interval)
        
        return sample
    
    async def stop(self):
        """Stop sensor."""
        self.running = False
        print(f"[MockImu] Stopped: {self.sensor_id} ({self.sample_count} samples)")


class RealCamera(ISensorAdapter):
    """
    Real camera using OpenCV.
    
    Requires cv2 (opencv-python).
    """
    
    def __init__(self, sensor_id: str, device_id: int = 0, width: int = 640, height: int = 480):
        """
        Initialize real camera.
        
        Args:
            sensor_id: Sensor identifier
            device_id: Camera device ID
            width: Desired width
            height: Desired height
        """
        try:
            import cv2
            self.cv2 = cv2
        except ImportError:
            raise ImportError("opencv-python required for RealCamera. Install with: pip install opencv-python")
        
        self.sensor_id = sensor_id
        self.device_id = device_id
        self.width = width
        self.height = height
        
        self.capture: Optional[any] = None
        self.running = False
        self.frame_count = 0
    
    async def start(self):
        """Start camera."""
        self.capture = self.cv2.VideoCapture(self.device_id)
        self.capture.set(self.cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.capture.set(self.cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        
        if not self.capture.isOpened():
            raise RuntimeError(f"Failed to open camera {self.device_id}")
        
        self.running = True
        print(f"[RealCamera] Started: {self.sensor_id} (device {self.device_id})")
    
    async def read(self) -> RawSample:
        """Read frame from camera."""
        if not self.running or self.capture is None:
            raise RuntimeError("Camera not started")
        
        # Capture frame
        ret, frame = self.capture.read()
        if not ret:
            raise RuntimeError("Failed to capture frame")
        
        # Convert BGR to RGB
        frame_rgb = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2RGB)
        
        self.frame_count += 1
        
        # Create sample
        h, w, c = frame_rgb.shape
        image_data = ImageData(
            data=frame_rgb.astype(np.uint8),
            width=w,
            height=h,
            channels=c,
            format="rgb8"
        )
        
        sample = RawSample(
            id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            sensor_id=self.sensor_id,
            data=image_data
        )
        
        return sample
    
    async def stop(self):
        """Stop camera."""
        if self.capture:
            self.capture.release()
            self.capture = None
        self.running = False
        print(f"[RealCamera] Stopped: {self.sensor_id} ({self.frame_count} frames)")
