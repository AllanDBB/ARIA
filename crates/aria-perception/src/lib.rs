//! ARIA Perception SDK
//! 
//! ML models for object detection (YOLO), SLAM/VIO, VAD/SED, ASR, and Audio DSP.
//! Uses ONNX Runtime with automatic backend selection (CUDA/TensorRT/CPU).

pub mod yolo;
pub mod slam;
pub mod audio;

pub use yolo::*;
pub use slam::*;
pub use audio::*;
