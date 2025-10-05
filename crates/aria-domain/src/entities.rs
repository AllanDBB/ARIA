//! Domain Entities
//! 
//! Core data structures representing the robot's world, commands, and state.

use chrono::{DateTime, Utc};
use nalgebra::{Vector3, UnitQuaternion};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

/// Envelope wraps all messages in the telemetry system
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Envelope {
    pub id: Uuid,
    pub timestamp: DateTime<Utc>,
    pub schema_id: u32,
    pub priority: Priority,
    pub topic: String,
    pub payload: Vec<u8>,
    pub metadata: EnvelopeMetadata,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum Priority {
    P0 = 0, // Critical: commands, acks, safety
    P1 = 1, // High: state updates, control
    P2 = 2, // Medium: perception data
    P3 = 3, // Low: logs, diagnostics
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EnvelopeMetadata {
    pub source_node: String,
    pub sequence_number: u64,
    pub fragment_info: Option<FragmentInfo>,
    pub fec_info: Option<FecInfo>,
    pub crypto_info: Option<CryptoInfo>,
    pub qos_class: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FragmentInfo {
    pub fragment_id: u32,
    pub total_fragments: u32,
    pub fragment_offset: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FecInfo {
    pub k: u32, // Original data blocks
    pub m: u32, // Redundancy blocks
    pub block_id: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CryptoInfo {
    pub signature: Vec<u8>,
    pub key_id: String,
    pub nonce: Vec<u8>,
}

/// Raw sensor sample
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RawSample {
    pub sensor_id: String,
    pub timestamp: DateTime<Utc>,
    pub data: SensorData,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum SensorData {
    Image { width: u32, height: u32, channels: u8, data: Vec<u8> },
    Audio { sample_rate: u32, channels: u8, samples: Vec<f32> },
    Imu { accel: Vector3<f32>, gyro: Vector3<f32>, mag: Option<Vector3<f32>> },
    Lidar { points: Vec<Vector3<f32>>, intensities: Vec<f32> },
    Temperature { celsius: f32 },
    Depth { width: u32, height: u32, data: Vec<f32> },
}

/// Command to actuators
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Command {
    pub id: Uuid,
    pub timestamp: DateTime<Utc>,
    pub actuator_id: String,
    pub action: ActuatorAction,
    pub justification: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ActuatorAction {
    Motion { velocity: Vector3<f32>, angular: Vector3<f32> },
    Servo { joint_id: String, position: f32, velocity: f32 },
    Digital { pin: u8, value: bool },
    AudioOut { samples: Vec<f32>, sample_rate: u32 },
    Custom { data: Vec<u8> },
}

/// Acknowledgment
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Ack {
    pub command_id: Uuid,
    pub timestamp: DateTime<Utc>,
    pub success: bool,
    pub error_code: Option<u32>,
    pub message: Option<String>,
}

/// Robot state
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct State {
    pub timestamp: DateTime<Utc>,
    pub pose: Pose,
    pub velocity: Twist,
    pub battery_percent: f32,
    pub mode: RobotMode,
    pub custom_state: HashMap<String, f32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Pose {
    pub position: Vector3<f32>,
    pub orientation: UnitQuaternion<f32>,
    pub covariance: Option<[f32; 36]>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Twist {
    pub linear: Vector3<f32>,
    pub angular: Vector3<f32>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum RobotMode {
    Idle,
    Manual,
    Autonomous,
    SafeStop,
    Error,
}

/// Mission goal
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MissionGoal {
    pub id: Uuid,
    pub priority: f32,
    pub goal_type: GoalType,
    pub deadline: Option<DateTime<Utc>>,
    pub constraints: Vec<Constraint>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum GoalType {
    NavigateTo { target: Vector3<f32>, tolerance: f32 },
    Explore { region: BoundingBox },
    Inspect { object_id: String, distance: f32 },
    FollowPath { waypoints: Vec<Vector3<f32>> },
    Dock,
    Custom { description: String, parameters: HashMap<String, f32> },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BoundingBox {
    pub min: Vector3<f32>,
    pub max: Vector3<f32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Constraint {
    pub name: String,
    pub constraint_type: ConstraintType,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ConstraintType {
    MaxVelocity(f32),
    AvoidRegion(BoundingBox),
    MinBattery(f32),
    TimeWindow { start: DateTime<Utc>, end: DateTime<Utc> },
    Custom { rule: String },
}

/// Task in the planning hierarchy
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Task {
    pub id: Uuid,
    pub name: String,
    pub parent_goal: Uuid,
    pub skill_name: String,
    pub parameters: HashMap<String, f32>,
    pub preconditions: Vec<String>,
    pub expected_duration: f32,
    pub status: TaskStatus,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TaskStatus {
    Pending,
    Running,
    Completed,
    Failed,
    Aborted,
}

/// Policy for skill selection
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Policy {
    pub id: Uuid,
    pub name: String,
    pub condition: String,
    pub skill_name: String,
    pub parameters: HashMap<String, f32>,
    pub priority: f32,
}

/// Detection from YOLO
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Detection {
    pub class_id: u32,
    pub class_name: String,
    pub confidence: f32,
    pub bbox: BoundingBox2D,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BoundingBox2D {
    pub x: f32,
    pub y: f32,
    pub width: f32,
    pub height: f32,
}

/// SLAM pose estimate
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SlamPose {
    pub timestamp: DateTime<Utc>,
    pub pose: Pose,
    pub keyframe_id: Option<u64>,
    pub tracking_quality: f32,
}

/// Audio event (VAD/SED)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AudioEvent {
    pub timestamp: DateTime<Utc>,
    pub event_type: AudioEventType,
    pub confidence: f32,
    pub duration: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AudioEventType {
    Voice,
    Alarm,
    Crash,
    Music,
    Silence,
    Unknown,
}
