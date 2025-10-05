"""
ARIA SDK - Telemetry Package

This package provides the complete telemetry pipeline for ARIA SDK:
- Codec: Protobuf serialization
- Compression: LZ4/Zstd
- Delta encoding: XOR-based
- CCEM: Channel conditioning
- FEC: Reed-Solomon forward error correction
- Packetization: MTU-aware fragmentation
- Crypto: NaCl sign-then-encrypt
- QoS: Priority queues + token bucket
- Transports: QUIC/MQTT-SN/DTN
- Recovery: Retry + buffering
- Router: Topic-based routing
"""

from aria_sdk.telemetry.codec import ProtobufCodec

__all__ = [
    'ProtobufCodec',
    # TODO: Add more exports as modules are implemented
    # 'Lz4Compressor',
    # 'ZstdCompressor',
    # 'SimpleDeltaCodec',
    # 'TxConditioner',
    # 'RxDeJitter',
    # 'ReedSolomonFEC',
    # 'Packetizer',
    # 'Defragmenter',
    # 'CryptoBox',
    # 'QoSShaper',
    # 'QuicTransport',
    # 'RecoveryManager',
    # 'TelemetryRouter',
]
