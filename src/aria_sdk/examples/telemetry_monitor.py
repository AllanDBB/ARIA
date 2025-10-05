#!/usr/bin/env python3
"""
ARIA Telemetry Monitor - Real-time telemetry data visualization

This script monitors and displays detailed telemetry information from the
ARIA system, including:
- Encoding statistics (throughput, latency)
- Compression ratios (LZ4 vs Zstd)
- Envelope details (size, priority, topic)
- Network-ready data metrics
"""

import sys
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from uuid import uuid4

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich import box
from rich.text import Text

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from aria_sdk.domain.entities import Envelope, Priority, EnvelopeMetadata, Detection
from aria_sdk.telemetry.codec import ProtobufCodec
from aria_sdk.telemetry.compression import Lz4Compressor, ZstdCompressor
from aria_sdk.perception.yolo_detector import YoloDetector


class TelemetryMonitor:
    """Real-time telemetry data monitor."""
    
    def __init__(self, compression_level_lz4: int = 0, compression_level_zstd: int = 3):
        """Initialize telemetry monitor.
        
        Args:
            compression_level_lz4: LZ4 compression level (0-16)
            compression_level_zstd: Zstandard compression level (1-22)
        """
        self.console = Console()
        self.codec = ProtobufCodec()
        self.lz4_compressor = Lz4Compressor(level=compression_level_lz4)
        self.zstd_compressor = ZstdCompressor(level=compression_level_zstd)
        
        # Statistics
        self.total_envelopes = 0
        self.total_raw_bytes = 0
        self.total_encoded_bytes = 0
        self.total_lz4_bytes = 0
        self.total_zstd_bytes = 0
        
        self.encoding_times = []
        self.lz4_times = []
        self.zstd_times = []
        
        self.envelope_history: List[Dict[str, Any]] = []
        self.max_history = 100
        
    def create_sample_envelope(self, detection: Detection, sequence: int) -> Envelope:
        """Create a telemetry envelope from detection.
        
        Args:
            detection: Detection entity
            sequence: Sequence number
            
        Returns:
            Telemetry envelope
        """
        # Serialize detection data (simplified JSON format)
        payload = f'{{"class": "{detection.class_name}", "confidence": {detection.confidence:.2f}}}'.encode('utf-8')
        
        envelope = Envelope(
            id=uuid4(),
            timestamp=datetime.now(),
            schema_id=1001,
            priority=Priority.P2,
            topic="vision/detections",
            payload=payload,
            metadata=EnvelopeMetadata(
                source_node="telemetry_monitor",
                sequence_number=sequence
            )
        )
        
        return envelope
    
    def process_envelope(self, envelope: Envelope) -> Dict[str, Any]:
        """Process envelope through encoding and compression.
        
        Args:
            envelope: Envelope to process
            
        Returns:
            Dictionary with metrics
        """
        raw_size = len(envelope.payload)
        
        # Encode
        t0 = time.perf_counter()
        encoded = self.codec.encode(envelope)
        t1 = time.perf_counter()
        encode_time = (t1 - t0) * 1000  # milliseconds
        encoded_size = len(encoded)
        
        # Compress with LZ4
        t0 = time.perf_counter()
        lz4_compressed = self.lz4_compressor.compress(encoded)
        t1 = time.perf_counter()
        lz4_time = (t1 - t0) * 1000
        lz4_size = len(lz4_compressed)
        
        # Compress with Zstd
        t0 = time.perf_counter()
        zstd_compressed = self.zstd_compressor.compress(encoded)
        t1 = time.perf_counter()
        zstd_time = (t1 - t0) * 1000
        zstd_size = len(zstd_compressed)
        
        # Update statistics
        self.total_envelopes += 1
        self.total_raw_bytes += raw_size
        self.total_encoded_bytes += encoded_size
        self.total_lz4_bytes += lz4_size
        self.total_zstd_bytes += zstd_size
        
        self.encoding_times.append(encode_time)
        self.lz4_times.append(lz4_time)
        self.zstd_times.append(zstd_time)
        
        # Keep last N times for averaging
        if len(self.encoding_times) > 100:
            self.encoding_times.pop(0)
            self.lz4_times.pop(0)
            self.zstd_times.pop(0)
        
        metrics = {
            'envelope_id': str(envelope.id)[:8],
            'topic': envelope.topic,
            'priority': envelope.priority.name,
            'raw_size': raw_size,
            'encoded_size': encoded_size,
            'lz4_size': lz4_size,
            'zstd_size': zstd_size,
            'encode_time': encode_time,
            'lz4_time': lz4_time,
            'zstd_time': zstd_time,
            'lz4_ratio': encoded_size / lz4_size if lz4_size > 0 else 0,
            'zstd_ratio': encoded_size / zstd_size if zstd_size > 0 else 0,
        }
        
        # Add to history
        self.envelope_history.append(metrics)
        if len(self.envelope_history) > self.max_history:
            self.envelope_history.pop(0)
        
        return metrics
    
    def create_dashboard(self) -> Layout:
        """Create dashboard layout.
        
        Returns:
            Rich layout
        """
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        layout["body"].split_row(
            Layout(name="stats", ratio=1),
            Layout(name="recent", ratio=1)
        )
        
        return layout
    
    def render_header(self) -> Panel:
        """Render header panel."""
        return Panel(
            "[bold cyan]ARIA Telemetry Monitor[/bold cyan] - Real-time Data Pipeline Analysis",
            box=box.DOUBLE
        )
    
    def render_stats(self) -> Panel:
        """Render statistics panel."""
        table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
        table.add_column("Metric", style="cyan", width=25)
        table.add_column("Value", justify="right", style="green")
        
        # Overall stats
        avg_encode_time = sum(self.encoding_times) / len(self.encoding_times) if self.encoding_times else 0
        avg_lz4_time = sum(self.lz4_times) / len(self.lz4_times) if self.lz4_times else 0
        avg_zstd_time = sum(self.zstd_times) / len(self.zstd_times) if self.zstd_times else 0
        
        overall_lz4_ratio = self.total_encoded_bytes / self.total_lz4_bytes if self.total_lz4_bytes > 0 else 0
        overall_zstd_ratio = self.total_encoded_bytes / self.total_zstd_bytes if self.total_zstd_bytes > 0 else 0
        
        table.add_row("Total Envelopes", f"{self.total_envelopes:,}")
        table.add_row("", "")
        table.add_row("Raw Payload", f"{self.total_raw_bytes:,} B")
        table.add_row("Encoded Size", f"{self.total_encoded_bytes:,} B")
        table.add_row("LZ4 Compressed", f"{self.total_lz4_bytes:,} B")
        table.add_row("Zstd Compressed", f"{self.total_zstd_bytes:,} B")
        table.add_row("", "")
        table.add_row("LZ4 Ratio", f"{overall_lz4_ratio:.2f}x")
        table.add_row("Zstd Ratio", f"{overall_zstd_ratio:.2f}x")
        table.add_row("", "")
        table.add_row("Avg Encode Time", f"{avg_encode_time:.3f} ms")
        table.add_row("Avg LZ4 Time", f"{avg_lz4_time:.3f} ms")
        table.add_row("Avg Zstd Time", f"{avg_zstd_time:.3f} ms")
        
        return Panel(table, title="📊 Overall Statistics", border_style="cyan")
    
    def render_recent(self) -> Panel:
        """Render recent envelopes panel."""
        table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
        table.add_column("ID", width=8)
        table.add_column("Topic", width=18)
        table.add_column("Raw", justify="right", width=7)
        table.add_column("Enc", justify="right", width=7)
        table.add_column("LZ4", justify="right", width=7)
        table.add_column("Zstd", justify="right", width=7)
        table.add_column("Ratio", justify="right", width=6)
        
        # Show last 10
        for envelope in self.envelope_history[-10:]:
            table.add_row(
                envelope['envelope_id'],
                envelope['topic'],
                f"{envelope['raw_size']} B",
                f"{envelope['encoded_size']} B",
                f"{envelope['lz4_size']} B",
                f"{envelope['zstd_size']} B",
                f"{envelope['lz4_ratio']:.2f}x"
            )
        
        return Panel(table, title="📦 Recent Envelopes", border_style="green")
    
    def render_footer(self) -> Panel:
        """Render footer panel."""
        bandwidth_saved_lz4 = self.total_encoded_bytes - self.total_lz4_bytes
        bandwidth_saved_zstd = self.total_encoded_bytes - self.total_zstd_bytes
        
        pct_saved_lz4 = (bandwidth_saved_lz4 / self.total_encoded_bytes * 100) if self.total_encoded_bytes > 0 else 0
        pct_saved_zstd = (bandwidth_saved_zstd / self.total_encoded_bytes * 100) if self.total_encoded_bytes > 0 else 0
        
        footer_text = (
            f"💾 Bandwidth Saved - "
            f"LZ4: {bandwidth_saved_lz4:,} B ({pct_saved_lz4:.1f}%) | "
            f"Zstd: {bandwidth_saved_zstd:,} B ({pct_saved_zstd:.1f}%) | "
            f"Press Ctrl+C to stop"
        )
        
        return Panel(footer_text, style="bold yellow")
    
    def update_dashboard(self, layout: Layout):
        """Update dashboard with current data."""
        layout["header"].update(self.render_header())
        layout["stats"].update(self.render_stats())
        layout["recent"].update(self.render_recent())
        layout["footer"].update(self.render_footer())
    
    def run_simulation(self, num_samples: int = 1000, interval: float = 0.1):
        """Run telemetry monitoring simulation.
        
        Args:
            num_samples: Number of sample envelopes to generate
            interval: Interval between samples in seconds
        """
        self.console.print("\n[cyan]🚀 Starting telemetry monitor simulation...[/cyan]\n")
        
        # Sample detection data
        sample_detections = [
            Detection(class_id=0, class_name="person", confidence=0.95, bbox=(100, 100, 200, 200)),
            Detection(class_id=16, class_name="dog", confidence=0.88, bbox=(150, 150, 250, 250)),
            Detection(class_id=2, class_name="car", confidence=0.92, bbox=(200, 200, 300, 300)),
            Detection(class_id=67, class_name="laptop", confidence=0.85, bbox=(50, 50, 150, 150)),
            Detection(class_id=41, class_name="cup", confidence=0.78, bbox=(300, 300, 350, 350)),
        ]
        
        layout = self.create_dashboard()
        
        try:
            with Live(layout, refresh_per_second=4, console=self.console) as live:
                for i in range(num_samples):
                    # Pick random detection
                    import random
                    detection = random.choice(sample_detections)
                    
                    # Create and process envelope
                    envelope = self.create_sample_envelope(detection, i)
                    self.process_envelope(envelope)
                    
                    # Update dashboard
                    self.update_dashboard(layout)
                    
                    time.sleep(interval)
                    
        except KeyboardInterrupt:
            self.console.print("\n\n[yellow]⚠️  Monitoring stopped by user[/yellow]")
        
        # Final summary
        self.print_summary()
    
    def print_summary(self):
        """Print final summary."""
        self.console.print("\n" + "=" * 70)
        self.console.print("[bold cyan]TELEMETRY MONITORING SUMMARY[/bold cyan]")
        self.console.print("=" * 70 + "\n")
        
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_column("Metric", style="cyan", width=30)
        table.add_column("Value", style="green", justify="right")
        
        table.add_row("Total Envelopes Processed", f"{self.total_envelopes:,}")
        table.add_row("", "")
        table.add_row("Raw Payload Size", f"{self.total_raw_bytes:,} B")
        table.add_row("Encoded Size", f"{self.total_encoded_bytes:,} B")
        table.add_row("LZ4 Compressed Size", f"{self.total_lz4_bytes:,} B")
        table.add_row("Zstd Compressed Size", f"{self.total_zstd_bytes:,} B")
        table.add_row("", "")
        
        lz4_ratio = self.total_encoded_bytes / self.total_lz4_bytes if self.total_lz4_bytes > 0 else 0
        zstd_ratio = self.total_encoded_bytes / self.total_zstd_bytes if self.total_zstd_bytes > 0 else 0
        
        table.add_row("Overall LZ4 Compression", f"{lz4_ratio:.2f}x")
        table.add_row("Overall Zstd Compression", f"{zstd_ratio:.2f}x")
        table.add_row("", "")
        
        avg_encode = sum(self.encoding_times) / len(self.encoding_times) if self.encoding_times else 0
        avg_lz4 = sum(self.lz4_times) / len(self.lz4_times) if self.lz4_times else 0
        avg_zstd = sum(self.zstd_times) / len(self.zstd_times) if self.zstd_times else 0
        
        table.add_row("Avg Encoding Time", f"{avg_encode:.3f} ms")
        table.add_row("Avg LZ4 Compression Time", f"{avg_lz4:.3f} ms")
        table.add_row("Avg Zstd Compression Time", f"{avg_zstd:.3f} ms")
        table.add_row("", "")
        
        bandwidth_saved_lz4 = self.total_encoded_bytes - self.total_lz4_bytes
        bandwidth_saved_zstd = self.total_encoded_bytes - self.total_zstd_bytes
        
        table.add_row("Bandwidth Saved (LZ4)", f"{bandwidth_saved_lz4:,} B")
        table.add_row("Bandwidth Saved (Zstd)", f"{bandwidth_saved_zstd:,} B")
        
        self.console.print(table)
        self.console.print("\n" + "=" * 70)
        self.console.print("[green]✅ Telemetry monitoring completed![/green]\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ARIA Telemetry Monitor - Real-time data pipeline analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default simulation (1000 samples, 0.1s interval)
  python -m aria_sdk.examples.telemetry_monitor
  
  # Fast simulation (500 samples, 0.05s interval)
  python -m aria_sdk.examples.telemetry_monitor --samples 500 --interval 0.05
  
  # Slow detailed view (100 samples, 0.5s interval)
  python -m aria_sdk.examples.telemetry_monitor --samples 100 --interval 0.5
  
  # Different compression levels
  python -m aria_sdk.examples.telemetry_monitor --lz4-level 9 --zstd-level 15
        """
    )
    
    parser.add_argument(
        '--samples',
        type=int,
        default=1000,
        help='Number of sample envelopes to process (default: 1000)'
    )
    
    parser.add_argument(
        '--interval',
        type=float,
        default=0.1,
        help='Interval between samples in seconds (default: 0.1)'
    )
    
    parser.add_argument(
        '--lz4-level',
        type=int,
        default=0,
        help='LZ4 compression level 0-16 (default: 0)'
    )
    
    parser.add_argument(
        '--zstd-level',
        type=int,
        default=3,
        help='Zstandard compression level 1-22 (default: 3)'
    )
    
    args = parser.parse_args()
    
    try:
        monitor = TelemetryMonitor(
            compression_level_lz4=args.lz4_level,
            compression_level_zstd=args.zstd_level
        )
        
        monitor.run_simulation(
            num_samples=args.samples,
            interval=args.interval
        )
        
    except Exception as e:
        console = Console()
        console.print(f"\n[red]❌ Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
