# MEDA Integration Plan - Real Mars Data Testing

## 🎯 Objective

Use **real Mars Perseverance rover data** (MEDA sensors) to test and validate the ARIA SDK telemetry pipeline with actual scientific data from NASA.

---

## 📊 Available Data

### MEDA Sensor Suite
- **PS** (Pressure Sensor): Atmospheric pressure in Pascals
- **TIRS** (Thermal IR): Air & ground temperature in °C
- **RHS** (Relative Humidity): % RH
- **WS** (Wind Sensor): Speed (m/s) and direction (degrees)
- **ATS** (Air Temperature): Multiple thermometers
- **RDS** (Radiation/Dust): UV radiation, dust opacity
- **Ancillary**: Solar longitude, local time, rover position

### Data Format
- **Source**: NASA PDS (Planetary Data System)
- **Format**: CSV files (time series)
- **Time Range**: Sols 1-1379 (first ~3.8 Earth years on Mars)
- **Size**: ~18GB total (derived data)
- **Download**: Kaggle dataset or direct from PDS

---

## 🏗️ Architecture Overview

```
┌────────────────────────────────────────────────────────────────┐
│                    MEDA Data Integration                       │
└────────────────────────────────────────────────────────────────┘

[CSV Files]                      [ARIA Pipeline]
   ↓                                    ↓
┌──────────────┐              ┌────────────────────┐
│ MEDA CSVs    │              │  ARIA Telemetry    │
│              │              │    Pipeline        │
│ - Pressure   │  ────→       │                    │
│ - Temp       │              │  1. Envelope       │
│ - Humidity   │              │  2. Codec          │
│ - Wind       │              │  3. Compression    │
│ - Radiation  │              │  4. Analysis       │
└──────────────┘              └────────────────────┘
                                       ↓
                              ┌────────────────────┐
                              │  Visualization     │
                              │                    │
                              │ - Time series      │
                              │ - Statistics       │
                              │ - Pipeline metrics │
                              └────────────────────┘
```

---

## 📁 File Structure

```
ARIA/
├── data/
│   └── meda/                           # MEDA dataset (gitignored)
│       ├── DER_PS/                     # Pressure
│       ├── DER_TIRS/                   # Temperature
│       ├── DER_RHS/                    # Humidity
│       ├── DER_WS/                     # Wind
│       └── DER_Ancillary/              # Context data
│
├── src/aria_sdk/
│   ├── telemetry/
│   │   ├── codec.py                    # ✅ Already done
│   │   ├── compression.py              # 🔨 TO BUILD
│   │   └── meda_adapter.py             # 🔨 TO BUILD - MEDA-specific
│   │
│   └── examples/
│       ├── meda_demo.py                # 🔨 TO BUILD - Main demo
│       ├── meda_benchmark.py           # 🔨 TO BUILD - Performance test
│       └── meda_visualizer.py          # 🔨 TO BUILD - Dashboard
│
├── scripts/
│   └── download_meda.py                # 🔨 TO BUILD - Data downloader
│
└── tests/
    ├── test_meda_adapter.py            # 🔨 TO BUILD
    └── test_meda_integration.py        # 🔨 TO BUILD
```

---

## 🎬 Implementation Phases

### Phase 1: Data Ingestion (IMMEDIATE)
**Goal**: Read MEDA CSV files and convert to ARIA Envelopes

**Files to create**:
1. `src/aria_sdk/telemetry/meda_adapter.py`
   - `MedaSensorType` enum (PRESSURE, TEMPERATURE, etc.)
   - `MedaReading` dataclass
   - `MedaCsvReader` class
   - `MedaToEnvelopeConverter` class

2. `scripts/download_meda.py`
   - Download sample MEDA data from Kaggle
   - Extract and organize by sensor type
   - Create index file

3. `tests/test_meda_adapter.py`
   - Test CSV parsing
   - Test Envelope conversion
   - Test schema mappings

**Example Usage**:
```python
from aria_sdk.telemetry.meda_adapter import MedaCsvReader, MedaToEnvelopeConverter

# Read pressure data for Sol 100
reader = MedaCsvReader("data/meda/DER_PS/")
readings = reader.read_sol(100)

# Convert to ARIA envelopes
converter = MedaToEnvelopeConverter()
envelopes = [converter.to_envelope(r) for r in readings]

print(f"Converted {len(envelopes)} readings to Envelopes")
```

### Phase 2: Compression Module (HIGH PRIORITY)
**Goal**: Add compression to telemetry pipeline

**Files to create**:
1. `src/aria_sdk/telemetry/compression.py`
   - `Lz4Compressor` class
   - `ZstdCompressor` class
   - Both implement `ICompressor` protocol

