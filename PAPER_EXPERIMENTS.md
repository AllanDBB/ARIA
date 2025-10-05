# 🧪 Experimentos para el Paper

## Experimento 1: Novelty Decay Rate

**Hipótesis:** Novelty score decreases logarithmically with exposure.

**Protocolo:**
```powershell
.\venv\Scripts\python.exe -m aria_sdk.examples.cognitive_loop_yolo --max-frames 1000
```

**Procedimiento:**
1. Mostrar el mismo objeto (ej: taza) repetidamente
2. Registrar novelty score cada frame
3. Plotear novelty vs exposure count

**Resultado Esperado:**
- Frame 1: novelty = 1.00
- Frame 10: novelty ≈ 0.33
- Frame 50: novelty ≈ 0.14
- Frame 100: novelty ≈ 0.09

**Fórmula:**
```python
novelty = 1.0 / (1.0 + log(exposure_count))
```

---

## Experimento 2: Decision Priority Hierarchy

**Hipótesis:** System prioritizes homeostasis over novelty.

**Protocolo:**
```powershell
.\venv\Scripts\python.exe -m aria_sdk.examples.cognitive_loop_yolo --max-frames 2000
```

**Procedimiento:**
1. Dejar correr hasta Energy < 20%
2. Mostrar objeto completamente nuevo (high novelty)
3. Verificar que decision = SEEK_CHARGING (no INSPECT_OBJECT)

**Resultado Esperado:**
- Energy > 20% + new object → INSPECT_OBJECT (priority 1)
- Energy < 20% + new object → SEEK_CHARGING (priority 2)
- Energy < 10% + new object → SEEK_CHARGING (priority 3, CRITICAL)

**Priority Hierarchy:**
1. P3 (Critical): Energy < 10%
2. P2 (High): Energy < 20%
3. P1 (Medium): Novelty > 0.5
4. P0 (Low): Default exploration

---

## Experimento 3: Cognitive Loop Latency

**Hipótesis:** Full cognitive loop runs at 25-30 FPS (33-40ms latency).

**Protocolo:**
```powershell
.\venv\Scripts\python.exe -m aria_sdk.examples.cognitive_loop_yolo --max-frames 1000 --no-video
```

**Métricas a Recolectar:**
- Frames processed
- Total runtime
- Average FPS
- Per-module latency:
  - YOLO detection: ~20-30ms
  - Novelty computation: <1ms
  - World model update: <1ms
  - Planning: <1ms

**Resultado Esperado:**
- Total latency: 30-40ms
- Throughput: 25-30 FPS
- 95% latency: <50ms

---

## Experimento 4: World Model Memory Efficiency

**Hipótesis:** Memory grows O(n) with unique objects, not total detections.

**Protocolo:**
```powershell
.\venv\Scripts\python.exe -m aria_sdk.examples.cognitive_loop_yolo --max-frames 5000
```

**Procedimiento:**
1. Mostrar 10 objetos diferentes
2. Repetir los mismos 10 objetos 500 veces
3. Verificar que world model solo trackea 10 entidades

**Resultado Esperado:**
- Total detections: ~5,000
- Unique entities tracked: 10
- Memory: O(unique_objects), not O(total_detections)

---

## Experimento 5: Multi-Object Tracking

**Hipótesis:** System tracks multiple objects simultaneously.

**Protocolo:**
```powershell
.\venv\Scripts\python.exe -m aria_sdk.examples.cognitive_loop_yolo --max-frames 500
```

**Procedimiento:**
1. Mostrar 5 objetos simultáneamente
2. Verificar que todos se detectan
3. Remover 2 objetos
4. Verificar que solo 3 siguen siendo detectados (pero 5 en world model)

**Resultado Esperado:**
- Frame 1-100: 5 objetos detectados + trackeados
- Frame 101-200: 3 objetos detectados, 5 trackeados (memoria)
- Observations de objetos removidos: no aumentan

---

## Experimento 6: Homeostatic Pressure Response

**Hipótesis:** Homeostatic pressure increases as energy decreases.

**Protocolo:**
```powershell
.\venv\Scripts\python.exe -m aria_sdk.examples.cognitive_loop_yolo --max-frames 3000
```

