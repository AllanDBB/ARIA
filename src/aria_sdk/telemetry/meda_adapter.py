"""MEDA (Mars Environmental Dynamics Analyzer) data adapter for ARIA SDK.

This module provides tools to read NASA Perseverance MEDA sensor data and convert
it into ARIA Envelope format for processing through the telemetry pipeline.

MEDA sensors include:
- Pressure Sensor (PS)
- Thermal Infrared Sensor (TIRS) - Air and ground temperature
- Relative Humidity Sensor (RHS)
- Wind Sensor (WS)
- Air Temperature Sensor (ATS)
- Radiation and Dust Sensor (RDS)
- Ancillary data (solar position, rover status, etc.)

Data source: https://atmos.nmsu.edu/data_and_services/atmospheres_data/PERSEVERANCE/meda.html
"""

import csv
import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import IntEnum
from pathlib import Path
from typing import List, Optional, Iterator
from uuid import uuid4

from aria_sdk.domain.entities import Envelope, Priority, EnvelopeMetadata


class MedaSensorType(IntEnum):
    """MEDA sensor types with schema IDs for ARIA Envelopes."""
    
    PRESSURE = 1                # Atmospheric pressure (Pa)
    TEMPERATURE_AIR = 2         # Air temperature (°C)
    TEMPERATURE_GROUND = 3      # Ground temperature (°C)
    HUMIDITY = 4                # Relative humidity (%)
    WIND_SPEED = 5              # Wind speed (m/s)
    WIND_DIRECTION = 6          # Wind direction (degrees)
    RADIATION_UV = 7            # UV radiation
    DUST_OPACITY = 8            # Dust opacity
    ANCILLARY = 9               # Rover context data


@dataclass
class MedaReading:
    """A single MEDA sensor reading."""
    
    sol: int                    # Martian day number
    lmst: str                   # Local Mean Solar Time (HH:MM:SS)
    utc: datetime               # UTC timestamp
    sensor_type: MedaSensorType # Type of sensor
    value: float                # Sensor reading value
    unit: str                   # Unit of measurement
    quality_flag: int = 1       # Data quality (1=good, 0=bad)
    
    def __repr__(self) -> str:
        return (f"MedaReading(sol={self.sol}, time={self.lmst}, "
                f"{self.sensor_type.name}={self.value:.2f} {self.unit})")