2. `tests/test_compression.py`
   - Test roundtrip compress/decompress
   - Test compression ratios
   - Benchmark speed

**Example Usage**:
```python
from aria_sdk.telemetry.codec import ProtobufCodec
from aria_sdk.telemetry.compression import Lz4Compressor

codec = ProtobufCodec()
compressor = Lz4Compressor()

# Encode + Compress
encoded = codec.encode(envelope)
compressed = compressor.compress(encoded)

print(f"Original: {len(encoded)} → Compressed: {len(compressed)} bytes")
print(f"Compression ratio: {len(encoded)/len(compressed):.2f}x")
```

### Phase 3: End-to-End Demo (DEMO READY)
**Goal**: Complete pipeline demonstration

**Files to create**:
1. `src/aria_sdk/examples/meda_demo.py`
   - Main demo script
   - Load MEDA data → Envelope → Encode → Compress → Decompress → Decode
   - Print statistics and metrics

**Demo Flow**:
```
1. Load MEDA CSV (e.g., Sol 100 pressure data)
2. Convert to ARIA Envelopes
3. Encode with ProtobufCodec
4. Compress with Lz4Compressor
5. Calculate metrics (throughput, compression ratio, latency)
6. Decompress + Decode
7. Validate data integrity
8. Print results
```

### Phase 4: Visualization (OPTIONAL)
**Goal**: Real-time dashboard showing data flowing through pipeline

**Files to create**:
1. `src/aria_sdk/examples/meda_visualizer.py`
   - Plot original MEDA time series
   - Show encoding/compression statistics
   - Display throughput metrics

**Tech Stack**:
- matplotlib/plotly for plots
- pandas for data manipulation
- Rich for terminal UI

---

## 🔬 Test Scenarios

### Scenario 1: Pressure Data Pipeline
**Input**: DER_PS CSV (pressure readings for Sol 100)
**Expected**:
- 86,400 readings (1 per second for 1 Martian day)
- Each reading: timestamp, pressure (Pa)
- Envelope size: ~100 bytes/reading
- Compression ratio: 3-5x with Lz4, 5-10x with Zstd

### Scenario 2: Multi-Sensor Fusion
**Input**: Pressure + Temperature + Humidity for Sol 100
**Expected**:
- ~250K total readings across sensors
- Different schema_id for each sensor type
- Prioritize critical sensors (pressure = P0, others = P2)
- Aggregate statistics

### Scenario 3: High-Throughput Stress Test
**Input**: All MEDA data for Sols 1-100
**Expected**:
- Millions of readings processed
- Pipeline throughput: >100K msg/s
- Memory usage: <500MB
- Compression reduces size by 80%+

### Scenario 4: Delta Encoding Optimization
**Input**: Temperature readings (slowly changing values)
**Expected**:
- Delta encoding gives 2-3x additional compression
- Combined with Lz4: 10-15x total compression
- Perfect for telemetry with temporal correlation

---

## 📊 Success Metrics

### Functionality
- ✅ Successfully parse MEDA CSV files
- ✅ Convert to ARIA Envelopes with correct schema_id
- ✅ Encode/decode roundtrip preserves data
- ✅ Compression reduces size by >3x
- ✅ Full pipeline runs without errors

### Performance
- **Throughput**: >10K envelopes/second
- **Compression Ratio**: >3x with Lz4, >5x with Zstd
- **Latency**: <1ms per envelope (encode + compress)
- **Memory**: <100MB for 1 Sol of data

### Data Quality
- **Integrity**: 100% data preserved through pipeline
- **Accuracy**: Decoded values match original CSV
- **Precision**: No floating-point degradation

---

## 🚀 Quick Start Commands

### Step 1: Download Sample Data
```powershell
# Download MEDA data from Kaggle (requires Kaggle API)
python scripts/download_meda.py --sols 1-10 --sensors pressure,temperature

# Or manually download from:
# https://www.kaggle.com/datasets/lolajackson/mars-2020-perseverance-meda-rover-data-derived
```

### Step 2: Run Demo
```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Run MEDA demo
python -m aria_sdk.examples.meda_demo --sol 100 --sensor pressure

# Expected output:
# Loaded 86,400 pressure readings from Sol 100
# Converted to 86,400 ARIA Envelopes
# Encoded: 8.6 MB
# Compressed (Lz4): 2.1 MB (4.1x ratio)
# Pipeline throughput: 45,000 msg/s
# Roundtrip validated: 100% data integrity ✅
```

### Step 3: Run Benchmark
```powershell
# Performance benchmark
python -m aria_sdk.examples.meda_benchmark --sols 1-100

# Expected output:
# Processed 8.64M readings across 100 Sols
# Total time: 3.2 seconds
# Throughput: 2.7M msg/s
# Compression ratio: 4.5x (Lz4), 7.2x (Zstd)
# Memory peak: 287 MB
```

