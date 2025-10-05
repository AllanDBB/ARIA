#!/usr/bin/env python3
"""
Ejemplo: Comparación de Diferentes Tasas de Drenaje de Energía

Este script demuestra cómo diferentes configuraciones de energy_drain_rate
afectan el comportamiento del sistema ARIA.
"""

import sys
import time
from aria_sdk.examples.cognitive_loop_demo import SimpleHomeostasisMonitor

def test_energy_drain_rates():
    """Prueba diferentes tasas de drenaje."""
    
    print("=" * 70)
    print("ARIA - Comparación de Tasas de Drenaje de Energía")
    print("=" * 70)
    print()
    
    # Configuraciones a probar
    configs = [
        (0.5, "Lento (Default)", "Testing normal"),
        (1.0, "Normal", "Operación estándar"),
        (2.0, "Rápido", "Testing acelerado"),
        (5.0, "Muy Rápido", "Debugging"),
        (10.0, "Extremo", "Stress test"),
    ]
    
    print(f"{'Rate':<8} {'Nombre':<18} {'Tiempo Total':<15} {'Caso de Uso'}")
    print("-" * 70)
    
    for rate, name, use_case in configs:
        total_time = 100.0 / rate
        minutes = int(total_time // 60)
        seconds = int(total_time % 60)
        
        time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
        
        print(f"{rate:<8.1f} {name:<18} {time_str:<15} {use_case}")
    
    print()
    print("=" * 70)
    print("Simulación en Tiempo Real (5 segundos de drenaje)")
    print("=" * 70)
    print()
    
    # Simular con rate = 20.0 (5 segundos para drenaje completo)
    monitor = SimpleHomeostasisMonitor(energy_drain_rate=20.0)
    
    print("Configuración: energy_drain_rate = 20.0 %/s")
    print("Tiempo esperado: 5 segundos\n")
    
    start_time = time.time()
    last_update = start_time
    
    print(f"{'Tiempo':<10} {'Energía':<10} {'Estado'}")
    print("-" * 40)
    
    while monitor.energy > 0:
        current_time = time.time()
        dt = current_time - last_update
        last_update = current_time
        
        # Actualizar homeostasis
        monitor.update(dt)
        
        # Mostrar estado cada 0.5 segundos
        elapsed = current_time - start_time
        if int(elapsed * 2) != int((elapsed - dt) * 2):  # Cada 0.5s
            status = "🟢 Normal" if monitor.energy > 50 else \
                    "🟡 Medio" if monitor.energy > 20 else \
                    "🔴 Crítico" if monitor.energy > 0 else "⚫ Agotado"
            
            print(f"{elapsed:<10.1f} {monitor.energy:<10.1f} {status}")
        
        time.sleep(0.1)
    
    total_time = time.time() - start_time
    print()
    print(f"✅ Drenaje completo en {total_time:.1f} segundos")
    print()
    
    print("=" * 70)
    print("Comandos para Diferentes Escenarios")
    print("=" * 70)
    print()
    
    scenarios = [
        ("Testing rápido (50s)", 
         "python -m aria_sdk.examples.full_system_demo --energy-drain 2.0"),
        
        ("Demo interactivo (20s)", 
         "python -m aria_sdk.examples.cognitive_loop_demo --energy-drain 5.0"),
        
        ("YOLO stress test (10s)", 
         "python -m aria_sdk.examples.cognitive_loop_yolo --energy-drain 10.0"),
        
        ("Simulación realista (5 minutos)", 
         "python -m aria_sdk.examples.full_system_demo --energy-drain 0.333"),
    ]
    
    for scenario, command in scenarios:
        print(f"# {scenario}")
        print(f"  {command}")
        print()
    
    print("=" * 70)
    print()
    print("💡 Tip: Usa --energy-drain 5.0 para ver comportamientos de baja")
    print("        energía en solo 20 segundos durante el desarrollo.")
    print()

if __name__ == "__main__":
    try:
        test_energy_drain_rates()
    except KeyboardInterrupt:
        print("\n\n❌ Interrumpido por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
