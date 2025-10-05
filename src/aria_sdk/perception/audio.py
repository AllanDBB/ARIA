"""
ARIA SDK - Audio Processing Module

Provides VAD, SED, and audio DSP capabilities.
"""

import numpy as np
from typing import List, Optional, Tuple
from scipy import signal
from dataclasses import dataclass

from aria_sdk.domain.entities import AudioEvent
from aria_sdk.domain.protocols import IAudioProcessor


@dataclass
class AudioConfig:
    """Audio processing configuration."""
    sample_rate: int = 16000
    frame_length_ms: int = 30
    vad_threshold: float = 0.5
    energy_threshold: float = 0.01


class AudioProcessor(IAudioProcessor):
    """
    Audio processor with VAD (Voice Activity Detection) and SED (Sound Event Detection).
    """
    
    def __init__(self, config: Optional[AudioConfig] = None):
        """
        Initialize audio processor.
        
        Args:
            config: Audio configuration (uses defaults if None)
        """
        self.config = config or AudioConfig()
        self.frame_length = int(self.config.sample_rate * self.config.frame_length_ms / 1000)
        
        # Sound event labels (simplified - real SED would use trained model)
        self.event_labels = [
            'speech', 'music', 'alarm', 'dog_bark', 'engine', 'footsteps',
            'door', 'silence', 'noise', 'other'
        ]
    
    def detect_voice_activity(self, audio: np.ndarray) -> bool:
        """
        Detect voice activity in audio frame.
        
        Args:
            audio: Audio samples (mono, float32, -1 to 1)
            
        Returns:
            True if voice detected
        """
        # Simple energy-based VAD
        energy = np.mean(audio ** 2)
        
        if energy < self.config.energy_threshold:
            return False
        
        # Compute zero-crossing rate (ZCR)
        zcr = np.mean(np.abs(np.diff(np.sign(audio)))) / 2.0
        
        # Voice typically has moderate ZCR (0.1-0.5)
        # Music/noise has higher ZCR
        is_voice = (zcr > 0.1) and (zcr < 0.5) and (energy > self.config.vad_threshold)
        
        return is_voice
    
    def detect_sound_events(self, audio: np.ndarray) -> List[AudioEvent]:
        """
        Detect sound events in audio.
        
        Args:
            audio: Audio samples
            
        Returns:
            List of detected events
        """
        # This is a placeholder - real SED would use a trained model (e.g., YAMNet, PANNs)
        events = []
        
        # Simple heuristics
        energy = np.mean(audio ** 2)
        zcr = np.mean(np.abs(np.diff(np.sign(audio)))) / 2.0
        
        if energy < 0.001:
            events.append(AudioEvent(
                event_type='silence',
                confidence=0.9,
                start_time=0.0,
                end_time=len(audio) / self.config.sample_rate
            ))
        elif self.detect_voice_activity(audio):
            events.append(AudioEvent(
                event_type='speech',
                confidence=0.7,
                start_time=0.0,
                end_time=len(audio) / self.config.sample_rate
            ))
        elif zcr > 0.6:
            events.append(AudioEvent(
                event_type='noise',
                confidence=0.6,
                start_time=0.0,
                end_time=len(audio) / self.config.sample_rate
            ))
        else:
            events.append(AudioEvent(
                event_type='other',
                confidence=0.5,
                start_time=0.0,
                end_time=len(audio) / self.config.sample_rate
            ))
        
        return events
    
    async def process(self, audio: np.ndarray) -> Tuple[bool, List[AudioEvent]]:
        """
        Process audio frame.
        
        Args:
            audio: Audio samples
            
        Returns:
            Tuple of (voice_active, sound_events)
        """
        voice_active = self.detect_voice_activity(audio)
        sound_events = self.detect_sound_events(audio)
        
        return (voice_active, sound_events)


