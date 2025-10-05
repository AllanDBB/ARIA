"""
ARIA SDK - Safety Supervisor Module

Imperative safety override and veto system.
"""

import numpy as np
from typing import Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

from aria_sdk.domain.entities import Command, State
from aria_sdk.domain.protocols import ISafetySupervisor


class ViolationType(Enum):
    """Types of safety violations."""
    VELOCITY_LIMIT = "velocity_limit"
    ACCELERATION_LIMIT = "acceleration_limit"
    POSITION_LIMIT = "position_limit"
    ORIENTATION_LIMIT = "orientation_limit"
    OBSTACLE_PROXIMITY = "obstacle_proximity"
    BATTERY_LOW = "battery_low"
    TIMEOUT = "timeout"


@dataclass
class SafetyViolation:
    """Description of a safety violation."""
    violation_type: ViolationType
    severity: float  # 0.0 (minor) to 1.0 (critical)
    description: str
    timestamp: float


@dataclass
class SafetyLimits:
    """Safety constraint limits."""
    max_linear_velocity: float = 2.0  # m/s
    max_angular_velocity: float = 1.0  # rad/s
    max_linear_acceleration: float = 5.0  # m/s^2
    max_angular_acceleration: float = 3.0  # rad/s^2
    min_obstacle_distance: float = 0.5  # meters
    min_battery_voltage: float = 10.5  # volts
    workspace_bounds: Optional[Tuple[float, float, float, float]] = None  # (x_min, x_max, y_min, y_max)


