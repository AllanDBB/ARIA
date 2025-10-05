#!/usr/bin/env python3
"""
ARIA SDK - Send Tool

Send test telemetry data.
"""

import asyncio
import click
from datetime import datetime, timezone
from uuid import uuid4

from aria_sdk.domain.entities import Envelope, RawSample, ImageData, Priority
from aria_sdk.telemetry.codec import AriaCodec


@click.command()
@click.option('--count', '-n', default=10, help='Number of envelopes to send')
@click.option('--width', '-w', default=640, help='Image width')
@click.option('--height', '-h', default=480, help='Image height')
@click.option('--output', '-o', type=click.Path(), help='Output file (optional)')
def main(count: int, width: int, height: int, output: str):
    """Send test telemetry data."""
    asyncio.run(send_test_data(count, width, height, output))


async def send_test_data(count: int, width: int, height: int, output: str = None):
    """Send test envelopes."""
    codec = AriaCodec()
    
    click.echo(f"🚀 Sending {count} test envelopes ({width}x{height})...")
    
    total_bytes = 0
    
    for i in range(count):
        # Create test image
        import numpy as np
        image = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
        
        image_data = ImageData(
            data=image,
            width=width,
            height=height,
            channels=3,
            format="rgb8"
        )
        
        sample = RawSample(
            id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            sensor_id=f"test_camera_{i}",
            data=image_data
        )
        
        envelope = Envelope(
            id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            robot_id="test_robot",
            priority=Priority.HIGH,
            payload=sample,
            metadata={"seq": i}
        )
        
        # Encode
        encoded = codec.encode(envelope)
        total_bytes += len(encoded)
        
        click.echo(f"  [{i+1}/{count}] Encoded: {len(encoded):,} bytes")
        
        # Write to file if specified
        if output:
            with open(output, 'ab') as f:
                # Write length prefix + data
                f.write(len(encoded).to_bytes(4, 'big'))
                f.write(encoded)
        
        await asyncio.sleep(0.1)
    
    avg_size = total_bytes / count
    click.echo(f"\n✅ Sent {count} envelopes")
    click.echo(f"📊 Total: {total_bytes:,} bytes | Avg: {avg_size:,.0f} bytes/envelope")
    
    if output:
        click.echo(f"💾 Saved to: {output}")


if __name__ == '__main__':
    main()
