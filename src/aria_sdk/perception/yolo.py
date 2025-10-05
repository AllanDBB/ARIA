"""
ARIA SDK - YOLO Object Detection Module

Provides YOLO detector using ONNX Runtime with automatic hardware acceleration.
"""

import numpy as np
from typing import List, Tuple, Optional
import cv2

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False

from aria_sdk.domain.entities import Detection, BoundingBox
from aria_sdk.domain.protocols import IYoloDetector


class YoloDetector(IYoloDetector):
    """
    YOLO object detector with ONNX Runtime backend.
    
    Supports:
    - YOLOv5, YOLOv8, YOLOv10 models
    - Auto-detect CUDA/TensorRT/DirectML
    - NMS (Non-Maximum Suppression)
    - Confidence thresholding
    """
    
    def __init__(
        self,
        model_path: str,
        conf_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        class_names: Optional[List[str]] = None,
        input_size: Tuple[int, int] = (640, 640),
        backend: str = 'auto'
    ):
        """
        Initialize YOLO detector.
        
        Args:
            model_path: Path to ONNX model file
            conf_threshold: Confidence threshold (0-1)
            iou_threshold: IOU threshold for NMS (0-1)
            class_names: List of class names (uses COCO if None)
            input_size: Model input size (width, height)
            backend: Execution provider ('auto', 'cpu', 'cuda', 'tensorrt', 'dml')
        """
        if not ONNX_AVAILABLE:
            raise ImportError(
                "onnxruntime not available. Install with: pip install onnxruntime or onnxruntime-gpu"
            )
        
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.input_size = input_size
        
        # Default COCO class names
        self.class_names = class_names or [
            'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat',
            'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat',
            'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe', 'backpack',
            'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
            'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket',
            'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
            'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair',
            'couch', 'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse',
            'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink', 'refrigerator',
            'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
        ]
        
        # Initialize ONNX Runtime session
        self.session = self._create_session(backend)
        
        # Get input/output names
        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [output.name for output in self.session.get_outputs()]
        
        print(f"[YoloDetector] Loaded model: {model_path}")
        print(f"[YoloDetector] Providers: {self.session.get_providers()}")
        print(f"[YoloDetector] Input: {self.input_name}, Outputs: {self.output_names}")
    
    def _create_session(self, backend: str) -> ort.InferenceSession:
        """Create ONNX Runtime session with optimal providers."""
        providers = []
        
        if backend == 'auto':
            # Auto-detect best available provider
            available = ort.get_available_providers()
            
            if 'TensorrtExecutionProvider' in available:
                providers.append('TensorrtExecutionProvider')
            if 'CUDAExecutionProvider' in available:
                providers.append('CUDAExecutionProvider')
            if 'DmlExecutionProvider' in available:  # DirectML (Windows GPU)
                providers.append('DmlExecutionProvider')
            
            providers.append('CPUExecutionProvider')
            
        elif backend == 'cuda':
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        elif backend == 'tensorrt':
            providers = ['TensorrtExecutionProvider', 'CPUExecutionProvider']
        elif backend == 'dml':
            providers = ['DmlExecutionProvider', 'CPUExecutionProvider']
        elif backend == 'cpu':
            providers = ['CPUExecutionProvider']
        else:
            raise ValueError(f"Unknown backend: {backend}")
        
        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        
        return ort.InferenceSession(self.model_path, sess_options=sess_options, providers=providers)
    
    def _preprocess(self, image: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Preprocess image for YOLO.
        
        Args:
            image: Input image (H, W, C) in BGR
            
        Returns:
            Tuple of (preprocessed_tensor, scale_factor)
        """
        # Get original size
        h, w = image.shape[:2]
        
        # Resize with letterboxing
        input_h, input_w = self.input_size
        scale = min(input_w / w, input_h / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        
        # Create padded image
        padded = np.full((input_h, input_w, 3), 114, dtype=np.uint8)
        pad_left = (input_w - new_w) // 2
        pad_top = (input_h - new_h) // 2
        padded[pad_top:pad_top+new_h, pad_left:pad_left+new_w] = resized
        
        # Convert to tensor: HWC -> CHW, BGR -> RGB, normalize
        tensor = padded.transpose(2, 0, 1)[::-1]  # HWC to CHW, BGR to RGB
        tensor = np.ascontiguousarray(tensor).astype(np.float32) / 255.0
        tensor = np.expand_dims(tensor, axis=0)  # Add batch dimension
        
        return tensor, scale
    
    def _postprocess(
        self,
        outputs: List[np.ndarray],
        scale: float,
        orig_shape: Tuple[int, int]
    ) -> List[Detection]:
        """
        Postprocess YOLO outputs with NMS.
        
        Args:
            outputs: Model outputs
            scale: Scale factor from preprocessing
            orig_shape: Original image shape (H, W)
            
        Returns:
            List of detections
        """
        # YOLO output shape: [batch, num_predictions, 85]
        # 85 = x, y, w, h, objectness, class_scores (80 for COCO)
        predictions = outputs[0][0]  # Remove batch dimension
        
        # Filter by confidence
        confidences = predictions[:, 4]
        mask = confidences >= self.conf_threshold
        filtered = predictions[mask]
        
        if len(filtered) == 0:
            return []
        
        # Extract boxes and class scores
        boxes = filtered[:, :4]
        obj_conf = filtered[:, 4:5]
        class_scores = filtered[:, 5:]
        class_ids = np.argmax(class_scores, axis=1)
        class_confs = np.max(class_scores, axis=1, keepdims=True)
        final_confs = obj_conf * class_confs
        
        # Convert from center format (x, y, w, h) to corner format (x1, y1, x2, y2)
        boxes_xyxy = np.zeros_like(boxes)
        boxes_xyxy[:, 0] = boxes[:, 0] - boxes[:, 2] / 2  # x1
        boxes_xyxy[:, 1] = boxes[:, 1] - boxes[:, 3] / 2  # y1
        boxes_xyxy[:, 2] = boxes[:, 0] + boxes[:, 2] / 2  # x2
        boxes_xyxy[:, 3] = boxes[:, 1] + boxes[:, 3] / 2  # y2
        
        # Scale boxes back to original image
        boxes_xyxy /= scale
        
        # Apply NMS
        indices = self._nms(boxes_xyxy, final_confs.flatten(), self.iou_threshold)
        
        # Create detections
        detections = []
        for idx in indices:
            x1, y1, x2, y2 = boxes_xyxy[idx]
            class_id = int(class_ids[idx])
            confidence = float(final_confs[idx, 0])
            
            detection = Detection(
                class_id=class_id,
                class_name=self.class_names[class_id] if class_id < len(self.class_names) else f"class_{class_id}",
                confidence=confidence,
                bbox=BoundingBox(
                    x=float(x1),
                    y=float(y1),
                    width=float(x2 - x1),
                    height=float(y2 - y1)
                ),
                track_id=None
            )
            detections.append(detection)
        
        return detections
    
    def _nms(self, boxes: np.ndarray, scores: np.ndarray, iou_threshold: float) -> List[int]:
        """
        Non-Maximum Suppression.
        
        Args:
            boxes: Boxes in xyxy format (N, 4)
            scores: Confidence scores (N,)
            iou_threshold: IOU threshold
            
        Returns:
            List of kept indices
        """
        # Sort by score
        order = scores.argsort()[::-1]
        
        keep = []
        while len(order) > 0:
            i = order[0]
            keep.append(i)
            
            if len(order) == 1:
                break
            
            # Compute IOUs with remaining boxes
            ious = self._compute_ious(boxes[i], boxes[order[1:]])
            
            # Keep boxes with IOU below threshold
            mask = ious <= iou_threshold
            order = order[1:][mask]
        
        return keep
    
    def _compute_ious(self, box: np.ndarray, boxes: np.ndarray) -> np.ndarray:
        """Compute IOUs between box and multiple boxes."""
        # Intersection
        x1 = np.maximum(box[0], boxes[:, 0])
        y1 = np.maximum(box[1], boxes[:, 1])
        x2 = np.minimum(box[2], boxes[:, 2])
        y2 = np.minimum(box[3], boxes[:, 3])
        
        intersection = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
        
        # Areas
        box_area = (box[2] - box[0]) * (box[3] - box[1])
        boxes_area = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
        
        # Union
        union = box_area + boxes_area - intersection
        
        return intersection / (union + 1e-7)
    
    async def detect(self, image: np.ndarray) -> List[Detection]:
        """
        Run object detection on image.
        
        Args:
            image: Input image (H, W, C) in BGR format
            
        Returns:
            List of detections
        """
        # Preprocess
        input_tensor, scale = self._preprocess(image)
        
        # Run inference
        outputs = self.session.run(self.output_names, {self.input_name: input_tensor})
        
        # Postprocess
        detections = self._postprocess(outputs, scale, image.shape[:2])
        
        return detections
