//! ARIA Telemetry Pipeline
//! 
//! Production-grade telemetry system with:
//! - Semantics (Protobuf codec with schema registry)
//! - Optimization (LZ4/Zstd compression + delta encoding)
//! - CCEM (Channel Conditioning & Error Mitigation)
//! - FEC (Forward Error Correction)
//! - Packetization (fragmentation/defragmentation)
//! - Security (sign-then-encrypt)
//! - QoS (priority queues with token bucket)
//! - Transports (QUIC, MQTT-SN, DTN)
//! - Recovery (loss concealment + integrity checks)

pub mod codec;
pub mod compression;
pub mod delta;
pub mod ccem;
pub mod fec;
pub mod packetization;
pub mod crypto;
pub mod qos;
pub mod transport;
pub mod recovery;
pub mod router;
pub mod link_health;

pub use codec::*;
pub use compression::*;
pub use delta::*;
pub use ccem::*;
pub use fec::*;
pub use packetization::*;
pub use crypto::*;
pub use qos::*;
pub use transport::*;
pub use recovery::*;
pub use router::*;
pub use link_health::*;
