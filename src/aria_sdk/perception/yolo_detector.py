"""YOLO-based object detection for ARIA perception system.

Integrates YOLOv8 for real-time object detection with the cognitive loop.

Usage:
    from aria_sdk.perception.yolo_detector import YoloDetector
    
    detector = YoloDetector(model_size='n')  # nano model
    detections = detector.detect_from_camera()
"""

import sys
from pathlib import Path
from typing import List, Optional, Tuple
import numpy as np
import numpy.typing as npt

try:
    import cv2
except ImportError:
    print("❌ OpenCV not installed")
    print("   Install with: pip install opencv-python")
    sys.exit(1)

try:
    from ultralytics import YOLO
except ImportError:
    print("❌ Ultralytics YOLO not installed")
    print("   Install with: pip install ultralytics")
    sys.exit(1)

from aria_sdk.domain.entities import Detection, ImageData


class YoloDetector:
    """YOLO object detector (supports YOLOv8 and YOLOv11)."""
    
    def __init__(
        self,
        model_size: str = 'n',  # 'n', 's', 'm', 'l', 'x'
        model_version: str = '11',  # '8' or '11'
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        device: str = 'cpu'  # 'cpu' or 'cuda'
    ):
        """Initialize YOLO detector.
        
        Args:
            model_size: Model size ('n'=nano, 's'=small, 'm'=medium, 'l'=large, 'x'=xlarge)
            model_version: YOLO version ('8' or '11')
            confidence_threshold: Minimum confidence for detections
            iou_threshold: IoU threshold for NMS
            device: Device to run inference ('cpu' or 'cuda')
        """
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.device = device
        self.model_version = model_version
        
        # Load YOLO model (v8 or v11)
        model_name = f'yolo{model_version}{model_size}.pt' if model_version == '11' else f'yolov8{model_size}.pt'
        print(f"📦 Loading YOLO model: {model_name}")
        self.model = YOLO(model_name)
        self.model.to(device)
        
        print(f"✅ YOLOv{model_version} {model_size} loaded on {device}")
        print(f"   Confidence threshold: {confidence_threshold}")
        print(f"   IoU threshold: {iou_threshold}")
    
    def detect(
        self,
        image: npt.NDArray[np.uint8],
        visualize: bool = False
    ) -> Tuple[List[Detection], Optional[npt.NDArray[np.uint8]]]:
        """Run detection on an image.
        
        Args:
            image: Input image (H, W, C) in BGR format
            visualize: If True, return annotated image
            
        Returns:
            (detections, annotated_image)
        """
        # Run inference
        results = self.model(
            image,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            verbose=False
        )[0]
        
        # Convert to ARIA Detection format
        detections = []
        
        for box in results.boxes:
            # Extract box data
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            cls_name = results.names[cls_id]
            
            # Convert to (x, y, w, h) format
            x = float(x1)
            y = float(y1)
            w = float(x2 - x1)
            h = float(y2 - y1)
            
            detection = Detection(
                class_id=cls_id,
                class_name=cls_name,
                confidence=conf,
                bbox=(x, y, w, h)
            )
            detections.append(detection)
        
        # Optionally visualize
        annotated_img = None
        if visualize:
            annotated_img = results.plot()
        
        return detections, annotated_img
    
    def detect_from_camera(
        self,
        camera_id: int = 0,
        visualize: bool = True
    ) -> Tuple[List[Detection], npt.NDArray[np.uint8], ImageData]:
        """Capture and detect from camera.
        
        Args:
            camera_id: Camera device ID
            visualize: If True, return annotated image
            
        Returns:
            (detections, annotated_image, raw_image_data)
        """
        cap = cv2.VideoCapture(camera_id)
        
        if not cap.isOpened():
            raise RuntimeError(f"Failed to open camera {camera_id}")
        
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            raise RuntimeError("Failed to capture frame")
        
        # Run detection
        detections, annotated = self.detect(frame, visualize=visualize)
        
        # Create ImageData
        h, w, c = frame.shape
        image_data = ImageData(
            width=w,
            height=h,
            channels=c,
            data=frame
        )
        
        return detections, annotated if annotated is not None else frame, image_data
    
    def detect_from_video(
        self,
        video_path: str,
        max_frames: Optional[int] = None,
        skip_frames: int = 0
    ):
        """Generator that yields detections from video file.
        
        Args:
            video_path: Path to video file
            max_frames: Maximum number of frames to process
            skip_frames: Number of frames to skip between detections
            
        Yields:
            (frame_number, detections, annotated_image)
        """
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise RuntimeError(f"Failed to open video: {video_path}")
        
        frame_num = 0
        processed = 0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Skip frames if requested
                if frame_num % (skip_frames + 1) != 0:
                    frame_num += 1
                    continue
                
                # Run detection
                detections, annotated = self.detect(frame, visualize=True)
                
                yield frame_num, detections, annotated
                
                processed += 1
                if max_frames and processed >= max_frames:
                    break
                
                frame_num += 1
        
        finally:
            cap.release()
    
    def get_class_names(self) -> List[str]:
        """Get list of class names the model can detect."""
        return list(self.model.names.values())
    
    def get_num_classes(self) -> int:
        """Get number of classes the model can detect."""
        return len(self.model.names)


