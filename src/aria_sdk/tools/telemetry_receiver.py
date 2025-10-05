"""
Telemetry Receiver - Mars-to-Earth Communication Simulator
==========================================================

Simulates receiving compressed telemetry from a remote robot (Mars).
Decodes and decompresses envelopes, displays metadata and payloads.

Usage:
    python -m aria_sdk.tools.telemetry_receiver --port 5555
    
    (In another terminal)
    python -m aria_sdk.examples.full_system_demo --stream --port 5555
"""

import socket
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import json
import struct

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text

from aria_sdk.telemetry.codec import ProtobufCodec
from aria_sdk.telemetry.compression import Lz4Compressor, ZstdCompressor
from aria_sdk.domain.entities import Priority


class TelemetryReceiver:
    """
    Receives and decodes telemetry from remote robot.
    
    Simulates Earth ground station receiving data from Mars rover.
    """
    
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 5555,
        save_dir: Optional[Path] = None
    ):
        self.host = host
        self.port = port
        self.save_dir = Path(save_dir) if save_dir else None
        
        # Initialize decoder/decompressor
        self.codec = ProtobufCodec()
        self.lz4 = Lz4Compressor()
        self.zstd = ZstdCompressor()
        
        # Statistics
        self.stats = {
            'envelopes_received': 0,
            'bytes_received': 0,
            'bytes_decompressed': 0,
            'start_time': None,
            'last_received': None,
            'errors': 0,
            'by_topic': {},
            'by_priority': {},
            'compression_ratios': []
        }
        
        # Recent envelopes for display
        self.recent_envelopes = []
        self.max_recent = 20
        
        # Control
        self.running = False
        self.socket: Optional[socket.socket] = None
        self.console = Console()
        
        if self.save_dir:
            self.save_dir.mkdir(parents=True, exist_ok=True)
    
    def _receive_message(self, sock: socket.socket) -> Optional[bytes]:
        """
        Receive length-prefixed message from socket.
        
        Protocol:
        - 4 bytes: message length (network byte order)
        - N bytes: message data
        """
        try:
            # Read 4-byte length prefix
            length_data = b''
            while len(length_data) < 4:
                chunk = sock.recv(4 - len(length_data))
                if not chunk:
                    return None
                length_data += chunk
            
            msg_length = struct.unpack('!I', length_data)[0]
            
            # Read message data
            data = b''
            while len(data) < msg_length:
                chunk = sock.recv(min(4096, msg_length - len(data)))
                if not chunk:
                    return None
                data += chunk
            
            return data
        except Exception as e:
            self.console.print(f"[red]Error receiving message: {e}[/red]")
            return None
    
    def _process_envelope(self, compressed_data: bytes, metadata: Dict[str, Any]):
        """Process received envelope: decompress, decode, display."""
        try:
            # Decompress
            compression = metadata.get('compression', 'lz4')
            if compression == 'lz4':
                encoded_data = self.lz4.decompress(compressed_data)
            elif compression == 'zstd':
                encoded_data = self.zstd.decompress(compressed_data)
            else:
                encoded_data = compressed_data
            
            # Decode
            envelope = self.codec.decode(encoded_data)
            
            # Update stats
            self.stats['envelopes_received'] += 1
            self.stats['bytes_received'] += len(compressed_data)
            self.stats['bytes_decompressed'] += len(encoded_data)
            self.stats['last_received'] = datetime.now()
            
            # Compression ratio
            ratio = len(compressed_data) / len(encoded_data) if len(encoded_data) > 0 else 1.0
            self.stats['compression_ratios'].append(ratio)
            
            # By topic
            topic = envelope.topic
            self.stats['by_topic'][topic] = self.stats['by_topic'].get(topic, 0) + 1
            
            # By priority
            priority = envelope.priority.name
            self.stats['by_priority'][priority] = self.stats['by_priority'].get(priority, 0) + 1
            
            # Add to recent
            envelope_info = {
                'timestamp': envelope.timestamp,
                'topic': topic,
                'priority': priority,
                'payload_size': envelope.payload_size,
                'compressed_size': len(compressed_data),
                'ratio': ratio,
                'metadata': metadata
            }
            self.recent_envelopes.append(envelope_info)
            if len(self.recent_envelopes) > self.max_recent:
                self.recent_envelopes.pop(0)
            
            # Save if requested
            if self.save_dir:
                filename = f"{envelope.envelope_id}.bin"
                with open(self.save_dir / filename, 'wb') as f:
                    f.write(encoded_data)
            
        except Exception as e:
            self.stats['errors'] += 1
            self.console.print(f"[red]Error processing envelope: {e}[/red]")
    
    def _handle_client(self, client_sock: socket.socket, addr):
        """Handle incoming connection from robot."""
        self.console.print(f"[green]📡 Connected to robot at {addr}[/green]")
        
        while self.running:
            try:
                # Receive metadata + compressed data
                msg_data = self._receive_message(client_sock)
                if not msg_data:
                    break
                
                # Parse: first line is JSON metadata, rest is binary data
                lines = msg_data.split(b'\n', 1)
                if len(lines) != 2:
                    continue
                
                metadata = json.loads(lines[0].decode())
                compressed_data = lines[1]
                
                # Process envelope
                self._process_envelope(compressed_data, metadata)
                
            except Exception as e:
                self.console.print(f"[red]Error handling client: {e}[/red]")
                break
        
        client_sock.close()
        self.console.print(f"[yellow]📡 Disconnected from {addr}[/yellow]")
    
    def _create_display(self) -> Layout:
        """Create rich display layout."""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="stats", size=12),
            Layout(name="recent", size=15),
        )
        return layout
    
    def _update_display(self, layout: Layout):
        """Update display with current stats."""
        # Header
        if self.stats['start_time']:
            uptime = (datetime.now() - self.stats['start_time']).total_seconds()
            uptime_str = f"{uptime:.1f}s"
        else:
            uptime_str = "N/A"
        
        header_text = Text()
        header_text.append("📡 TELEMETRY RECEIVER ", style="bold cyan")
        header_text.append(f"| Uptime: {uptime_str} ", style="yellow")
        header_text.append(f"| Envelopes: {self.stats['envelopes_received']}", style="green")
        layout["header"].update(Panel(header_text, border_style="cyan"))
        
        # Stats
        stats_table = Table(title="📊 Statistics", show_header=True)
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="yellow")
        
        total_kb = self.stats['bytes_received'] / 1024
        decompressed_kb = self.stats['bytes_decompressed'] / 1024
        avg_ratio = sum(self.stats['compression_ratios']) / len(self.stats['compression_ratios']) if self.stats['compression_ratios'] else 1.0
        
        stats_table.add_row("Envelopes Received", str(self.stats['envelopes_received']))
        stats_table.add_row("Bytes Received", f"{total_kb:.2f} KB")
        stats_table.add_row("Bytes Decompressed", f"{decompressed_kb:.2f} KB")
        stats_table.add_row("Avg Compression Ratio", f"{avg_ratio:.3f}x")
        stats_table.add_row("Errors", str(self.stats['errors']))
        
        if self.stats['last_received']:
            elapsed = (datetime.now() - self.stats['last_received']).total_seconds()
            stats_table.add_row("Last Received", f"{elapsed:.1f}s ago")
        
        # Topics
        for topic, count in self.stats['by_topic'].items():
            stats_table.add_row(f"  Topic: {topic}", str(count))
        
        # Priorities
        for priority, count in self.stats['by_priority'].items():
            stats_table.add_row(f"  Priority: {priority}", str(count))
        
        layout["stats"].update(Panel(stats_table, border_style="yellow"))
        
        # Recent envelopes
        recent_table = Table(title="📦 Recent Envelopes", show_header=True)
        recent_table.add_column("Time", style="cyan", width=12)
        recent_table.add_column("Topic", style="yellow", width=20)
        recent_table.add_column("Priority", style="magenta", width=10)
        recent_table.add_column("Payload", style="green", width=10)
        recent_table.add_column("Compressed", style="blue", width=12)
        recent_table.add_column("Ratio", style="red", width=8)
        
        for env in reversed(self.recent_envelopes[-10:]):
            time_str = datetime.fromtimestamp(env['timestamp']).strftime('%H:%M:%S.%f')[:-3]
            recent_table.add_row(
                time_str,
                env['topic'],
                env['priority'],
                f"{env['payload_size']} B",
                f"{env['compressed_size']} B",
                f"{env['ratio']:.2f}x"
            )
        
        layout["recent"].update(Panel(recent_table, border_style="green"))
    
    def start(self):
        """Start receiver server."""
        self.running = True
        self.stats['start_time'] = datetime.now()
        
        # Create socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        
        self.console.print(f"[bold green]🚀 Receiver listening on {self.host}:{self.port}[/bold green]")
        self.console.print("[yellow]Waiting for robot connection...[/yellow]")
        
        # Accept connections in background
        def accept_loop():
            while self.running:
                try:
                    self.socket.settimeout(1.0)
                    client_sock, addr = self.socket.accept()
                    threading.Thread(target=self._handle_client, args=(client_sock, addr), daemon=True).start()
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        self.console.print(f"[red]Accept error: {e}[/red]")
                    break
        
        accept_thread = threading.Thread(target=accept_loop, daemon=True)
        accept_thread.start()
        
        # Live display
        layout = self._create_display()
        try:
            with Live(layout, console=self.console, refresh_per_second=4) as live:
                while self.running:
                    self._update_display(layout)
                    live.update(layout)
                    time.sleep(0.25)
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Shutting down receiver...[/yellow]")
        finally:
            self.running = False
            if self.socket:
                self.socket.close()
    
    def stop(self):
        """Stop receiver."""
        self.running = False


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Telemetry Receiver - Mars-to-Earth Simulator")
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5555, help='Port to listen on')
    parser.add_argument('--save-dir', help='Directory to save decoded envelopes')
    
    args = parser.parse_args()
    
    receiver = TelemetryReceiver(
        host=args.host,
        port=args.port,
        save_dir=args.save_dir
    )
    
    try:
        receiver.start()
    except KeyboardInterrupt:
        receiver.stop()


if __name__ == '__main__':
    main()
