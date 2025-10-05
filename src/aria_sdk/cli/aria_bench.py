#!/usr/bin/env python3
"""
ARIA SDK - Benchmark Tool

Run performance benchmarks.
"""

import asyncio
import time
import click
import numpy as np
from datetime import datetime, timezone
from uuid import uuid4

from aria_sdk.domain.entities import Envelope, RawSample, ImageData, Priority
from aria_sdk.telemetry.codec import AriaCodec
from aria_sdk.telemetry.compression import create_compressor
from aria_sdk.telemetry.delta import AdaptiveDeltaCodec
from aria_sdk.telemetry.fec import ReedSolomonFEC
from aria_sdk.telemetry.crypto import CryptoBox


@click.group()
def cli():
    """ARIA SDK Benchmarks."""
    pass


@cli.command()
@click.option('--count', '-n', default=1000, help='Number of envelopes')
@click.option('--width', '-w', default=640, help='Image width')
@click.option('--height', '-h', default=480, help='Image height')
def codec(count: int, width: int, height: int):
    """Benchmark codec encode/decode."""
    click.echo(f"🏁 Codec Benchmark: {count} envelopes ({width}x{height})")
    
    codec_obj = AriaCodec()
    
    # Create test envelope
    image = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
    image_data = ImageData(data=image, width=width, height=height, channels=3, format="rgb8")
    sample = RawSample(id=uuid4(), timestamp=datetime.now(timezone.utc), sensor_id="bench", data=image_data)
    envelope = Envelope(id=uuid4(), timestamp=datetime.now(timezone.utc), robot_id="bench", priority=Priority.HIGH, payload=sample, metadata={})
    
    # Encode benchmark
    start = time.perf_counter()
    encoded_size = 0
    for _ in range(count):
        encoded = codec_obj.encode(envelope)
        encoded_size += len(encoded)
    encode_time = time.perf_counter() - start
    
    # Decode benchmark
    encoded = codec_obj.encode(envelope)
    start = time.perf_counter()
    for _ in range(count):
        _ = codec_obj.decode(encoded)
    decode_time = time.perf_counter() - start
    
    # Results
    encode_rate = count / encode_time
    decode_rate = count / decode_time
    avg_size = encoded_size / count
    
    click.echo(f"\n📊 Results:")
    click.echo(f"  Encode: {encode_rate:,.0f} msg/s ({encode_time*1000/count:.2f} ms/msg)")
    click.echo(f"  Decode: {decode_rate:,.0f} msg/s ({decode_time*1000/count:.2f} ms/msg)")
    click.echo(f"  Avg size: {avg_size:,.0f} bytes")


@cli.command()
@click.option('--size', '-s', default=1_000_000, help='Data size (bytes)')
@click.option('--algorithm', '-a', type=click.Choice(['lz4', 'zstd']), default='lz4', help='Algorithm')
def compression(size: int, algorithm: str):
    """Benchmark compression."""
    click.echo(f"🏁 Compression Benchmark: {size:,} bytes ({algorithm})")
    
    # Generate test data
    data = np.random.randint(0, 255, size, dtype=np.uint8).tobytes()
    
    compressor = create_compressor(algorithm)
    
    # Compress
    start = time.perf_counter()
    compressed = compressor.compress(data)
    compress_time = time.perf_counter() - start
    
    # Decompress
    start = time.perf_counter()
    decompressed = compressor.decompress(compressed)
    decompress_time = time.perf_counter() - start
    
    # Verify
    assert decompressed == data
    
    # Results
    ratio = len(data) / len(compressed)
    compress_throughput = len(data) / compress_time / 1e6  # MB/s
    decompress_throughput = len(data) / decompress_time / 1e6
    
    click.echo(f"\n📊 Results:")
    click.echo(f"  Original: {len(data):,} bytes")
    click.echo(f"  Compressed: {len(compressed):,} bytes")
    click.echo(f"  Ratio: {ratio:.2f}x")
    click.echo(f"  Compress: {compress_throughput:.1f} MB/s")
    click.echo(f"  Decompress: {decompress_throughput:.1f} MB/s")


@cli.command()
@click.option('--size', '-s', default=1_000_000, help='Data size (bytes)')
@click.option('--loss', '-l', default=10, help='Loss percentage')
def fec(size: int, loss: int):
    """Benchmark FEC."""
    click.echo(f"🏁 FEC Benchmark: {size:,} bytes ({loss}% loss)")
    
    # Create FEC
    k, m = 10, 4  # 10 data + 4 parity
    fec_obj = ReedSolomonFEC(k, m)
    
    # Generate test data
    data = np.random.randint(0, 255, size, dtype=np.uint8).tobytes()
    
    # Encode
    start = time.perf_counter()
    shards = fec_obj.encode(data)
    encode_time = time.perf_counter() - start
    
    # Simulate loss
    num_to_erase = int(len(shards) * loss / 100)
    erased_indices = np.random.choice(len(shards), num_to_erase, replace=False)
    for idx in erased_indices:
        shards[idx] = None
    
    # Decode
    start = time.perf_counter()
    recovered = fec_obj.decode(shards, len(data))
    decode_time = time.perf_counter() - start
    
    # Verify
    assert recovered == data
    
    # Results
    encode_throughput = len(data) / encode_time / 1e6
    decode_throughput = len(data) / decode_time / 1e6
    
    click.echo(f"\n📊 Results:")
    click.echo(f"  Encode: {encode_throughput:.1f} MB/s")
    click.echo(f"  Decode: {decode_throughput:.1f} MB/s (with {loss}% loss)")
    click.echo(f"  ✅ Successfully recovered data")


@cli.command()
@click.option('--size', '-s', default=1_000_000, help='Data size (bytes)')
def crypto(size: int):
    """Benchmark encryption."""
    click.echo(f"🏁 Crypto Benchmark: {size:,} bytes")
    
    # Generate keys
    from nacl.public import PrivateKey
    sender_key = PrivateKey.generate()
    receiver_key = PrivateKey.generate()
    
    crypto_box = CryptoBox(sender_key.encode(), receiver_key.public_key.encode())
    
    # Generate test data
    data = np.random.randint(0, 255, size, dtype=np.uint8).tobytes()
    
    # Encrypt
    start = time.perf_counter()
    encrypted = crypto_box.encrypt(data)
    encrypt_time = time.perf_counter() - start
    
    # Decrypt
    start = time.perf_counter()
    decrypted = crypto_box.decrypt(encrypted)
    decrypt_time = time.perf_counter() - start
    
    # Verify
    assert decrypted == data
    
    # Results
    encrypt_throughput = len(data) / encrypt_time / 1e6
    decrypt_throughput = len(data) / decrypt_time / 1e6
    
    click.echo(f"\n📊 Results:")
    click.echo(f"  Encrypt: {encrypt_throughput:.1f} MB/s")
    click.echo(f"  Decrypt: {decrypt_throughput:.1f} MB/s")


if __name__ == '__main__':
    cli()
