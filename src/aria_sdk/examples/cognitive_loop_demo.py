"""Cognitive Loop Demo - Simple demonstration of ARIA's brain/IMA system.

Shows how the cognitive loop works:
1. Perception: Detect objects (simulated detections)
2. IMA: Compute novelty, check homeostasis
3. World Model: Track entities
4. Planner: Decide next action
5. Safety: Validate action
6. Execute: Show action

Usage:
    python -m aria_sdk.examples.cognitive_loop_demo --scenario exploration
    python -m aria_sdk.examples.cognitive_loop_demo --interactive
"""

import argparse
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional
from enum import Enum

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

from aria_sdk.domain.entities import Detection


# ==================== Simple IMA Components ====================

@dataclass
class NoveltyScore:
    """Novelty score for an object."""
    object_class: str
    score: float  # 0.0 = seen many times, 1.0 = completely new
    reason: str


class SimpleNoveltyDetector:
    """Detects novel (new/unusual) objects."""
    
    def __init__(self):
        self.object_counts: Dict[str, int] = {}
        self.total_observations = 0
    
    def compute_novelty(self, detection: Detection) -> NoveltyScore:
        """Compute novelty score for a detection.
        
        Returns:
            NoveltyScore with value 0.0-1.0
        """
        key = detection.class_name
        count = self.object_counts.get(key, 0)
        
        # Update counts
        self.object_counts[key] = count + 1
        self.total_observations += 1
        
        if count == 0:
            # Completely new
            return NoveltyScore(
                object_class=key,
                score=1.0,
                reason="Never seen before"
            )
        elif count < 3:
            # Still quite novel
            score = 1.0 / (count + 1)
            return NoveltyScore(
                object_class=key,
                score=score,
                reason=f"Seen {count} times"
            )
        else:
            # Common object
            score = 1.0 / (count + 1)
            return NoveltyScore(
                object_class=key,
                score=score,
                reason=f"Common (seen {count}x)"
            )


@dataclass
class HomeostasisState:
    """Internal state of the robot."""
    energy: float  # 0-100%
    temperature: float  # °C
    cpu_load: float  # 0-100%
    pressure: float  # 0.0-1.0 (0=OK, 1=CRITICAL)


class SimpleHomeostasisMonitor:
    """Monitors internal state and homeostasis."""
    
    def __init__(self, energy_drain_rate: float = 0.5):
        """Initialize homeostasis monitor.
        
        Args:
            energy_drain_rate: Energy drain rate in % per second (default: 0.5)
                              Higher = faster energy drain
                              Examples: 0.5 = slow (200s to drain)
                                       1.0 = normal (100s to drain)
                                       2.0 = fast (50s to drain)
                                       5.0 = very fast (20s to drain)
        """
        self.energy = 100.0
        self.temperature = 25.0
        self.cpu_load = 0.0
        self.energy_drain_rate = energy_drain_rate
    
    def update(self, dt: float):
        """Update internal state.
        
        Args:
            dt: Time delta in seconds
        """
        # Energy decreases over time (configurable rate)
        self.energy -= self.energy_drain_rate * dt
        self.energy = max(0.0, self.energy)
        
        # Temperature varies with CPU load
        target_temp = 25.0 + (self.cpu_load / 100.0) * 30.0
        self.temperature += (target_temp - self.temperature) * 0.1 * dt
        
        # CPU load varies randomly (simulate work)
        self.cpu_load += random.gauss(0, 5) * dt
        self.cpu_load = max(0.0, min(100.0, self.cpu_load))
    
    def get_state(self) -> HomeostasisState:
        """Get current homeostatic state."""
        # Compute pressure (how bad is our state?)
        energy_pressure = max(0.0, (30.0 - self.energy) / 30.0)  # Pressure starts at 30%
        temp_pressure = max(0.0, (self.temperature - 50.0) / 30.0)  # Pressure starts at 50°C
        pressure = max(energy_pressure, temp_pressure)
        
        return HomeostasisState(
            energy=self.energy,
            temperature=self.temperature,
            cpu_load=self.cpu_load,
            pressure=pressure
        )
    
    def needs_charging(self) -> bool:
        """Check if robot needs to recharge."""
        return self.energy < 20.0


# ==================== World Model ====================

@dataclass
class TrackedEntity:
    """An entity tracked in the world model."""
    id: str
    class_name: str
    position: tuple[float, float]  # x, y
    confidence: float
    observations: int
    last_seen: datetime
    novelty_score: float = 0.0


