"""
Tests for telemetry codec module.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from aria_sdk.domain.entities import Envelope, Priority, EnvelopeMetadata
from aria_sdk.telemetry.codec import ProtobufCodec


class TestProtobufCodec:
    """Test suite for ProtobufCodec."""
    
    @pytest.fixture
    def codec(self):
        """Create a codec instance."""
        return ProtobufCodec()
    
    @pytest.fixture
    def sample_envelope(self):
        """Create a sample envelope for testing."""
        return Envelope(
            id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            schema_id=1,
            priority=Priority.P1,
            topic="test/sensor/camera",
            payload=b"test payload data",
            metadata=EnvelopeMetadata(
                source_node="test_node",
                sequence_number=1
            )
        )
    
    def test_encode_decode_roundtrip(self, codec, sample_envelope):
        """Test that encoding and decoding preserves data."""
        # Encode
        encoded = codec.encode(sample_envelope)
        
        # Verify encoded is bytes
        assert isinstance(encoded, bytes)
        assert len(encoded) > 0
        
        # Decode
        decoded = codec.decode(encoded)
        
        # Verify fields match
        assert decoded.id == sample_envelope.id
        assert decoded.timestamp == sample_envelope.timestamp
        assert decoded.priority == sample_envelope.priority
        assert decoded.topic == sample_envelope.topic
        assert decoded.payload == sample_envelope.payload
    
    def test_encode_all_priorities(self, codec):
        """Test encoding envelopes with different priorities."""
        for priority in Priority:
            envelope = Envelope(
                id=uuid4(),
                timestamp=datetime.now(timezone.utc),
                schema_id=1,
                priority=priority,
                topic="test/priority",
                payload=b"data",
                metadata=EnvelopeMetadata(
                    source_node="test_node",
                    sequence_number=1
                )
            )
            
            encoded = codec.encode(envelope)
            decoded = codec.decode(encoded)
            
            assert decoded.priority == priority
    
    def test_encode_large_payload(self, codec):
        """Test encoding an envelope with a large payload."""
        large_payload = b"x" * 10000  # 10KB
        
        envelope = Envelope(
            id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            schema_id=1,
            priority=Priority.P2,
            topic="test/large",
            payload=large_payload,
            metadata=EnvelopeMetadata(
                source_node="test_node",
                sequence_number=1
            )
        )
        
        encoded = codec.encode(envelope)
        decoded = codec.decode(encoded)
        
        assert decoded.payload == large_payload
    
    def test_encode_empty_payload(self, codec):
        """Test encoding an envelope with empty payload."""
        envelope = Envelope(
            id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            schema_id=1,
            priority=Priority.P3,
            topic="test/empty",
            payload=b"",
            metadata=EnvelopeMetadata(
                source_node="test_node",
                sequence_number=1
            )
        )
        
        encoded = codec.encode(envelope)
        decoded = codec.decode(encoded)
        
        assert decoded.payload == b""
    
    def test_decode_invalid_magic(self, codec):
        """Test that decoding rejects invalid magic bytes."""
        invalid_data = b"\xFF\xFF\x01\x00\x00\x00\x00"
        
        with pytest.raises(ValueError, match="Invalid magic bytes"):
            codec.decode(invalid_data)
    
    def test_decode_invalid_version(self, codec):
        """Test that decoding rejects unsupported versions."""
        invalid_data = b"\xAA\xBB\xFF\x00\x00\x00\x00"
        
        with pytest.raises(ValueError, match="Unsupported version"):
            codec.decode(invalid_data)
    
    def test_decode_truncated_data(self, codec):
        """Test that decoding handles truncated data gracefully."""
        truncated_data = b"\xAA\xBB\x01\x00\x00\x00\x10"
        
        with pytest.raises(ValueError):
            codec.decode(truncated_data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
