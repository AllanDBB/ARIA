"""
ARIA SDK - Stigmergy Module

Pheromone-based coordination for multi-robot systems.
"""

import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import numpy as np

from aria_sdk.domain.protocols import IStigmergy


@dataclass
class Pheromone:
    """Pheromone trace."""
    position: np.ndarray  # (x, y) position
    intensity: float  # Current intensity
    decay_rate: float  # Decay rate per second
    deposited_at: float  # Timestamp
    robot_id: str  # Robot that deposited it


class StigmergySystem(IStigmergy):
    """
    Stigmergy system for indirect coordination via pheromone traces.
    
    Use cases:
    - Path marking (explored areas)
    - Attractants (interesting regions)
    - Repellents (obstacles, crowded areas)
    """
    
    def __init__(self, decay_rate: float = 0.1, grid_resolution: float = 0.5):
        """
        Initialize stigmergy system.
        
        Args:
            decay_rate: Pheromone decay rate (intensity/second)
            grid_resolution: Spatial grid resolution (meters)
        """
        self.decay_rate = decay_rate
        self.grid_resolution = grid_resolution
        
        # Pheromone map: (grid_x, grid_y) -> List[Pheromone]
        self.pheromones: Dict[Tuple[int, int], List[Pheromone]] = {}
        
        # Statistics
        self.total_deposited = 0
        self.total_decayed = 0
    
    def deposit(
        self,
        position: np.ndarray,
        intensity: float,
        decay_rate: Optional[float] = None,
        robot_id: str = "unknown"
    ):
        """
        Deposit pheromone at position.
        
        Args:
            position: Position (x, y) in meters
            intensity: Initial intensity
            decay_rate: Custom decay rate (None=use default)
            robot_id: Robot depositing pheromone
        """
        # Quantize to grid
        grid_pos = self._to_grid(position)
        
        # Create pheromone
        pheromone = Pheromone(
            position=position.copy(),
            intensity=intensity,
            decay_rate=decay_rate if decay_rate is not None else self.decay_rate,
            deposited_at=time.monotonic(),
            robot_id=robot_id
        )
        
        # Add to map
        if grid_pos not in self.pheromones:
            self.pheromones[grid_pos] = []
        self.pheromones[grid_pos].append(pheromone)
        
        self.total_deposited += 1
    
    def sense(self, position: np.ndarray, radius: float = 2.0) -> float:
        """
        Sense pheromone intensity at position.
        
        Args:
            position: Query position (x, y)
            radius: Sensing radius (meters)
            
        Returns:
            Total pheromone intensity
        """
        # Update pheromones (decay)
        self._update_pheromones()
        
        # Query nearby grid cells
        grid_pos = self._to_grid(position)
        grid_radius = int(radius / self.grid_resolution) + 1
        
        total_intensity = 0.0
        
        for dx in range(-grid_radius, grid_radius + 1):
            for dy in range(-grid_radius, grid_radius + 1):
                query_pos = (grid_pos[0] + dx, grid_pos[1] + dy)
                
                if query_pos in self.pheromones:
                    for pheromone in self.pheromones[query_pos]:
                        # Distance-weighted intensity
                        distance = np.linalg.norm(pheromone.position - position)
                        if distance <= radius:
                            # Gaussian falloff
                            weight = np.exp(-(distance ** 2) / (2 * (radius / 2) ** 2))
                            total_intensity += pheromone.intensity * weight
        
        return total_intensity
    
    def get_gradient(self, position: np.ndarray, epsilon: float = 0.1) -> np.ndarray:
        """
        Compute pheromone gradient at position.
        
        Args:
            position: Query position (x, y)
            epsilon: Gradient step size
            
        Returns:
            Gradient vector (2,)
        """
        # Finite difference gradient
        intensity_center = self.sense(position)
        
        pos_x_plus = position + np.array([epsilon, 0])
        intensity_x_plus = self.sense(pos_x_plus)
        
        pos_y_plus = position + np.array([0, epsilon])
        intensity_y_plus = self.sense(pos_y_plus)
        
        gradient = np.array([
            (intensity_x_plus - intensity_center) / epsilon,
            (intensity_y_plus - intensity_center) / epsilon
        ])
        
        return gradient
    
    def _update_pheromones(self):
        """Update all pheromones (decay and remove dead ones)."""
        now = time.monotonic()
        
        for grid_pos in list(self.pheromones.keys()):
            pheromone_list = self.pheromones[grid_pos]
            
            # Decay and filter
            updated_list = []
            for pheromone in pheromone_list:
                # Apply decay
                elapsed = now - pheromone.deposited_at
                pheromone.intensity -= pheromone.decay_rate * elapsed
                pheromone.deposited_at = now
                
                # Keep if still has intensity
                if pheromone.intensity > 0.01:
                    updated_list.append(pheromone)
                else:
                    self.total_decayed += 1
            
            if updated_list:
                self.pheromones[grid_pos] = updated_list
            else:
                # Remove empty grid cell
                del self.pheromones[grid_pos]
    
    def _to_grid(self, position: np.ndarray) -> Tuple[int, int]:
        """Convert position to grid coordinates."""
        grid_x = int(position[0] / self.grid_resolution)
        grid_y = int(position[1] / self.grid_resolution)
        return (grid_x, grid_y)
    
    def get_pheromone_map(self) -> Dict[Tuple[int, int], float]:
        """
        Get pheromone intensity map.
        
        Returns:
            Dict of (grid_x, grid_y) -> total_intensity
        """
        self._update_pheromones()
        
        intensity_map = {}
        for grid_pos, pheromone_list in self.pheromones.items():
            total = sum(p.intensity for p in pheromone_list)
            intensity_map[grid_pos] = total
        
        return intensity_map
    
    def clear(self):
        """Clear all pheromones."""
        self.pheromones.clear()
        print("[Stigmergy] Pheromone map cleared")
    
    def get_stats(self) -> Dict:
        """Get stigmergy statistics."""
        self._update_pheromones()
        
        total_pheromones = sum(len(plist) for plist in self.pheromones.values())
        
        return {
            'total_deposited': self.total_deposited,
            'total_decayed': self.total_decayed,
            'active_pheromones': total_pheromones,
            'grid_cells_occupied': len(self.pheromones),
        }
