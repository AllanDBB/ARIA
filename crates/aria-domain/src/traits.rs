//! Core Trait Definitions
//! 
//! Interfaces for all pluggable components in the ARIA SDK.

use crate::entities::*;
use crate::error::AriaResult;
use async_trait::async_trait;
use std::any::Any;

// ============================================================================
// Sensor & Actuator Ports
// ============================================================================

#[async_trait]
pub trait ISensorAdapter: Send + Sync {
    /// Start the sensor
    async fn start(&mut self) -> AriaResult<()>;
    
    /// Stop the sensor
    async fn stop(&mut self) -> AriaResult<()>;
    
    /// Read a sample from the sensor
    async fn read(&mut self) -> AriaResult<RawSample>;
    
    /// Get sensor ID
    fn sensor_id(&self) -> &str;
}

#[async_trait]
pub trait IActuatorPort: Send + Sync {
    /// Open/initialize the actuator
    async fn open(&mut self) -> AriaResult<()>;
    
    /// Close the actuator
    async fn close(&mut self) -> AriaResult<()>;
    
    /// Send a command and receive acknowledgment
    async fn send(&mut self, command: Command) -> AriaResult<Ack>;
    
    /// Get actuator ID
    fn actuator_id(&self) -> &str;
}

// ============================================================================
// Telemetry Pipeline Traits
// ============================================================================

pub trait ICodec: Send + Sync {
    /// Encode an object to bytes with schema ID
    fn encode(&self, obj: &dyn Any, schema_id: u32) -> AriaResult<Vec<u8>>;
    
    /// Decode bytes to an object using schema ID
    fn decode(&self, bytes: &[u8], schema_id: u32) -> AriaResult<Box<dyn Any>>;
}

pub trait ICompressor: Send + Sync {
    /// Compress data
    fn compress(&self, data: &[u8]) -> AriaResult<Vec<u8>>;
    
    /// Decompress data
    fn decompress(&self, data: &[u8]) -> AriaResult<Vec<u8>>;
    
    /// Compressor name/type
    fn name(&self) -> &str;
}

pub trait IDeltaCodec: Send + Sync {
    /// Encode delta between current and previous
    fn encode(&mut self, current: &[u8], previous: Option<&[u8]>) -> AriaResult<Vec<u8>>;
    
    /// Decode delta to reconstruct full data
    fn decode(&mut self, delta: &[u8], previous: Option<&[u8]>) -> AriaResult<Vec<u8>>;
}

pub trait IFEC: Send + Sync {
    /// Encode data into k+m fragments (k original, m redundancy)
    fn encode(&self, data: &[u8], k: usize, m: usize) -> AriaResult<Vec<Vec<u8>>>;
    
    /// Decode fragments back to original data (need at least k fragments)
    fn decode(&self, fragments: &[Option<Vec<u8>>], k: usize, m: usize) -> AriaResult<Vec<u8>>;
}

pub trait ICryptoBox: Send + Sync {
    /// Sign data
    fn sign(&self, data: &[u8]) -> AriaResult<Vec<u8>>;
    
    /// Verify signature
    fn verify(&self, data: &[u8], signature: &[u8]) -> AriaResult<bool>;
    
    /// Encrypt data (authenticated encryption)
    fn encrypt(&self, data: &[u8], nonce: &[u8]) -> AriaResult<Vec<u8>>;
    
    /// Decrypt data
    fn decrypt(&self, ciphertext: &[u8], nonce: &[u8]) -> AriaResult<Vec<u8>>;
    
    /// Get key ID
    fn key_id(&self) -> &str;
}

#[async_trait]
pub trait IQoSShaper: Send + Sync {
    /// Shape an envelope according to QoS policy
    async fn shape(&mut self, envelope: Envelope) -> AriaResult<Envelope>;
    
    /// Set QoS policy for a topic
    fn set_policy(&mut self, topic: &str, policy: QoSPolicy);
    
    /// Check if capacity is available for priority
    fn can_send(&self, priority: Priority) -> bool;
}

#[derive(Debug, Clone)]
pub struct QoSPolicy {
    pub max_rate_per_sec: f32,
    pub burst_size: usize,
    pub max_queue_depth: usize,
}

#[async_trait]
pub trait ITransport: Send + Sync {
    /// Send an envelope
    async fn send(&mut self, envelope: Envelope) -> AriaResult<()>;
    
    /// Register receive handler
    async fn on_receive(&mut self, handler: Box<dyn Fn(Envelope) + Send + Sync>);
    
    /// Connect to endpoint
    async fn connect(&mut self, endpoint: &str) -> AriaResult<()>;
    
    /// Disconnect
    async fn disconnect(&mut self) -> AriaResult<()>;
    
    /// Transport name
    fn name(&self) -> &str;
}

// ============================================================================
// Perception Traits
// ============================================================================

#[async_trait]
pub trait IModel: Send + Sync {
    /// Load model from path
    async fn load(&mut self, path: &str) -> AriaResult<()>;
    
    /// Run inference
    async fn infer(&mut self, input: &[u8]) -> AriaResult<Vec<u8>>;
    
    /// Get model metadata
    fn metadata(&self) -> ModelMetadata;
}

#[derive(Debug, Clone)]
pub struct ModelMetadata {
    pub name: String,
    pub version: String,
    pub input_shape: Vec<usize>,
    pub output_shape: Vec<usize>,
    pub backend: String,
}

pub trait IYoloDetector: Send + Sync {
    /// Detect objects in image
    fn detect(&mut self, image: &[u8], width: u32, height: u32) -> AriaResult<Vec<Detection>>;
}

