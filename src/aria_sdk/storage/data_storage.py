"""
ARIA SDK - Data Storage Module

Provides persistent storage for telemetry, cognitive state, and decision logs.
All data is stored in structured format (SQLite + binary files) for analysis.
"""

import sqlite3
import json
import gzip
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import struct

from aria_sdk.domain.entities import Envelope, Detection, Priority


@dataclass
class TelemetryRecord:
    """Record of telemetry data."""
    timestamp: datetime
    envelope_id: str
    topic: str
    priority: int
    payload_size: int
    encoded_size: int
    compressed_size: int
    compression_algo: str
    compression_ratio: float
    encoding_time_ms: float
    compression_time_ms: float


@dataclass
class CognitiveStateRecord:
    """Record of cognitive state."""
    timestamp: datetime
    loop_id: int
    energy: float
    temperature: float
    novelty_drive: float
    num_detections: int
    unique_classes: int


@dataclass
class DecisionRecord:
    """Record of decision made by planner."""
    timestamp: datetime
    loop_id: int
    action: str
    target: Optional[str]
    reasoning: str
    priority_level: int
    energy_level: float


class DataStorage:
    """
    Persistent data storage for ARIA system.
    
    Stores:
    - Telemetry envelopes (compressed binary)
    - Cognitive states (time series)
    - Decisions (action log)
    - Performance metrics
    """
    
    def __init__(self, storage_dir: Path):
        """Initialize storage.
        
        Args:
            storage_dir: Directory for data storage
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Database file
        self.db_path = self.storage_dir / "aria_data.db"
        
        # Binary data directories
        self.telemetry_dir = self.storage_dir / "telemetry"
        self.telemetry_dir.mkdir(exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        # Current session ID
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._create_session()
    
    def _init_database(self):
        """Initialize SQLite database with schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                total_frames INTEGER DEFAULT 0,
                total_loops INTEGER DEFAULT 0,
                config_json TEXT
            )
        """)
        
        # Telemetry records
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp TIMESTAMP,
                envelope_id TEXT,
                topic TEXT,
                priority INTEGER,
                payload_size INTEGER,
                encoded_size INTEGER,
                compressed_size INTEGER,
                compression_algo TEXT,
                compression_ratio REAL,
                encoding_time_ms REAL,
                compression_time_ms REAL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)
        
        # Cognitive state records
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cognitive_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp TIMESTAMP,
                loop_id INTEGER,
                energy REAL,
                temperature REAL,
                novelty_drive REAL,
                num_detections INTEGER,
                unique_classes INTEGER,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)
        
        # Decision records
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp TIMESTAMP,
                loop_id INTEGER,
                action TEXT,
                target TEXT,
                reasoning TEXT,
                priority_level INTEGER,
                energy_level REAL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)
        
        # Performance metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp TIMESTAMP,
                metric_name TEXT,
                metric_value REAL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)
        
        # Create indices for fast queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_session ON telemetry(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cognitive_session ON cognitive_states(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_decisions_session ON decisions(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_time ON telemetry(timestamp)")
        
        conn.commit()
        conn.close()
    
    def _create_session(self):
        """Create new session entry."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO sessions (session_id, start_time, config_json)
            VALUES (?, ?, ?)
        """, (self.session_id, datetime.now(), "{}"))
        
        conn.commit()
        conn.close()
    
    def store_telemetry(
        self, 
        envelope: Envelope, 
        encoded_data: bytes,
        compressed_data: bytes,
        compression_algo: str,
        encoding_time: float,
        compression_time: float
    ):
        """Store telemetry data.
        
        Args:
            envelope: Telemetry envelope
            encoded_data: Encoded payload
            compressed_data: Compressed payload
            compression_algo: Algorithm used (lz4/zstd)
            encoding_time: Encoding time in ms
            compression_time: Compression time in ms
        """
        # Store binary data (compressed)
        data_file = self.telemetry_dir / f"{self.session_id}_{envelope.id}.bin.gz"
        with gzip.open(data_file, 'wb') as f:
            f.write(compressed_data)
        
        # Store metadata in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        compression_ratio = len(encoded_data) / len(compressed_data) if len(compressed_data) > 0 else 0
        
        cursor.execute("""
            INSERT INTO telemetry (
                session_id, timestamp, envelope_id, topic, priority,
                payload_size, encoded_size, compressed_size,
                compression_algo, compression_ratio,
                encoding_time_ms, compression_time_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.session_id,
            envelope.timestamp,
            str(envelope.id),
            envelope.topic,
            envelope.priority.value,
            len(envelope.payload),
            len(encoded_data),
            len(compressed_data),
            compression_algo,
            compression_ratio,
            encoding_time,
            compression_time
        ))
        
        conn.commit()
        conn.close()
    
    def store_cognitive_state(
        self,
        loop_id: int,
        energy: float,
        temperature: float,
        novelty_drive: float,
        num_detections: int,
        unique_classes: int
    ):
        """Store cognitive state snapshot.
        
        Args:
            loop_id: Cognitive loop iteration number
            energy: Current energy level (%)
            temperature: System temperature
            novelty_drive: Novelty drive level
            num_detections: Number of detections
            unique_classes: Number of unique object classes
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO cognitive_states (
                session_id, timestamp, loop_id, energy, temperature,
                novelty_drive, num_detections, unique_classes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.session_id,
            datetime.now(),
            loop_id,
            energy,
            temperature,
            novelty_drive,
            num_detections,
            unique_classes
        ))
        
        conn.commit()
        conn.close()
    
    def store_decision(
        self,
        loop_id: int,
        action: str,
        target: Optional[str],
        reasoning: str,
        priority_level: int,
        energy_level: float
    ):
        """Store decision made by planner.
        
        Args:
            loop_id: Cognitive loop iteration
            action: Action taken
            target: Target of action (if any)
            reasoning: Reasoning for decision
            priority_level: Priority level (0-3)
            energy_level: Energy level when decision made
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO decisions (
                session_id, timestamp, loop_id, action, target,
                reasoning, priority_level, energy_level
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.session_id,
            datetime.now(),
            loop_id,
            action,
            target,
            reasoning,
            priority_level,
            energy_level
        ))
        
        conn.commit()
        conn.close()
    
    def store_metric(self, metric_name: str, value: float):
        """Store performance metric.
        
        Args:
            metric_name: Name of metric
            value: Metric value
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO performance_metrics (
                session_id, timestamp, metric_name, metric_value
            ) VALUES (?, ?, ?, ?)
        """, (self.session_id, datetime.now(), metric_name, value))
        
        conn.commit()
        conn.close()
    
    def close_session(self, total_frames: int, total_loops: int):
        """Close current session.
        
        Args:
            total_frames: Total frames processed
            total_loops: Total cognitive loops
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE sessions
            SET end_time = ?, total_frames = ?, total_loops = ?
            WHERE session_id = ?
        """, (datetime.now(), total_frames, total_loops, self.session_id))
        
        conn.commit()
        conn.close()
    
    def get_session_summary(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get summary of a session.
        
        Args:
            session_id: Session ID (uses current if None)
            
        Returns:
            Dictionary with session summary
        """
        if session_id is None:
            session_id = self.session_id
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Session info
        cursor.execute("""
            SELECT start_time, end_time, total_frames, total_loops
            FROM sessions WHERE session_id = ?
        """, (session_id,))
        session = cursor.fetchone()
        
        # Telemetry stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_envelopes,
                SUM(payload_size) as total_payload,
                SUM(encoded_size) as total_encoded,
                SUM(compressed_size) as total_compressed,
                AVG(compression_ratio) as avg_ratio,
                AVG(encoding_time_ms) as avg_encode_time,
                AVG(compression_time_ms) as avg_compress_time
            FROM telemetry WHERE session_id = ?
        """, (session_id,))
        telemetry = cursor.fetchone()
        
        # Cognitive stats
        cursor.execute("""
            SELECT 
                MIN(energy) as min_energy,
                MAX(energy) as max_energy,
                AVG(energy) as avg_energy,
                AVG(temperature) as avg_temp,
                AVG(novelty_drive) as avg_novelty
            FROM cognitive_states WHERE session_id = ?
        """, (session_id,))
        cognitive = cursor.fetchone()
        
        # Decision stats
        cursor.execute("""
            SELECT action, COUNT(*) as count
            FROM decisions
            WHERE session_id = ?
            GROUP BY action
        """, (session_id,))
        decisions = cursor.fetchall()
        
        conn.close()
        
        return {
            'session_id': session_id,
            'start_time': session[0] if session else None,
            'end_time': session[1] if session else None,
            'total_frames': session[2] if session else 0,
            'total_loops': session[3] if session else 0,
            'telemetry': {
                'total_envelopes': telemetry[0] if telemetry else 0,
                'total_payload_bytes': telemetry[1] if telemetry else 0,
                'total_encoded_bytes': telemetry[2] if telemetry else 0,
                'total_compressed_bytes': telemetry[3] if telemetry else 0,
                'avg_compression_ratio': telemetry[4] if telemetry else 0,
                'avg_encoding_time_ms': telemetry[5] if telemetry else 0,
                'avg_compression_time_ms': telemetry[6] if telemetry else 0,
            },
            'cognitive': {
                'min_energy': cognitive[0] if cognitive else 0,
                'max_energy': cognitive[1] if cognitive else 0,
                'avg_energy': cognitive[2] if cognitive else 0,
                'avg_temperature': cognitive[3] if cognitive else 0,
                'avg_novelty_drive': cognitive[4] if cognitive else 0,
            },
            'decisions': {action: count for action, count in decisions}
        }
    
    def export_session_json(self, session_id: Optional[str] = None) -> Path:
        """Export session data to JSON file.
        
        Args:
            session_id: Session ID (uses current if None)
            
        Returns:
            Path to exported JSON file
        """
        if session_id is None:
            session_id = self.session_id
        
        summary = self.get_session_summary(session_id)
        
        export_file = self.storage_dir / f"session_{session_id}_export.json"
        with open(export_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        return export_file
