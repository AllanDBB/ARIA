//! ARIA Domain Layer
//! 
//! Core domain entities, value objects, and trait definitions for the ARIA SDK.
//! This layer is technology-agnostic and defines the business logic interfaces.

pub mod entities;
pub mod traits;
pub mod error;

pub use entities::*;
pub use traits::*;
pub use error::*;