class SimpleWorldModel:
    """Tracks entities in the world."""
    
    def __init__(self):
        self.entities: Dict[str, TrackedEntity] = {}
        self.next_id = 0
    
    def update(self, detections: List[Detection], novelty_scores: List[NoveltyScore], timestamp: datetime):
        """Update world model with new detections."""
        for det, novelty in zip(detections, novelty_scores):
            # Group by class name (simplified tracking)
            entity_id = det.class_name
            
            # bbox is (x, y, w, h)
            bbox_x, bbox_y = det.bbox[0], det.bbox[1]
            
            if entity_id in self.entities:
                # Update existing entity
                entity = self.entities[entity_id]
                entity.position = (bbox_x, bbox_y)
                entity.confidence = det.confidence
                entity.observations += 1
                entity.last_seen = timestamp
                entity.novelty_score = novelty.score
            else:
                # Create new entity
                self.entities[entity_id] = TrackedEntity(
                    id=entity_id,
                    class_name=det.class_name,
                    position=(bbox_x, bbox_y),
                    confidence=det.confidence,
                    observations=1,
                    last_seen=timestamp,
                    novelty_score=novelty.score
                )
    
    def get_entities(self) -> List[TrackedEntity]:
        """Get all tracked entities."""
        return list(self.entities.values())
    
    def get_most_novel(self) -> Optional[TrackedEntity]:
        """Get most novel entity."""
        if not self.entities:
            return None
        return max(self.entities.values(), key=lambda e: e.novelty_score)


# ==================== Planner ====================

class Action(Enum):
    """Possible actions."""
    EXPLORE = "explore"
    INSPECT_OBJECT = "inspect_object"
    SEEK_CHARGING = "seek_charging"
    REST = "rest"
    AVOID_DANGER = "avoid_danger"


@dataclass
class DecisionInfo:
    """Information about a decision."""
    action: Action
    target: Optional[str] = None  # Entity ID if applicable
    reasoning: str = ""
    priority: int = 0  # 0=low, 1=medium, 2=high, 3=critical


class SimplePlanner:
    """Makes decisions based on IMA and world state."""
    
    def decide(
        self,
        world_model: SimpleWorldModel,
        homeostasis: HomeostasisState,
        novelty_detector: SimpleNoveltyDetector
    ) -> DecisionInfo:
        """Decide next action.
        
        Priority order:
        1. Safety (avoid danger, seek charging if critical)
        2. Homeostasis (seek charging if low energy)
        3. Novelty (inspect novel objects)
        4. Default (explore)
        """
        # Check critical energy
        if homeostasis.energy < 10.0:
            return DecisionInfo(
                action=Action.SEEK_CHARGING,
                reasoning="CRITICAL: Energy below 10%",
                priority=3
            )
        
        # Check low energy
        if homeostasis.energy < 20.0:
            return DecisionInfo(
                action=Action.SEEK_CHARGING,
                reasoning="Low energy, need to recharge",
                priority=2
            )
        
        # Check for novel objects
        most_novel = world_model.get_most_novel()
        if most_novel and most_novel.novelty_score > 0.5:
            return DecisionInfo(
                action=Action.INSPECT_OBJECT,
                target=most_novel.id,
                reasoning=f"High novelty detected: {most_novel.class_name} (score: {most_novel.novelty_score:.2f})",
                priority=1
            )
        
        # Default: explore
        return DecisionInfo(
            action=Action.EXPLORE,
            reasoning="No immediate priorities, exploring environment",
            priority=0
        )


# ==================== Cognitive Loop Demo ====================

