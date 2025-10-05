"""
ARIA SDK - Goal Manager Module

Manages mission goals with priority queuing.
"""

import time
from typing import List, Optional, Dict
from dataclasses import dataclass, field
from enum import Enum

from aria_sdk.domain.entities import MissionGoal
from aria_sdk.domain.protocols import IGoalManager


class GoalStatus(Enum):
    """Goal execution status."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ManagedGoal:
    """Internal goal representation with metadata."""
    goal: MissionGoal
    status: GoalStatus = GoalStatus.PENDING
    created_at: float = field(default_factory=time.monotonic)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    progress: float = 0.0
    failure_reason: Optional[str] = None


class GoalManager(IGoalManager):
    """
    Manages mission goals with priority-based execution.
    
    Features:
    - Priority queuing
    - Goal lifecycle tracking
    - Timeout handling
    - Goal cancellation
    """
    
    def __init__(self, max_concurrent_goals: int = 3):
        """
        Initialize goal manager.
        
        Args:
            max_concurrent_goals: Maximum simultaneously active goals
        """
        self.max_concurrent_goals = max_concurrent_goals
        
        # goal_id -> ManagedGoal
        self.goals: Dict[str, ManagedGoal] = {}
        
        # Priority queues
        self.pending_goals: List[str] = []
        self.active_goals: List[str] = []
    
    def add_goal(self, goal: MissionGoal):
        """
        Add new goal to queue.
        
        Args:
            goal: Mission goal to add
        """
        managed_goal = ManagedGoal(goal=goal)
        self.goals[goal.id] = managed_goal
        
        # Insert into pending queue sorted by priority
        self.pending_goals.append(goal.id)
        self.pending_goals.sort(key=lambda gid: self.goals[gid].goal.priority, reverse=True)
        
        print(f"[GoalManager] Added goal: {goal.name} (priority={goal.priority})")
    
    def get_active_goals(self) -> List[MissionGoal]:
        """Get currently active goals."""
        return [self.goals[gid].goal for gid in self.active_goals if gid in self.goals]
    
    def get_next_goal(self) -> Optional[MissionGoal]:
        """
        Get next goal to execute.
        
        Returns:
            Next pending goal, or None if none available or max active reached
        """
        # Check if we can activate more goals
        if len(self.active_goals) >= self.max_concurrent_goals:
            return None
        
        # Get highest priority pending goal
        if not self.pending_goals:
            return None
        
        goal_id = self.pending_goals.pop(0)
        managed_goal = self.goals[goal_id]
        
        # Activate goal
        managed_goal.status = GoalStatus.ACTIVE
        managed_goal.started_at = time.monotonic()
        self.active_goals.append(goal_id)
        
        print(f"[GoalManager] Activated goal: {managed_goal.goal.name}")
        
        return managed_goal.goal
    
    def update_progress(self, goal_id: str, progress: float):
        """
        Update goal progress.
        
        Args:
            goal_id: Goal ID
            progress: Progress (0.0-1.0)
        """
        if goal_id in self.goals:
            self.goals[goal_id].progress = max(0.0, min(1.0, progress))
    
    def complete_goal(self, goal_id: str, success: bool = True, reason: Optional[str] = None):
        """
        Mark goal as completed or failed.
        
        Args:
            goal_id: Goal ID
            success: True if completed successfully
            reason: Failure reason if not successful
        """
        if goal_id not in self.goals:
            return
        
        managed_goal = self.goals[goal_id]
        managed_goal.completed_at = time.monotonic()
        
        if success:
            managed_goal.status = GoalStatus.COMPLETED
            managed_goal.progress = 1.0
            print(f"[GoalManager] Goal completed: {managed_goal.goal.name}")
        else:
            managed_goal.status = GoalStatus.FAILED
            managed_goal.failure_reason = reason
            print(f"[GoalManager] Goal failed: {managed_goal.goal.name} - {reason}")
        
        # Remove from active
        if goal_id in self.active_goals:
            self.active_goals.remove(goal_id)
    
    def cancel_goal(self, goal_id: str):
        """Cancel a goal."""
        if goal_id not in self.goals:
            return
        
        managed_goal = self.goals[goal_id]
        managed_goal.status = GoalStatus.CANCELLED
        managed_goal.completed_at = time.monotonic()
        
        # Remove from queues
        if goal_id in self.pending_goals:
            self.pending_goals.remove(goal_id)
        if goal_id in self.active_goals:
            self.active_goals.remove(goal_id)
        
        print(f"[GoalManager] Goal cancelled: {managed_goal.goal.name}")
    
    def get_goal_status(self, goal_id: str) -> Optional[GoalStatus]:
        """Get goal status."""
        managed_goal = self.goals.get(goal_id)
        return managed_goal.status if managed_goal else None
    
    def get_stats(self) -> Dict:
        """Get goal manager statistics."""
        completed = sum(1 for g in self.goals.values() if g.status == GoalStatus.COMPLETED)
        failed = sum(1 for g in self.goals.values() if g.status == GoalStatus.FAILED)
        
        return {
            'total_goals': len(self.goals),
            'pending': len(self.pending_goals),
            'active': len(self.active_goals),
            'completed': completed,
            'failed': failed,
        }
