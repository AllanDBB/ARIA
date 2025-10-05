"""
ARIA SDK - Novelty Detector Module

Detects novel/unexpected events for intrinsic motivation.
"""

from typing import Dict, List, Optional
from collections import defaultdict
import numpy as np
import hashlib

from aria_sdk.domain.protocols import INoveltyDetector


class NoveltyDetector(INoveltyDetector):
    """
    Frequency-based novelty detector.
    
    Tracks observation frequencies and scores novelty based on rarity.
    """
    
    def __init__(self, decay_rate: float = 0.99, novelty_threshold: float = 0.7):
        """
        Initialize novelty detector.
        
        Args:
            decay_rate: Frequency decay rate per update (0-1)
            novelty_threshold: Threshold for novelty (0-1)
        """
        self.decay_rate = decay_rate
        self.novelty_threshold = novelty_threshold
        
        # observation_hash -> frequency
        self.frequencies: Dict[str, float] = defaultdict(float)
        
        # Statistics
        self.total_observations = 0
        self.novel_count = 0
    
    def detect(self, observation: bytes) -> float:
        """
        Compute novelty score for observation.
        
        Args:
            observation: Serialized observation
            
        Returns:
            Novelty score (0-1, higher=more novel)
        """
        self.total_observations += 1
        
        # Hash observation
        obs_hash = hashlib.sha256(observation).hexdigest()
        
        # Get frequency (defaults to 0)
        frequency = self.frequencies[obs_hash]
        
        # Compute novelty score (inverse of frequency)
        # Novel = never seen before (freq=0, score=1)
        # Familiar = seen often (freq=high, score=low)
        novelty_score = 1.0 / (1.0 + frequency)
        
        # Update frequency
        self.frequencies[obs_hash] += 1.0
        
        # Decay all frequencies
        for key in self.frequencies:
            self.frequencies[key] *= self.decay_rate
        
        # Track novel events
        if novelty_score >= self.novelty_threshold:
            self.novel_count += 1
        
        return novelty_score
    
    def is_novel(self, observation: bytes) -> bool:
        """
        Check if observation is novel.
        
        Args:
            observation: Serialized observation
            
        Returns:
            True if novel
        """
        return self.detect(observation) >= self.novelty_threshold
    
    def reset(self):
        """Reset frequency table."""
        self.frequencies.clear()
        print("[NoveltyDetector] Frequency table reset")
    
    def get_stats(self) -> Dict:
        """Get novelty statistics."""
        return {
            'total_observations': self.total_observations,
            'novel_count': self.novel_count,
            'novelty_rate': self.novel_count / max(1, self.total_observations),
            'unique_observations': len(self.frequencies),
        }
