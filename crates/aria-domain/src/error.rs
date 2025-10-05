//! Error Types

use thiserror::Error;

#[derive(Debug, Error)]
pub enum AriaError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    
    #[error("Serialization error: {0}")]
    Serialization(String),
    
    #[error("Compression error: {0}")]
    Compression(String),
    
    #[error("Cryptography error: {0}")]
    Crypto(String),
    
    #[error("FEC error: {0}")]
    Fec(String),
    
    #[error("Transport error: {0}")]
    Transport(String),
    
    #[error("Model error: {0}")]
    Model(String),
    
    #[error("Sensor error: {0}")]
    Sensor(String),
    
    #[error("Actuator error: {0}")]
    Actuator(String),
    
    #[error("Planning error: {0}")]
    Planning(String),
    
    #[error("Safety violation: {0}")]
    Safety(String),
    
    #[error("Configuration error: {0}")]
    Config(String),
    
    #[error("Timeout")]
    Timeout,
    
    #[error("Not implemented: {0}")]
    NotImplemented(String),
    
    #[error("Invalid state: {0}")]
    InvalidState(String),
    
    #[error("Unknown error: {0}")]
    Unknown(String),
}

pub type AriaResult<T> = Result<T, AriaError>;
