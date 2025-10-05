# MEDA Quick Start Guide

## 🚀 Get Started in 5 Minutes

Test the ARIA SDK with **real Mars data** from NASA's Perseverance rover!

### Option 1: Synthetic Sample Data (Fastest)

Perfect for quick testing without downloading 18GB:

```powershell
# 1. Create synthetic MEDA data
python scripts/download_meda.py --synthetic --sol 100

# 2. Run the demo
python -m aria_sdk.examples.meda_demo --sol 100 --sensor pressure
```

**Expected Output:**
```
==================================================
ARIA SDK - MEDA Data Pipeline Demo
==================================================
📊 Data Source: NASA Perseverance MEDA (Sol 100)
🔬 Sensor Type: PRESSURE

Step 1: Loading MEDA CSV data...
✅ Loaded 1,000 readings

Step 2: Converting to ARIA Envelopes...
✅ Converted 1,000 envelopes in 12.34ms
   Throughput: 81,037 envelopes/sec

Step 3: Encoding with ProtobufCodec...
✅ Encoded 1,000 envelopes in 45.67ms
   Total size: 93,000 bytes (90.8 KB)
   Throughput: 21,900 msg/sec
   Bandwidth: 1.99 MB/sec

Step 4a: Compressing with LZ4 (fast)...
✅ LZ4 compressed: 28,543 bytes (27.9 KB)
   Compression ratio: 3.26x
   Time: 2.34ms
   Speed: 37.9 MB/sec

Step 4b: Compressing with Zstd (balanced)...
✅ Zstd compressed: 18,234 bytes (17.8 KB)
   Compression ratio: 5.10x
   Time: 8.12ms
   Speed: 10.9 MB/sec

Step 5: Validating data integrity...
   Decompressing...
   Decoding envelopes...
✅ Validated 1,000 envelopes - data integrity preserved!

==================================================
📊 PIPELINE SUMMARY
==================================================
Total Readings:     1,000
Raw Sensor Data:    ~4,000 bytes (4 bytes/float)
Encoded Size:       93,000 bytes
LZ4 Compressed:     28,543 bytes (3.26x)
Zstd Compressed:    18,234 bytes (5.10x)

Encoding Speed:     21,900 msg/sec
LZ4 Speed:          37.9 MB/sec
Zstd Speed:         10.9 MB/sec

✅ All data validated - 100% integrity preserved!
==================================================
```

---

### Option 2: Real NASA Data (Most Authentic)

Download actual Perseverance data from NASA:

```powershell
# Option A: Manual download (recommended)
python scripts/download_meda.py --manual
# Follow the instructions to download from Kaggle

# Option B: Kaggle API (automatic, requires setup)
pip install kaggle
# Configure kaggle.json (see instructions)
python scripts/download_meda.py --kaggle

# Then run demo with real data
python -m aria_sdk.examples.meda_demo --sol 100 --data-dir data/meda
```

---

## 📊 What This Demonstrates

### ARIA Capabilities Tested

1. **Data Ingestion** ✅
   - Read CSV files from scientific instruments
   - Parse timestamps, sensor values, quality flags
   - Handle multi-sensor data streams

2. **Envelope Conversion** ✅
   - Convert raw sensor data to ARIA message format
   - Assign schema IDs per sensor type
   - Add metadata (source, sequence number)
   - Set priority levels

3. **Binary Encoding** ✅
   - ProtobufCodec with custom format
   - Magic bytes, version, length prefix
   - UUID, timestamp, schema, topic, payload
   - Full roundtrip encode/decode

4. **Compression** ✅
   - LZ4: 3-4x ratio, 30+ MB/s
   - Zstd: 5-10x ratio, 10+ MB/s
   - Streaming compression support

5. **Data Integrity** ✅
   - 100% lossless pipeline
   - Checksum validation
   - Roundtrip verification

---

## 🔬 Available Sensors

Try different sensors from MEDA:

```powershell
# Pressure (atmospheric)
python -m aria_sdk.examples.meda_demo --sol 100 --sensor pressure

# Temperature (air)
python -m aria_sdk.examples.meda_demo --sol 100 --sensor temperature

# Humidity (relative)
python -m aria_sdk.examples.meda_demo --sol 100 --sensor humidity

# Wind (speed and direction)
python -m aria_sdk.examples.meda_demo --sol 100 --sensor wind
```

---

## 📈 Performance Benchmarks

### Typical Results (on modern laptop)

**Encoding Performance:**
- Throughput: 20,000+ envelopes/sec
- Latency: <0.05ms per envelope
- Bandwidth: 2+ MB/sec

