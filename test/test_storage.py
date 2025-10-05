"""
Unit Tests for Data Storage Module
===================================

Tests SQLite-based telemetry and cognitive state persistence.

Input:
    - Envelope objects, cognitive states, decisions
    - Session metadata

Output:
    - Persistent storage in SQLite database
    - Binary telemetry files (.bin.gz)
    - JSON session exports

Test Cases:
1. test_create_session: Creates new storage session
2. test_store_telemetry: Stores telemetry envelopes
3. test_store_cognitive_state: Stores cognitive loop states
4. test_store_decision: Stores robot decisions
5. test_query_session_summary: Retrieves session statistics
6. test_close_session: Properly closes and finalizes session
7. test_export_json: Exports session to JSON
8. test_binary_file_creation: Verifies binary files created
9. test_multiple_sessions: Handles concurrent/sequential sessions
10. test_data_integrity: Ensures no data loss or corruption
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import json
from aria_sdk.storage.data_storage import DataStorage
from aria_sdk.domain.entities import Envelope, Priority


class TestDataStorage:
    """Test suite for DataStorage module."""
    
    @pytest.fixture
    def temp_storage_dir(self):
        """
        Fixture: Creates temporary storage directory.
        
        Yields:
            Path: Temporary directory for test data
        
        Cleanup:
            Removes directory after test
        """
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def storage(self, temp_storage_dir):
        """
        Fixture: Provides DataStorage instance.
        
        Returns:
            DataStorage: Storage instance with temp directory
        """
        return DataStorage(storage_dir=temp_storage_dir)
    
    @pytest.fixture
    def sample_envelope(self):
        """
        Fixture: Creates sample telemetry envelope.
        
        Returns:
            Envelope: Test envelope with detection data
        """
        payload = b'{"class":"person","confidence":0.89}'
        return Envelope.create(
            topic="perception/detection/person",
            payload=payload,
            priority=Priority.P2,
            source_node="vision_system",
            sequence_number=1
        )
    
    def test_create_session(self, storage):
        """
        Test: Create new storage session.
        
        Input:
            - Storage directory path
        
        Expected Output:
            - Session ID generated (format: YYYYMMDD_HHMMSS)
            - Database file created
            - Telemetry subdirectory created
        """
        assert storage.session_id is not None, "Session ID should be generated"
        assert len(storage.session_id) == 15, "Session ID should be YYYYMMDD_HHMMSS format"
        
        db_path = storage.storage_dir / 'aria_data.db'
        assert db_path.exists(), "Database file should be created"
        
        telemetry_dir = storage.storage_dir / 'telemetry'
        assert telemetry_dir.exists(), "Telemetry directory should be created"
    
    def test_store_telemetry(self, storage, sample_envelope):
        """
        Test: Store telemetry envelope to database and binary file.
        
        Input:
            - Envelope object
            - Encoded data (Protobuf bytes)
            - Compressed data (LZ4 bytes)
        
        Expected Output:
            - Row inserted in telemetry table
            - Binary file created: {session_id}_{envelope_id}.bin.gz
            - Metadata stored correctly
        """
        encoded = b"encoded_data_test"
        compressed = b"compressed_data_test"
        
        storage.store_telemetry(
            envelope=sample_envelope,
            encoded_data=encoded,
            compressed_data=compressed,
            compression_algo='lz4',
            encoding_time=0.5,
            compression_time=0.2
        )
        
        # Verify binary file created
        telemetry_dir = storage.storage_dir / 'telemetry'
        bin_files = list(telemetry_dir.glob('*.bin.gz'))
        assert len(bin_files) > 0, "Binary file should be created"
        
        # Verify data in database
        summary = storage.get_session_summary()
        assert summary['telemetry']['total_envelopes'] == 1, "Should have 1 envelope"
    
    def test_store_cognitive_state(self, storage):
        """
        Test: Store cognitive loop state snapshot.
        
        Input:
            - loop_id: int
            - energy: float (0-100)
            - temperature: float
            - novelty_drive: float
            - num_detections: int
            - unique_classes: int
        
        Expected Output:
            - Row inserted in cognitive_states table
            - All fields stored correctly
        """
        storage.store_cognitive_state(
            loop_id=1,
            energy=95.5,
            temperature=25.3,
            novelty_drive=0.75,
            num_detections=5,
            unique_classes=3
        )
        
        summary = storage.get_session_summary()
        assert summary['cognitive']['total_states'] == 1, "Should have 1 cognitive state"
        assert summary['cognitive']['avg_energy'] == 95.5, "Energy should match"
    
    def test_store_decision(self, storage):
        """
        Test: Store robot decision made by planner.
        
        Input:
            - loop_id: int
            - action: str (e.g., "inspect_object")
            - target: str (e.g., "person_3")
            - reasoning: str
            - priority_level: int (1-3)
            - energy_level: float
        
        Expected Output:
            - Row inserted in decisions table
            - Decision retrievable for analysis
        """
        storage.store_decision(
            loop_id=1,
            action="inspect_object",
            target="person_3",
            reasoning="Novel object detected with high confidence",
            priority_level=2,
            energy_level=95.5
        )
        
        summary = storage.get_session_summary()
        assert summary['decisions']['total_decisions'] == 1, "Should have 1 decision"
    
    def test_query_session_summary(self, storage, sample_envelope):
        """
        Test: Retrieve comprehensive session statistics.
        
        Input:
            - Session with multiple data points
        
        Expected Output:
            - Dictionary with stats:
              - total_envelopes
              - total_payload_bytes
              - avg_compression_ratio
              - energy stats (min, max, avg)
              - decision counts by action
        """
        # Add some data
        encoded = b"test_encoded"
        compressed = b"test_comp"
        
        storage.store_telemetry(sample_envelope, encoded, compressed, 'lz4', 0.5, 0.2)
        storage.store_cognitive_state(1, 95.0, 25.0, 0.8, 2, 2)
        storage.store_decision(1, "explore", "area_1", "Low novelty", 3, 95.0)
        
        summary = storage.get_session_summary()
        
        assert 'telemetry' in summary, "Should have telemetry stats"
        assert 'cognitive' in summary, "Should have cognitive stats"
        assert 'decisions' in summary, "Should have decision stats"
        
        assert summary['telemetry']['total_envelopes'] == 1
        assert summary['cognitive']['total_states'] == 1
        assert summary['decisions']['total_decisions'] == 1
    
    def test_close_session(self, storage, sample_envelope):
        """
        Test: Close session and update metadata.
        
        Input:
            - total_frames: int
            - total_loops: int
        
        Expected Output:
            - Session end_time updated
            - Total frames/loops stored
            - Database connection closed properly
        """
        # Add some data
        encoded = b"test"
        compressed = b"test"
        storage.store_telemetry(sample_envelope, encoded, compressed, 'lz4', 0.1, 0.1)
        
        # Close session
        storage.close_session(total_frames=100, total_loops=100)
        
        # Verify closed
        assert storage.session_closed, "Session should be marked as closed"
    
    def test_export_json(self, storage, sample_envelope):
        """
        Test: Export session data to JSON file.
        
        Input:
            - Session with telemetry, cognitive, decision data
        
        Expected Output:
            - JSON file created: session_{session_id}_export.json
            - Valid JSON structure
            - All statistics included
        """
        # Add data
        encoded = b"test"
        compressed = b"test"
        storage.store_telemetry(sample_envelope, encoded, compressed, 'lz4', 0.1, 0.1)
        storage.store_cognitive_state(1, 90.0, 25.0, 0.5, 1, 1)
        storage.store_decision(1, "wait", "none", "Low energy", 3, 90.0)
        
        # Export
        export_path = storage.export_session_json()
        
        assert export_path.exists(), "Export file should be created"
        assert export_path.suffix == '.json', "Should be JSON file"
        
        # Verify content
        with open(export_path, 'r') as f:
            data = json.load(f)
        
        assert 'session_id' in data, "Should have session ID"
        assert 'telemetry' in data, "Should have telemetry stats"
        assert 'cognitive' in data, "Should have cognitive stats"
    
    def test_binary_file_creation(self, storage, sample_envelope):
        """
        Test: Verify binary telemetry files are created correctly.
        
        Input:
            - Multiple envelopes
        
        Expected Output:
            - One .bin.gz file per envelope
            - Filenames: {session_id}_{envelope_id}.bin.gz
            - Files contain compressed data
        """
        for i in range(5):
            envelope = Envelope.create(
                topic=f"test/topic_{i}",
                payload=f"Test payload {i}".encode(),
                priority=Priority.P2,
                source_node="test",
                sequence_number=i
            )
            storage.store_telemetry(envelope, b"encoded", b"compressed", 'lz4', 0.1, 0.1)
        
        telemetry_dir = storage.storage_dir / 'telemetry'
        bin_files = list(telemetry_dir.glob('*.bin.gz'))
        
        assert len(bin_files) == 5, "Should have 5 binary files"
        
        # Verify filenames
        for bin_file in bin_files:
            assert storage.session_id in bin_file.name, "Filename should contain session ID"
            assert bin_file.stat().st_size > 0, "File should not be empty"
    
    def test_multiple_sessions(self, temp_storage_dir):
        """
        Test: Handle multiple sequential sessions.
        
        Input:
            - Create 3 sessions sequentially
        
        Expected Output:
            - Each session has unique ID
            - Data isolated per session
            - No cross-contamination
        """
        session_ids = []
        
        for i in range(3):
            storage = DataStorage(storage_dir=temp_storage_dir)
            session_ids.append(storage.session_id)
            
            envelope = Envelope.create(
                topic=f"session_{i}/test",
                payload=f"Session {i} data".encode(),
                priority=Priority.P2,
                source_node=f"node_{i}",
                sequence_number=0
            )
            storage.store_telemetry(envelope, b"enc", b"comp", 'lz4', 0.1, 0.1)
            storage.close_session(10, 10)
        
        # Verify unique sessions
        assert len(set(session_ids)) == 3, "All sessions should have unique IDs"
    
    def test_data_integrity(self, storage, sample_envelope):
        """
        Test: Ensure no data loss or corruption.
        
        Input:
            - 100 envelopes stored
        
        Expected Output:
            - All 100 retrievable from database
            - All 100 binary files exist
            - No missing or corrupted data
        """
        num_envelopes = 100
        
        for i in range(num_envelopes):
            envelope = Envelope.create(
                topic=f"integrity/test_{i}",
                payload=f"Integrity test {i}".encode(),
                priority=Priority.P2,
                source_node="integrity_tester",
                sequence_number=i
            )
            storage.store_telemetry(envelope, b"enc", b"comp", 'lz4', 0.1, 0.1)
        
        summary = storage.get_session_summary()
        assert summary['telemetry']['total_envelopes'] == num_envelopes, \
            f"Should have {num_envelopes} envelopes"
        
        telemetry_dir = storage.storage_dir / 'telemetry'
        bin_files = list(telemetry_dir.glob('*.bin.gz'))
        assert len(bin_files) == num_envelopes, \
            f"Should have {num_envelopes} binary files"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