class AudioDsp:
    """
    Audio DSP utilities: beamforming, denoising, filtering.
    """
    
    @staticmethod
    def beamform(multichannel_audio: np.ndarray, mic_positions: np.ndarray, target_angle: float) -> np.ndarray:
        """
        Delay-and-sum beamforming for microphone array.
        
        Args:
            multichannel_audio: Audio from multiple mics (channels, samples)
            mic_positions: Microphone positions in meters (channels, 3)
            target_angle: Target angle in degrees (0=front, 90=right)
            
        Returns:
            Beamformed audio (mono)
        """
        num_channels, num_samples = multichannel_audio.shape
        sample_rate = 16000  # Assume 16kHz
        speed_of_sound = 343.0  # m/s
        
        # Convert angle to direction vector
        angle_rad = np.deg2rad(target_angle)
        direction = np.array([np.cos(angle_rad), np.sin(angle_rad), 0.0])
        
        # Compute delays for each microphone
        delays = np.dot(mic_positions, direction) / speed_of_sound
        delays -= np.min(delays)  # Normalize to minimum delay
        
        # Convert to sample delays
        sample_delays = delays * sample_rate
        
        # Apply delays and sum
        beamformed = np.zeros(num_samples)
        for ch in range(num_channels):
            delay_samples = int(sample_delays[ch])
            if delay_samples < num_samples:
                beamformed[:-delay_samples or None] += multichannel_audio[ch, delay_samples:]
        
        beamformed /= num_channels
        return beamformed
    
    @staticmethod
    def spectral_subtraction(audio: np.ndarray, noise_profile: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Spectral subtraction noise reduction.
        
        Args:
            audio: Noisy audio
            noise_profile: Noise spectrum estimate (None=estimate from first 0.5s)
            
        Returns:
            Denoised audio
        """
        # STFT
        f, t, Zxx = signal.stft(audio, nperseg=512, noverlap=256)
        
        # Estimate noise spectrum
        if noise_profile is None:
            # Use first 0.5 seconds as noise estimate
            noise_frames = int(0.5 * len(t))
            noise_profile = np.mean(np.abs(Zxx[:, :noise_frames]) ** 2, axis=1)
        
        # Subtract noise spectrum
        magnitude = np.abs(Zxx)
        phase = np.angle(Zxx)
        
        denoised_magnitude = np.maximum(magnitude ** 2 - noise_profile[:, np.newaxis], 0)
        denoised_magnitude = np.sqrt(denoised_magnitude)
        
        # Reconstruct
        Zxx_denoised = denoised_magnitude * np.exp(1j * phase)
        _, audio_denoised = signal.istft(Zxx_denoised, nperseg=512, noverlap=256)
        
        return audio_denoised
    
    @staticmethod
    def bandpass_filter(audio: np.ndarray, lowcut: float, highcut: float, sample_rate: int = 16000, order: int = 5) -> np.ndarray:
        """
        Bandpass filter.
        
        Args:
            audio: Input audio
            lowcut: Low cutoff frequency (Hz)
            highcut: High cutoff frequency (Hz)
            sample_rate: Sample rate (Hz)
            order: Filter order
            
        Returns:
            Filtered audio
        """
        nyquist = sample_rate / 2
        low = lowcut / nyquist
        high = highcut / nyquist
        
        sos = signal.butter(order, [low, high], btype='band', output='sos')
        filtered = signal.sosfilt(sos, audio)
        
        return filtered
    
    @staticmethod
    def compute_mfcc(audio: np.ndarray, sample_rate: int = 16000, n_mfcc: int = 13) -> np.ndarray:
        """
        Compute MFCC features (placeholder - would use librosa in production).
        
        Args:
            audio: Audio samples
            sample_rate: Sample rate
            n_mfcc: Number of MFCC coefficients
            
        Returns:
            MFCC features (n_mfcc, n_frames)
        """
        # This is a simplified placeholder
        # Real implementation would use librosa.feature.mfcc
        
        # Compute spectrogram
        f, t, Sxx = signal.spectrogram(audio, sample_rate, nperseg=512)
        
        # Log power
        log_power = np.log(Sxx + 1e-10)
        
        # Simplified MFCC (just return first n_mfcc frequency bins)
        mfcc = log_power[:n_mfcc, :]
        
        return mfcc
