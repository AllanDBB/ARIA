"""
ARIA SDK - Action Synthesizer Module

Synthesizes actuator commands from high-level actions.
"""

from typing import Dict, Optional
from datetime import datetime, timezone
from uuid import uuid4
import numpy as np

from aria_sdk.domain.entities import Command, State, ActuatorAction
from aria_sdk.domain.protocols import IActionSynthesizer


class ActionSynthesizer(IActionSynthesizer):
    """
    Synthesizes low-level commands from high-level actions.
    
    Translates skill names and parameters into actuator commands.
    """
    
    def __init__(self):
        """Initialize action synthesizer."""
        # Skill registry: skill_name -> synthesis function
        self.skills = {
            'stop': self._skill_stop,
            'move_forward': self._skill_move_forward,
            'turn': self._skill_turn,
            'navigate': self._skill_navigate,
            'follow': self._skill_follow,
            'avoid': self._skill_avoid,
        }
    
    def synthesize(self, action_name: str, parameters: Dict, state: State) -> Command:
        """
        Synthesize command from action.
        
        Args:
            action_name: High-level action/skill name
            parameters: Action parameters
            state: Current robot state
            
        Returns:
            Synthesized command
            
        Raises:
            ValueError: If action not found
        """
        if action_name not in self.skills:
            raise ValueError(f"Unknown action: {action_name}. Available: {list(self.skills.keys())}")
        
        # Call skill function
        action = self.skills[action_name](parameters, state)
        
        # Wrap in command
        command = Command(
            id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            actuator_id="base_controller",
            action=action
        )
        
        return command
    
    def _skill_stop(self, params: Dict, state: State) -> ActuatorAction:
        """Stop skill - zero velocity."""
        return ActuatorAction(
            action_type="velocity",
            values={'vx': 0.0, 'vy': 0.0, 'vz': 0.0, 'wz': 0.0}
        )
    
    def _skill_move_forward(self, params: Dict, state: State) -> ActuatorAction:
        """Move forward skill."""
        speed = params.get('speed', 0.5)
        return ActuatorAction(
            action_type="velocity",
            values={'vx': speed, 'vy': 0.0, 'vz': 0.0, 'wz': 0.0}
        )
    
    def _skill_turn(self, params: Dict, state: State) -> ActuatorAction:
        """Turn skill."""
        angular_speed = params.get('angular_speed', 0.5)
        direction = params.get('direction', 'left')  # 'left' or 'right'
        
        wz = angular_speed if direction == 'left' else -angular_speed
        
        return ActuatorAction(
            action_type="velocity",
            values={'vx': 0.0, 'vy': 0.0, 'vz': 0.0, 'wz': wz}
        )
    
    def _skill_navigate(self, params: Dict, state: State) -> ActuatorAction:
        """Navigate skill - move toward goal."""
        vx = params.get('vx', 0.5)
        vy = params.get('vy', 0.0)
        wz = params.get('wz', 0.0)
        
        return ActuatorAction(
            action_type="velocity",
            values={'vx': vx, 'vy': vy, 'vz': 0.0, 'wz': wz}
        )
    
    def _skill_follow(self, params: Dict, state: State) -> ActuatorAction:
        """Follow skill - follow detected object."""
        target_x = params.get('target_x', 320)  # Image coordinates
        target_y = params.get('target_y', 240)
        image_width = params.get('image_width', 640)
        
        # Simple proportional control to center target
        error_x = (target_x - image_width / 2) / (image_width / 2)
        
        # Turn to center target
        wz = -0.5 * error_x  # Proportional gain
        
        # Move forward at constant speed
        vx = 0.3
        
        return ActuatorAction(
            action_type="velocity",
            values={'vx': vx, 'vy': 0.0, 'vz': 0.0, 'wz': wz}
        )
    
    def _skill_avoid(self, params: Dict, state: State) -> ActuatorAction:
        """Avoid skill - avoid obstacle."""
        obstacle_direction = params.get('direction', 'front')  # 'front', 'left', 'right'
        
        if obstacle_direction == 'front':
            # Back up and turn
            return ActuatorAction(
                action_type="velocity",
                values={'vx': -0.2, 'vy': 0.0, 'vz': 0.0, 'wz': 0.5}
            )
        elif obstacle_direction == 'left':
            # Turn right
            return ActuatorAction(
                action_type="velocity",
                values={'vx': 0.1, 'vy': 0.0, 'vz': 0.0, 'wz': -0.5}
            )
        else:  # 'right'
            # Turn left
            return ActuatorAction(
                action_type="velocity",
                values={'vx': 0.1, 'vy': 0.0, 'vz': 0.0, 'wz': 0.5}
            )
    
    def register_skill(self, name: str, function):
        """
        Register custom skill.
        
        Args:
            name: Skill name
            function: Synthesis function(params, state) -> ActuatorAction
        """
        self.skills[name] = function
        print(f"[ActionSynthesizer] Registered skill: {name}")
    
    def list_skills(self) -> list[str]:
        """List available skills."""
        return list(self.skills.keys())
