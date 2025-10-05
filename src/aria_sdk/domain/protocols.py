"""
Protocol Interfaces - Structural subtyping for all components

Using typing.Protocol instead of ABC for duck-typing compatibility
and better mypy support.
"""

from typing import Protocol, Any, Callable, Awaitable
from aria_sdk.domain.entities import *


class ISensorAdapter(Protocol):
    """Sensor adapter interface"""

    async def start(self) -> None:
        """Start the sensor"""
        ...

    async def stop(self) -> None:
        """Stop the sensor"""
        ...

    async def read(self) -> RawSample:
        """Read a sample from the sensor"""
        ...

    @property
    def sensor_id(self) -> str:
        """Get sensor ID"""
        ...


class IActuatorPort(Protocol):
    """Actuator port interface"""

    async def open(self) -> None:
        """Open/initialize the actuator"""
        ...

    async def close(self) -> None:
        """Close the actuator"""
        ...

    async def send(self, command: Command) -> Ack:
        """Send a command and receive acknowledgment"""
        ...

    @property
    def actuator_id(self) -> str:
        """Get actuator ID"""
        ...


class ICodec(Protocol):
    """Codec interface for serialization"""

    def encode(self, obj: Any, schema_id: int) -> bytes:
        """Encode an object to bytes"""
        ...

    def decode(self, data: bytes, schema_id: int) -> Any:
        """Decode bytes to an object"""
        ...


class ICompressor(Protocol):
    """Compressor interface"""

    def compress(self, data: bytes) -> bytes:
        """Compress data"""
        ...

    def decompress(self, data: bytes) -> bytes:
        """Decompress data"""
        ...

    @property
    def name(self) -> str:
        """Compressor name/type"""
        ...


class IDeltaCodec(Protocol):
    """Delta encoding interface"""

    def encode(self, current: bytes, previous: Optional[bytes] = None) -> bytes:
        """Encode delta between current and previous"""
        ...

    def decode(self, delta: bytes, previous: Optional[bytes] = None) -> bytes:
        """Decode delta to reconstruct full data"""
        ...


class IFEC(Protocol):
    """Forward error correction interface"""

    def encode(self, data: bytes, k: int, m: int) -> list[bytes]:
        """Encode data into k+m fragments"""
        ...

    def decode(self, fragments: list[Optional[bytes]], k: int, m: int) -> bytes:
        """Decode fragments back to original data"""
        ...


class ICryptoBox(Protocol):
    """Cryptography interface"""

    def sign(self, data: bytes) -> bytes:
        """Sign data"""
        ...

    def verify(self, data: bytes, signature: bytes) -> bool:
        """Verify signature"""
        ...

    def encrypt(self, data: bytes, nonce: bytes) -> bytes:
        """Encrypt data"""
        ...

    def decrypt(self, ciphertext: bytes, nonce: bytes) -> bytes:
        """Decrypt data"""
        ...

    @property
    def key_id(self) -> str:
        """Get key ID"""
        ...


class IQoSShaper(Protocol):
    """QoS shaper interface"""

    async def shape(self, envelope: Envelope) -> Envelope:
        """Shape an envelope according to QoS policy"""
        ...

    def set_policy(self, topic: str, max_rate: float, burst_size: int) -> None:
        """Set QoS policy for a topic"""
        ...

    def can_send(self, priority: Priority) -> bool:
        """Check if capacity is available for priority"""
        ...


class ITransport(Protocol):
    """Transport interface"""

    async def send(self, envelope: Envelope) -> None:
        """Send an envelope"""
        ...

    async def connect(self, endpoint: str) -> None:
        """Connect to endpoint"""
        ...

    async def disconnect(self) -> None:
        """Disconnect"""
        ...

    @property
    def name(self) -> str:
        """Transport name"""
        ...


class IModel(Protocol):
    """Generic ML model interface"""

    async def load(self, path: str) -> None:
        """Load model from path"""
        ...

    async def infer(self, input_data: npt.NDArray) -> npt.NDArray:
        """Run inference"""
        ...


