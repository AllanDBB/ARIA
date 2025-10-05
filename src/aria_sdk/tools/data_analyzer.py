#!/usr/bin/env python3
"""
ARIA Data Analyzer - Analyze stored robot data

This script analyzes data stored during robot operation:
- Telemetry statistics
- Cognitive state evolution
- Decision patterns
- Performance metrics
"""

import sys
import argparse
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


class DataAnalyzer:
    """Analyzer for stored ARIA data."""
    
    def __init__(self, storage_dir: Path):
        """Initialize analyzer.
        
        Args:
            storage_dir: Directory with stored data
        """
        self.storage_dir = Path(storage_dir)
        self.db_path = self.storage_dir / "aria_data.db"
        self.console = Console()
        
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
    
    def list_sessions(self):
        """List all available sessions."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT session_id, start_time, end_time, total_frames, total_loops
            FROM sessions
            ORDER BY start_time DESC
        """)
        
        sessions = cursor.fetchall()
        conn.close()
        
        if not sessions:
            self.console.print("[yellow]No sessions found in database.[/yellow]")
            return []
        
        table = Table(title="Available Sessions", box=box.ROUNDED)
        table.add_column("Session ID", style="cyan")
        table.add_column("Start Time", style="green")
        table.add_column("End Time", style="green")
        table.add_column("Frames", justify="right")
        table.add_column("Loops", justify="right")
        table.add_column("Duration", justify="right")
        
        for session_id, start, end, frames, loops in sessions:
            if start and end:
                start_dt = datetime.fromisoformat(start)
                end_dt = datetime.fromisoformat(end)
                duration = (end_dt - start_dt).total_seconds()
                duration_str = f"{duration:.1f}s"
            else:
                duration_str = "In progress"
            
            table.add_row(
                session_id,
                start[:19] if start else "N/A",
                end[:19] if end else "N/A",
                str(frames) if frames else "0",
                str(loops) if loops else "0",
                duration_str
            )
        
        self.console.print(table)
        return [s[0] for s in sessions]
    
    def analyze_session(self, session_id: str):
        """Analyze a specific session.
        
        Args:
            session_id: Session ID to analyze
        """
        self.console.print(f"\n[bold cyan]Analyzing Session: {session_id}[/bold cyan]\n")
        
        conn = sqlite3.connect(self.db_path)
        
        # Session info
        self._print_session_info(conn, session_id)
        
        # Telemetry analysis
        self._print_telemetry_stats(conn, session_id)
        
        # Cognitive state analysis
        self._print_cognitive_stats(conn, session_id)
        
        # Decision analysis
        self._print_decision_stats(conn, session_id)
        
        conn.close()
    
    def _print_session_info(self, conn: sqlite3.Connection, session_id: str):
        """Print session information."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT start_time, end_time, total_frames, total_loops
            FROM sessions WHERE session_id = ?
        """, (session_id,))
        
        row = cursor.fetchone()
        if not row:
            self.console.print(f"[red]Session {session_id} not found![/red]")
            return
        
        start, end, frames, loops = row
        
        table = Table(title="📋 Session Information", box=box.SIMPLE)
        table.add_column("Property", style="cyan", width=20)
        table.add_column("Value", style="green")
        
        table.add_row("Session ID", session_id)
        table.add_row("Start Time", start[:19] if start else "N/A")
        table.add_row("End Time", end[:19] if end else "N/A")
        
        if start and end:
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
            duration = (end_dt - start_dt).total_seconds()
            table.add_row("Duration", f"{duration:.1f}s ({duration/60:.1f}min)")
        
        table.add_row("Total Frames", str(frames) if frames else "0")
        table.add_row("Total Loops", str(loops) if loops else "0")
        
        if frames and loops:
            table.add_row("Frames/Loop", f"{frames/loops:.1f}")
        
        self.console.print(table)
        self.console.print()
    
    def _print_telemetry_stats(self, conn: sqlite3.Connection, session_id: str):
        """Print telemetry statistics."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(payload_size) as total_payload,
                SUM(encoded_size) as total_encoded,
                SUM(compressed_size) as total_compressed,
                AVG(compression_ratio) as avg_ratio,
                AVG(encoding_time_ms) as avg_encode,
                AVG(compression_time_ms) as avg_compress,
                compression_algo
            FROM telemetry
            WHERE session_id = ?
            GROUP BY compression_algo
        """, (session_id,))
        
        rows = cursor.fetchall()
        if not rows:
            return
        
        table = Table(title="📡 Telemetry Statistics", box=box.SIMPLE)
        table.add_column("Metric", style="cyan", width=25)
        table.add_column("Value", style="green", justify="right")
        
        total_envelopes = sum(r[0] for r in rows)
        total_payload = sum(r[1] for r in rows)
        total_encoded = sum(r[2] for r in rows)
        total_compressed = sum(r[3] for r in rows)
        
        table.add_row("Total Envelopes", f"{total_envelopes:,}")
        table.add_row("Total Payload Size", f"{total_payload:,} B ({total_payload/1024:.1f} KB)")
        table.add_row("Total Encoded Size", f"{total_encoded:,} B ({total_encoded/1024:.1f} KB)")
        table.add_row("Total Compressed Size", f"{total_compressed:,} B ({total_compressed/1024:.1f} KB)")
        table.add_row("", "")
        
        for row in rows:
            algo = row[7]
            count = row[0]
            avg_ratio = row[4]
            avg_encode = row[5]
            avg_compress = row[6]
            
            table.add_row(f"└─ {algo.upper()} Envelopes", f"{count:,}")
            table.add_row(f"└─ {algo.upper()} Avg Ratio", f"{avg_ratio:.2f}x")
            table.add_row(f"└─ {algo.upper()} Avg Encode Time", f"{avg_encode:.3f} ms")
            table.add_row(f"└─ {algo.upper()} Avg Compress Time", f"{avg_compress:.3f} ms")
            table.add_row("", "")
        
        # Bandwidth saved
        bandwidth_saved = total_encoded - total_compressed
        pct_saved = (bandwidth_saved / total_encoded * 100) if total_encoded > 0 else 0
        
        table.add_row("Bandwidth Saved", f"{bandwidth_saved:,} B ({pct_saved:.1f}%)")
        
        self.console.print(table)
        self.console.print()
    
    def _print_cognitive_stats(self, conn: sqlite3.Connection, session_id: str):
        """Print cognitive state statistics."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                MIN(energy) as min_energy,
                MAX(energy) as max_energy,
                AVG(energy) as avg_energy,
                MIN(temperature) as min_temp,
                MAX(temperature) as max_temp,
                AVG(temperature) as avg_temp,
                AVG(novelty_drive) as avg_novelty,
                SUM(num_detections) as total_detections,
                MAX(unique_classes) as max_classes
            FROM cognitive_states
            WHERE session_id = ?
        """, (session_id,))
        
        row = cursor.fetchone()
        if not row or row[0] is None:
            return
        
        table = Table(title="🧠 Cognitive State Statistics", box=box.SIMPLE)
        table.add_column("Metric", style="cyan", width=25)
        table.add_column("Value", style="green", justify="right")
        
        table.add_row("Energy Range", f"{row[0]:.1f}% - {row[1]:.1f}%")
        table.add_row("Average Energy", f"{row[2]:.1f}%")
        table.add_row("", "")
        table.add_row("Temperature Range", f"{row[3]:.1f}°C - {row[4]:.1f}°C")
        table.add_row("Average Temperature", f"{row[5]:.1f}°C")
        table.add_row("", "")
        table.add_row("Average Novelty Drive", f"{row[6]:.3f}")
        table.add_row("Total Detections", f"{int(row[7]):,}")
        table.add_row("Max Unique Classes", f"{int(row[8])}")
        
        self.console.print(table)
        self.console.print()
    
    def _print_decision_stats(self, conn: sqlite3.Connection, session_id: str):
        """Print decision statistics."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT action, COUNT(*) as count
            FROM decisions
            WHERE session_id = ?
            GROUP BY action
            ORDER BY count DESC
        """, (session_id,))
        
        rows = cursor.fetchall()
        if not rows:
            return
        
        table = Table(title="🎯 Decision Statistics", box=box.SIMPLE)
        table.add_column("Action", style="cyan")
        table.add_column("Count", style="green", justify="right")
        table.add_column("Percentage", style="yellow", justify="right")
        
        total = sum(r[1] for r in rows)
        
        for action, count in rows:
            pct = (count / total * 100) if total > 0 else 0
            table.add_row(action, f"{count:,}", f"{pct:.1f}%")
        
        table.add_row("", "", "")
        table.add_row("[bold]TOTAL[/bold]", f"[bold]{total:,}[/bold]", "[bold]100.0%[/bold]")
        
        self.console.print(table)
        self.console.print()
    
    def plot_energy_timeline(self, session_id: str, output_file: Optional[Path] = None):
        """Plot energy level over time.
        
        Args:
            session_id: Session ID
            output_file: Output file path (shows plot if None)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timestamp, energy
            FROM cognitive_states
            WHERE session_id = ?
            ORDER BY timestamp
        """, (session_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            self.console.print("[yellow]No cognitive state data found.[/yellow]")
            return
        
        timestamps = [datetime.fromisoformat(r[0]) for r in rows]
        energy = [r[1] for r in rows]
        
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(timestamps, energy, linewidth=2, color='#00ff00')
        ax.axhline(y=20, color='r', linestyle='--', label='Low Energy Threshold')
        ax.axhline(y=10, color='darkred', linestyle='--', label='Critical Threshold')
        
        ax.set_xlabel('Time')
        ax.set_ylabel('Energy (%)')
        ax.set_title(f'Energy Level Timeline - Session {session_id}')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        fig.autofmt_xdate()
        
        if output_file:
            plt.savefig(output_file, dpi=150, bbox_inches='tight')
            self.console.print(f"[green]Plot saved to: {output_file}[/green]")
        else:
            plt.show()
        
        plt.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ARIA Data Analyzer - Analyze stored robot data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all sessions
  python -m aria_sdk.tools.data_analyzer --storage-dir ./data --list
  
  # Analyze specific session
  python -m aria_sdk.tools.data_analyzer --storage-dir ./data --session 20251005_143022
  
  # Plot energy timeline
  python -m aria_sdk.tools.data_analyzer --storage-dir ./data --session 20251005_143022 --plot-energy
        """
    )
    
    parser.add_argument(
        '--storage-dir',
        type=Path,
        default=Path('./data'),
        help='Data storage directory (default: ./data)'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all available sessions'
    )
    
    parser.add_argument(
        '--session',
        type=str,
        help='Session ID to analyze'
    )
    
    parser.add_argument(
        '--plot-energy',
        action='store_true',
        help='Plot energy timeline'
    )
    
    parser.add_argument(
        '--output',
        type=Path,
        help='Output file for plots'
    )
    
    args = parser.parse_args()
    
    try:
        analyzer = DataAnalyzer(args.storage_dir)
        
        if args.list:
            analyzer.list_sessions()
        
        elif args.session:
            analyzer.analyze_session(args.session)
            
            if args.plot_energy:
                analyzer.plot_energy_timeline(args.session, args.output)
        
        else:
            # Show most recent session
            sessions = analyzer.list_sessions()
            if sessions:
                analyzer.console.print(f"\n[cyan]Analyzing most recent session...[/cyan]\n")
                analyzer.analyze_session(sessions[0])
        
    except Exception as e:
        console = Console()
        console.print(f"\n[red]❌ Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
