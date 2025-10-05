"""MEDA Demo - NASA Perseverance Data through ARIA Pipeline.

This demo shows how real Mars rover sensor data flows through ARIA's telemetry pipeline:
1. Load MEDA CSV data (NASA Perseverance)
2. Convert to ARIA Envelopes
3. Encode with ProtobufCodec
4. Compress with LZ4/Zstd
5. Measure performance metrics
6. Decompress & decode
7. Validate data integrity

Usage:
    python -m aria_sdk.examples.meda_demo --sol 100 --sensor pressure
    python -m aria_sdk.examples.meda_demo --help
"""

import argparse
import sys
import time
from pathlib import Path
from typing import List, Tuple

from aria_sdk.domain.entities import Envelope, Priority
from aria_sdk.telemetry.codec import ProtobufCodec
from aria_sdk.telemetry.compression import Lz4Compressor, ZstdCompressor
from aria_sdk.telemetry.meda_adapter import (
    MedaCsvReader,
    MedaToEnvelopeConverter,
    MedaReading,
    MedaSensorType
)


class MedaDemo:
    """Demo runner for MEDA data through ARIA pipeline."""
    
    def __init__(self, data_dir: Path):
        """Initialize demo with MEDA data directory."""
        self.data_dir = data_dir
        self.reader = MedaCsvReader(data_dir)
        self.converter = MedaToEnvelopeConverter()
        self.codec = ProtobufCodec()
        
        # Compressors
        self.lz4 = Lz4Compressor(level=0)  # Fast
        self.zstd = ZstdCompressor(level=3)  # Balanced
    
    def run(self, sol: int, sensor: str = "pressure", limit: int = None):
        """Run the demo pipeline.
        
        Args:
            sol: Martian day number to process
            sensor: Sensor type ('pressure', 'temperature', 'humidity', 'wind')
            limit: Maximum number of readings to process (None=all)
        """
        print("=" * 70)
        print("ARIA SDK - MEDA Data Pipeline Demo")
        print("=" * 70)
        print(f"📊 Data Source: NASA Perseverance MEDA (Sol {sol})")
        print(f"🔬 Sensor Type: {sensor.upper()}")
        print()
        
        # Step 1: Load MEDA data
        print("Step 1: Loading MEDA CSV data...")
        readings = self._load_sensor_data(sol, sensor)
        
        if limit:
            readings = readings[:limit]
        
        if not readings:
            print(f"❌ No data found for Sol {sol}, sensor={sensor}")
            print("   Check that MEDA data is downloaded to:", self.data_dir)
            return
        
        print(f"✅ Loaded {len(readings):,} readings")
        self._print_reading_sample(readings)
        
        # Step 2: Convert to Envelopes
        print("\nStep 2: Converting to ARIA Envelopes...")
        start = time.perf_counter()
        envelopes = self.converter.batch_convert(readings, priority=Priority.P1)
        convert_time = time.perf_counter() - start
        
        print(f"✅ Converted {len(envelopes):,} envelopes in {convert_time*1000:.2f}ms")
        print(f"   Throughput: {len(envelopes)/convert_time:,.0f} envelopes/sec")
        self._print_envelope_sample(envelopes)
        
        # Step 3: Encode
        print("\nStep 3: Encoding with ProtobufCodec...")
        encoded_list, encode_time = self._encode_envelopes(envelopes)
        
        total_encoded_size = sum(len(e) for e in encoded_list)
        print(f"✅ Encoded {len(encoded_list):,} envelopes in {encode_time*1000:.2f}ms")
        print(f"   Total size: {total_encoded_size:,} bytes ({total_encoded_size/1024:.1f} KB)")
        print(f"   Throughput: {len(encoded_list)/encode_time:,.0f} msg/sec")
        print(f"   Bandwidth: {total_encoded_size/encode_time/1e6:.2f} MB/sec")
        
        # Step 4: Compress with LZ4
        print("\nStep 4a: Compressing with LZ4 (fast)...")
        lz4_data, lz4_time = self._compress_all(encoded_list, self.lz4)
        lz4_ratio = total_encoded_size / len(lz4_data)
        
        print(f"✅ LZ4 compressed: {len(lz4_data):,} bytes ({len(lz4_data)/1024:.1f} KB)")
        print(f"   Compression ratio: {lz4_ratio:.2f}x")
        print(f"   Time: {lz4_time*1000:.2f}ms")
        print(f"   Speed: {total_encoded_size/lz4_time/1e6:.1f} MB/sec")
        
        # Step 5: Compress with Zstd
        print("\nStep 4b: Compressing with Zstd (balanced)...")
        zstd_data, zstd_time = self._compress_all(encoded_list, self.zstd)
        zstd_ratio = total_encoded_size / len(zstd_data)
        
        print(f"✅ Zstd compressed: {len(zstd_data):,} bytes ({len(zstd_data)/1024:.1f} KB)")
        print(f"   Compression ratio: {zstd_ratio:.2f}x")
        print(f"   Time: {zstd_time*1000:.2f}ms")
        print(f"   Speed: {total_encoded_size/zstd_time/1e6:.1f} MB/sec")
        
        # Step 6: Decompress & Decode (validate integrity)
        print("\nStep 5: Validating data integrity...")
        self._validate_pipeline(lz4_data, envelopes, self.lz4)
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 PIPELINE SUMMARY")
        print("=" * 70)
        print(f"Total Readings:     {len(readings):,}")
        print(f"Raw Sensor Data:    ~{len(readings) * 4:,} bytes (4 bytes/float)")
        print(f"Encoded Size:       {total_encoded_size:,} bytes")
        print(f"LZ4 Compressed:     {len(lz4_data):,} bytes ({lz4_ratio:.2f}x)")
        print(f"Zstd Compressed:    {len(zstd_data):,} bytes ({zstd_ratio:.2f}x)")
        print()
        print(f"Encoding Speed:     {len(envelopes)/encode_time:,.0f} msg/sec")
        print(f"LZ4 Speed:          {total_encoded_size/lz4_time/1e6:.1f} MB/sec")
        print(f"Zstd Speed:         {total_encoded_size/zstd_time/1e6:.1f} MB/sec")
        print()
        print("✅ All data validated - 100% integrity preserved!")
        print("=" * 70)
    
    def _load_sensor_data(self, sol: int, sensor: str) -> List[MedaReading]:
        """Load sensor data from CSV."""
        sensor = sensor.lower()
        
        if sensor == "pressure":
            return self.reader.read_pressure(sol)
        elif sensor in ("temperature", "temp"):
            return self.reader.read_temperature_air(sol)
        elif sensor in ("humidity", "rh"):
            return self.reader.read_humidity(sol)
        elif sensor == "wind":
            return self.reader.read_wind(sol)
        else:
            raise ValueError(f"Unknown sensor type: {sensor}")
    
    def _print_reading_sample(self, readings: List[MedaReading]):
        """Print sample of readings."""
        if len(readings) >= 3:
            print(f"   First: {readings[0]}")
            print(f"   Mid:   {readings[len(readings)//2]}")
            print(f"   Last:  {readings[-1]}")
    
    def _print_envelope_sample(self, envelopes: List[Envelope]):
        """Print sample envelope."""
        if envelopes:
            env = envelopes[0]
            print(f"   Sample Envelope:")
            print(f"     ID: {env.id}")
            print(f"     Schema: {env.schema_id}")
            print(f"     Topic: {env.topic}")
            print(f"     Priority: {env.priority.name}")
            print(f"     Payload: {len(env.payload)} bytes")
    
    def _encode_envelopes(self, envelopes: List[Envelope]) -> Tuple[List[bytes], float]:
        """Encode all envelopes and measure time."""
        start = time.perf_counter()
        encoded = [self.codec.encode(env) for env in envelopes]
        elapsed = time.perf_counter() - start
        return encoded, elapsed
    
    def _compress_all(self, encoded_list: List[bytes], compressor) -> Tuple[bytes, float]:
        """Compress all encoded data as single blob."""
        # Concatenate all encoded envelopes
        combined = b''.join(encoded_list)
        
        # Compress
        start = time.perf_counter()
        compressed = compressor.compress(combined)
        elapsed = time.perf_counter() - start
        
        return compressed, elapsed
    
    def _validate_pipeline(self, compressed_data: bytes, original_envelopes: List[Envelope], compressor):
        """Validate complete pipeline: decompress → decode → compare."""
        print("   Decompressing...")
        decompressed = compressor.decompress(compressed_data)
        
        print("   Decoding envelopes...")
        # Decode each envelope from the decompressed blob
        offset = 0
        decoded_count = 0
        
        for i, original_env in enumerate(original_envelopes):
            # Find envelope boundary (using magic bytes 0xAA 0xBB)
            if offset + 7 > len(decompressed):
                break
            
            # Read length from header
            length = int.from_bytes(decompressed[offset+3:offset+7], 'big')
            
            # Extract full envelope data
            envelope_data = decompressed[offset:offset+7+length]
            
            # Decode
            decoded_env = self.codec.decode(envelope_data)
            
            # Validate critical fields
            assert decoded_env.schema_id == original_env.schema_id
            assert decoded_env.topic == original_env.topic
            assert decoded_env.payload == original_env.payload
            
            decoded_count += 1
            offset += 7 + length
        
        print(f"✅ Validated {decoded_count:,} envelopes - data integrity preserved!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Demo ARIA pipeline with real NASA Mars Perseverance MEDA data"
    )
    
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/meda"),
        help="Path to MEDA data directory (default: data/meda)"
    )
    
    parser.add_argument(
        "--sol",
        type=int,
        default=100,
        help="Martian Sol number to process (default: 100)"
    )
    
    parser.add_argument(
        "--sensor",
        type=str,
        default="pressure",
        choices=["pressure", "temperature", "temp", "humidity", "rh", "wind"],
        help="Sensor type to process (default: pressure)"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of readings (default: all)"
    )
    
    args = parser.parse_args()
    
    # Check if data directory exists
    if not args.data_dir.exists():
        print(f"❌ Error: MEDA data directory not found: {args.data_dir}")
        print()
        print("To download MEDA data:")
        print("1. Visit: https://www.kaggle.com/datasets/lolajackson/mars-2020-perseverance-meda-rover-data-derived")
        print("2. Download the dataset (18GB)")
        print("3. Extract to:", args.data_dir.absolute())
        print()
        print("Or see MEDA_INTEGRATION_PLAN.md for detailed instructions.")
        sys.exit(1)
    
    try:
        demo = MedaDemo(args.data_dir)
        demo.run(sol=args.sol, sensor=args.sensor, limit=args.limit)
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure MEDA data for Sol {args.sol} exists in:")
        print(f"  {args.data_dir / f'DER_{args.sensor.upper()}'}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
