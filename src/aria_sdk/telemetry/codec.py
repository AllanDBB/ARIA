"""
ARIA SDK - Telemetry Codec Module

Provides Protobuf-based serialization for all telemetry envelopes.
"""

from typing import Optional
import struct
from datetime import datetime, timezone
from uuid import UUID

from aria_sdk.domain.entities import Envelope, Priority, EnvelopeMetadata, FragmentInfo, FecInfo, CryptoInfo
from aria_sdk.domain.protocols import ICodec


class ProtobufCodec(ICodec):
    """
    Protobuf codec for telemetry envelopes.
    
    Wire format:
    - Magic bytes: 0xAA 0xBB (2 bytes) for framing detection
    - Version: 1 byte (currently 0x01)
    - Payload length: 4 bytes (big-endian uint32)
    - Serialized protobuf message
    
    TODO: Generate actual .proto definitions and use protobuf library.
    This is a simplified binary format for demonstration.
    """
    
    MAGIC = b'\xAA\xBB'
    VERSION = 1
    
    def encode(self, envelope: Envelope) -> bytes:
        """
        Encode an envelope to bytes.
        
        Args:
            envelope: The envelope to encode
            
        Returns:
            Serialized bytes
            
        Raises:
            ValueError: If encoding fails
        """
        try:
            # Build simplified binary format (TODO: replace with real protobuf)
            parts = []
            
            # Header
            parts.append(self.MAGIC)
            parts.append(struct.pack('B', self.VERSION))
            
            # Envelope ID (UUID as 16 bytes)
            parts.append(envelope.id.bytes)
            
            # Timestamp (ISO 8601 string)
            timestamp_str = envelope.timestamp.isoformat().encode('utf-8')
            parts.append(struct.pack('!H', len(timestamp_str)))
            parts.append(timestamp_str)
            
            # Schema ID (4 bytes)
            parts.append(struct.pack('!I', envelope.schema_id))
            
            # Priority (1 byte)
            parts.append(struct.pack('B', envelope.priority.value))
            
            # Topic (length-prefixed string)
            topic_bytes = envelope.topic.encode('utf-8')
            parts.append(struct.pack('!H', len(topic_bytes)))
            parts.append(topic_bytes)
            
            # Payload (length-prefixed bytes)
            parts.append(struct.pack('!I', len(envelope.payload)))
            parts.append(envelope.payload)
            
            # Metadata - source_node and sequence_number
            source_node_bytes = envelope.metadata.source_node.encode('utf-8')
            parts.append(struct.pack('!H', len(source_node_bytes)))
            parts.append(source_node_bytes)
            parts.append(struct.pack('!I', envelope.metadata.sequence_number))
            
            # Metadata (simplified - only fragment info for now)
            if envelope.metadata and envelope.metadata.fragment_info:
                parts.append(b'\x01')  # Has fragment info
                frag = envelope.metadata.fragment_info
                parts.append(struct.pack('!I', frag.fragment_id))
                parts.append(struct.pack('!I', frag.total_fragments))
                parts.append(struct.pack('!I', frag.offset))
                parts.append(struct.pack('!I', frag.length))
                parts.append(frag.message_id.bytes)
            else:
                parts.append(b'\x00')  # No fragment info
            
            # Combine all parts
            payload_data = b''.join(parts[2:])  # Everything after header
            
            # Build final message with length prefix
            final_parts = [
                self.MAGIC,
                struct.pack('B', self.VERSION),
                struct.pack('!I', len(payload_data)),
                payload_data
            ]
            
            return b''.join(final_parts)
            
        except Exception as e:
            raise ValueError(f"Encoding failed: {e}") from e
    
    def decode(self, data: bytes) -> Envelope:
        """
        Decode bytes to an envelope.
        
        Args:
            data: Serialized envelope bytes
            
        Returns:
            Decoded envelope
            
        Raises:
            ValueError: If decoding fails
        """
        try:
            offset = 0
            
            # Check magic bytes
            magic = data[offset:offset+2]
            if magic != self.MAGIC:
                raise ValueError(f"Invalid magic bytes: {magic.hex()}")
            offset += 2
            
            # Check version
            version = struct.unpack('B', data[offset:offset+1])[0]
            if version != self.VERSION:
                raise ValueError(f"Unsupported version: {version}")
            offset += 1
            
            # Read payload length
            payload_len = struct.unpack('!I', data[offset:offset+4])[0]
            offset += 4
            
            # Envelope ID (UUID)
            envelope_id = UUID(bytes=data[offset:offset+16])
            offset += 16
            
            # Timestamp
            timestamp_len = struct.unpack('!H', data[offset:offset+2])[0]
            offset += 2
            timestamp_str = data[offset:offset+timestamp_len].decode('utf-8')
            timestamp = datetime.fromisoformat(timestamp_str)
            offset += timestamp_len
            
            # Schema ID
            schema_id = struct.unpack('!I', data[offset:offset+4])[0]
            offset += 4
            
            # Priority
            priority_val = struct.unpack('B', data[offset:offset+1])[0]
            priority = Priority(priority_val)
            offset += 1
            
            # Topic
            topic_len = struct.unpack('!H', data[offset:offset+2])[0]
            offset += 2
            topic = data[offset:offset+topic_len].decode('utf-8')
            offset += topic_len
            
            # Payload
            payload_size = struct.unpack('!I', data[offset:offset+4])[0]
            offset += 4
            payload = data[offset:offset+payload_size]
            offset += payload_size
            
            # Metadata - source_node and sequence_number
            source_node_len = struct.unpack('!H', data[offset:offset+2])[0]
            offset += 2
            source_node = data[offset:offset+source_node_len].decode('utf-8')
            offset += source_node_len
            sequence_number = struct.unpack('!I', data[offset:offset+4])[0]
            offset += 4
            
            # Metadata (fragment info)
            has_fragment = struct.unpack('B', data[offset:offset+1])[0]
            offset += 1
            
            fragment_info: Optional[FragmentInfo] = None
            if has_fragment:
                frag_id = struct.unpack('!I', data[offset:offset+4])[0]
                offset += 4
                total_frags = struct.unpack('!I', data[offset:offset+4])[0]
                offset += 4
                frag_offset = struct.unpack('!I', data[offset:offset+4])[0]
                offset += 4
                frag_length = struct.unpack('!I', data[offset:offset+4])[0]
                offset += 4
                msg_id = UUID(bytes=data[offset:offset+16])
                offset += 16
                
                fragment_info = FragmentInfo(
                    fragment_id=frag_id,
                    total_fragments=total_frags,
                    offset=frag_offset,
                    length=frag_length,
                    message_id=msg_id
                )
            
            # Create metadata
            metadata = EnvelopeMetadata(
                source_node=source_node,
                sequence_number=sequence_number,
                fragment_info=fragment_info
            )
            
            return Envelope(
                id=envelope_id,
                timestamp=timestamp,
                schema_id=schema_id,
                priority=priority,
                topic=topic,
                payload=payload,
                metadata=metadata
            )
            
        except Exception as e:
            raise ValueError(f"Decoding failed: {e}") from e


# TODO: Replace with proper protobuf definitions
# 
# Example .proto file structure:
#
# syntax = "proto3";
# package aria.telemetry;
#
# message Envelope {
#   string id = 1;            // UUID as string
#   int64 timestamp = 2;      // Unix timestamp (nanoseconds)
#   Priority priority = 3;
#   string topic = 4;
#   bytes payload = 5;
#   EnvelopeMetadata metadata = 6;
# }
#
# enum Priority {
#   P0_CRITICAL = 0;
#   P1_HIGH = 1;
#   P2_NORMAL = 2;
#   P3_LOW = 3;
# }
#
# message EnvelopeMetadata {
#   FragmentInfo fragment_info = 1;
#   FecInfo fec_info = 2;
#   CryptoInfo crypto_info = 3;
# }
#
# message FragmentInfo {
#   uint32 fragment_id = 1;
#   uint32 total_fragments = 2;
#   uint32 offset = 3;
#   uint32 length = 4;
#   string message_id = 5;
# }
#
# Generate with: protoc --python_out=. telemetry.proto
