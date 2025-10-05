"""Complete End-to-End ARIA System Demo.

Full pipeline demonstration:
1. Perception: YOLO vision (camera)
2. Cognitive: IMA + Brain (novelty, homeostasis, planning)
3. Telemetry: Encoding + Compression (ProtobufCodec + LZ4/Zstd)
4. Visualization: Real-time metrics

This proves the entire ARIA architecture working together.

Usage:
    # Full system with YOLOv11
    python -m aria_sdk.examples.full_system_demo
    
    # With YOLOv8
    python -m aria_sdk.examples.full_system_demo --yolo-version 8
    
    # With video file
    python -m aria_sdk.examples.full_system_demo --video demo.mp4
    
    # Measure telemetry performance
    python -m aria_sdk.examples.full_system_demo --telemetry-test
"""

import argparse
import sys
import time
import struct
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict
import json

try:
    import cv2
except ImportError:
    print("❌ OpenCV not installed: pip install opencv-python")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.table import Table
    from rich import box
except ImportError:
    print("❌ Rich not installed: pip install rich")
    sys.exit(1)

try:
    from aria_sdk.perception.yolo_detector import YoloDetector
except ImportError:
    print("❌ YOLO detector not available: pip install ultralytics")
    sys.exit(1)

from aria_sdk.domain.entities import Detection, Envelope, Priority
from aria_sdk.telemetry.codec import ProtobufCodec
from aria_sdk.telemetry.compression import Lz4Compressor, ZstdCompressor
from aria_sdk.storage.data_storage import DataStorage

# Import cognitive components
sys.path.insert(0, str(Path(__file__).parent))
from cognitive_loop_demo import (
    SimpleNoveltyDetector,
    SimpleHomeostasisMonitor,
    SimpleWorldModel,
    SimplePlanner,
    NoveltyScore,
    HomeostasisState,
    DecisionInfo,
    Action
)


class TelemetryStats:
    """Track telemetry performance metrics."""
    
    def __init__(self):
        self.total_detections = 0
        self.total_envelopes = 0
        self.total_raw_bytes = 0
        self.total_encoded_bytes = 0
        self.total_lz4_bytes = 0
        self.total_zstd_bytes = 0
        self.encoding_time = 0.0
        self.lz4_time = 0.0
        self.zstd_time = 0.0
    
    @property
    def encoding_throughput(self) -> float:
        """MB/s encoding throughput."""
        if self.encoding_time == 0:
            return 0.0
        return (self.total_encoded_bytes / (1024 * 1024)) / self.encoding_time
    
    @property
    def lz4_compression_ratio(self) -> float:
        """LZ4 compression ratio."""
        if self.total_lz4_bytes == 0:
            return 0.0
        return self.total_encoded_bytes / self.total_lz4_bytes
    
    @property
    def zstd_compression_ratio(self) -> float:
        """Zstd compression ratio."""
        if self.total_zstd_bytes == 0:
            return 0.0
        return self.total_encoded_bytes / self.total_zstd_bytes
    
    @property
    def lz4_throughput(self) -> float:
        """MB/s LZ4 throughput."""
        if self.lz4_time == 0:
            return 0.0
        return (self.total_encoded_bytes / (1024 * 1024)) / self.lz4_time
    
    @property
    def zstd_throughput(self) -> float:
        """MB/s Zstd throughput."""
        if self.zstd_time == 0:
            return 0.0
        return (self.total_encoded_bytes / (1024 * 1024)) / self.zstd_time