---

## 💡 Use Cases

### 1. **Telemetry Validation**
Use real Mars data to validate that ARIA's telemetry pipeline can handle:
- High-frequency sensor data (1 Hz)
- Multiple sensor types with different schemas
- Long-duration missions (1000+ Sols)
- Realistic compression ratios

### 2. **Machine Learning Training**
- Use MEDA data to train anomaly detection models
- Predict weather patterns on Mars
- Detect sensor malfunctions or calibration drift
- Train world model with real environmental data

### 3. **Robotics Simulation**
- Simulate Mars rover operations with real environmental conditions
- Test decision-making under realistic atmospheric pressure/temperature
- Validate safety constraints (e.g., don't operate below -90°C)

### 4. **Performance Benchmarking**
- Compare ARIA's codec vs. Protobuf, MessagePack, JSON
- Measure compression ratios vs. competitors
- Validate throughput claims
- Profile memory usage

### 5. **Educational Demos**
- Show students/researchers how real Mars data flows through a modern robotics SDK
- Demonstrate telemetry pipeline concepts with tangible examples
- Visualize data compression benefits

---

## 🔧 Technical Details

### MEDA Data Structure

**Pressure Sensor (DER_PS) CSV**:
```csv
SOL,LMST,UTC,PRESSURE,QUALITY_FLAG
100,00:00:01,2021-06-09T00:00:01.123Z,730.5,1
100,00:00:02,2021-06-09T00:00:02.123Z,730.6,1
100,00:00:03,2021-06-09T00:00:03.123Z,730.5,1
...
```

**ARIA Envelope Mapping**:
```python
Envelope(
    id=uuid4(),
    timestamp=datetime.fromisoformat("2021-06-09T00:00:01.123Z"),
    schema_id=1,  # MEDA_PRESSURE
    priority=Priority.P0,  # Critical environmental data
    topic="mars/perseverance/meda/pressure",
    payload=struct.pack('!f', 730.5),  # 4 bytes
    metadata=EnvelopeMetadata(
        source_node="perseverance_rover",
        sequence_number=sol * 86400 + seconds,
        fragment_info=None
    )
)
```

### Schema ID Mappings
```python
class MedaSensorSchema:
    PRESSURE = 1
    TEMPERATURE_AIR = 2
    TEMPERATURE_GROUND = 3
    HUMIDITY = 4
    WIND_SPEED = 5
    WIND_DIRECTION = 6
    RADIATION_UV = 7
    DUST_OPACITY = 8
    ANCILLARY = 9
```

---

## 📚 Resources

### Official NASA Documentation
- [MEDA Overview](https://atmos.nmsu.edu/data_and_services/atmospheres_data/PERSEVERANCE/meda.html)
- [Data Products](https://atmos.nmsu.edu/PDS/data/PDS4/Mars2020/mars2020_meda/)
- [Software Interface Spec](https://atmos.nmsu.edu/data_and_services/atmospheres_data/PERSEVERANCE/logs/MEDA_SIS_v0.27_10Sep2020.docx)

### Data Access
- [Kaggle Dataset](https://www.kaggle.com/datasets/lolajackson/mars-2020-perseverance-meda-rover-data-derived) (18GB, organized)
- [PDS Direct Download](https://atmos.nmsu.edu/PDS/data/PDS4/Mars2020/mars2020_meda/) (raw archives)

### Scientific Papers
- Rodriguez-Manfredi et al. (2021) - MEDA instrument design
- Farley et al. (2020) - Mars 2020 Mission Overview

---

## 🎯 Next Actions

1. **IMMEDIATE**: Create `meda_adapter.py` to read CSV files
2. **TODAY**: Implement compression module (`Lz4Compressor`, `ZstdCompressor`)
3. **THIS WEEK**: Build end-to-end demo with Sol 100 pressure data
4. **NEXT WEEK**: Add visualization dashboard
5. **FUTURE**: Integrate with cognitive loop (world model uses MEDA data)

---

## ✅ Success Criteria

This integration is successful when:

1. ✅ Can load any MEDA CSV file into ARIA Envelopes
2. ✅ Full encode → compress → decompress → decode pipeline works
3. ✅ Compression ratio >3x on real Mars data
4. ✅ Throughput >10K msg/s on typical laptop
5. ✅ 100% data integrity through pipeline
6. ✅ Demo runs in <5 seconds for 1 Sol of data
7. ✅ Code is clean, tested, and documented

---

**Status**: 🔨 **READY TO BUILD**

Start with Phase 1 (Data Ingestion) to get MEDA data flowing through ARIA!