class IYoloDetector(Protocol):
    """YOLO object detector interface"""

    def detect(
        self, image: npt.NDArray[np.uint8], conf_threshold: float = 0.5
    ) -> list[Detection]:
        """Detect objects in image"""
        ...


class IAudioProcessor(Protocol):
    """Audio processing interface"""

    def detect_vad(self, audio: npt.NDArray[np.float32], sample_rate: int) -> bool:
        """Detect voice activity"""
        ...

    def detect_sed(self, audio: npt.NDArray[np.float32], sample_rate: int) -> list[AudioEvent]:
        """Detect sound events"""
        ...


class IWorldModel(Protocol):
    """World model interface"""

    def update(self, detections: list[Detection], timestamp: datetime) -> None:
        """Update world model with new observations"""
        ...

    def query_region(
        self, min_pos: npt.NDArray[np.float32], max_pos: npt.NDArray[np.float32]
    ) -> list[Any]:
        """Query entities in region"""
        ...


class IStateEstimator(Protocol):
    """State estimator interface"""

    def predict(self, dt: float) -> None:
        """Predict next state"""
        ...

    def update(self, measurement: State) -> None:
        """Update with measurement"""
        ...

    def get_state(self) -> State:
        """Get current state estimate"""
        ...


class IGoalManager(Protocol):
    """Goal manager interface"""

    def add_goal(self, goal: MissionGoal) -> None:
        """Add a new goal"""
        ...

    def get_active_goals(self) -> list[MissionGoal]:
        """Get active goals"""
        ...

    def complete_goal(self, goal_id: UUID) -> None:
        """Complete a goal"""
        ...


class ITaskPlanner(Protocol):
    """Task planner interface"""

    def plan(self, goal: MissionGoal) -> list[Task]:
        """Plan tasks for a goal"""
        ...


class IScheduler(Protocol):
    """Scheduler interface"""

    def schedule(self, tasks: list[Task]) -> list[Task]:
        """Schedule tasks"""
        ...

    def next_task(self) -> Optional[Task]:
        """Get next task to execute"""
        ...


class IPolicyManager(Protocol):
    """Policy manager interface"""

    def select_skill(self, task: Task, state: State) -> str:
        """Select skill for current context"""
        ...

    def register_policy(self, policy: Policy) -> None:
        """Register a policy"""
        ...


class ISkill(Protocol):
    """Skill interface"""

    async def execute(self, task: Task, state: State) -> Ack:
        """Execute the skill"""
        ...

    @property
    def name(self) -> str:
        """Skill name"""
        ...


class IRuleChecker(Protocol):
    """Rule checker interface"""

    def check(self, action: Command, state: State) -> bool:
        """Check if action violates rules"""
        ...

    def get_violations(self, action: Command, state: State) -> list[str]:
        """Get violated rules"""
        ...


class ISafetySupervisor(Protocol):
    """Safety supervisor interface"""

    def supervise(self, action: Command, state: State) -> Command:
        """Override/veto unsafe actions"""
        ...

    def emergency_stop(self) -> Command:
        """Emergency stop"""
        ...


class IActionSynthesizer(Protocol):
    """Action synthesizer interface"""

    def synthesize(self, skill_name: str, parameters: dict[str, float], state: State) -> Command:
        """Synthesize action from skill output"""
        ...


class IActionJustifier(Protocol):
    """Action justifier interface"""

    def justify(self, action: Command, context: str) -> str:
        """Generate justification for action"""
        ...


class INoveltyDetector(Protocol):
    """Novelty detector interface"""

    def compute_novelty(self, detections: list[Detection]) -> float:
        """Compute novelty score for observations"""
        ...


class IHomeostasis(Protocol):
    """Homeostasis interface"""

    def advise(self, metrics: dict[str, float]) -> dict[str, Any]:
        """Monitor internal state and advise adjustments"""
        ...


class IStigmergy(Protocol):
    """Stigmergy interface"""

    def leave_trace(self, location: npt.NDArray[np.float32], trace_type: str, intensity: float) -> None:
        """Leave pheromone trace"""
        ...

    def read_traces(
        self, min_pos: npt.NDArray[np.float32], max_pos: npt.NDArray[np.float32]
    ) -> list[Any]:
        """Read traces in region"""
        ...