class MedaCsvReader:
    """Read MEDA CSV files from NASA PDS archive."""
    
    def __init__(self, data_dir: Path):
        """Initialize reader with path to MEDA data directory.
        
        Args:
            data_dir: Path to directory containing MEDA CSV files
                     Expected structure:
                     data_dir/
                       DER_PS/          # Pressure data
                       DER_TIRS/        # Temperature data
                       DER_RHS/         # Humidity data
                       DER_WS/          # Wind data
                       DER_Ancillary/   # Context data
        """
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            raise FileNotFoundError(f"MEDA data directory not found: {data_dir}")
    
    def read_pressure(self, sol: int) -> List[MedaReading]:
        """Read pressure sensor data for a specific Sol.
        
        Args:
            sol: Martian day number (0-1379 available)
            
        Returns:
            List of pressure readings (~86,400 per Sol)
        """
        return self._read_sensor_data(
            sensor_dir="DER_PS",
            sol=sol,
            sensor_type=MedaSensorType.PRESSURE,
            value_column="PRESSURE",
            unit="Pa"
        )
    
    def read_temperature_air(self, sol: int) -> List[MedaReading]:
        """Read air temperature data for a specific Sol.
        
        Args:
            sol: Martian day number
            
        Returns:
            List of air temperature readings
        """
        return self._read_sensor_data(
            sensor_dir="DER_TIRS",
            sol=sol,
            sensor_type=MedaSensorType.TEMPERATURE_AIR,
            value_column="AIR_TEMP",
            unit="°C"
        )
    
    def read_humidity(self, sol: int) -> List[MedaReading]:
        """Read relative humidity data for a specific Sol.
        
        Args:
            sol: Martian day number
            
        Returns:
            List of humidity readings
        """
        return self._read_sensor_data(
            sensor_dir="DER_RHS",
            sol=sol,
            sensor_type=MedaSensorType.HUMIDITY,
            value_column="HUMIDITY",
            unit="%"
        )
    
    def read_wind(self, sol: int) -> List[MedaReading]:
        """Read wind sensor data for a specific Sol.
        
        Args:
            sol: Martian day number
            
        Returns:
            List of wind speed and direction readings
        """
        # Note: Wind data includes both speed and direction
        # For simplicity, we'll read speed here
        return self._read_sensor_data(
            sensor_dir="DER_WS",
            sol=sol,
            sensor_type=MedaSensorType.WIND_SPEED,
            value_column="WIND_SPEED",
            unit="m/s"
        )
    
    def _read_sensor_data(
        self,
        sensor_dir: str,
        sol: int,
        sensor_type: MedaSensorType,
        value_column: str,
        unit: str
    ) -> List[MedaReading]:
        """Internal method to read sensor CSV files.
        
        Args:
            sensor_dir: Subdirectory name (e.g., 'DER_PS')
            sol: Sol number
            sensor_type: Type of sensor
            value_column: Name of column containing sensor value
            unit: Unit of measurement
            
        Returns:
            List of readings
        """
        # Find CSV file for this Sol
        # Files are typically named like: SOL_0100_0100_DER_PS.csv
        sensor_path = self.data_dir / sensor_dir
        if not sensor_path.exists():
            raise FileNotFoundError(f"Sensor directory not found: {sensor_path}")
        
        # Search for file matching this Sol
        pattern = f"*SOL_{sol:04d}*.csv"
        csv_files = list(sensor_path.glob(pattern))
        
        if not csv_files:
            # Try alternative pattern
            pattern = f"*_{sol:04d}_*.csv"
            csv_files = list(sensor_path.glob(pattern))
        
        if not csv_files:
            raise FileNotFoundError(
                f"No CSV file found for Sol {sol} in {sensor_path}\n"
                f"Tried patterns: *SOL_{sol:04d}*.csv and *_{sol:04d}_*.csv"
            )
        
        # Read first matching file
        csv_file = csv_files[0]
        readings = []
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    # Parse timestamp (format: 2021-06-09T00:00:01.123Z)
                    utc_str = row.get('UTC', row.get('LTST', ''))
                    if utc_str:
                        # Handle ISO format with 'Z' suffix
                        utc_str = utc_str.replace('Z', '+00:00')
                        utc = datetime.fromisoformat(utc_str)
                    else:
                        # Fallback to current time if no UTC column
                        utc = datetime.now(timezone.utc)
                    
                    # Parse sensor value
                    value = float(row.get(value_column, 0.0))
                    
                    # Parse quality flag
                    quality = int(row.get('QUALITY_FLAG', row.get('VALID', 1)))
                    
                    # Parse LMST (Local Mean Solar Time)
                    lmst = row.get('LMST', row.get('LTST', '00:00:00'))
                    
                    reading = MedaReading(
                        sol=sol,
                        lmst=lmst,
                        utc=utc,
                        sensor_type=sensor_type,
                        value=value,
                        unit=unit,
                        quality_flag=quality
                    )
                    
                    readings.append(reading)
                    
                except (ValueError, KeyError) as e:
                    # Skip malformed rows
                    continue
        
        return readings
    
    def iter_all_sols(self, sensor_dir: str) -> Iterator[int]:
        """Iterate over all available Sol numbers for a sensor.
        
        Args:
            sensor_dir: Sensor directory name (e.g., 'DER_PS')
            
        Yields:
            Sol numbers found in the directory
        """
        sensor_path = self.data_dir / sensor_dir
        if not sensor_path.exists():
            return
        
        # Extract Sol numbers from filenames
        sols = set()
        for csv_file in sensor_path.glob("*.csv"):
            # Try to extract Sol number from filename
            # Expected formats: SOL_0100_0100_DER_PS.csv or similar
            parts = csv_file.stem.split('_')
            for i, part in enumerate(parts):
                if part.upper() == 'SOL' and i + 1 < len(parts):
                    try:
                        sol = int(parts[i + 1])
                        sols.add(sol)
                        break
                    except ValueError:
                        continue
                elif part.isdigit() and len(part) == 4:
                    # Might be a Sol number in NNNN format
                    sols.add(int(part))
        
        yield from sorted(sols)