**Métricas:**
- Energy (100% → 0%)
- Homeostatic pressure (0.0 → 1.0)
- Decision priority (0 → 3)

**Resultado Esperado:**
- Energy 100-30%: Pressure = 0.0, Priority = 0
- Energy 30-20%: Pressure = 0.0-0.33, Priority = 0
- Energy 20-10%: Pressure = 0.33-0.66, Priority = 2
- Energy < 10%: Pressure > 0.66, Priority = 3

**Fórmula:**
```python
pressure = max(
    (30.0 - energy) / 30.0,  # Energy pressure
    (temperature - 50.0) / 30.0  # Temp pressure
)
```

---

## Experimento 7: YOLO Model Comparison

**Hipótesis:** Larger models are more accurate but slower.

**Protocolo:**
```bash
# Nano
python -m aria_sdk.examples.cognitive_loop_yolo --model-size n --max-frames 500

# Small
python -m aria_sdk.examples.cognitive_loop_yolo --model-size s --max-frames 500

# Medium
python -m aria_sdk.examples.cognitive_loop_yolo --model-size m --max-frames 500
```

**Métricas:**
- Average FPS
- Detection confidence (promedio)
- Detections per frame

**Resultado Esperado:**
| Model | FPS | Confidence | Detections/Frame |
|-------|-----|------------|------------------|
| Nano  | 30  | 0.65       | 3.2              |
| Small | 20  | 0.72       | 4.1              |
| Medium| 12  | 0.78       | 4.5              |

---

## Experimento 8: Novelty-Driven Exploration

**Hipótesis:** Robot inspects novel objects before common ones.

**Protocolo:**
```powershell
.\venv\Scripts\python.exe -m aria_sdk.examples.cognitive_loop_yolo
```

**Procedimiento:**
1. Mostrar objeto común (cup) 50 veces → novelty ≈ 0.14
2. Mostrar objeto nuevo (book) → novelty = 1.00
3. Verificar que decision = INSPECT_OBJECT → book

**Resultado Esperado:**
- Common object (low novelty): Decision = EXPLORE
- New object (high novelty): Decision = INSPECT_OBJECT
- Threshold: novelty > 0.5 triggers inspection

---

## Experimento 9: Compression + Cognitive Integration (MEDA)

**Hipótesis:** MEDA data can be integrated with cognitive loop.

**Protocolo:**
```bash
# Step 1: Generate MEDA data
python scripts/download_meda.py --synthetic --sol 100

# Step 2: Run MEDA demo with compression
python -m aria_sdk.examples.meda_demo --sol 100 --sensor pressure

# Step 3: Visualize
python -m aria_sdk.examples.meda_visualizer --sol 100 --sensor pressure
```

**Métricas:**
- Compression ratio (LZ4 vs Zstd)
- Throughput (MB/s)
- Data integrity (100% validation)

**Resultado Esperado:**
- LZ4: 3-4x compression, 30+ MB/s
- Zstd: 5-10x compression, 10+ MB/s
- 100% data integrity after decompression

---

## Experimento 10: End-to-End System Validation

**Hipótesis:** Full system runs stable for 1+ hours.

**Protocolo:**
```powershell
# Run for 10,000 frames (~5-10 minutes)
.\venv\Scripts\python.exe -m aria_sdk.examples.cognitive_loop_yolo --max-frames 10000
```

**Métricas:**
- Total runtime
- Average FPS
- Memory usage (stable or growing?)
- Crash rate (0 expected)
- Unique objects detected
- Decisions made

**Success Criteria:**
- ✅ No crashes
- ✅ Consistent FPS (±10%)
- ✅ Memory stable (not growing unbounded)
- ✅ All metrics within expected ranges

---

## 📊 Tabla Resumen de Experimentos

