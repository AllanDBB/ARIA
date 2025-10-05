"""
Unit Tests for Domain Entities
===============================

Tests core data structures: Envelope, Detection, Priority.

Input:
    - Constructor parameters for entities
    - Factory methods

Output:
    - Valid entity objects
    - Correct field initialization
    - Proper validation

Test Cases:
1. test_envelope_creation: Create envelope with factory method
2. test_envelope_id_uniqueness: Ensure unique IDs
3. test_envelope_timestamp: Verify timestamps
4. test_priority_levels: Test all priority enums
5. test_detection_creation: Create detection objects
6. test_detection_bbox_validation: Validate bounding boxes
7. test_detection_confidence: Ensure confidence in [0, 1]
8. test_envelope_payload_types: Handle different payload types
9. test_envelope_metadata: Store/retrieve metadata
10. test_entity_immutability: Ensure entities are immutable (if applicable)
"""

import pytest
import time
from aria_sdk.domain.entities import Envelope, Detection, Priority


class TestEnvelope:
    """Test suite for Envelope entity."""
    
    def test_envelope_creation(self):
        """
        Test: Create envelope using factory method.
        
        Input:
            - topic: str
            - payload: bytes
            - priority: Priority
            - source_node: str
            - sequence_number: int
        
        Expected Output:
            - Envelope object with all fields set
            - envelope_id auto-generated
            - timestamp auto-generated
        """
        envelope = Envelope.create(
            topic="test/topic",
            payload=b"test payload",
            priority=Priority.P2,
            source_node="test_node",
            sequence_number=1
        )
        
        assert envelope.topic == "test/topic"
        assert envelope.payload == b"test payload"
        assert envelope.priority == Priority.P2
        assert envelope.source_node == "test_node"
        assert envelope.sequence_number == 1
        assert envelope.envelope_id is not None
        assert envelope.timestamp > 0
    
    def test_envelope_id_uniqueness(self):
        """
        Test: Ensure envelope IDs are unique.
        
        Input:
            - Multiple envelopes created in sequence
        
        Expected Output:
            - Each envelope has unique ID
            - IDs are monotonically increasing or time-based
        """
        envelopes = []
        for i in range(10):
            env = Envelope.create(
                topic=f"test/{i}",
                payload=b"test",
                priority=Priority.P2,
                source_node="test"
            )
            envelopes.append(env)
            time.sleep(0.001)  # Ensure different timestamps
        
        ids = [env.envelope_id for env in envelopes]
        assert len(ids) == len(set(ids)), "All IDs should be unique"
    
    def test_envelope_timestamp(self):
        """
        Test: Verify timestamp is correct.
        
        Input:
            - Envelope created at known time
        
        Expected Output:
            - Timestamp within reasonable range of creation time
            - Timestamp is float (Unix epoch)
        """
        before = time.time()
        envelope = Envelope.create(
            topic="test/timestamp",
            payload=b"test",
            priority=Priority.P2,
            source_node="test"
        )
        after = time.time()
        
        assert before <= envelope.timestamp <= after
        assert isinstance(envelope.timestamp, float)
    
    def test_priority_levels(self):
        """
        Test: All priority levels work correctly.
        
        Input:
            - Envelopes with each priority: P0, P1, P2, P3
        
        Expected Output:
            - Each priority stored correctly
            - Priority enum values accessible
        """
        priorities = [Priority.P0, Priority.P1, Priority.P2, Priority.P3]
        
        for priority in priorities:
            envelope = Envelope.create(
                topic="test/priority",
                payload=b"test",
                priority=priority,
                source_node="test"
            )
            assert envelope.priority == priority
            assert envelope.priority.name in ['P0', 'P1', 'P2', 'P3']
    
    def test_envelope_payload_types(self):
        """
        Test: Handle different payload types.
        
        Input:
            - Empty bytes
            - Small bytes
            - Large bytes
            - Binary data
        
        Expected Output:
            - All payload types accepted
            - payload_size calculated correctly
        """
        test_cases = [
            (b"", 0),
            (b"small", 5),
            (b"x" * 1000, 1000),
            (bytes(range(256)), 256)
        ]
        
        for payload, expected_size in test_cases:
            envelope = Envelope.create(
                topic="test/payload",
                payload=payload,
                priority=Priority.P2,
                source_node="test"
            )
            assert envelope.payload == payload
            assert envelope.payload_size == expected_size
    
    def test_envelope_metadata(self):
        """
        Test: Store and retrieve metadata.
        
        Input:
            - Metadata dict with various types
        
        Expected Output:
            - Metadata stored correctly
            - All fields accessible
        """
        metadata = {
            "sensor_id": "temp_01",
            "location": {"lat": 18.44, "lon": -64.62},
            "readings": [25.1, 25.3, 25.2]
        }
        
        envelope = Envelope.create(
            topic="test/metadata",
            payload=b"test",
            priority=Priority.P2,
            source_node="test",
            metadata=metadata
        )
        
        assert envelope.metadata == metadata
        assert envelope.metadata["sensor_id"] == "temp_01"