class CameraStream:
    """Continuous camera stream for real-time detection."""
    
    def __init__(
        self,
        detector: YoloDetector,
        camera_id: int = 0,
        display: bool = True
    ):
        """Initialize camera stream.
        
        Args:
            detector: YoloDetector instance
            camera_id: Camera device ID
            display: If True, display video window
        """
        self.detector = detector
        self.camera_id = camera_id
        self.display = display
        self.running = False
        
        # Stats
        self.frame_count = 0
        self.detection_count = 0
    
    def start(self, callback=None):
        """Start camera stream.
        
        Args:
            callback: Optional callback function(frame_num, detections, image)
        """
        cap = cv2.VideoCapture(self.camera_id)
        
        if not cap.isOpened():
            raise RuntimeError(f"Failed to open camera {self.camera_id}")
        
        self.running = True
        print(f"🎥 Camera stream started (press 'q' to quit)")
        
        try:
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    print("⚠️  Failed to capture frame")
                    break
                
                # Run detection
                detections, annotated = self.detector.detect(frame, visualize=True)
                
                self.frame_count += 1
                self.detection_count += len(detections)
                
                # Call user callback
                if callback:
                    callback(self.frame_count, detections, frame)
                
                # Display
                if self.display:
                    # Add stats overlay
                    cv2.putText(
                        annotated,
                        f"Frame: {self.frame_count} | Detections: {len(detections)}",
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 0),
                        2
                    )
                    
                    cv2.imshow('ARIA Perception', annotated)
                    
                    # Check for 'q' key
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
        
        finally:
            cap.release()
            if self.display:
                cv2.destroyAllWindows()
            
            print(f"\n📊 Stream stats:")
            print(f"   Frames processed: {self.frame_count}")
            print(f"   Total detections: {self.detection_count}")
            print(f"   Avg detections/frame: {self.detection_count / max(self.frame_count, 1):.1f}")
    
    def stop(self):
        """Stop camera stream."""
        self.running = False


# ==================== Demo / Test Functions ====================

def demo_webcam():
    """Demo: Detect from webcam."""
    print("\n" + "="*70)
    print("YOLO Webcam Demo")
    print("="*70 + "\n")
    
    # Initialize detector
    detector = YoloDetector(model_size='n', confidence_threshold=0.5)
    
    print(f"\n📋 Model can detect {detector.get_num_classes()} classes:")
    print(f"   {', '.join(detector.get_class_names()[:10])}...\n")
    
    # Capture single frame
    print("📸 Capturing from camera...")
    detections, annotated, image_data = detector.detect_from_camera(visualize=True)
    
    print(f"\n✅ Detected {len(detections)} objects:")
    for det in detections:
        print(f"   - {det.class_name}: {det.confidence:.2f}")
    
    # Show result
    cv2.imshow('Detection Result', annotated)
    print("\nPress any key to close...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def demo_stream():
    """Demo: Continuous stream with cognitive integration."""
    print("\n" + "="*70)
    print("YOLO Stream Demo")
    print("="*70 + "\n")
    
    detector = YoloDetector(model_size='n', confidence_threshold=0.5)
    stream = CameraStream(detector, display=True)
    
    # Callback to process detections
    def on_detection(frame_num, detections, image):
        if frame_num % 30 == 0:  # Print every 30 frames
            print(f"Frame {frame_num}: {len(detections)} objects detected")
    
    stream.start(callback=on_detection)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="YOLO Detector Demo")
    parser.add_argument(
        '--mode',
        choices=['webcam', 'stream'],
        default='webcam',
        help='Demo mode'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'webcam':
        demo_webcam()
    else:
        demo_stream()
