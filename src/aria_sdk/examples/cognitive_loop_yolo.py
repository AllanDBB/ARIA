"""Real Cognitive Loop with YOLO Vision.

Full cognitive loop using real camera + YOLO detection + IMA + decision-making.

This is the REAL version that proves the architecture works end-to-end:
- Real camera input (webcam)
- Real object detection (YOLOv8)
- Real cognitive processing (IMA, WorldModel, Planner)
- Real-time decision making

Usage:
    # With webcam
    python -m aria_sdk.examples.cognitive_loop_yolo
    
    # With video file
    python -m aria_sdk.examples.cognitive_loop_yolo --video path/to/video.mp4
    
    # With different YOLO model
    python -m aria_sdk.examples.cognitive_loop_yolo --model-size s
"""

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

try:
    import cv2
except ImportError:
    print("❌ OpenCV not installed")
    print("   Install with: pip install opencv-python")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.table import Table
    from rich import box
except ImportError:
    print("❌ rich not installed")
    print("   Install with: pip install rich")
    sys.exit(1)

try:
    from aria_sdk.perception.yolo_detector import YoloDetector
except ImportError:
    print("❌ YOLO detector not available")
    print("   Install with: pip install ultralytics")
    sys.exit(1)

from aria_sdk.domain.entities import Detection

# Import IMA components from the demo
import sys
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


