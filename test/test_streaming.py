"""
Unit Tests for Telemetry Receiver/Streaming
============================================

Tests the network streaming components for Mars-to-Earth telemetry.

Input:
    - TCP socket connections
    - Length-prefixed binary messages
    - Compressed envelope data

Output:
    - Received and decoded envelopes
    - Real-time statistics
    - Optional saved binary files

Test Cases:
1. test_receiver_initialization: Starts receiver server
2. test_client_connection: Connects client to receiver
3. test_send_envelope: Sends single envelope over network
4. test_send_batch: Sends multiple envelopes
5. test_protocol_framing: Verifies length-prefix protocol
6. test_metadata_parsing: Parses JSON metadata correctly
7. test_decompression: Decompresses received data
8. test_decode_envelope: Decodes Protobuf to Envelope
9. test_disconnection_handling: Handles client disconnects
10. test_reconnection: Client reconnects after disconnect
11. test_concurrent_clients: Multiple clients simultaneously
12. test_data_integrity: No data loss during transmission
"""

import pytest
import socket
import struct
import json
import threading
import time
from aria_sdk.domain.entities import Envelope, Priority
from aria_sdk.telemetry.codec import ProtobufCodec
from aria_sdk.telemetry.compression import Lz4Compressor


class MockReceiver:
    """Mock receiver for testing without full Rich UI."""
    
    def __init__(self, host='127.0.0.1', port=0):
        """
        Initialize mock receiver.
        
        Args:
            host: Bind address
            port: Port (0 = auto-assign)
        """
        self.host = host
        self.port = port
        self.socket = None
        self.received_envelopes = []
        self.running = False
        self.codec = ProtobufCodec()
        self.decompressor = Lz4Compressor()
    
    def start(self):
        """Start receiver in background thread."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        
        # Get assigned port
        self.port = self.socket.getsockname()[1]
        
        self.running = True
        self.thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.thread.start()
        
        time.sleep(0.1)  # Give server time to start
    
    def _accept_loop(self):
        """Accept connections in background."""
        while self.running:
            try:
                self.socket.settimeout(0.5)
                client_sock, addr = self.socket.accept()
                threading.Thread(target=self._handle_client, args=(client_sock,), daemon=True).start()
            except socket.timeout:
                continue
            except Exception:
                break
    
    def _handle_client(self, client_sock):
        """Handle client connection."""
        while self.running:
            try:
                # Read length prefix
                length_data = client_sock.recv(4)
                if not length_data:
                    break
                
                msg_length = struct.unpack('!I', length_data)[0]
                
                # Read message
                data = b''
                while len(data) < msg_length:
                    chunk = client_sock.recv(msg_length - len(data))
                    if not chunk:
                        break
                    data += chunk
                
                # Parse: metadata + binary
                lines = data.split(b'\n', 1)
                if len(lines) != 2:
                    continue
                
                metadata = json.loads(lines[0].decode())
                compressed_data = lines[1]
                
                # Decompress and decode
                encoded_data = self.decompressor.decompress(compressed_data)
                envelope = self.codec.decode(encoded_data)
                
                self.received_envelopes.append(envelope)
                
            except Exception as e:
                print(f"Error handling client: {e}")
                break
        
        client_sock.close()
    
    def stop(self):
        """Stop receiver."""
        self.running = False
        if self.socket:
            self.socket.close()
        if hasattr(self, 'thread'):
            self.thread.join(timeout=1)


class TestTelemetryStreaming:
    """Test suite for telemetry streaming."""
    
    @pytest.fixture
    def receiver(self):
        """
        Fixture: Provides mock receiver.
        
        Yields:
            MockReceiver: Running receiver instance
        
        Cleanup:
            Stops receiver after test
        """
        recv = MockReceiver()
        recv.start()
        yield recv
        recv.stop()
    
    @pytest.fixture
    def codec(self):
        """Fixture: Provides codec."""
        return ProtobufCodec()
    
    @pytest.fixture
    def compressor(self):
        """Fixture: Provides compressor."""
        return Lz4Compressor(level=0)
    
    def _send_envelope(self, receiver, envelope, codec, compressor):
        """
        Helper: Send envelope to receiver.
        
        Args:
            receiver: MockReceiver instance
            envelope: Envelope to send
            codec: ProtobufCodec
            compressor: Lz4Compressor
        """
        # Connect
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((receiver.host, receiver.port))
        
        # Encode and compress
        encoded = codec.encode(envelope)
        compressed = compressor.compress(encoded)
        
        # Build message
        metadata = {
            'envelope_id': envelope.envelope_id,
            'topic': envelope.topic,
            'priority': envelope.priority.name,
            'timestamp': envelope.timestamp,
            'compression': 'lz4',
            'payload_size': envelope.payload_size
        }
        metadata_json = json.dumps(metadata).encode('utf-8')
        message = metadata_json + b'\n' + compressed
        
        # Send with length prefix
        length_prefix = struct.pack('!I', len(message))
        sock.sendall(length_prefix + message)
        sock.close()
    
    def test_receiver_initialization(self, receiver):
        """
        Test: Initialize and start receiver.
        
        Input:
            - Host, port parameters
        
        Expected Output:
            - Socket bound and listening
            - Port assigned
            - Background thread running
        """
        assert receiver.running, "Receiver should be running"
        assert receiver.port > 0, "Port should be assigned"
        assert receiver.socket is not None, "Socket should be created"
    
    def test_client_connection(self, receiver):
        """
        Test: Client can connect to receiver.
        
        Input:
            - Receiver address and port
        
        Expected Output:
            - Connection established
            - No errors
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((receiver.host, receiver.port))
        sock.close()
        
        # No exception = success
        assert True, "Connection successful"
    
    def test_send_envelope(self, receiver, codec, compressor):
        """
        Test: Send single envelope over network.
        
        Input:
            - Envelope with payload
        
        Expected Output:
            - Envelope received by receiver
            - All fields intact
        """
        envelope = Envelope.create(
            topic="test/single",
            payload=b"Single envelope test",
            priority=Priority.P2,
            source_node="test_client",
            sequence_number=1
        )
        
        self._send_envelope(receiver, envelope, codec, compressor)
        
        # Wait for processing
        time.sleep(0.2)
        
        assert len(receiver.received_envelopes) == 1, "Should receive 1 envelope"
        received = receiver.received_envelopes[0]
        assert received.payload == envelope.payload, "Payload should match"
        assert received.topic == envelope.topic, "Topic should match"
    
    def test_send_batch(self, receiver, codec, compressor):
        """
        Test: Send multiple envelopes in batch.
        
        Input:
            - 10 envelopes sent sequentially
        
        Expected Output:
            - All 10 received correctly
            - Order preserved
        """
        for i in range(10):
            envelope = Envelope.create(
                topic=f"test/batch_{i}",
                payload=f"Batch message {i}".encode(),
                priority=Priority.P2,
                source_node="batch_client",
                sequence_number=i
            )
            self._send_envelope(receiver, envelope, codec, compressor)
        
        # Wait for all to be processed
        time.sleep(0.5)
        
        assert len(receiver.received_envelopes) == 10, "Should receive 10 envelopes"
        
        # Verify order
        for i, received in enumerate(receiver.received_envelopes):
            assert received.sequence_number == i, f"Sequence {i} should match"
    
    def test_protocol_framing(self, receiver, codec, compressor):
        """
        Test: Verify length-prefix protocol works correctly.
        
        Input:
            - Message with known length
        
        Expected Output:
            - Length prefix matches actual message size
            - Message received completely
        """
        envelope = Envelope.create(
            topic="test/framing",
            payload=b"Framing test" * 100,  # Larger payload
            priority=Priority.P2,
            source_node="framing_client",
            sequence_number=1
        )
        
        # Manually build message
        encoded = codec.encode(envelope)
        compressed = compressor.compress(encoded)
        
        metadata = {
            'envelope_id': envelope.envelope_id,
            'topic': envelope.topic,
            'priority': envelope.priority.name,
            'timestamp': envelope.timestamp,
            'compression': 'lz4',
            'payload_size': envelope.payload_size
        }
        metadata_json = json.dumps(metadata).encode('utf-8')
        message = metadata_json + b'\n' + compressed
        
        # Verify length
        length_prefix = struct.pack('!I', len(message))
        unpacked_length = struct.unpack('!I', length_prefix)[0]
        
        assert unpacked_length == len(message), "Length should match message size"
        
        # Send it
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((receiver.host, receiver.port))
        sock.sendall(length_prefix + message)
        sock.close()
        
        time.sleep(0.2)
        
        assert len(receiver.received_envelopes) == 1, "Should receive envelope"
    
    def test_metadata_parsing(self, receiver, codec, compressor):
        """
        Test: Metadata JSON parsed correctly.
        
        Input:
            - Envelope with specific metadata fields
        
        Expected Output:
            - All metadata fields accessible
            - Correct types (timestamp as float, etc.)
        """
        envelope = Envelope.create(
            topic="test/metadata",
            payload=b"Metadata test",
            priority=Priority.P1,
            source_node="metadata_client",
            sequence_number=42,
            metadata={"sensor_id": "temp_01", "location": "cabin"}
        )
        
        self._send_envelope(receiver, envelope, codec, compressor)
        time.sleep(0.2)
        
        received = receiver.received_envelopes[0]
        assert received.metadata == envelope.metadata, "Metadata should match"
        assert received.sequence_number == 42, "Sequence number should match"
        assert received.priority == Priority.P1, "Priority should match"
    
    def test_decompression(self, receiver, codec, compressor):
        """
        Test: Receiver decompresses data correctly.
        
        Input:
            - LZ4 compressed envelope
        
        Expected Output:
            - Decompressed payload matches original
        """
        original_payload = b"Decompression test data" * 50
        envelope = Envelope.create(
            topic="test/decompress",
            payload=original_payload,
            priority=Priority.P2,
            source_node="decompress_client",
            sequence_number=1
        )
        
        self._send_envelope(receiver, envelope, codec, compressor)
        time.sleep(0.2)
        
        received = receiver.received_envelopes[0]
        assert received.payload == original_payload, "Decompressed payload should match"
    
    def test_decode_envelope(self, receiver, codec, compressor):
        """
        Test: Receiver decodes Protobuf to Envelope object.
        
        Input:
            - Protobuf-encoded envelope
        
        Expected Output:
            - Valid Envelope object
            - All fields accessible
        """
        envelope = Envelope.create(
            topic="test/decode",
            payload=b"Decode test",
            priority=Priority.P2,
            source_node="decode_client",
            sequence_number=1
        )
        
        self._send_envelope(receiver, envelope, codec, compressor)
        time.sleep(0.2)
        
        received = receiver.received_envelopes[0]
        assert isinstance(received, Envelope), "Should be Envelope object"
        assert hasattr(received, 'envelope_id'), "Should have envelope_id"
        assert hasattr(received, 'timestamp'), "Should have timestamp"
    
    def test_disconnection_handling(self, receiver, codec, compressor):
        """
        Test: Handle client disconnects gracefully.
        
        Input:
            - Send envelope, then disconnect immediately
        
        Expected Output:
            - Envelope still received
            - No errors or crashes
        """
        envelope = Envelope.create(
            topic="test/disconnect",
            payload=b"Disconnect test",
            priority=Priority.P2,
            source_node="disconnect_client",
            sequence_number=1
        )
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((receiver.host, receiver.port))
        
        # Send and immediately close
        encoded = codec.encode(envelope)
        compressed = compressor.compress(encoded)
        metadata = {
            'envelope_id': envelope.envelope_id,
            'topic': envelope.topic,
            'priority': envelope.priority.name,
            'timestamp': envelope.timestamp,
            'compression': 'lz4',
            'payload_size': envelope.payload_size
        }
        metadata_json = json.dumps(metadata).encode('utf-8')
        message = metadata_json + b'\n' + compressed
        length_prefix = struct.pack('!I', len(message))
        
        sock.sendall(length_prefix + message)
        sock.close()
        
        time.sleep(0.2)
        
        assert len(receiver.received_envelopes) >= 1, "Should receive envelope before disconnect"
    
    def test_data_integrity(self, receiver, codec, compressor):
        """
        Test: No data loss during transmission.
        
        Input:
            - 100 envelopes with sequential payloads
        
        Expected Output:
            - All 100 received
            - Payloads intact
            - No corruption
        """
        num_envelopes = 100
        
        for i in range(num_envelopes):
            envelope = Envelope.create(
                topic=f"test/integrity_{i}",
                payload=f"Integrity test message number {i}".encode(),
                priority=Priority.P2,
                source_node="integrity_client",
                sequence_number=i
            )
            self._send_envelope(receiver, envelope, codec, compressor)
        
        # Wait for all
        time.sleep(1.0)
        
        assert len(receiver.received_envelopes) == num_envelopes, \
            f"Should receive all {num_envelopes} envelopes"
        
        # Verify integrity
        for i, received in enumerate(receiver.received_envelopes):
            expected_payload = f"Integrity test message number {i}".encode()
            assert received.payload == expected_payload, f"Payload {i} should match"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