| # | Experimento | Duración | Difficulty | Paper Section |
|---|-------------|----------|------------|---------------|
| 1 | Novelty Decay | 5 min | Easy | IMA - Novelty |
| 2 | Priority Hierarchy | 10 min | Easy | IMA - Planning |
| 3 | Latency | 5 min | Easy | Performance |
| 4 | Memory Efficiency | 10 min | Medium | World Model |
| 5 | Multi-Object | 5 min | Easy | Perception |
| 6 | Homeostasis | 15 min | Easy | IMA - Homeostasis |
| 7 | YOLO Comparison | 15 min | Medium | Perception |
| 8 | Novelty-Driven | 5 min | Easy | IMA - Behavior |
| 9 | MEDA Integration | 10 min | Medium | Telemetry |
| 10 | End-to-End | 30 min | Hard | System Validation |

---

## 📝 Comandos Rápidos para Recolectar Datos

```powershell
# Experimento completo automatizado
$experiments = @(
    @{name="novelty"; frames=1000; model="n"},
    @{name="priority"; frames=2000; model="n"},
    @{name="latency"; frames=1000; model="n"},
    @{name="memory"; frames=5000; model="n"},
    @{name="tracking"; frames=500; model="n"},
    @{name="homeostasis"; frames=3000; model="n"},
    @{name="yolo_nano"; frames=500; model="n"},
    @{name="yolo_small"; frames=500; model="s"},
    @{name="yolo_medium"; frames=500; model="m"},
    @{name="exploration"; frames=1000; model="n"},
    @{name="validation"; frames=10000; model="n"}
)

foreach ($exp in $experiments) {
    Write-Host "Running experiment: $($exp.name)"
    .\venv\Scripts\python.exe -m aria_sdk.examples.cognitive_loop_yolo `
        --model-size $exp.model `
        --max-frames $exp.frames `
        --no-video `
        > "results_$($exp.name).txt"
}
```

---

## 🎓 Para el Paper

**Secciones que puedes escribir:**

1. **Introduction**
   - Problem: Autonomous robots need intrinsic motivation
   - Solution: ARIA SDK with IMA

2. **Architecture**
   - Telemetry layer (compression, encoding)
   - IMA layer (novelty, homeostasis)
   - Brain layer (world model, planner)
   - Perception layer (YOLO)

3. **IMA Implementation**
   - Novelty detection algorithm
   - Homeostasis monitoring
   - Priority-based planning

4. **Experiments**
   - Use experiments 1-10 above
   - Include graphs, tables, metrics

5. **Results**
   - 25-30 FPS latency
   - Logarithmic novelty decay
   - Priority hierarchy validated
   - Memory efficiency O(n)

6. **Discussion**
   - Strengths: Real-time, modular, extensible
   - Limitations: Simulated homeostasis, no motor control
   - Future work: RL integration, multi-modal perception

7. **Conclusion**
   - ARIA SDK demonstrates functional IMA
   - Real-world YOLO integration proves viability
   - Open-source for community use

---

## 📈 Gráficos Sugeridos

1. **Novelty vs Exposure** (Exp 1)
   - X: Exposure count (1-100)
   - Y: Novelty score (0-1)
   - Expected: Logarithmic decay

2. **Decision Priority Over Time** (Exp 2)
   - X: Time (frames)
   - Y: Energy % + Decision priority
   - Expected: Priority increases as energy decreases

3. **Latency Breakdown** (Exp 3)
   - Pie chart or bar chart
   - Components: YOLO, Novelty, World Model, Planning

4. **Memory Growth** (Exp 4)
   - X: Total detections
   - Y: Unique entities tracked
   - Expected: Linear with unique objects, not total

5. **YOLO Model Comparison** (Exp 7)
   - Bar chart: FPS, Confidence, Detections
   - Models: Nano, Small, Medium

6. **Homeostatic Pressure** (Exp 6)
   - X: Energy %
   - Y: Pressure + Priority
   - Expected: Pressure increases, priority jumps at thresholds

---

## 🚀 Next Steps

1. ✅ Run all 10 experiments
2. ✅ Collect data (screenshots, metrics, logs)
3. ✅ Create visualizations (matplotlib)
4. ✅ Write paper sections
5. ✅ Submit to conference/journal

**Venues sugeridos:**
- ICRA (International Conference on Robotics and Automation)
- IROS (International Conference on Intelligent Robots and Systems)
- RSS (Robotics: Science and Systems)
- IEEE Transactions on Robotics
- Autonomous Robots (Springer)
