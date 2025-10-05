"""
ARIA SDK - World Model Module

Maintains spatial-temporal representation of detected entities.
"""

import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
import numpy as np

from aria_sdk.domain.entities import Detection, State
from aria_sdk.domain.protocols import IWorldModel


@dataclass
class TrackedEntity:
    """A tracked entity in the world."""
    id: str
    class_name: str
    position: np.ndarray  # (x, y, z) in meters
    velocity: np.ndarray  # (vx, vy, vz) in m/s
    confidence: float
    last_seen: float  # monotonic time
    first_seen: float
    observation_count: int
    track_history: List[np.ndarray] = field(default_factory=list)
    
    def age(self) -> float:
        """Get entity age in seconds."""
        return time.monotonic() - self.first_seen
    
    def time_since_seen(self) -> float:
        """Get time since last observation in seconds."""
        return time.monotonic() - self.last_seen


class WorldModel(IWorldModel):
    """
    Maintains a representation of the robot's environment.
    
    Tracks detected objects with:
    - Spatial position and velocity
    - Temporal history
    - Confidence and belief
    """
    
    def __init__(self, max_entities: int = 100, timeout: float = 5.0):
        """
        Initialize world model.
        
        Args:
            max_entities: Maximum tracked entities
            timeout: Timeout for unseen entities (seconds)
        """
        self.max_entities = max_entities
        self.timeout = timeout
        
        # entity_id -> TrackedEntity
        self.entities: Dict[str, TrackedEntity] = {}
        
        # Statistics
        self.total_observations = 0
        self.total_entities_created = 0
        self.total_entities_removed = 0
    
    def update(self, detections: List[Detection], timestamp: datetime):
        """
        Update world model with new detections.
        
        Args:
            detections: List of detections from perception
            timestamp: Detection timestamp
        """
        now = time.monotonic()
        self.total_observations += len(detections)
        
        # Associate detections with existing entities or create new ones
        for detection in detections:
            entity_id = self._get_entity_id(detection)
            
            # Estimate 3D position from 2D bbox (placeholder - would use depth/SLAM in reality)
            position = np.array([
                detection.bbox.x + detection.bbox.width / 2,
                detection.bbox.y + detection.bbox.height / 2,
                0.0  # No depth info
            ])
            
            if entity_id in self.entities:
                # Update existing entity
                entity = self.entities[entity_id]
                
                # Estimate velocity
                dt = now - entity.last_seen
                if dt > 0:
                    velocity = (position - entity.position) / dt
                    # Smooth velocity with exponential moving average
                    entity.velocity = 0.7 * entity.velocity + 0.3 * velocity
                
                entity.position = position
                entity.confidence = 0.8 * entity.confidence + 0.2 * detection.confidence
                entity.last_seen = now
                entity.observation_count += 1
                entity.track_history.append(position.copy())
                
                # Limit history length
                if len(entity.track_history) > 50:
                    entity.track_history.pop(0)
            else:
                # Create new entity
                self._add_entity(
                    entity_id=entity_id,
                    class_name=detection.class_name,
                    position=position,
                    confidence=detection.confidence,
                    now=now
                )
        
        # Garbage collect old entities
        self._gc_timeout()
    
    def _get_entity_id(self, detection: Detection) -> str:
        """Generate entity ID from detection."""
        if detection.track_id is not None:
            return f"{detection.class_name}_{detection.track_id}"
        else:
            # Use spatial hashing for matching
            spatial_hash = int(detection.bbox.x / 50) * 1000 + int(detection.bbox.y / 50)
            return f"{detection.class_name}_{detection.class_id}_{spatial_hash}"
    
    def _add_entity(self, entity_id: str, class_name: str, position: np.ndarray, confidence: float, now: float):
        """Add new entity to world model."""
        if len(self.entities) >= self.max_entities:
            # Remove oldest low-confidence entity
            self._evict_one()
        
        self.entities[entity_id] = TrackedEntity(
            id=entity_id,
            class_name=class_name,
            position=position,
            velocity=np.zeros(3),
            confidence=confidence,
            last_seen=now,
            first_seen=now,
            observation_count=1,
            track_history=[position.copy()]
        )
        
        self.total_entities_created += 1
    
    def _evict_one(self):
        """Evict one entity (lowest confidence or oldest)."""
        if not self.entities:
            return
        
        # Find entity with lowest score (confidence / age)
        worst_id = None
        worst_score = float('inf')
        
        now = time.monotonic()
        for entity_id, entity in self.entities.items():
            age = now - entity.first_seen
            score = entity.confidence * entity.observation_count / (age + 1.0)
            if score < worst_score:
                worst_score = score
                worst_id = entity_id
        
        if worst_id:
            self.entities.pop(worst_id)
            self.total_entities_removed += 1
    
    def _gc_timeout(self):
        """Remove entities not seen for timeout period."""
        now = time.monotonic()
        to_remove = []
        
        for entity_id, entity in self.entities.items():
            if now - entity.last_seen > self.timeout:
                to_remove.append(entity_id)
        
        for entity_id in to_remove:
            self.entities.pop(entity_id)
            self.total_entities_removed += 1
    
    def get_entities(self, class_filter: Optional[str] = None) -> List[TrackedEntity]:
        """
        Get all tracked entities.
        
        Args:
            class_filter: Filter by class name (None=all)
            
        Returns:
            List of tracked entities
        """
        if class_filter:
            return [e for e in self.entities.values() if e.class_name == class_filter]
        return list(self.entities.values())
    
    def get_entity(self, entity_id: str) -> Optional[TrackedEntity]:
        """Get specific entity by ID."""
        return self.entities.get(entity_id)
    
    def get_nearby_entities(self, position: np.ndarray, radius: float) -> List[TrackedEntity]:
        """
        Get entities within radius of position.
        
        Args:
            position: Query position (x, y, z)
            radius: Search radius (meters)
            
        Returns:
            List of nearby entities
        """
        nearby = []
        for entity in self.entities.values():
            distance = np.linalg.norm(entity.position - position)
            if distance <= radius:
                nearby.append(entity)
        return nearby
    
    def predict_entity_position(self, entity_id: str, dt: float) -> Optional[np.ndarray]:
        """
        Predict entity position after dt seconds.
        
        Args:
            entity_id: Entity ID
            dt: Time delta (seconds)
            
        Returns:
            Predicted position, or None if entity not found
        """
        entity = self.entities.get(entity_id)
        if not entity:
            return None
        
        # Simple linear prediction
        predicted_pos = entity.position + entity.velocity * dt
        return predicted_pos
    
    def get_stats(self) -> Dict:
        """Get world model statistics."""
        return {
            'num_entities': len(self.entities),
            'total_observations': self.total_observations,
            'total_entities_created': self.total_entities_created,
            'total_entities_removed': self.total_entities_removed,
        }
