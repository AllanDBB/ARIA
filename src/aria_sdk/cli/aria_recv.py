#!/usr/bin/env python3
"""
ARIA SDK - Receive Tool

Receive and decode telemetry data.
"""

import asyncio
import click
from pathlib import Path

from aria_sdk.telemetry.codec import AriaCodec


@click.command()
@click.option('--input', '-i', required=True, type=click.Path(exists=True), help='Input file')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def main(input: str, verbose: bool):
    """Receive and decode telemetry data."""
    asyncio.run(receive_data(input, verbose))


async def receive_data(input_path: str, verbose: bool):
    """Decode envelopes from file."""
    codec = AriaCodec()
    
    click.echo(f"📥 Reading from: {input_path}")
    
    file_size = Path(input_path).stat().st_size
    click.echo(f"📊 File size: {file_size:,} bytes")
    
    count = 0
    total_decoded = 0
    
    with open(input_path, 'rb') as f:
        while True:
            # Read length prefix
            length_bytes = f.read(4)
            if not length_bytes:
                break
            
            length = int.from_bytes(length_bytes, 'big')
            
            # Read envelope data
            data = f.read(length)
            if len(data) != length:
                click.echo(f"⚠️  Truncated data at envelope {count+1}")
                break
            
            # Decode
            try:
                envelope = codec.decode(data)
                count += 1
                total_decoded += length
                
                if verbose:
                    click.echo(f"\n📦 Envelope #{count}")
                    click.echo(f"  ID: {envelope.id}")
                    click.echo(f"  Robot: {envelope.robot_id}")
                    click.echo(f"  Priority: {envelope.priority.name}")
                    click.echo(f"  Timestamp: {envelope.timestamp}")
                    click.echo(f"  Metadata: {envelope.metadata}")
                else:
                    click.echo(f"  [{count}] Decoded {length:,} bytes (robot={envelope.robot_id})")
            
            except Exception as e:
                click.echo(f"❌ Failed to decode envelope {count+1}: {e}")
                break
    
    click.echo(f"\n✅ Decoded {count} envelopes")
    click.echo(f"📊 Total: {total_decoded:,} bytes")


if __name__ == '__main__':
    main()
