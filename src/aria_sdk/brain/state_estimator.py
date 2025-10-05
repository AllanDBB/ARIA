"""
ARIA SDK - State Estimator Module

Kalman filter for robot state estimation (pose, velocity).
"""

import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass

from aria_sdk.domain.entities import State, Pose, Twist
from aria_sdk.domain.protocols import IStateEstimator


@dataclass
class KalmanState:
    """Kalman filter internal state."""
    # State vector: [x, y, z, vx, vy, vz, roll, pitch, yaw]
    x: np.ndarray  # State estimate (9,)
    P: np.ndarray  # Covariance matrix (9, 9)


class StateEstimator(IStateEstimator):
    """
    Extended Kalman Filter for robot state estimation.
    
    State vector: [x, y, z, vx, vy, vz, roll, pitch, yaw]
    - Position (x, y, z) in meters
    - Velocity (vx, vy, vz) in m/s
    - Orientation (roll, pitch, yaw) in radians
    """
    
    def __init__(self, process_noise: float = 0.1, measurement_noise: float = 0.5):
        """
        Initialize Kalman filter.
        
        Args:
            process_noise: Process noise std deviation
            measurement_noise: Measurement noise std deviation
        """
        # State dimension
        self.n = 9
        
        # Initialize state
        self.state = KalmanState(
            x=np.zeros(9),
            P=np.eye(9) * 10.0  # Initial uncertainty
        )
        
        # Process noise covariance Q
        self.Q = np.eye(9) * (process_noise ** 2)
        
        # Measurement noise covariance R
        self.R = np.eye(9) * (measurement_noise ** 2)
        
        # State transition matrix F (will be updated in predict)
        self.F = np.eye(9)
        
        # Measurement matrix H (identity - we measure all states directly)
        self.H = np.eye(9)
    
    def predict(self, dt: float, control: Optional[np.ndarray] = None):
        """
        Prediction step: predict state forward by dt.
        
        Args:
            dt: Time step (seconds)
            control: Optional control input (vx, vy, vz, wx, wy, wz)
        """
        # Update state transition matrix with dt
        # Position evolves with velocity: x += vx * dt
        self.F = np.eye(9)
        self.F[0, 3] = dt  # x += vx * dt
        self.F[1, 4] = dt  # y += vy * dt
        self.F[2, 5] = dt  # z += vz * dt
        
        # Predict state
        if control is not None:
            # Apply control input (simplified)
            control_full = np.zeros(9)
            control_full[3:6] = control[:3]  # Linear velocity control
            control_full[6:9] = control[3:6] * dt  # Angular velocity control
            self.state.x = self.F @ self.state.x + control_full
        else:
            self.state.x = self.F @ self.state.x
        
        # Predict covariance
        self.state.P = self.F @ self.state.P @ self.F.T + self.Q
    
    def update(self, measurement: np.ndarray, measurement_noise: Optional[np.ndarray] = None):
        """
        Update step: correct state with measurement.
        
        Args:
            measurement: Measurement vector (up to 9 dimensions)
            measurement_noise: Optional measurement noise covariance
        """
        # Measurement dimension
        m = len(measurement)
        
        # Measurement matrix (identity for available measurements)
        H = self.H[:m, :]
        
        # Measurement noise
        R = self.R[:m, :m] if measurement_noise is None else measurement_noise
        
        # Innovation
        y = measurement - (H @ self.state.x)
        
        # Innovation covariance
        S = H @ self.state.P @ H.T + R
        
        # Kalman gain
        K = self.state.P @ H.T @ np.linalg.inv(S)
        
        # Update state
        self.state.x = self.state.x + K @ y
        
        # Update covariance (Joseph form for numerical stability)
        I_KH = np.eye(9) - K @ H
        self.state.P = I_KH @ self.state.P @ I_KH.T + K @ R @ K.T
    
    def update_pose(self, pose: Pose):
        """
        Update with pose measurement.
        
        Args:
            pose: Measured pose (x, y, z, roll, pitch, yaw)
        """
        measurement = np.array([
            pose.x, pose.y, pose.z,
            0, 0, 0,  # No velocity info
            pose.roll, pose.pitch, pose.yaw
        ])
        self.update(measurement)
    
    def update_velocity(self, twist: Twist):
        """
        Update with velocity measurement.
        
        Args:
            twist: Measured twist (linear and angular velocity)
        """
        # Create partial measurement (only velocity)
        # We'll use a modified H matrix for this
        measurement = np.array([
            twist.linear_x, twist.linear_y, twist.linear_z,
            twist.angular_x, twist.angular_y, twist.angular_z
        ])
        
        # Measurement matrix for velocity only
        H = np.zeros((6, 9))
        H[0, 3] = 1  # vx
        H[1, 4] = 1  # vy
        H[2, 5] = 1  # vz
        H[3, 6] = 1  # roll_rate (approx)
        H[4, 7] = 1  # pitch_rate (approx)
        H[5, 8] = 1  # yaw_rate (approx)
        
        # Innovation
        y = measurement - (H @ self.state.x)
        
        # Innovation covariance
        R = np.eye(6) * 0.1  # Lower noise for velocity
        S = H @ self.state.P @ H.T + R
        
        # Kalman gain
        K = self.state.P @ H.T @ np.linalg.inv(S)
        
        # Update
        self.state.x = self.state.x + K @ y
        I_KH = np.eye(9) - K @ H
        self.state.P = I_KH @ self.state.P @ I_KH.T + K @ R @ K.T
    
    def get_state(self) -> State:
        """
        Get current state estimate.
        
        Returns:
            Estimated robot state
        """
        from aria_sdk.domain.entities import RobotMode
        
        pose = Pose(
            x=float(self.state.x[0]),
            y=float(self.state.x[1]),
            z=float(self.state.x[2]),
            roll=float(self.state.x[6]),
            pitch=float(self.state.x[7]),
            yaw=float(self.state.x[8])
        )
        
        twist = Twist(
            linear_x=float(self.state.x[3]),
            linear_y=float(self.state.x[4]),
            linear_z=float(self.state.x[5]),
            angular_x=0.0,  # Not tracked
            angular_y=0.0,
            angular_z=0.0
        )
        
        return State(
            pose=pose,
            twist=twist,
            mode=RobotMode.AUTONOMOUS,
            battery_voltage=12.0  # Placeholder
        )
    
    def get_covariance(self) -> np.ndarray:
        """Get state covariance matrix."""
        return self.state.P.copy()
    
    def get_uncertainty(self) -> Tuple[float, float, float]:
        """
        Get position uncertainty (std deviations).
        
        Returns:
            Tuple of (sigma_x, sigma_y, sigma_z)
        """
        return (
            float(np.sqrt(self.state.P[0, 0])),
            float(np.sqrt(self.state.P[1, 1])),
            float(np.sqrt(self.state.P[2, 2]))
        )
    
    def reset(self, initial_state: Optional[np.ndarray] = None, initial_cov: Optional[np.ndarray] = None):
        """
        Reset filter state.
        
        Args:
            initial_state: Initial state vector (None=zeros)
            initial_cov: Initial covariance (None=identity * 10)
        """
        self.state.x = initial_state if initial_state is not None else np.zeros(9)
        self.state.P = initial_cov if initial_cov is not None else np.eye(9) * 10.0