pub trait ISlamEstimator: Send + Sync {
    /// Process frame and return pose
    fn process_frame(&mut self, image: &[u8], width: u32, height: u32, timestamp: DateTime<Utc>) -> AriaResult<SlamPose>;
    
    /// Get current map points
    fn get_map_points(&self) -> Vec<Vector3<f32>>;
}

pub trait IAudioProcessor: Send + Sync {
    /// Detect voice activity
    fn detect_vad(&mut self, audio: &[f32], sample_rate: u32) -> AriaResult<bool>;
    
    /// Detect sound events
    fn detect_sed(&mut self, audio: &[f32], sample_rate: u32) -> AriaResult<Vec<AudioEvent>>;
}

// ============================================================================
// Brain Traits
// ============================================================================

pub trait IWorldModel: Send + Sync {
    /// Update world model with new observation
    fn update(&mut self, observation: Observation);
    
    /// Query entities in region
    fn query_region(&self, bbox: &BoundingBox) -> Vec<Entity>;
    
    /// Get belief about entity
    fn get_belief(&self, entity_id: &str) -> Option<Belief>;
}

#[derive(Debug, Clone)]
pub struct Observation {
    pub timestamp: DateTime<Utc>,
    pub source: String,
    pub entities: Vec<Entity>,
}

#[derive(Debug, Clone)]
pub struct Entity {
    pub id: String,
    pub class_name: String,
    pub pose: Pose,
    pub properties: std::collections::HashMap<String, f32>,
}

#[derive(Debug, Clone)]
pub struct Belief {
    pub entity_id: String,
    pub pose: Pose,
    pub uncertainty: f32,
    pub last_seen: DateTime<Utc>,
}

pub trait IStateEstimator: Send + Sync {
    /// Predict next state
    fn predict(&mut self, dt: f32);
    
    /// Update with measurement
    fn update(&mut self, measurement: &State);
    
    /// Get current state estimate
    fn get_state(&self) -> State;
}

pub trait IGoalManager: Send + Sync {
    /// Add a new goal
    fn add_goal(&mut self, goal: MissionGoal);
    
    /// Get active goals
    fn get_active_goals(&self) -> Vec<MissionGoal>;
    
    /// Complete a goal
    fn complete_goal(&mut self, goal_id: Uuid);
}

pub trait ITaskPlanner: Send + Sync {
    /// Plan tasks for a goal
    fn plan(&mut self, goal: &MissionGoal, world: &dyn IWorldModel) -> AriaResult<Vec<Task>>;
}

pub trait IScheduler: Send + Sync {
    /// Schedule tasks
    fn schedule(&mut self, tasks: Vec<Task>) -> Vec<Task>;
    
    /// Get next task to execute
    fn next_task(&mut self) -> Option<Task>;
}

pub trait IPolicyManager: Send + Sync {
    /// Select skill for current context
    fn select_skill(&self, task: &Task, state: &State, world: &dyn IWorldModel) -> AriaResult<String>;
    
    /// Register a policy
    fn register_policy(&mut self, policy: Policy);
}

pub trait ISkill: Send + Sync {
    /// Execute the skill
    async fn execute(&mut self, context: SkillContext) -> AriaResult<Ack>;
    
    /// Skill name
    fn name(&self) -> &str;
}

#[derive(Debug, Clone)]
pub struct SkillContext {
    pub task: Task,
    pub state: State,
    pub world_snapshot: Vec<Entity>,
}

pub trait IRuleChecker: Send + Sync {
    /// Check if action violates rules
    fn check(&self, action: &Command, state: &State) -> AriaResult<bool>;
    
    /// Get violated rules
    fn get_violations(&self, action: &Command, state: &State) -> Vec<String>;
}

pub trait ISafetySupervisor: Send + Sync {
    /// Override/veto unsafe actions
    fn supervise(&self, action: Command, state: &State) -> AriaResult<Command>;
    
    /// Emergency stop
    fn emergency_stop(&mut self) -> Command;
}

pub trait IActionSynthesizer: Send + Sync {
    /// Synthesize action from skill output
    fn synthesize(&self, skill_name: &str, parameters: &std::collections::HashMap<String, f32>, state: &State) -> AriaResult<Command>;
}

pub trait IActionJustifier: Send + Sync {
    /// Generate justification for action
    fn justify(&self, action: &Command, context: &str) -> String;
}

// ============================================================================
// IMA Traits
// ============================================================================

pub trait INoveltyDetector: Send + Sync {
    /// Compute novelty score for observation
    fn compute_novelty(&mut self, observation: &Observation) -> f32;
}

pub trait IHomeostasis: Send + Sync {
    /// Monitor internal state and advise adjustments
    fn advise(&mut self, metrics: &SystemMetrics) -> HomeostasisAdvice;
}

#[derive(Debug, Clone)]
pub struct SystemMetrics {
    pub packet_loss_rate: f32,
    pub latency_ms: f32,
    pub cpu_usage: f32,
    pub memory_mb: f32,
    pub bandwidth_mbps: f32,
}

#[derive(Debug, Clone)]
pub struct HomeostasisAdvice {
    pub adjust_rate: Option<f32>,
    pub adjust_fec: Option<(usize, usize)>,
    pub adjust_codec: Option<String>,
}

pub trait IStigmergy: Send + Sync {
    /// Leave pheromone trace
    fn leave_trace(&mut self, location: Vector3<f32>, trace_type: &str, intensity: f32);
    
    /// Read traces in region
    fn read_traces(&self, region: &BoundingBox) -> Vec<Trace>;
}

#[derive(Debug, Clone)]
pub struct Trace {
    pub location: Vector3<f32>,
    pub trace_type: String,
    pub intensity: f32,
    pub timestamp: DateTime<Utc>,
}