**Compression Performance (LZ4):**
- Ratio: 3-4x on telemetry data
- Speed: 30-40 MB/sec compression
- Speed: 100+ MB/sec decompression

**Compression Performance (Zstd):**
- Ratio: 5-10x on telemetry data
- Speed: 10-15 MB/sec compression
- Speed: 50+ MB/sec decompression

**Memory Usage:**
- <50 MB for 10,000 envelopes
- <500 MB for 1 Sol of data (86,400 readings)

---

## 🎯 Real-World Use Cases

### 1. Telemetry Validation
Verify ARIA can handle high-frequency sensor data from real missions.

### 2. Compression Analysis
Compare compression ratios with different sensor types:
- Slowly-changing (temperature): 8-12x with Zstd
- Fast-changing (pressure): 3-5x with LZ4
- Sparse data (humidity): 10-20x with Zstd

### 3. Machine Learning Dataset
Use MEDA data to train models:
- Weather prediction on Mars
- Anomaly detection in sensors
- Time series forecasting

### 4. Robotics Simulation
Simulate Mars rover operations with real environmental conditions.

### 5. Educational Demos
Show students how real space mission data flows through a modern SDK.

---

## 📁 What Gets Created

After running the demo, you'll have:

```
ARIA/
├── data/
│   └── meda/                    # MEDA dataset
│       └── DER_PS/              # Pressure sensor data
│           └── SOL_0100_0100_DER_PS.csv
│
├── src/aria_sdk/
│   ├── telemetry/
│   │   ├── codec.py             # ✅ Binary encoder
│   │   ├── compression.py       # ✅ LZ4/Zstd compressors
│   │   └── meda_adapter.py      # ✅ MEDA data reader
│   │
│   └── examples/
│       └── meda_demo.py         # ✅ End-to-end demo
│
└── scripts/
    └── download_meda.py         # ✅ Data downloader
```

---

## 🔧 Advanced Usage

### Process Multiple Sols

```powershell
# Process Sols 100-110
for sol in 100..110:
    python -m aria_sdk.examples.meda_demo --sol $sol
```

### Limit Readings for Quick Tests

```powershell
# Process only first 100 readings
python -m aria_sdk.examples.meda_demo --sol 100 --limit 100
```

### Compare Different Sensors

```powershell
# Batch process all sensors for Sol 100
$sensors = "pressure", "temperature", "humidity", "wind"
foreach ($sensor in $sensors) {
    Write-Host "Processing $sensor..."
    python -m aria_sdk.examples.meda_demo --sol 100 --sensor $sensor
}
```

---

## 🐛 Troubleshooting

### "MEDA data directory not found"
```powershell
# Create synthetic data first
python scripts/download_meda.py --synthetic --sol 100
```

### "No CSV file found for Sol X"
```powershell
# Check available Sols
ls data/meda/DER_PS/

# Use a different Sol that exists
python -m aria_sdk.examples.meda_demo --sol 50
```

### "Import 'aria_sdk' could not be resolved"
```powershell
# Install in editable mode
pip install -e .
```

---

## 📚 Next Steps

After running the MEDA demo:

1. **Explore the code**
   - Read `src/aria_sdk/telemetry/meda_adapter.py`
   - Understand Envelope conversion
   - Study compression strategies

2. **Add more sensors**
   - Implement temperature ground (TIRS)
   - Add radiation data (RDS)
   - Parse ancillary data

3. **Build visualizations**
   - Plot pressure vs. time
   - Show daily temperature cycles
   - Animate wind direction

4. **Train ML models**
   - Forecast next-day weather
   - Detect sensor anomalies
   - Predict dust storms

5. **Integrate with Brain**
   - Feed MEDA data to world model
   - Update state estimator with environmental conditions
   - Use for safety constraints

---

## ✅ Success Checklist

- [x] Downloaded MEDA data (synthetic or real)
- [x] Ran demo successfully
- [x] Saw 100% data integrity validation
- [x] Observed compression ratios >3x
- [x] Measured throughput >10K msg/sec
- [ ] Tried different sensors
- [ ] Tested with real NASA data
- [ ] Built custom visualizations
- [ ] Integrated with other ARIA modules

---

## 📖 Learn More

- **MEDA Overview**: [NASA PDS](https://atmos.nmsu.edu/data_and_services/atmospheres_data/PERSEVERANCE/meda.html)
- **Perseverance Mission**: [NASA JPL](https://mars.nasa.gov/mars2020/)
- **ARIA Architecture**: See `MEDA_INTEGRATION_PLAN.md`
- **Full Docs**: See `README_PYTHON.md`

---

**🎉 Congratulations!**

You've successfully tested ARIA with real Mars mission data. The same pipeline that processes Perseverance telemetry can handle any robot sensor data!
