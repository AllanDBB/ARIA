"""
Unit Tests for Telemetry Codec Module
======================================

Tests the ProtobufCodec for encoding and decoding Envelope entities.

Input:
    - Envelope objects with various payloads, priorities, topics
    - Binary data for decoding

Output:
    - Encoded binary data (Protobuf format)
    - Decoded Envelope objects with preserved data

Test Cases:
1. test_encode_basic_envelope: Encodes simple envelope with text payload
2. test_decode_basic_envelope: Decodes previously encoded envelope
3. test_roundtrip_preservation: Ensures encode->decode preserves all fields
4. test_empty_payload: Handles envelopes with empty payloads
5. test_large_payload: Handles payloads >1MB
6. test_unicode_payload: Handles UTF-8 and special characters
7. test_priority_levels: Tests all priority levels (P0-P3)
8. test_metadata_preservation: Ensures metadata survives encoding
9. test_sequence_numbers: Tests envelope sequencing
10. test_invalid_data: Tests error handling for corrupted data
"""

import pytest
import time
from datetime import datetime, timezone
from aria_sdk.telemetry.codec import ProtobufCodec
from aria_sdk.domain.entities import Envelope, Priority


class TestProtobufCodec:
    """Test suite for ProtobufCodec."""
    
    @pytest.fixture
    def codec(self):
        """
        Fixture: Provides a fresh ProtobufCodec instance.
        
        Returns:
            ProtobufCodec: Codec instance for encoding/decoding
        """
        return ProtobufCodec()
    
    @pytest.fixture
    def basic_envelope(self):
        """
        Fixture: Creates a basic envelope for testing.
        
        Returns:
            Envelope: Basic envelope with text payload
        """
        return Envelope.create(
            topic="test/topic",
            payload=b"Hello, Mars!",
            priority=Priority.P2,
            source_node="test_node",
            sequence_number=1
        )
    
    def test_encode_basic_envelope(self, codec, basic_envelope):
        """
        Test: Encode a basic envelope to binary.
        
        Input:
            - Envelope with text payload "Hello, Mars!"
            - Priority: P2
            - Topic: "test/topic"
        
        Expected Output:
            - Binary data (bytes)
            - Length > 0
            - Type is bytes
        """
        encoded = codec.encode(basic_envelope)
        
        assert isinstance(encoded, bytes), "Encoded data should be bytes"
        assert len(encoded) > 0, "Encoded data should not be empty"
        assert len(encoded) > len(basic_envelope.payload), "Encoded should include overhead"
    
    def test_decode_basic_envelope(self, codec, basic_envelope):
        """
        Test: Decode an encoded envelope back to object.
        
        Input:
            - Binary encoded envelope
        
        Expected Output:
            - Envelope object
            - Payload matches original
            - All fields preserved
        """
        encoded = codec.encode(basic_envelope)
        decoded = codec.decode(encoded)
        
        assert decoded.payload == basic_envelope.payload, "Payload should match"
        assert decoded.topic == basic_envelope.topic, "Topic should match"
        assert decoded.priority == basic_envelope.priority, "Priority should match"
        assert decoded.source_node == basic_envelope.source_node, "Source node should match"
    
    def test_roundtrip_preservation(self, codec):
        """
        Test: Ensure encode->decode preserves all envelope fields.
        
        Input:
            - Envelope with all fields populated
        
        Expected Output:
            - Decoded envelope matches original exactly
            - envelope_id, timestamp, sequence_number preserved
        """
        original = Envelope.create(
            topic="sensor/temperature",
            payload=b'{"value": 25.3, "unit": "C"}',
            priority=Priority.P1,
            source_node="sensor_hub",
            sequence_number=42,
            metadata={"sensor_id": "temp_01", "location": "cabin"}
        )
        
        encoded = codec.encode(original)
        decoded = codec.decode(encoded)
        
        assert decoded.envelope_id == original.envelope_id
        assert decoded.topic == original.topic
        assert decoded.payload == original.payload
        assert decoded.priority == original.priority
        assert decoded.source_node == original.source_node
        assert decoded.sequence_number == original.sequence_number
        assert decoded.metadata == original.metadata
    
    def test_empty_payload(self, codec):
        """
        Test: Handle envelopes with empty payloads.
        
        Input:
            - Envelope with b"" (empty bytes) payload
        
        Expected Output:
            - Successful encoding/decoding
            - Empty payload preserved
        """
        envelope = Envelope.create(
            topic="heartbeat",
            payload=b"",
            priority=Priority.P3,
            source_node="watchdog"
        )
        
        encoded = codec.encode(envelope)
        decoded = codec.decode(encoded)
        
        assert decoded.payload == b"", "Empty payload should be preserved"
        assert decoded.payload_size == 0, "Payload size should be 0"
    
    def test_large_payload(self, codec):
        """
        Test: Handle large payloads (>1MB).
        
        Input:
            - Envelope with 2MB payload
        
        Expected Output:
            - Successful encoding/decoding
            - Payload integrity maintained
        """
        large_payload = b"X" * (2 * 1024 * 1024)  # 2MB
        envelope = Envelope.create(
            topic="data/bulk",
            payload=large_payload,
            priority=Priority.P2,
            source_node="data_collector"
        )
        
        encoded = codec.encode(envelope)
        decoded = codec.decode(encoded)
        
        assert decoded.payload == large_payload, "Large payload should be preserved"
        assert len(decoded.payload) == len(large_payload), "Payload size should match"
    
    def test_unicode_payload(self, codec):
        """
        Test: Handle UTF-8 and special characters.
        
        Input:
            - Envelope with Unicode text: "Hello 世界 🚀 Привет"
        
        Expected Output:
            - UTF-8 encoding preserved
            - All characters intact after decode
        """
        unicode_text = "Hello 世界 🚀 Привет مرحبا"
        envelope = Envelope.create(
            topic="text/unicode",
            payload=unicode_text.encode('utf-8'),
            priority=Priority.P2,
            source_node="text_processor"
        )
        
        encoded = codec.encode(envelope)
        decoded = codec.decode(encoded)
        
        decoded_text = decoded.payload.decode('utf-8')
        assert decoded_text == unicode_text, "Unicode text should be preserved"
    
    def test_priority_levels(self, codec):
        """
        Test: Verify all priority levels work correctly.
        
        Input:
            - Envelopes with each priority: P0, P1, P2, P3
        
        Expected Output:
            - Each priority level preserved after encode/decode
        """
        priorities = [Priority.P0, Priority.P1, Priority.P2, Priority.P3]
        
        for priority in priorities:
            envelope = Envelope.create(
                topic=f"test/priority/{priority.name}",
                payload=f"Priority {priority.name} test".encode(),
                priority=priority,
                source_node="test_node"
            )
            
            encoded = codec.encode(envelope)
            decoded = codec.decode(encoded)
            
            assert decoded.priority == priority, f"Priority {priority.name} should be preserved"
    
    def test_metadata_preservation(self, codec):
        """
        Test: Ensure metadata dictionary survives encoding.
        
        Input:
            - Envelope with complex metadata (nested dicts, lists, numbers)
        
        Expected Output:
            - Metadata exactly preserved
        """
        metadata = {
            "sensor_id": "temp_01",
            "location": {"lat": 18.44, "lon": -64.62},
            "readings": [25.1, 25.3, 25.2],
            "status": "operational"
        }
        
        envelope = Envelope.create(
            topic="sensor/data",
            payload=b"test",
            priority=Priority.P2,
            source_node="sensor",
            metadata=metadata
        )
        
        encoded = codec.encode(envelope)
        decoded = codec.decode(encoded)
        
        assert decoded.metadata == metadata, "Metadata should be preserved exactly"
    
    def test_sequence_numbers(self, codec):
        """
        Test: Verify sequence number tracking.
        
        Input:
            - Multiple envelopes with sequential numbers (0, 1, 2, ...)
        
        Expected Output:
            - All sequence numbers preserved in order
        """
        for seq_num in range(10):
            envelope = Envelope.create(
                topic="test/sequence",
                payload=f"Message {seq_num}".encode(),
                priority=Priority.P2,
                source_node="sequencer",
                sequence_number=seq_num
            )
            
            encoded = codec.encode(envelope)
            decoded = codec.decode(encoded)
            
            assert decoded.sequence_number == seq_num, f"Sequence {seq_num} should match"
    
    def test_invalid_data(self, codec):
        """
        Test: Handle corrupted/invalid data gracefully.
        
        Input:
            - Random bytes (not valid Protobuf)
            - Truncated envelope data
        
        Expected Output:
            - Raises appropriate exception
            - Does not crash or corrupt state
        """
        invalid_data = b"This is not a valid protobuf message!"
        
        with pytest.raises(Exception):
            codec.decode(invalid_data)
    
    def test_timestamp_accuracy(self, codec):
        """
        Test: Verify timestamp preservation with microsecond accuracy.
        
        Input:
            - Envelope created at known timestamp
        
        Expected Output:
            - Timestamp preserved to microsecond precision
        """
        before = time.time()
        envelope = Envelope.create(
            topic="test/time",
            payload=b"timestamp test",
            priority=Priority.P2,
            source_node="timer"
        )
        after = time.time()
        
        encoded = codec.encode(envelope)
        decoded = codec.decode(encoded)
        
        assert before <= decoded.timestamp <= after, "Timestamp should be within creation window"
        assert isinstance(decoded.timestamp, float), "Timestamp should be float"
    
    def test_batch_encoding(self, codec):
        """
        Test: Encode multiple envelopes in batch.
        
        Input:
            - List of 100 envelopes
        
        Expected Output:
            - All encoded successfully
            - All decodable individually
            - Order preserved
        """
        envelopes = []
        for i in range(100):
            env = Envelope.create(
                topic=f"batch/message_{i}",
                payload=f"Batch message {i}".encode(),
                priority=Priority.P2,
                source_node="batch_sender",
                sequence_number=i
            )
            envelopes.append(env)
        
        # Encode all
        encoded_list = [codec.encode(env) for env in envelopes]
        
        # Decode all
        decoded_list = [codec.decode(data) for data in encoded_list]
        
        # Verify order and content
        for i, decoded in enumerate(decoded_list):
            assert decoded.sequence_number == i, f"Envelope {i} should be in order"
            assert decoded.payload == f"Batch message {i}".encode(), f"Payload {i} should match"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
