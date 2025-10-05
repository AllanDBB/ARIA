"""
Quick test script to verify streaming system works.
Run this to test both receiver and transmitter locally.
"""

import subprocess
import time
import sys
from pathlib import Path

def main():
    print("🚀 ARIA Streaming System Test\n")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not Path("src/aria_sdk").exists():
        print("❌ Error: Must run from ARIA root directory")
        sys.exit(1)
    
    print("\n📋 Test Plan:")
    print("  1. Start receiver in background")
    print("  2. Wait 2 seconds for receiver to initialize")
    print("  3. Start robot with streaming for 50 frames")
    print("  4. Verify data received\n")
    
    input("Press Enter to start test...")
    
    # Start receiver in background
    print("\n📡 Starting receiver...")
    receiver_proc = subprocess.Popen(
        [sys.executable, "-m", "aria_sdk.tools.telemetry_receiver", "--port", "5555"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    print("✅ Receiver started (PID: {})".format(receiver_proc.pid))
    print("   Waiting 2 seconds for initialization...")
    time.sleep(2)
    
    # Check if receiver is still running
    if receiver_proc.poll() is not None:
        print("❌ Receiver failed to start!")
        stdout, stderr = receiver_proc.communicate()
        print("STDOUT:", stdout.decode())
        print("STDERR:", stderr.decode())
        sys.exit(1)
    
    print("✅ Receiver ready\n")
    
    # Start robot with streaming
    print("🤖 Starting robot with streaming...")
    print("   (This will run for ~10 seconds with 50 frames)\n")
    
    robot_proc = subprocess.run(
        [
            sys.executable, "-m", "aria_sdk.examples.full_system_demo",
            "--stream", "127.0.0.1",
            "--port", "5555",
            "--max-frames", "50",
            "--no-video",
            "--energy-drain", "2.0"
        ],
        capture_output=True,
        text=True
    )
    
    if robot_proc.returncode != 0:
        print("❌ Robot failed!")
        print("STDOUT:", robot_proc.stdout)
        print("STDERR:", robot_proc.stderr)
    else:
        print("✅ Robot completed successfully!\n")
        print("📊 Robot Output (last 20 lines):")
        print("-" * 60)
        lines = robot_proc.stdout.split('\n')
        for line in lines[-20:]:
            print(line)
    
    # Stop receiver
    print("\n🛑 Stopping receiver...")
    receiver_proc.terminate()
    try:
        receiver_proc.wait(timeout=5)
        print("✅ Receiver stopped cleanly")
    except subprocess.TimeoutExpired:
        receiver_proc.kill()
        print("⚠️  Receiver killed (timeout)")
    
    print("\n" + "=" * 60)
    print("✅ Test completed!")
    print("\nTo manually test with live display:")
    print("  Terminal 1: python -m aria_sdk.tools.telemetry_receiver --port 5555")
    print("  Terminal 2: python -m aria_sdk.examples.full_system_demo --stream 127.0.0.1 --max-frames 100 --no-video")


if __name__ == "__main__":
    main()