class RealCognitiveLoop:
    """Real cognitive loop with camera vision."""
    
    def __init__(
        self,
        camera_id: int = 0,
        video_path: Optional[str] = None,
        model_size: str = 'n',
        confidence: float = 0.5,
        energy_drain_rate: float = 0.5
    ):
        """Initialize real cognitive loop.
        
        Args:
            camera_id: Camera device ID (if not using video)
            video_path: Path to video file (if not using camera)
            model_size: YOLO model size ('n', 's', 'm', 'l', 'x')
            confidence: Detection confidence threshold
            energy_drain_rate: Energy drain rate in % per second (default: 0.5)
        """
        self.console = Console()
        
        # Vision system
        self.console.print(f"\n[cyan]🎥 Initializing vision system...[/cyan]")
        self.detector = YoloDetector(
            model_size=model_size,
            confidence_threshold=confidence,
            device='cpu'  # Use 'cuda' if you have GPU
        )
        
        # Cognitive components
        self.novelty_detector = SimpleNoveltyDetector()
        self.homeostasis = SimpleHomeostasisMonitor(energy_drain_rate=energy_drain_rate)
        self.world_model = SimpleWorldModel()
        self.planner = SimplePlanner()
        
        # Input source

        self.camera_id = camera_id
        self.video_path = video_path
        self.cap = None
        
        # Metrics
        self.loop_count = 0
        self.start_time = time.time()
        self.decisions_made = 0
        self.frame_count = 0
        
        self.console.print(f"[green]✅ Cognitive system ready[/green]\n")
    
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
        
        # Get video properties
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        self.console.print(f"[green]✅ Video source opened: {width}x{height} @ {fps:.1f} FPS[/green]\n")
    
    def close_source(self):
        """Close video source."""
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
    
    def run_loop_iteration(self) -> tuple:
        """Run one cognitive loop iteration.
        
        Returns:
            (frame, detections, novelty_scores, decision, homeostasis_state)
        """
        # 1. PERCEPTION: Capture frame
        ret, frame = self.cap.read()
        if not ret:
            return None, [], [], None, None
        
        self.frame_count += 1
        
        # 2. VISION: Detect objects with YOLO
        detections, annotated = self.detector.detect(frame, visualize=True)
        timestamp = datetime.now(timezone.utc)
        
        # 3. IMA: Compute novelty
        novelty_scores = [self.novelty_detector.compute_novelty(det) for det in detections]
        
        # 4. WORLD MODEL: Update with detections
        self.world_model.update(detections, novelty_scores, timestamp)
        
        # 5. HOMEOSTASIS: Update internal state
        dt = 1.0 / 30.0  # Assume 30 FPS
        self.homeostasis.update(dt=dt)
        homeostasis_state = self.homeostasis.get_state()
        
        # 6. PLANNER: Decide action
        decision = self.planner.decide(self.world_model, homeostasis_state, self.novelty_detector)
        self.decisions_made += 1
        
        # 7. SAFETY: Would validate here (skipped for demo)
        
        # 8. EXECUTE: Would send commands here (skipped for demo)
        
        self.loop_count += 1
        
        return annotated, detections, novelty_scores, decision, homeostasis_state
    
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
            Layout(name="world_model", ratio=1)
        )
        
        layout["right"].split(
            Layout(name="ima", ratio=1),
            Layout(name="decision", ratio=1)
        )
        
        return layout
    
    def update_dashboard(self, layout: Layout, detections, novelty_scores, decision, homeostasis_state):
        """Update dashboard with current state."""
        elapsed = time.time() - self.start_time
        fps = self.frame_count / elapsed if elapsed > 0 else 0
        
        # Header
        source_name = Path(self.video_path).name if self.video_path else f"Camera {self.camera_id}"
        header = Panel(
            f"[bold cyan]ARIA Real Cognitive Loop[/bold cyan] - YOLO Vision + IMA Decision Making\n"
            f"[dim]Source: {source_name} | Frame: {self.frame_count} | FPS: {fps:.1f} | Loop: {self.loop_count} | Press Ctrl+C to stop[/dim]",
            style="bold white on blue"
        )
        layout["header"].update(header)
        
        # Perception
        perception_table = Table(title="📸 Real Vision (YOLOv8)", box=box.ROUNDED)
        perception_table.add_column("Object", style="cyan")
        perception_table.add_column("Confidence", style="yellow", justify="right")
        perception_table.add_column("Novelty", style="green", justify="right")
        
        for det, nov in zip(detections[:5], novelty_scores[:5]):  # Show max 5
            novelty_color = "red" if nov.score > 0.7 else "yellow" if nov.score > 0.4 else "green"
            perception_table.add_row(
                det.class_name.capitalize(),
                f"{det.confidence:.2f}",
                f"[{novelty_color}]{nov.score:.2f}[/{novelty_color}]"
            )
        
        if not detections:
            perception_table.add_row("[dim]No objects detected[/dim]", "", "")
        
        layout["left"]["perception"].update(Panel(perception_table, border_style="blue"))
        
        # World Model
        world_table = Table(title="🗺️  World Model (Memory)", box=box.ROUNDED)
        world_table.add_column("Entity", style="cyan")
        world_table.add_column("Observations", style="yellow", justify="right")
        world_table.add_column("Novelty", style="green", justify="right")
        
        entities = self.world_model.get_entities()
        for entity in sorted(entities, key=lambda e: e.observations, reverse=True)[:5]:
            novelty_color = "red" if entity.novelty_score > 0.7 else "yellow" if entity.novelty_score > 0.4 else "green"
            world_table.add_row(
                f"{entity.class_name}",
                f"{entity.observations}",
                f"[{novelty_color}]{entity.novelty_score:.2f}[/{novelty_color}]"
            )
        
        if not entities:
            world_table.add_row("[dim]No entities tracked[/dim]", "", "")
        
        layout["left"]["world_model"].update(Panel(world_table, border_style="green"))
        
        # IMA State
        ima_table = Table(title="🧠 IMA State (Motivation)", box=box.ROUNDED)
        ima_table.add_column("Metric", style="cyan")
        ima_table.add_column("Value", style="yellow", justify="right")
        ima_table.add_column("Status", style="green", justify="center")
        
        # Energy status
        energy_status = "🔴 CRITICAL" if homeostasis_state.energy < 10 else "🟡 LOW" if homeostasis_state.energy < 30 else "🟢 OK"
        ima_table.add_row("Energy", f"{homeostasis_state.energy:.1f}%", energy_status)
        
        # Temperature status
        temp_status = "🔴 HOT" if homeostasis_state.temperature > 50 else "🟡 WARM" if homeostasis_state.temperature > 40 else "🟢 OK"
        ima_table.add_row("Temperature", f"{homeostasis_state.temperature:.1f}°C", temp_status)
        
        # Homeostatic pressure
        pressure_status = "🔴 HIGH" if homeostasis_state.pressure > 0.7 else "🟡 MEDIUM" if homeostasis_state.pressure > 0.3 else "🟢 LOW"
        ima_table.add_row("Pressure", f"{homeostasis_state.pressure:.2f}", pressure_status)
        
        # Novelty drive
        avg_novelty = sum(n.score for n in novelty_scores) / len(novelty_scores) if novelty_scores else 0.0
        novelty_status = "🔴 HIGH" if avg_novelty > 0.7 else "🟡 MEDIUM" if avg_novelty > 0.4 else "🟢 LOW"
        ima_table.add_row("Novelty Drive", f"{avg_novelty:.2f}", novelty_status)
        
        layout["right"]["ima"].update(Panel(ima_table, border_style="magenta"))
        
        # Decision
        decision_table = Table(title="🎯 Decision (Planning)", box=box.ROUNDED, show_header=False)
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
        footer = Panel(
            f"[dim]ARIA SDK - Real Cognitive Loop: Camera → YOLO → IMA → Decision | "
            f"Tracked: {len(entities)} | Unique: {len(self.novelty_detector.object_counts)}[/dim]",
            style="dim white on black"
        )
        layout["footer"].update(footer)
    
    def run(self, max_frames: Optional[int] = None, show_video: bool = True):
        """Run real cognitive loop.
        
        Args:
            max_frames: Maximum frames to process (None = infinite)
            show_video: Show video window with detections
        """
        self.open_source()
        
        layout = self.create_dashboard()
        
        try:
            with Live(layout, refresh_per_second=4, console=self.console) as live:
                while True:
                    # Run one iteration
                    annotated, detections, novelty_scores, decision, homeostasis_state = self.run_loop_iteration()
                    
                    if annotated is None:
                        self.console.print("\n[yellow]⚠️  Video ended[/yellow]")
                        break
                    
                    # Update dashboard
                    self.update_dashboard(layout, detections, novelty_scores, decision, homeostasis_state)
                    
                    # Show video window
                    if show_video:
                        # Add decision overlay to video
                        cv2.putText(
                            annotated,
                            f"Action: {decision.action.value.upper()}",
                            (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.8,
                            (0, 255, 0),
                            2
                        )
                        cv2.putText(
                            annotated,
                            f"Energy: {homeostasis_state.energy:.0f}%",
                            (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.8,
                            (0, 255, 255),
                            2
                        )
                        
                        cv2.imshow('ARIA Vision', annotated)
                        
                        # Check for 'q' key
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            self.console.print("\n[yellow]⚠️  Stopped by user (q pressed)[/yellow]")
                            break
                    
                    # Check max frames
                    if max_frames and self.frame_count >= max_frames:
                        self.console.print(f"\n[green]✅ Reached max frames: {max_frames}[/green]")
                        break
                
                # Keep final display
                time.sleep(2)
                
        except KeyboardInterrupt:
            self.console.print("\n[yellow]⚠️  Stopped by user (Ctrl+C)[/yellow]")
        
        finally:
            self.close_source()
            self._print_summary()
    
    def _print_summary(self):
        """Print final summary."""
        elapsed = time.time() - self.start_time
        fps = self.frame_count / elapsed if elapsed > 0 else 0
        
        self.console.print("\n" + "="*70)
        self.console.print("[bold cyan]REAL COGNITIVE LOOP SUMMARY[/bold cyan]")
        self.console.print("="*70)
        
        summary_table = Table(show_header=False, box=box.SIMPLE)
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="yellow", justify="right")
        
        summary_table.add_row("Frames Processed", f"{self.frame_count}")
        summary_table.add_row("Runtime", f"{elapsed:.1f}s")
        summary_table.add_row("Average FPS", f"{fps:.1f}")
        summary_table.add_row("", "")
        summary_table.add_row("Cognitive Loops", f"{self.loop_count}")
        summary_table.add_row("Decisions Made", f"{self.decisions_made}")
        summary_table.add_row("Objects Tracked", f"{len(self.world_model.entities)}")
        summary_table.add_row("Unique Classes", f"{len(self.novelty_detector.object_counts)}")
        summary_table.add_row("", "")
        summary_table.add_row("Final Energy", f"{self.homeostasis.energy:.1f}%")
        summary_table.add_row("Final Temp", f"{self.homeostasis.temperature:.1f}°C")
        
        self.console.print(summary_table)
        self.console.print("="*70)
        self.console.print("[bold green]✅ Real cognitive loop with YOLO vision completed![/bold green]\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ARIA Real Cognitive Loop with YOLO Vision",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Webcam (default)
  python -m aria_sdk.examples.cognitive_loop_yolo
  
  # Specific camera
  python -m aria_sdk.examples.cognitive_loop_yolo --camera 1
  
  # Video file
  python -m aria_sdk.examples.cognitive_loop_yolo --video demo.mp4
  
  # Different YOLO model (s=small, more accurate but slower)
  python -m aria_sdk.examples.cognitive_loop_yolo --model-size s
  
  # Process only 300 frames
  python -m aria_sdk.examples.cognitive_loop_yolo --max-frames 300
  
  # No video window (terminal only)
  python -m aria_sdk.examples.cognitive_loop_yolo --no-video
        """
    )
    
    parser.add_argument(
        '--camera',
        type=int,
        default=0,
        help='Camera device ID (default: 0)'
    )
    
    parser.add_argument(
        '--video',
        type=str,
        help='Path to video file (instead of camera)'
    )
    
    parser.add_argument(
        '--model-size',
        choices=['n', 's', 'm', 'l', 'x'],
        default='n',
        help='YOLO model size: n=nano (fastest), s=small, m=medium, l=large, x=xlarge (default: n)'
    )
    
    parser.add_argument(
        '--confidence',
        type=float,
        default=0.5,
        help='Detection confidence threshold (default: 0.5)'
    )
    
    parser.add_argument(
        '--energy-drain',
        type=float,
        default=0.5,
        help='Energy drain rate (%%/s): 0.5=slow(200s), 1.0=normal(100s), 2.0=fast(50s), 5.0=very_fast(20s) (default: 0.5)'
    )
    
    parser.add_argument(
        '--max-frames',
        type=int,
        help='Maximum frames to process (default: infinite)'
    )
    
    parser.add_argument(
        '--no-video',
        action='store_true',
        help='Disable video window (terminal dashboard only)'
    )
    
    args = parser.parse_args()
    
    try:
        console = Console()
        console.print("\n[bold cyan]╔═══════════════════════════════════════════════════════════════╗[/bold cyan]")
        console.print("[bold cyan]║           ARIA Real Cognitive Loop with YOLO Vision           ║[/bold cyan]")
        console.print("[bold cyan]╚═══════════════════════════════════════════════════════════════╝[/bold cyan]\n")
        
        loop = RealCognitiveLoop(
            camera_id=args.camera,
            video_path=args.video,
            model_size=args.model_size,
            confidence=args.confidence,
            energy_drain_rate=args.energy_drain
        )
        
        loop.run(
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