class FullSystemDemo:
    """Complete ARIA system demonstration."""
    
    def __init__(
        self,
        camera_id: int = 0,
        video_path: Optional[str] = None,
        yolo_version: str = '11',
        model_size: str = 'n',
        confidence: float = 0.5,
        enable_telemetry: bool = True,
        energy_drain_rate: float = 0.5,
        stream_host: Optional[str] = None,
        stream_port: int = 5555
    ):
        """Initialize full system.
        
        Args:
            camera_id: Camera device ID
            video_path: Path to video file (optional)
            yolo_version: YOLO version ('8' or '11')
            model_size: Model size ('n', 's', 'm', 'l', 'x')
            confidence: Detection confidence threshold
            enable_telemetry: Enable telemetry encoding/compression
            energy_drain_rate: Energy drain rate in % per second (default: 0.5)
                              Higher = faster drain for testing
                              Examples: 0.5=slow(200s), 1.0=normal(100s), 
                                       2.0=fast(50s), 5.0=very_fast(20s)
            stream_host: Host to stream telemetry to (None = no streaming)
            stream_port: Port for streaming
        """
        self.console = Console()
        
        # Streaming setup
        self.stream_socket = None
        self.envelopes_sent = 0  # Track sent envelopes
        if stream_host:
            self.console.print(f"[cyan]📡 Connecting to receiver at {stream_host}:{stream_port}...[/cyan]")
            try:
                self.stream_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.stream_socket.connect((stream_host, stream_port))
                self.console.print(f"[green]✅ Connected to receiver[/green]")
            except Exception as e:
                self.console.print(f"[red]❌ Failed to connect to receiver: {e}[/red]")
                self.stream_socket = None
        else:
            self.console.print(f"[yellow]⚠️  Streaming disabled (no --stream parameter)[/yellow]")
        
        # Vision system
        self.console.print(f"\n[cyan]🎥 Initializing YOLOv{yolo_version} vision system...[/cyan]")
        self.detector = YoloDetector(
            model_size=model_size,
            model_version=yolo_version,
            confidence_threshold=confidence,
            device='cpu'
        )
        
        # Cognitive components
        self.console.print(f"[cyan]🧠 Initializing cognitive system (IMA + Brain)...[/cyan]")
        self.novelty_detector = SimpleNoveltyDetector()
        self.homeostasis = SimpleHomeostasisMonitor(energy_drain_rate=energy_drain_rate)
        self.world_model = SimpleWorldModel()
        self.planner = SimplePlanner()
        
        # Telemetry system
        self.enable_telemetry = enable_telemetry
        if enable_telemetry:
            self.console.print(f"[cyan]📡 Initializing telemetry system (Codec + Compression)...[/cyan]")
            self.codec = ProtobufCodec()
            self.lz4_compressor = Lz4Compressor(level=0)  # Fast compression
            self.zstd_compressor = ZstdCompressor(level=3)  # Balanced compression
            self.telemetry_stats = TelemetryStats()
        
        # Data storage
        self.console.print(f"[cyan]💾 Initializing data storage system...[/cyan]")
        self.storage = DataStorage(storage_dir=Path("./data"))
        
        # Input source
        self.camera_id = camera_id
        self.video_path = video_path
        self.cap = None
        
        # Metrics
        self.loop_count = 0
        self.start_time = time.time()
        self.frame_count = 0
        
        self.console.print(f"[green]✅ Full ARIA system ready[/green]\n")
    
    def open_source(self):
        """Open video source."""
        if self.video_path:
            self.console.print(f"[cyan]📹 Opening video: {self.video_path}[/cyan]")
            self.cap = cv2.VideoCapture(self.video_path)
        else:
            self.console.print(f"[cyan]📷 Opening camera: {self.camera_id}[/cyan]")
            self.cap = cv2.VideoCapture(self.camera_id)
        
        if not self.cap.isOpened():
            raise RuntimeError("Failed to open video source")
        
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        self.console.print(f"[green]✅ Source: {width}x{height} @ {fps:.1f} FPS[/green]\n")
    
    def close_source(self):
        """Close video source."""
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        if self.stream_socket:
            self.stream_socket.close()
    
    def _send_envelope(self, envelope: Envelope, compressed_data: bytes):
        """Send envelope to receiver over network.
        
        Protocol:
        - 4 bytes: message length (network byte order)
        - JSON metadata line
        - Compressed binary data
        """
        # Build metadata
        metadata = {
            'envelope_id': envelope.envelope_id,
            'topic': envelope.topic,
            'priority': envelope.priority.name,
            'timestamp': envelope.timestamp,
            'compression': 'lz4',
            'payload_size': envelope.payload_size
        }
        metadata_json = json.dumps(metadata).encode('utf-8')
        
        # Build message: metadata + newline + binary data
        message = metadata_json + b'\n' + compressed_data
        
        # Send with length prefix
        length_prefix = struct.pack('!I', len(message))
        self.stream_socket.sendall(length_prefix + message)
    
    def process_telemetry(self, detections: List[Detection]) -> Dict:
        """Process detections through telemetry pipeline.
        
        Returns:
            Dict with telemetry metrics
        """
        if not self.enable_telemetry:
            return {}
        
        if not detections:
            # No detections, nothing to transmit
            return {}
        
        # Create envelopes from detections
        envelopes = []
        for det in detections:
            # Serialize detection as JSON for payload
            payload_dict = {
                'class_id': det.class_id,
                'class_name': det.class_name,
                'confidence': det.confidence,
                'bbox': list(det.bbox)
            }
            payload = json.dumps(payload_dict).encode('utf-8')
            
            envelope = Envelope.create(
                topic=f"perception/detection/{det.class_name}",
                payload=payload,
                priority=Priority.P2,
                source_node="vision_system",
                sequence_number=self.telemetry_stats.total_envelopes
            )
            envelopes.append(envelope)
        
        self.telemetry_stats.total_detections += len(detections)
        self.telemetry_stats.total_envelopes += len(envelopes)
        
        # Encode each envelope individually and concatenate
        t0 = time.perf_counter()
        encoded_parts = []
        for envelope in envelopes:
            encoded_parts.append(self.codec.encode(envelope))
        encoded_batch = b''.join(encoded_parts)
        t1 = time.perf_counter()
        encode_time_ms = (t1 - t0) * 1000
        self.telemetry_stats.encoding_time += (t1 - t0)
        self.telemetry_stats.total_encoded_bytes += len(encoded_batch)
        
        # Compress with LZ4
        t0 = time.perf_counter()
        lz4_compressed = self.lz4_compressor.compress(encoded_batch)
        t1 = time.perf_counter()
        lz4_time_ms = (t1 - t0) * 1000
        self.telemetry_stats.lz4_time += (t1 - t0)
        self.telemetry_stats.total_lz4_bytes += len(lz4_compressed)
        
        # Compress with Zstd
        t0 = time.perf_counter()
        zstd_compressed = self.zstd_compressor.compress(encoded_batch)
        t1 = time.perf_counter()
        zstd_time_ms = (t1 - t0) * 1000
        self.telemetry_stats.zstd_time += (t1 - t0)
        self.telemetry_stats.total_zstd_bytes += len(zstd_compressed)
        
        # Store telemetry data for each envelope (using LZ4 as primary)
        for envelope in envelopes:
            encoded = self.codec.encode(envelope)
            compressed = self.lz4_compressor.compress(encoded)
            self.storage.store_telemetry(
                envelope=envelope,
                encoded_data=encoded,
                compressed_data=compressed,
                compression_algo='lz4',
                encoding_time=encode_time_ms / len(envelopes),
                compression_time=lz4_time_ms / len(envelopes)
            )
            
            # Stream to receiver if connected
            if self.stream_socket:
                try:
                    self._send_envelope(envelope, compressed)
                    self.envelopes_sent += 1
                    # Debug: confirm sending (uncomment for verbose mode)
                    if self.envelopes_sent <= 5 or self.envelopes_sent % 50 == 0:
                        self.console.print(f"[dim]📤 Sent envelope #{self.envelopes_sent}: {envelope.topic}[/dim]")
                except Exception as e:
                    self.console.print(f"[red]❌ Stream error: {e}[/red]")
                    import traceback
                    traceback.print_exc()
                    self.stream_socket = None
        
        return {
            'envelopes': len(envelopes),
            'raw_size': len(encoded_batch),
            'lz4_size': len(lz4_compressed),
            'zstd_size': len(zstd_compressed),
            'lz4_ratio': len(encoded_batch) / len(lz4_compressed) if lz4_compressed else 0,
            'zstd_ratio': len(encoded_batch) / len(zstd_compressed) if zstd_compressed else 0
        }
    
    def run_loop_iteration(self) -> tuple:
        """Run one full system iteration.
        
        Returns:
            (frame, detections, novelty_scores, decision, homeostasis_state, telemetry_metrics)
        """
        # 1. PERCEPTION: Capture frame
        ret, frame = self.cap.read()
        if not ret:
            return None, [], [], None, None, {}
        
        self.frame_count += 1
        
        # 2. VISION: Detect objects with YOLO
        detections, annotated = self.detector.detect(frame, visualize=True)
        timestamp = datetime.now(timezone.utc)
        
        # 3. TELEMETRY: Encode + Compress detections
        telemetry_metrics = self.process_telemetry(detections)
        
        # 4. IMA: Compute novelty
        novelty_scores = [self.novelty_detector.compute_novelty(det) for det in detections]
        
        # 5. WORLD MODEL: Update with detections
        self.world_model.update(detections, novelty_scores, timestamp)
        
        # 6. HOMEOSTASIS: Update internal state
        dt = 1.0 / 30.0
        self.homeostasis.update(dt=dt)
        homeostasis_state = self.homeostasis.get_state()
        
        # 7. PLANNER: Decide action
        decision = self.planner.decide(self.world_model, homeostasis_state, self.novelty_detector)
        
        self.loop_count += 1
        
        # 8. STORAGE: Store cognitive state and decision
        avg_novelty = sum(ns.score for ns in novelty_scores) / len(novelty_scores) if novelty_scores else 0.0
        self.storage.store_cognitive_state(
            loop_id=self.loop_count,
            energy=homeostasis_state.energy,
            temperature=homeostasis_state.temperature,
            novelty_drive=avg_novelty,
            num_detections=len(detections),
            unique_classes=len(set(d.class_name for d in detections))
        )
        
        self.storage.store_decision(
            loop_id=self.loop_count,
            action=decision.action.value if hasattr(decision.action, 'value') else str(decision.action),
            target=decision.target,
            reasoning=decision.reasoning,
            priority_level=decision.priority,
            energy_level=homeostasis_state.energy
        )
        
        return annotated, detections, novelty_scores, decision, homeostasis_state, telemetry_metrics
    
    def create_dashboard(self) -> Layout:
        """Create dashboard layout."""
        layout = Layout()
        
        layout.split(
            Layout(name="header", size=3),
            Layout(name="body", ratio=1),
            Layout(name="footer", size=3)
        )
        
        layout["body"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        layout["left"].split(
            Layout(name="perception", ratio=1),
            Layout(name="telemetry", ratio=1)
        )
        
        layout["right"].split(
            Layout(name="ima", ratio=1),
            Layout(name="decision", ratio=1)
        )
        
        return layout
    
    def update_dashboard(self, layout: Layout, detections, novelty_scores, decision, homeostasis_state, telemetry_metrics):
        """Update dashboard."""
        elapsed = time.time() - self.start_time
        fps = self.frame_count / elapsed if elapsed > 0 else 0
        
        # Header
        yolo_ver = f"YOLOv{self.detector.model_version}"
        source_name = Path(self.video_path).name if self.video_path else f"Camera {self.camera_id}"
        header = Panel(
            f"[bold cyan]ARIA Complete System Demo[/bold cyan] - {yolo_ver} + IMA + Telemetry\n"
            f"[dim]Source: {source_name} | Frame: {self.frame_count} | FPS: {fps:.1f} | Loop: {self.loop_count} | Press Ctrl+C to stop[/dim]",
            style="bold white on blue"
        )
        layout["header"].update(header)
        
        # Perception
        perception_table = Table(title=f"📸 Perception ({yolo_ver})", box=box.ROUNDED)
        perception_table.add_column("Object", style="cyan")
        perception_table.add_column("Conf", style="yellow", justify="right")
        perception_table.add_column("Novelty", style="green", justify="right")
        
        for det, nov in zip(detections[:5], novelty_scores[:5]):
            novelty_color = "red" if nov.score > 0.7 else "yellow" if nov.score > 0.4 else "green"
            perception_table.add_row(
                det.class_name.capitalize(),
                f"{det.confidence:.2f}",
                f"[{novelty_color}]{nov.score:.2f}[/{novelty_color}]"
            )
        
        if not detections:
            perception_table.add_row("[dim]No objects detected[/dim]", "", "")
        
        layout["left"]["perception"].update(Panel(perception_table, border_style="blue"))
        
        # Telemetry
        if self.enable_telemetry:
            telem_table = Table(title="📡 Telemetry Pipeline", box=box.ROUNDED)
            telem_table.add_column("Metric", style="cyan")
            telem_table.add_column("Value", style="yellow", justify="right")
            
            stats = self.telemetry_stats
            telem_table.add_row("Envelopes", f"{stats.total_envelopes:,}")
            telem_table.add_row("Encoded", f"{stats.total_encoded_bytes:,} B")
            telem_table.add_row("LZ4 Ratio", f"{stats.lz4_compression_ratio:.2f}x")
            telem_table.add_row("Zstd Ratio", f"{stats.zstd_compression_ratio:.2f}x")
            telem_table.add_row("Throughput", f"{stats.encoding_throughput:.1f} MB/s")
            
            layout["left"]["telemetry"].update(Panel(telem_table, border_style="cyan"))
        else:
            layout["left"]["telemetry"].update(Panel("[dim]Telemetry disabled[/dim]", border_style="dim"))
        
        # IMA State
        ima_table = Table(title="🧠 IMA State", box=box.ROUNDED)
        ima_table.add_column("Metric", style="cyan")
        ima_table.add_column("Value", style="yellow", justify="right")
        ima_table.add_column("Status", style="green", justify="center")
        
        energy_status = "🔴 CRITICAL" if homeostasis_state.energy < 10 else "🟡 LOW" if homeostasis_state.energy < 30 else "🟢 OK"
        ima_table.add_row("Energy", f"{homeostasis_state.energy:.1f}%", energy_status)
        
        temp_status = "🔴 HOT" if homeostasis_state.temperature > 50 else "🟡 WARM" if homeostasis_state.temperature > 40 else "🟢 OK"
        ima_table.add_row("Temperature", f"{homeostasis_state.temperature:.1f}°C", temp_status)
        
        pressure_status = "🔴 HIGH" if homeostasis_state.pressure > 0.7 else "🟡 MEDIUM" if homeostasis_state.pressure > 0.3 else "🟢 LOW"
        ima_table.add_row("Pressure", f"{homeostasis_state.pressure:.2f}", pressure_status)
        
        avg_novelty = sum(n.score for n in novelty_scores) / len(novelty_scores) if novelty_scores else 0.0
        novelty_status = "🔴 HIGH" if avg_novelty > 0.7 else "🟡 MEDIUM" if avg_novelty > 0.4 else "🟢 LOW"
        ima_table.add_row("Novelty Drive", f"{avg_novelty:.2f}", novelty_status)
        
        layout["right"]["ima"].update(Panel(ima_table, border_style="magenta"))
        
        # Decision
        decision_table = Table(title="🎯 Decision", box=box.ROUNDED, show_header=False)
        decision_table.add_column("Field", style="cyan")
        decision_table.add_column("Value", style="yellow")
        
        priority_emoji = "🔴" if decision.priority == 3 else "🟡" if decision.priority == 2 else "🟢"
        decision_table.add_row("Action", f"{priority_emoji} {decision.action.value.upper()}")
        if decision.target:
            decision_table.add_row("Target", decision.target)
        decision_table.add_row("Reasoning", decision.reasoning)
        decision_table.add_row("Priority", f"{'⚠️ ' * decision.priority}Level {decision.priority}")
        
        layout["right"]["decision"].update(Panel(decision_table, border_style="yellow"))
        
        # Footer
        entities = len(self.world_model.get_entities())
        unique = len(self.novelty_detector.object_counts)
        footer = Panel(
            f"[dim]ARIA SDK - Full Pipeline: Vision → Telemetry → IMA → Decision | "
            f"Tracked: {entities} | Unique: {unique} | Telemetry: {'ON' if self.enable_telemetry else 'OFF'}[/dim]",
            style="dim white on black"
        )
        layout["footer"].update(footer)
    
    def run(self, max_frames: Optional[int] = None, show_video: bool = True):
        """Run full system demo."""
        self.open_source()
        
        layout = self.create_dashboard()
        
        try:
            with Live(layout, refresh_per_second=4, console=self.console) as live:
                while True:
                    # Run iteration
                    annotated, detections, novelty_scores, decision, homeostasis_state, telemetry_metrics = self.run_loop_iteration()
                    
                    if annotated is None:
                        self.console.print("\n[yellow]⚠️  Video ended[/yellow]")
                        break
                    
                    # Update dashboard
                    self.update_dashboard(layout, detections, novelty_scores, decision, homeostasis_state, telemetry_metrics)
                    
                    # Show video
                    if show_video:
                        # Add overlay
                        cv2.putText(annotated, f"Action: {decision.action.value.upper()}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                        cv2.putText(annotated, f"Energy: {homeostasis_state.energy:.0f}%", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                        if self.enable_telemetry and telemetry_metrics:
                            cv2.putText(annotated, f"Telemetry: {telemetry_metrics.get('lz4_ratio', 0):.1f}x", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 255), 2)
                        
                        cv2.imshow('ARIA Full System', annotated)
                        
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            self.console.print("\n[yellow]⚠️  Stopped (q pressed)[/yellow]")
                            break
                    
                    if max_frames and self.frame_count >= max_frames:
                        self.console.print(f"\n[green]✅ Reached max frames: {max_frames}[/green]")
                        break
                
                time.sleep(2)
                
        except KeyboardInterrupt:
            self.console.print("\n[yellow]⚠️  Stopped (Ctrl+C)[/yellow]")
        
        finally:
            self.close_source()
            self._print_summary()
    
    def _print_summary(self):
        """Print final summary."""
        elapsed = time.time() - self.start_time
        fps = self.frame_count / elapsed if elapsed > 0 else 0
        
        self.console.print("\n" + "="*70)
        self.console.print("[bold cyan]FULL SYSTEM SUMMARY[/bold cyan]")
        self.console.print("="*70)
        
        summary_table = Table(show_header=False, box=box.SIMPLE)
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="yellow", justify="right")
        
        summary_table.add_row("Frames Processed", f"{self.frame_count:,}")
        summary_table.add_row("Runtime", f"{elapsed:.1f}s")
        summary_table.add_row("Average FPS", f"{fps:.1f}")
        summary_table.add_row("", "")
        summary_table.add_row("Cognitive Loops", f"{self.loop_count:,}")
        summary_table.add_row("Objects Tracked", f"{len(self.world_model.entities)}")
        summary_table.add_row("Unique Classes", f"{len(self.novelty_detector.object_counts)}")
        
        if self.enable_telemetry:
            stats = self.telemetry_stats
            summary_table.add_row("", "")
            summary_table.add_row("Total Detections", f"{stats.total_detections:,}")
            summary_table.add_row("Telemetry Envelopes", f"{stats.total_envelopes:,}")
            
            # Show warning if no detections
            if stats.total_envelopes == 0:
                summary_table.add_row("⚠️  WARNING", "No envelopes sent (no detections)")
            else:
                summary_table.add_row("Encoded Data", f"{stats.total_encoded_bytes / 1024:.1f} KB")
                summary_table.add_row("LZ4 Compressed", f"{stats.total_lz4_bytes / 1024:.1f} KB ({stats.lz4_compression_ratio:.2f}x)")
                summary_table.add_row("Zstd Compressed", f"{stats.total_zstd_bytes / 1024:.1f} KB ({stats.zstd_compression_ratio:.2f}x)")
                summary_table.add_row("Encoding Throughput", f"{stats.encoding_throughput:.1f} MB/s")
                summary_table.add_row("LZ4 Throughput", f"{stats.lz4_throughput:.1f} MB/s")
                summary_table.add_row("Zstd Throughput", f"{stats.zstd_throughput:.1f} MB/s")
            
            # Show streaming status
            summary_table.add_row("", "")
            if hasattr(self, 'envelopes_sent'):
                summary_table.add_row("Envelopes Streamed", f"{self.envelopes_sent:,}")
            if self.stream_socket:
                summary_table.add_row("Stream Status", "✅ Connected")
            elif hasattr(self, 'stream_socket'):
                summary_table.add_row("Stream Status", "❌ Disconnected or not configured")
        
        summary_table.add_row("", "")
        summary_table.add_row("Final Energy", f"{self.homeostasis.energy:.1f}%")
        summary_table.add_row("Final Temp", f"{self.homeostasis.temperature:.1f}°C")
        
        self.console.print(summary_table)
        self.console.print("="*70)
        self.console.print("[bold green]✅ Full ARIA system validated![/bold green]\n")
        
        # Close storage session and export data
        self.storage.close_session(total_frames=self.frame_count, total_loops=self.loop_count)
        export_file = self.storage.export_session_json()
        self.console.print(f"[cyan]💾 Data saved to: {self.storage.storage_dir}[/cyan]")
        self.console.print(f"[cyan]📊 Session ID: {self.storage.session_id}[/cyan]")
        self.console.print(f"[cyan]📄 Summary exported to: {export_file}[/cyan]\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ARIA Complete System Demo - Vision + IMA + Telemetry",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--camera', type=int, default=0, help='Camera device ID (default: 0)')
    parser.add_argument('--video', type=str, help='Path to video file')
    parser.add_argument('--yolo-version', choices=['8', '11'], default='11', help='YOLO version (default: 11)')
    parser.add_argument('--model-size', choices=['n', 's', 'm', 'l', 'x'], default='n', help='Model size (default: n)')
    parser.add_argument('--confidence', type=float, default=0.5, help='Detection confidence (default: 0.5)')
    parser.add_argument('--energy-drain', type=float, default=0.5, 
                        help='Energy drain rate (%%/s): 0.5=slow(200s), 1.0=normal(100s), 2.0=fast(50s), 5.0=very_fast(20s) (default: 0.5)')
    parser.add_argument('--max-frames', type=int, help='Maximum frames to process')
    parser.add_argument('--no-video', action='store_true', help='Disable video window')
    parser.add_argument('--no-telemetry', action='store_true', help='Disable telemetry pipeline')
    parser.add_argument('--telemetry-test', action='store_true', help='Run telemetry performance test')
    parser.add_argument('--stream', type=str, metavar='HOST', help='Stream telemetry to receiver at HOST (e.g., 127.0.0.1)')
    parser.add_argument('--port', type=int, default=5555, help='Receiver port (default: 5555)')
    
    args = parser.parse_args()
    
    try:
        console = Console()
        console.print("\n[bold cyan]╔═══════════════════════════════════════════════════════════╗[/bold cyan]")
        console.print("[bold cyan]║         ARIA Complete System Demonstration                ║[/bold cyan]")
        console.print("[bold cyan]║    Vision → Telemetry → Cognitive → Decision              ║[/bold cyan]")
        console.print("[bold cyan]╚═══════════════════════════════════════════════════════════╝[/bold cyan]\n")
        
        if args.telemetry_test:
            console.print("[yellow]🔬 Running telemetry performance test...[/yellow]\n")
            args.max_frames = 300
            args.no_video = True
        
        demo = FullSystemDemo(
            camera_id=args.camera,
            video_path=args.video,
            yolo_version=args.yolo_version,
            model_size=args.model_size,
            confidence=args.confidence,
            enable_telemetry=not args.no_telemetry,
            energy_drain_rate=args.energy_drain,
            stream_host=args.stream,
            stream_port=args.port
        )
        
        demo.run(
            max_frames=args.max_frames,
            show_video=not args.no_video
        )
        
    except Exception as e:
        console = Console()
        console.print(f"\n[red]❌ Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
