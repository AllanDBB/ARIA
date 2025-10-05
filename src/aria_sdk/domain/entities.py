"""
Domain Entities - Dataclasses representing core concepts
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, IntEnum
from typing import Optional
from uuid import UUID, uuid4

import numpy as np
import numpy.typing as npt


class Priority(IntEnum):
    """Message priority levels"""

    P0 = 0  # Critical: commands, acks, safety
    P1 = 1  # High: state updates, control
    P2 = 2  # Medium: perception data
    P3 = 3  # Low: logs, diagnostics


@dataclass
class FragmentInfo:
    """Packet fragmentation metadata"""

    fragment_id: int
    total_fragments: int
    fragment_offset: int


@dataclass
class FecInfo:
    """Forward error correction metadata"""

    k: int  # Original data shards
    m: int  # Redundancy shards
    block_id: int


@dataclass
class CryptoInfo:
    """Cryptographic metadata"""

    signature: bytes
    key_id: str
    nonce: bytes


@dataclass
class EnvelopeMetadata:
    """Envelope metadata"""

    source_node: str
    sequence_number: int
    fragment_info: Optional[FragmentInfo] = None
    fec_info: Optional[FecInfo] = None
    crypto_info: Optional[CryptoInfo] = None
    qos_class: str = "default"


@dataclass
class Envelope:
    """Universal message envelope for telemetry"""

    id: UUID
    timestamp: datetime
    schema_id: int
    priority: Priority
    topic: str
    payload: bytes
    metadata: EnvelopeMetadata

    @classmethod
    def create(
        cls,
        topic: str,
        payload: bytes,
        priority: Priority = Priority.P2,
        source_node: str = "default",
        sequence_number: int = 0,
    ) -> "Envelope":
        """Factory method"""
        return cls(
            id=uuid4(),
            timestamp=datetime.now(),
            schema_id=1,
            priority=priority,
            topic=topic,
            payload=payload,
            metadata=EnvelopeMetadata(
                source_node=source_node,
                sequence_number=sequence_number,
            ),
        )


@dataclass
class ImageData:
    """Image sensor data"""

    width: int
    height: int
    channels: int
    data: npt.NDArray[np.uint8]


@dataclass
class AudioData:
    """Audio sensor data"""

    sample_rate: int
    channels: int
    samples: npt.NDArray[np.float32]


@dataclass
class ImuData:
    """IMU sensor data"""

    accel: npt.NDArray[np.float32]  # 3D acceleration
    gyro: npt.NDArray[np.float32]  # 3D angular velocity
    mag: Optional[npt.NDArray[np.float32]] = None  # 3D magnetic field


@dataclass
class SensorData:
    """Union type for sensor data"""

    image: Optional[ImageData] = None
    audio: Optional[AudioData] = None
    imu: Optional[ImuData] = None
    temperature: Optional[float] = None


@dataclass
class RawSample:
    """Raw sensor sample"""

    sensor_id: str
    timestamp: datetime
    data: SensorData


@dataclass
class MotionAction:
    """Motion command"""

    velocity: npt.NDArray[np.float32]  # Linear velocity (3D)
    angular: npt.NDArray[np.float32]  # Angular velocity (3D)


@dataclass
class ActuatorAction:
    """Union type for actuator actions"""

    motion: Optional[MotionAction] = None
    digital_pin: Optional[tuple[int, bool]] = None  # (pin, value)


@dataclass
class Command:
    """Command to actuators"""

    id: UUID
    timestamp: datetime
    actuator_id: str
    action: ActuatorAction
    justification: Optional[str] = None

    @classmethod
    def create_motion(
        cls,
        actuator_id: str,
        velocity: npt.NDArray[np.float32],
        angular: npt.NDArray[np.float32],
        justification: Optional[str] = None,
    ) -> "Command":
        """Factory for motion commands"""
        return cls(
            id=uuid4(),
            timestamp=datetime.now(),
            actuator_id=actuator_id,
            action=ActuatorAction(motion=MotionAction(velocity=velocity, angular=angular)),
            justification=justification,
        )


@dataclass
class Ack:
    """Acknowledgment"""

    command_id: UUID
    timestamp: datetime
    success: bool
    error_code: Optional[int] = None
    message: Optional[str] = None


@dataclass
class Pose:
    """6-DOF pose"""

    position: npt.NDArray[np.float32]  # 3D position
    orientation: npt.NDArray[np.float32]  # Quaternion (w, x, y, z)
    covariance: Optional[npt.NDArray[np.float32]] = None  # 6x6


@dataclass
class Twist:
    """Velocity (linear + angular)"""

    linear: npt.NDArray[np.float32]
    angular: npt.NDArray[np.float32]


class RobotMode(Enum):
    """Robot operating mode"""

    IDLE = "idle"
    MANUAL = "manual"
    AUTONOMOUS = "autonomous"
    SAFE_STOP = "safe_stop"
    ERROR = "error"


@dataclass
class State:
    """Robot state"""

    timestamp: datetime
    pose: Pose
    velocity: Twist
    battery_percent: float
    mode: RobotMode
    custom_state: dict[str, float] = field(default_factory=dict)


@dataclass
class GoalType:
    """Mission goal type (union)"""

    navigate_to: Optional[tuple[npt.NDArray[np.float32], float]] = None  # (target, tolerance)
    explore_region: Optional[tuple[npt.NDArray[np.float32], npt.NDArray[np.float32]]] = (
        None  # (min, max)
    )


@dataclass
class MissionGoal:
    """High-level mission goal"""

    id: UUID
    priority: float
    goal_type: GoalType
    deadline: Optional[datetime] = None


class TaskStatus(Enum):
    """Task execution status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass
class Task:
    """Decomposed task"""

    id: UUID
    name: str
    parent_goal: UUID
    skill_name: str
    parameters: dict[str, float]
    status: TaskStatus = TaskStatus.PENDING


@dataclass
class Policy:
    """Policy for skill selection"""

    id: UUID
    name: str
    skill_name: str
    parameters: dict[str, float]
    priority: float


@dataclass
class Detection:
    """Object detection"""

    class_id: int
    class_name: str
    confidence: float
    bbox: tuple[float, float, float, float]  # (x, y, width, height)


@dataclass
class SlamPose:
    """SLAM pose estimate"""

    timestamp: datetime
    pose: Pose
    keyframe_id: Optional[int] = None
    tracking_quality: float = 1.0


@dataclass
class AudioEvent:
    """Audio event detection"""

    timestamp: datetime
    event_type: str
    confidence: float
    duration: float