class SafetySupervisor(ISafetySupervisor):
    """
    Safety supervisor with imperative override and veto.
    
    Responsibilities:
    - Velocity/acceleration clamping
    - Workspace boundary enforcement
    - Collision avoidance
    - Emergency stop
    - Safety violation logging
    """
    
    def __init__(self, limits: Optional[SafetyLimits] = None):
        """
        Initialize safety supervisor.
        
        Args:
            limits: Safety limits (uses defaults if None)
        """
        self.limits = limits or SafetyLimits()
        
        # State tracking
        self.last_command: Optional[Command] = None
        self.last_state: Optional[State] = None
        self.last_timestamp: float = 0.0
        
        # Violation history
        self.violations: List[SafetyViolation] = []
        self.emergency_stop_active = False
        
        # Statistics
        self.total_commands = 0
        self.total_violations = 0
        self.total_vetoes = 0
    
    def supervise(self, command: Command, state: State) -> Command:
        """
        Supervise command for safety violations.
        
        Args:
            command: Proposed command
            state: Current robot state
            
        Returns:
            Safe command (clamped/vetoed if needed)
        """
        import time
        now = time.monotonic()
        
        self.total_commands += 1
        
        # Check emergency stop
        if self.emergency_stop_active:
            return self._emergency_stop_command()
        
        # Check battery
        if state.battery_voltage < self.limits.min_battery_voltage:
            self._add_violation(
                ViolationType.BATTERY_LOW,
                0.9,
                f"Battery low: {state.battery_voltage:.1f}V < {self.limits.min_battery_voltage:.1f}V"
            )
            return self._emergency_stop_command()
        
        # Check workspace bounds
        if self.limits.workspace_bounds:
            x_min, x_max, y_min, y_max = self.limits.workspace_bounds
            if not (x_min <= state.pose.x <= x_max and y_min <= state.pose.y <= y_max):
                self._add_violation(
                    ViolationType.POSITION_LIMIT,
                    0.8,
                    f"Outside workspace: ({state.pose.x:.2f}, {state.pose.y:.2f})"
                )
                # Veto command
                self.total_vetoes += 1
                return self._stop_command()
        
        # Clamp velocities
        safe_command = self._clamp_velocities(command, state)
        
        # Check acceleration limits
        safe_command = self._limit_acceleration(safe_command, state, now)
        
        # Update tracking
        self.last_command = safe_command
        self.last_state = state
        self.last_timestamp = now
        
        return safe_command
    
    def _clamp_velocities(self, command: Command, state: State) -> Command:
        """Clamp command velocities to safe limits."""
        from aria_sdk.domain.entities import ActuatorAction
        import copy
        
        safe_command = copy.deepcopy(command)
        
        if safe_command.action.action_type != 'velocity':
            return safe_command  # Only clamp velocity commands
        
        # Extract velocities
        vx = safe_command.action.values.get('vx', 0.0)
        vy = safe_command.action.values.get('vy', 0.0)
        vz = safe_command.action.values.get('vz', 0.0)
        
        # Compute linear velocity magnitude
        linear_vel = np.sqrt(vx**2 + vy**2 + vz**2)
        
        if linear_vel > self.limits.max_linear_velocity:
            # Clamp and maintain direction
            scale = self.limits.max_linear_velocity / linear_vel
            safe_command.action.values['vx'] = vx * scale
            safe_command.action.values['vy'] = vy * scale
            safe_command.action.values['vz'] = vz * scale
            
            self._add_violation(
                ViolationType.VELOCITY_LIMIT,
                0.5,
                f"Velocity clamped: {linear_vel:.2f} -> {self.limits.max_linear_velocity:.2f} m/s"
            )
        
        # Clamp angular velocity
        wz = safe_command.action.values.get('wz', 0.0)
        if abs(wz) > self.limits.max_angular_velocity:
            safe_command.action.values['wz'] = np.sign(wz) * self.limits.max_angular_velocity
            self._add_violation(
                ViolationType.VELOCITY_LIMIT,
                0.5,
                f"Angular velocity clamped: {wz:.2f} -> {safe_command.action.values['wz']:.2f} rad/s"
            )
        
        return safe_command
    
    def _limit_acceleration(self, command: Command, state: State, now: float) -> Command:
        """Limit command acceleration."""
        if self.last_command is None or self.last_state is None:
            return command  # First command, no previous to compare
        
        dt = now - self.last_timestamp
        if dt <= 0 or dt > 1.0:
            return command  # Invalid dt
        
        # Extract current and previous velocities
        curr_vx = command.action.values.get('vx', 0.0)
        curr_vy = command.action.values.get('vy', 0.0)
        prev_vx = self.last_command.action.values.get('vx', 0.0)
        prev_vy = self.last_command.action.values.get('vy', 0.0)
        
        # Compute acceleration
        ax = (curr_vx - prev_vx) / dt
        ay = (curr_vy - prev_vy) / dt
        accel_mag = np.sqrt(ax**2 + ay**2)
        
        if accel_mag > self.limits.max_linear_acceleration:
            # Limit acceleration
            scale = self.limits.max_linear_acceleration / accel_mag
            limited_ax = ax * scale
            limited_ay = ay * scale
            
            # Compute limited velocities
            import copy
            safe_command = copy.deepcopy(command)
            safe_command.action.values['vx'] = prev_vx + limited_ax * dt
            safe_command.action.values['vy'] = prev_vy + limited_ay * dt
            
            self._add_violation(
                ViolationType.ACCELERATION_LIMIT,
                0.6,
                f"Acceleration limited: {accel_mag:.2f} -> {self.limits.max_linear_acceleration:.2f} m/s^2"
            )
            
            return safe_command
        
        return command
    
    def _add_violation(self, violation_type: ViolationType, severity: float, description: str):
        """Add safety violation to history."""
        import time
        
        violation = SafetyViolation(
            violation_type=violation_type,
            severity=severity,
            description=description,
            timestamp=time.monotonic()
        )
        
        self.violations.append(violation)
        self.total_violations += 1
        
        # Limit history size
        if len(self.violations) > 1000:
            self.violations.pop(0)
        
        print(f"[SafetySupervisor] VIOLATION: {description}")
    
    def _stop_command(self) -> Command:
        """Generate stop command."""
        from aria_sdk.domain.entities import ActuatorAction
        from uuid import uuid4
        from datetime import datetime, timezone
        
        return Command(
            id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            actuator_id="all",
            action=ActuatorAction(
                action_type="velocity",
                values={'vx': 0.0, 'vy': 0.0, 'vz': 0.0, 'wz': 0.0}
            )
        )
    
    def _emergency_stop_command(self) -> Command:
        """Generate emergency stop command."""
        return self._stop_command()
    
    def trigger_emergency_stop(self, reason: str):
        """
        Trigger emergency stop.
        
        Args:
            reason: Reason for emergency stop
        """
        self.emergency_stop_active = True
        self._add_violation(
            ViolationType.TIMEOUT,
            1.0,
            f"EMERGENCY STOP: {reason}"
        )
        print(f"[SafetySupervisor] EMERGENCY STOP ACTIVATED: {reason}")
    
    def reset_emergency_stop(self):
        """Reset emergency stop."""
        self.emergency_stop_active = False
        print("[SafetySupervisor] Emergency stop reset")
    
    def get_recent_violations(self, count: int = 10) -> List[SafetyViolation]:
        """Get recent violations."""
        return self.violations[-count:]
    
    def get_stats(self) -> dict:
        """Get safety statistics."""
        return {
            'total_commands': self.total_commands,
            'total_violations': self.total_violations,
            'total_vetoes': self.total_vetoes,
            'emergency_stop_active': self.emergency_stop_active,
            'recent_violations': len(self.violations[-100:])
        }
