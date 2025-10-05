"""Test script to verify YOLO + Cognitive Loop setup.

Quick test to ensure all dependencies are installed and working.

Usage:
    python scripts/test_yolo_system.py
"""

import sys
from pathlib import Path

def test_imports():
    """Test that all required modules can be imported."""
    print("\n" + "="*70)
    print("Testing ARIA YOLO System Dependencies")
    print("="*70 + "\n")
    
    results = []
    
    # Test OpenCV
    print("1️⃣  Testing OpenCV...")
    try:
        import cv2
        version = cv2.__version__
        print(f"   ✅ OpenCV {version} installed")
        results.append(("OpenCV", True, version))
    except ImportError as e:
        print(f"   ❌ OpenCV not found: {e}")
        print("      Install: pip install opencv-python")
        results.append(("OpenCV", False, None))
    
    # Test Ultralytics YOLO
    print("\n2️⃣  Testing Ultralytics YOLO...")
    try:
        import ultralytics
        from ultralytics import YOLO
        version = ultralytics.__version__
        print(f"   ✅ Ultralytics {version} installed")
        results.append(("Ultralytics", True, version))
    except ImportError as e:
        print(f"   ❌ Ultralytics not found: {e}")
        print("      Install: pip install ultralytics")
        results.append(("Ultralytics", False, None))
    
    # Test Rich
    print("\n3️⃣  Testing Rich...")
    try:
        import rich
        from rich.console import Console
        # Rich doesn't expose __version__ directly, check if it works
        try:
            from importlib.metadata import version as get_version
            version = get_version('rich')
        except:
            version = "installed"
        print(f"   ✅ Rich {version} installed")
        results.append(("Rich", True, version))
    except ImportError as e:
        print(f"   ❌ Rich not found: {e}")
        print("      Install: pip install rich")
        results.append(("Rich", False, None))
    
    # Test ARIA SDK modules
    print("\n4️⃣  Testing ARIA SDK modules...")
    try:
        from aria_sdk.domain.entities import Detection
        from aria_sdk.perception.yolo_detector import YoloDetector
        print(f"   ✅ ARIA SDK modules found")
        results.append(("ARIA SDK", True, "local"))
    except ImportError as e:
        print(f"   ❌ ARIA SDK modules not found: {e}")
        print("      Make sure you're in the ARIA directory")
        results.append(("ARIA SDK", False, None))
    
    # Print summary
    print("\n" + "="*70)
    print("Summary")
    print("="*70 + "\n")
    
    all_ok = all(r[1] for r in results)
    
    for name, ok, version in results:
        status = "✅ OK" if ok else "❌ MISSING"
        version_str = f"(v{version})" if version else ""
        print(f"   {status} {name} {version_str}")
    
    print("\n" + "="*70 + "\n")
    
    if all_ok:
        print("✅ All dependencies installed!")
        print("\nYou can now run:")
        print("   python -m aria_sdk.examples.cognitive_loop_yolo")
        return True
    else:
        print("❌ Some dependencies are missing.")
        print("\nInstall missing packages:")
        if not results[0][1]:  # OpenCV
            print("   pip install opencv-python")
        if not results[1][1]:  # Ultralytics
            print("   pip install ultralytics")
        if not results[2][1]:  # Rich
            print("   pip install rich")
        return False


def test_camera():
    """Test camera access."""
    print("\n" + "="*70)
    print("Testing Camera Access")
    print("="*70 + "\n")
    
    try:
        import cv2
        
        print("Attempting to open camera 0...")
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("❌ Failed to open camera 0")
            print("   Possible issues:")
            print("   - Camera is being used by another application")
            print("   - No camera connected")
            print("   - Permission denied")
            return False
        
        # Try to read a frame
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            print("❌ Failed to capture frame from camera")
            return False
        
        h, w, c = frame.shape
        print(f"✅ Camera working!")
        print(f"   Resolution: {w}x{h}")
        print(f"   Channels: {c}")
        
        return True
        
    except Exception as e:
        print(f"❌ Camera test failed: {e}")
        return False


def test_yolo_model():
    """Test YOLO model loading."""
    print("\n" + "="*70)
    print("Testing YOLO Model")
    print("="*70 + "\n")
    
    try:
        from ultralytics import YOLO
        import numpy as np
        
        print("Loading YOLOv8 nano model...")
        model = YOLO('yolov8n.pt')
        
        print(f"✅ Model loaded successfully!")
        print(f"   Classes: {len(model.names)}")
        print(f"   Examples: {', '.join(list(model.names.values())[:10])}...")
        
        # Test inference on dummy image
        print("\nTesting inference on dummy image...")
        dummy_img = np.zeros((640, 640, 3), dtype=np.uint8)
        results = model(dummy_img, verbose=False)
        
        print(f"✅ Inference successful!")
        print(f"   Detections: {len(results[0].boxes)}")
        
        return True
        
    except Exception as e:
        print(f"❌ YOLO test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("ARIA YOLO System Test Suite")
    print("="*70)
    
    # Test imports
    imports_ok = test_imports()
    
    if not imports_ok:
        print("\n❌ Cannot continue - missing dependencies")
        sys.exit(1)
    
    # Test camera (optional)
    camera_ok = test_camera()
    
    # Test YOLO model
    yolo_ok = test_yolo_model()
    
    # Final summary
    print("\n" + "="*70)
    print("Final Results")
    print("="*70 + "\n")
    
    print(f"   Dependencies: {'✅ OK' if imports_ok else '❌ FAIL'}")
    print(f"   Camera:       {'✅ OK' if camera_ok else '⚠️  SKIP (no camera or in use)'}")
    print(f"   YOLO Model:   {'✅ OK' if yolo_ok else '❌ FAIL'}")
    
    print("\n" + "="*70 + "\n")
    
    if imports_ok and yolo_ok:
        print("✅ System ready!")
        print("\n🚀 Run the cognitive loop:")
        print("   python -m aria_sdk.examples.cognitive_loop_yolo")
        
        if not camera_ok:
            print("\n⚠️  Note: Camera test failed, but you can still use video files:")
            print("   python -m aria_sdk.examples.cognitive_loop_yolo --video video.mp4")
    else:
        print("❌ System not ready - fix errors above")
        sys.exit(1)


if __name__ == "__main__":
    main()
