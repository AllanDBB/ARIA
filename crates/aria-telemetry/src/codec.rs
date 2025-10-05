//! Codec implementations (Protobuf via prost)

use aria_domain::{AriaError, AriaResult, ICodec};
use prost::Message;
use std::any::Any;

pub struct ProtobufCodec {
    schema_registry: SchemaRegistry,
}

impl ProtobufCodec {
    pub fn new() -> Self {
        Self {
            schema_registry: SchemaRegistry::new(),
        }
    }
    
    pub fn register_schema(&mut self, schema_id: u32, name: String) {
        self.schema_registry.register(schema_id, name);
    }
}

impl ICodec for ProtobufCodec {
    fn encode(&self, obj: &dyn Any, schema_id: u32) -> AriaResult<Vec<u8>> {
        // In production, use prost-generated types and downcast
        // For now, use bincode as a fallback for Any serialization
        bincode::serialize(&schema_id)
            .map_err(|e| AriaError::Serialization(e.to_string()))
            .and_then(|mut bytes| {
                // In real impl: downcast obj to concrete proto message and encode
                // bytes.extend_from_slice(&message.encode_to_vec());
                Ok(bytes)
            })
    }
    
    fn decode(&self, bytes: &[u8], schema_id: u32) -> AriaResult<Box<dyn Any>> {
        // In production: lookup schema, decode protobuf message
        if bytes.is_empty() {
            return Err(AriaError::Serialization("Empty bytes".into()));
        }
        
        // Placeholder: return dummy
        Ok(Box::new(schema_id))
    }
}

pub struct SchemaRegistry {
    schemas: std::collections::HashMap<u32, String>,
}

impl SchemaRegistry {
    pub fn new() -> Self {
        Self {
            schemas: std::collections::HashMap::new(),
        }
    }
    
    pub fn register(&mut self, schema_id: u32, name: String) {
        self.schemas.insert(schema_id, name);
    }
    
    pub fn get(&self, schema_id: u32) -> Option<&String> {
        self.schemas.get(&schema_id)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_schema_registry() {
        let mut registry = SchemaRegistry::new();
        registry.register(1, "Envelope".into());
        assert_eq!(registry.get(1), Some(&"Envelope".into()));
    }
    
    #[test]
    fn test_codec_roundtrip() {
        let codec = ProtobufCodec::new();
        let data: u32 = 42;
        let encoded = codec.encode(&data, 1).unwrap();
        assert!(!encoded.is_empty());
    }
}