class MedaToEnvelopeConverter:
    """Convert MEDA readings to ARIA Envelopes."""
    
    def __init__(self, source_node: str = "perseverance_rover"):
        """Initialize converter.
        
        Args:
            source_node: Name of source node (rover identifier)
        """
        self.source_node = source_node
        self._sequence_counter = 0
    
    def to_envelope(
        self,
        reading: MedaReading,
        priority: Priority = Priority.P1
    ) -> Envelope:
        """Convert a MEDA reading to an ARIA Envelope.
        
        Args:
            reading: MEDA sensor reading
            priority: Message priority (default P1=High)
            
        Returns:
            ARIA Envelope containing the sensor data
        """
        # Encode sensor value as binary payload
        # Use big-endian float (4 bytes)
        payload = struct.pack('!f', reading.value)
        
        # Build topic name
        sensor_name = reading.sensor_type.name.lower()
        topic = f"mars/perseverance/meda/{sensor_name}"
        
        # Create envelope
        envelope = Envelope(
            id=uuid4(),
            timestamp=reading.utc,
            schema_id=reading.sensor_type.value,
            priority=priority,
            topic=topic,
            payload=payload,
            metadata=EnvelopeMetadata(
                source_node=self.source_node,
                sequence_number=self._next_sequence(),
                fragment_info=None,
                fec_info=None,
                crypto_info=None
            )
        )
        
        return envelope
    
    def batch_convert(
        self,
        readings: List[MedaReading],
        priority: Priority = Priority.P1
    ) -> List[Envelope]:
        """Convert a batch of MEDA readings to Envelopes.
        
        Args:
            readings: List of MEDA readings
            priority: Message priority
            
        Returns:
            List of ARIA Envelopes
        """
        return [self.to_envelope(r, priority) for r in readings]
    
    def decode_envelope(self, envelope: Envelope) -> float:
        """Extract sensor value from an Envelope payload.
        
        Args:
            envelope: ARIA Envelope
            
        Returns:
            Sensor reading value
        """
        # Decode big-endian float from payload
        value, = struct.unpack('!f', envelope.payload)
        return value
    
    def _next_sequence(self) -> int:
        """Get next sequence number."""
        seq = self._sequence_counter
        self._sequence_counter += 1
        return seq
    
    def reset_sequence(self):
        """Reset sequence counter to 0."""
        self._sequence_counter = 0


# Example usage
if __name__ == "__main__":
    import sys
    
    # Check if data directory is provided
    if len(sys.argv) < 2:
        print("Usage: python meda_adapter.py <meda_data_dir> [sol]")
        print("\nExample:")
        print("  python meda_adapter.py data/meda 100")
        sys.exit(1)
    
    data_dir = sys.argv[1]
    sol = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    
    try:
        # Initialize reader
        reader = MedaCsvReader(data_dir)
        
        # Read pressure data
        print(f"Reading pressure data for Sol {sol}...")
        readings = reader.read_pressure(sol)
        print(f"✅ Loaded {len(readings)} pressure readings")
        
        if readings:
            print(f"\nFirst reading: {readings[0]}")
            print(f"Last reading:  {readings[-1]}")
        
        # Convert to Envelopes
        converter = MedaToEnvelopeConverter()
        envelopes = converter.batch_convert(readings)
        print(f"\n✅ Converted to {len(envelopes)} ARIA Envelopes")
        
        if envelopes:
            env = envelopes[0]
            print(f"\nExample Envelope:")
            print(f"  ID: {env.id}")
            print(f"  Schema: {env.schema_id} (PRESSURE)")
            print(f"  Topic: {env.topic}")
            print(f"  Priority: {env.priority.name}")
            print(f"  Payload: {len(env.payload)} bytes")
            
            # Decode to verify
            decoded_value = converter.decode_envelope(env)
            print(f"  Decoded value: {decoded_value:.2f} Pa")
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("\nMake sure you have downloaded MEDA data.")
        print("See MEDA_INTEGRATION_PLAN.md for instructions.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