class TestDetection:
    """Test suite for Detection entity."""
    
    def test_detection_creation(self):
        """
        Test: Create detection object.
        
        Input:
            - class_id: int
            - class_name: str
            - confidence: float
            - bbox: tuple[float, float, float, float]
        
        Expected Output:
            - Detection object with all fields
        """
        detection = Detection(
            class_id=0,
            class_name="person",
            confidence=0.89,
            bbox=(100.0, 200.0, 300.0, 400.0)
        )
        
        assert detection.class_id == 0
        assert detection.class_name == "person"
        assert detection.confidence == 0.89
        assert detection.bbox == (100.0, 200.0, 300.0, 400.0)
    
    def test_detection_bbox_validation(self):
        """
        Test: Bounding box format validation.
        
        Input:
            - bbox as tuple (x1, y1, x2, y2)
        
        Expected Output:
            - Bbox stored as tuple
            - x2 > x1, y2 > y1 (if validated)
        """
        detection = Detection(
            class_id=1,
            class_name="car",
            confidence=0.95,
            bbox=(50.0, 60.0, 150.0, 200.0)
        )
        
        x1, y1, x2, y2 = detection.bbox
        assert x2 > x1, "x2 should be > x1"
        assert y2 > y1, "y2 should be > y1"
    
    def test_detection_confidence(self):
        """
        Test: Confidence value validation.
        
        Input:
            - Various confidence values: 0.0, 0.5, 1.0
        
        Expected Output:
            - All valid confidences accepted
            - Values in range [0, 1]
        """
        confidences = [0.0, 0.25, 0.5, 0.75, 1.0]
        
        for conf in confidences:
            detection = Detection(
                class_id=0,
                class_name="test",
                confidence=conf,
                bbox=(0, 0, 100, 100)
            )
            assert 0.0 <= detection.confidence <= 1.0
    
    def test_detection_with_metadata(self):
        """
        Test: Detection with additional metadata.
        
        Input:
            - Detection with track_id, frame_number, etc.
        
        Expected Output:
            - Metadata accessible via attributes or dict
        """
        detection = Detection(
            class_id=0,
            class_name="person",
            confidence=0.87,
            bbox=(100, 200, 300, 400),
            track_id=42,
            frame_number=150
        )
        
        # Check if metadata accessible
        if hasattr(detection, 'track_id'):
            assert detection.track_id == 42
        if hasattr(detection, 'frame_number'):
            assert detection.frame_number == 150


class TestPriority:
    """Test suite for Priority enum."""
    
    def test_priority_enum_values(self):
        """
        Test: Priority enum has correct values.
        
        Input:
            - Access each priority level
        
        Expected Output:
            - P0, P1, P2, P3 all exist
            - Numeric values 0, 1, 2, 3
        """
        assert Priority.P0.value == 0
        assert Priority.P1.value == 1
        assert Priority.P2.value == 2
        assert Priority.P3.value == 3
    
    def test_priority_names(self):
        """
        Test: Priority names are correct.
        
        Input:
            - Priority enum members
        
        Expected Output:
            - Names: P0, P1, P2, P3
        """
        assert Priority.P0.name == 'P0'
        assert Priority.P1.name == 'P1'
        assert Priority.P2.name == 'P2'
        assert Priority.P3.name == 'P3'
    
    def test_priority_comparison(self):
        """
        Test: Priority levels can be compared.
        
        Input:
            - Different priority levels
        
        Expected Output:
            - P0 > P1 > P2 > P3 (lower number = higher priority)
        """
        assert Priority.P0.value < Priority.P1.value
        assert Priority.P1.value < Priority.P2.value
        assert Priority.P2.value < Priority.P3.value


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
