"""
ARIA SDK - Telemetry Packetization Module

Provides MTU-aware fragmentation and reassembly of large envelopes.
"""

import time
from typing import Dict, List, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone
from collections import defaultdict

from aria_sdk.domain.entities import Envelope, EnvelopeMetadata, FragmentInfo


class Packetizer:
    """
    Packetizes large envelopes into MTU-sized fragments.
    """
    
    def __init__(self, mtu: int = 1400):
        """
        Initialize packetizer.
        
        Args:
            mtu: Maximum transmission unit (bytes). Default: 1400 (safe for most networks)
        """
        if mtu < 64:
            raise ValueError(f"MTU too small: {mtu} (minimum 64 bytes)")
        
        self.mtu = mtu
        # Reserve space for metadata (~100 bytes for fragment info)
        self.max_payload_per_fragment = mtu - 100
    
    def packetize(self, envelope: Envelope) -> List[Envelope]:
        """
        Fragment envelope into smaller packets if needed.
        
        Args:
            envelope: Envelope to fragment
            
        Returns:
            List of envelope fragments (1 if no fragmentation needed)
        """
        payload_size = len(envelope.payload)
        
        if payload_size <= self.max_payload_per_fragment:
            # No fragmentation needed
            return [envelope]
        
        # Generate message ID for this fragmentation
        message_id = uuid4()
        
        # Calculate number of fragments
        num_fragments = (payload_size + self.max_payload_per_fragment - 1) // self.max_payload_per_fragment
        
        fragments = []
        for frag_idx in range(num_fragments):
            offset = frag_idx * self.max_payload_per_fragment
            end = min(offset + self.max_payload_per_fragment, payload_size)
            fragment_payload = envelope.payload[offset:end]
            
            # Create fragment metadata
            frag_info = FragmentInfo(
                fragment_id=frag_idx,
                total_fragments=num_fragments,
                offset=offset,
                length=len(fragment_payload),
                message_id=message_id
            )
            
            # Copy existing metadata and add fragment info
            if envelope.metadata:
                metadata = EnvelopeMetadata(
                    fragment_info=frag_info,
                    fec_info=envelope.metadata.fec_info,
                    crypto_info=envelope.metadata.crypto_info
                )
            else:
                metadata = EnvelopeMetadata(fragment_info=frag_info)
            
            # Create fragment envelope
            fragment = Envelope(
                id=uuid4(),  # Each fragment gets unique ID
                timestamp=envelope.timestamp,
                priority=envelope.priority,
                topic=envelope.topic,
                payload=fragment_payload,
                metadata=metadata
            )
            
            fragments.append(fragment)
        
        return fragments


class Defragmenter:
    """
    Reassembles fragmented envelopes.
    
    Handles out-of-order fragments and detects incomplete messages.
    """
    
    def __init__(self, timeout: float = 5.0, max_messages: int = 100):
        """
        Initialize defragmenter.
        
        Args:
            timeout: Timeout for incomplete messages (seconds)
            max_messages: Maximum concurrent in-progress messages
        """
        self.timeout = timeout
        self.max_messages = max_messages
        
        # message_id -> {fragment_id: (envelope, arrival_time)}
        self.fragments: Dict[UUID, Dict[int, tuple[Envelope, float]]] = defaultdict(dict)
        
        # message_id -> (total_fragments, topic, priority, timestamp)
        self.message_info: Dict[UUID, tuple[int, str, int, datetime]] = {}
    
    def defragment(self, envelope: Envelope) -> Optional[Envelope]:
        """
        Process a fragment and try to reassemble.
        
        Args:
            envelope: Fragment envelope
            
        Returns:
            Reassembled envelope if complete, None if waiting for more fragments
            
        Raises:
            ValueError: If fragment metadata is missing or invalid
        """
        if not envelope.metadata or not envelope.metadata.fragment_info:
            # Not a fragment - return as-is
            return envelope
        
        frag_info = envelope.metadata.fragment_info
        message_id = frag_info.message_id
        frag_id = frag_info.fragment_id
        total_frags = frag_info.total_fragments
        
        # Garbage collect old incomplete messages
        self._gc_timeout()
        
        # Check capacity
        if len(self.fragments) >= self.max_messages and message_id not in self.fragments:
            print(f"[Defragmenter] Warning: Too many incomplete messages, dropping oldest")
            self._drop_oldest()
        
        # Store fragment
        arrival_time = time.monotonic()
        self.fragments[message_id][frag_id] = (envelope, arrival_time)
        
        # Store message info
        if message_id not in self.message_info:
            self.message_info[message_id] = (
                total_frags,
                envelope.topic,
                envelope.priority.value,
                envelope.timestamp
            )
        
        # Check if complete
        if len(self.fragments[message_id]) == total_frags:
            return self._reassemble(message_id)
        
        return None
    
    def _reassemble(self, message_id: UUID) -> Envelope:
        """
        Reassemble complete message.
        
        Args:
            message_id: Message to reassemble
            
        Returns:
            Reassembled envelope
        """
        frags_dict = self.fragments.pop(message_id)
        total_frags, topic, priority_val, timestamp = self.message_info.pop(message_id)
        
        # Sort fragments by ID
        sorted_frags = sorted(frags_dict.items(), key=lambda x: x[0])
        
        # Concatenate payloads
        full_payload = b''.join([env.payload for _, (env, _) in sorted_frags])
        
        # Create reassembled envelope
        from aria_sdk.domain.entities import Priority
        
        reassembled = Envelope(
            id=uuid4(),
            timestamp=timestamp,
            priority=Priority(priority_val),
            topic=topic,
            payload=full_payload,
            metadata=None  # Remove fragment info
        )
        
        return reassembled
    
    def _gc_timeout(self):
        """Garbage collect timed-out incomplete messages."""
        now = time.monotonic()
        to_remove = []
        
        for message_id, frags_dict in self.fragments.items():
            # Check oldest fragment
            oldest_time = min(arrival_time for _, arrival_time in frags_dict.values())
            if now - oldest_time > self.timeout:
                to_remove.append(message_id)
        
        for message_id in to_remove:
            total_frags = self.message_info[message_id][0]
            received_frags = len(self.fragments[message_id])
            print(
                f"[Defragmenter] Timeout: message {message_id} "
                f"incomplete ({received_frags}/{total_frags} fragments)"
            )
            self.fragments.pop(message_id)
            self.message_info.pop(message_id)
    
    def _drop_oldest(self):
        """Drop oldest incomplete message."""
        if not self.fragments:
            return
        
        # Find oldest message
        oldest_id = None
        oldest_time = float('inf')
        
        for message_id, frags_dict in self.fragments.items():
            min_time = min(arrival_time for _, arrival_time in frags_dict.values())
            if min_time < oldest_time:
                oldest_time = min_time
                oldest_id = message_id
        
        if oldest_id:
            self.fragments.pop(oldest_id)
            self.message_info.pop(oldest_id)
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get defragmenter statistics.
        
        Returns:
            Dict with 'incomplete_messages' and 'total_fragments'
        """
        total_fragments = sum(len(frags) for frags in self.fragments.values())
        return {
            'incomplete_messages': len(self.fragments),
            'total_fragments': total_fragments
        }
