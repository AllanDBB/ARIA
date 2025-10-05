"""
Test streaming with guaranteed detections.
Creates synthetic detections to test the streaming pipeline.
"""

import socket
import struct
import json
import time
from aria_sdk.domain.entities import Envelope, Priority, Detection
from aria_sdk.telemetry.codec import ProtobufCodec
from aria_sdk.telemetry.compression import Lz4Compressor

def send_test_envelopes(host='127.0.0.1', port=5555, count=20):
    """Send test envelopes to receiver."""
    
    print(f"🚀 Test Streaming to {host}:{port}")
    print(f"   Sending {count} test envelopes...\n")
    
    # Connect to receiver
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        print(f"✅ Connected to receiver\n")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return
    
    # Initialize codec
    codec = ProtobufCodec()
    compressor = Lz4Compressor(level=0)
    
    # Send test envelopes
    classes = ['person', 'car', 'bicycle', 'dog', 'cat']
    
    for i in range(count):
        # Create synthetic detection
        class_name = classes[i % len(classes)]
        payload_dict = {
            'class_id': i % len(classes),
            'class_name': class_name,
            'confidence': 0.75 + (i % 20) / 100.0,
            'bbox': [100 + i*5, 200 + i*3, 300 + i*4, 400 + i*2]
        }
        payload = json.dumps(payload_dict).encode('utf-8')
        
        # Create envelope
        envelope = Envelope.create(
            topic=f"perception/detection/{class_name}",
            payload=payload,
            priority=Priority.P2 if i % 2 == 0 else Priority.P1,
            source_node="test_robot",
            sequence_number=i
        )
        
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
        
        print(f"📤 Sent [{i+1}/{count}]: {class_name} ({len(encoded)} → {len(compressed)} bytes)")
        
        # Small delay to simulate real robot
        time.sleep(0.1)
    
    print(f"\n✅ Sent {count} envelopes successfully!")
    sock.close()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description="Test telemetry streaming")
    parser.add_argument('--host', default='127.0.0.1', help='Receiver host')
    parser.add_argument('--port', type=int, default=5555, help='Receiver port')
    parser.add_argument('--count', type=int, default=20, help='Number of envelopes to send')
    
    args = parser.parse_args()
    
    send_test_envelopes(host=args.host, port=args.port, count=args.count)