class CognitiveLoopDemo:
    """Demonstrates the cognitive loop."""
    
    def __init__(self, energy_drain_rate: float = 0.5):
        """Initialize cognitive loop demo.
        
        Args:
            energy_drain_rate: Energy drain rate in % per second (default: 0.5)
        """
        self.console = Console()
        self.novelty_detector = SimpleNoveltyDetector()
        self.homeostasis = SimpleHomeostasisMonitor(energy_drain_rate=energy_drain_rate)
        self.world_model = SimpleWorldModel()
        self.planner = SimplePlanner()
        
        # Metrics
        self.loop_count = 0
        self.start_time = time.time()
        self.decisions_made = 0
    
    def generate_detections(self) -> List[Detection]:
        """Generate simulated detections."""
        # Pool of possible objects
        possible_objects = [
            ("person", 0.95),
            ("car", 0.88),
            ("tree", 0.92),
            ("building", 0.85),
            ("dog", 0.90),
            ("bicycle", 0.87),
            ("chair", 0.82),
            ("bottle", 0.78),
        ]
        
        # Random number of detections (1-5)
        num_detections = random.randint(1, 5)
        
        detections = []
        for _ in range(num_detections):
            class_name, base_conf = random.choice(possible_objects)
            confidence = base_conf + random.gauss(0, 0.05)
            confidence = max(0.0, min(1.0, confidence))
            
            # Random position
            x = random.randint(100, 1820)
            y = random.randint(100, 980)
            w = random.randint(50, 200)
            h = random.randint(50, 200)
            
            det = Detection(
                class_id=hash(class_name) % 1000,
                class_name=class_name,
                confidence=confidence,
                bbox=(x, y, w, h)  # bbox is a tuple (x, y, width, height)
            )
            detections.append(det)
        
        return detections
    
    def run_loop_iteration(self) -> tuple:
        """Run one cognitive loop iteration.
        
        Returns:
            (detections, novelty_scores, decision, homeostasis_state)
        """
        timestamp = datetime.now(timezone.utc)
        
        # 1. PERCEPTION: Generate detections
        detections = self.generate_detections()
        
        # 2. IMA: Compute novelty
        novelty_scores = [self.novelty_detector.compute_novelty(det) for det in detections]
        
        # 3. WORLD MODEL: Update with detections
        self.world_model.update(detections, novelty_scores, timestamp)
        
        # 4. HOMEOSTASIS: Update internal state
        self.homeostasis.update(dt=1.0)  # 1 second per iteration
        homeostasis_state = self.homeostasis.get_state()
        
        # 5. PLANNER: Decide action
        decision = self.planner.decide(self.world_model, homeostasis_state, self.novelty_detector)
        self.decisions_made += 1
        
        # 6. SAFETY: Would validate here (skipped for demo)
        
        # 7. EXECUTE: Would send commands here (skipped for demo)
        
        self.loop_count += 1
        
        return detections, novelty_scores, decision, homeostasis_state
    
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
        
        # Header
        header = Panel(
            f"[bold cyan]ARIA Cognitive Loop Demo[/bold cyan] - Autonomous Decision Making\n"
            f"[dim]Loop: {self.loop_count} | Decisions: {self.decisions_made} | Runtime: {elapsed:.1f}s | Press Ctrl+C to stop[/dim]",
            style="bold white on blue"
        )
        layout["header"].update(header)
        
        # Perception
        perception_table = Table(title="📸 Perception (Sensors)", box=box.ROUNDED)
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
            f"[dim]ARIA SDK - Cognitive Loop: Perceive → Analyze → Decide → Act | "
            f"Tracked objects: {len(entities)} | Unique classes: {len(self.novelty_detector.object_counts)}[/dim]",
            style="dim white on black"
        )
        layout["footer"].update(footer)
    
    def run_interactive(self, iterations: int = 100, delay: float = 1.0):
        """Run interactive demo with dashboard."""
        self.console.clear()
        self.console.print("\n[bold cyan]Starting ARIA Cognitive Loop...[/bold cyan]\n")
        
        layout = self.create_dashboard()
        
        try:
            with Live(layout, refresh_per_second=4, console=self.console) as live:
                for i in range(iterations):
                    # Run one iteration
                    detections, novelty_scores, decision, homeostasis_state = self.run_loop_iteration()
                    
                    # Update dashboard
                    self.update_dashboard(layout, detections, novelty_scores, decision, homeostasis_state)
                    
                    # Delay
                    time.sleep(delay)
                
                # Keep final display
                self.console.print("\n[green]✅ Demo completed![/green]")
                time.sleep(3)
                
        except KeyboardInterrupt:
            self.console.print("\n[yellow]⚠️  Stopped by user[/yellow]")
        
        # Print summary
        self._print_summary()
    
    def _print_summary(self):
        """Print final summary."""
        elapsed = time.time() - self.start_time
        
        self.console.print("\n" + "="*70)
        self.console.print("[bold cyan]COGNITIVE LOOP SUMMARY[/bold cyan]")
        self.console.print("="*70)
        
        summary_table = Table(show_header=False, box=box.SIMPLE)
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="yellow", justify="right")
        
        summary_table.add_row("Total Iterations", f"{self.loop_count}")
        summary_table.add_row("Runtime", f"{elapsed:.1f}s")
        summary_table.add_row("Loop Rate", f"{self.loop_count/elapsed:.1f} Hz")
        summary_table.add_row("", "")
        summary_table.add_row("Decisions Made", f"{self.decisions_made}")
        summary_table.add_row("Objects Tracked", f"{len(self.world_model.entities)}")
        summary_table.add_row("Unique Classes", f"{len(self.novelty_detector.object_counts)}")
        summary_table.add_row("", "")
        summary_table.add_row("Final Energy", f"{self.homeostasis.energy:.1f}%")
        summary_table.add_row("Final Temp", f"{self.homeostasis.temperature:.1f}°C")
        
        self.console.print(summary_table)
        self.console.print("="*70)
        self.console.print("[green]✅ Cognitive loop functioned correctly![/green]\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ARIA Cognitive Loop Demo"
    )
    
    parser.add_argument(
        "--iterations",
        type=int,
        default=50,
        help="Number of loop iterations (default: 50)"
    )
    
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between iterations in seconds (default: 0.5)"
    )
    
    parser.add_argument(
        '--energy-drain',
        type=float,
        default=0.5,
        help='Energy drain rate (%%/s): 0.5=slow(200s), 1.0=normal(100s), 2.0=fast(50s), 5.0=very_fast(20s) (default: 0.5)'
    )
    
    args = parser.parse_args()
    
    try:
        demo = CognitiveLoopDemo(energy_drain_rate=args.energy_drain)
        demo.run_interactive(iterations=args.iterations, delay=args.delay)
        
    except Exception as e:
        console = Console()
        console.print(f"\n[red]❌ Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
