"""
Module de gestion audio et détection d'activité vocale (VAD).

Ce module gère :
- Capture audio depuis le microphone
- Détection d'activité vocale (Voice Activity Detection)
- Preprocessing audio pour la reconnaissance vocale
- Gestion des périphériques audio
"""

import logging
import time
import threading
import queue
import numpy as np
from typing import Optional, Tuple, Callable, Dict, Any
from dataclasses import dataclass
from enum import Enum

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    pyaudio = None

try:
    import webrtcvad
    WEBRTC_VAD_AVAILABLE = True
except ImportError:
    WEBRTC_VAD_AVAILABLE = False
    webrtcvad = None

class AudioFormat:
    """Configuration audio standard pour STT."""
    SAMPLE_RATE = 16000  # Hz - Standard pour la plupart des modèles STT
    CHANNELS = 1         # Mono
    SAMPLE_WIDTH = 2     # 16-bit
    CHUNK_SIZE = 1024    # Échantillons par chunk
    FORMAT = pyaudio.paInt16 if PYAUDIO_AVAILABLE else None

class VADMode(Enum):
    """Modes de sensibilité pour la détection d'activité vocale."""
    QUALITY = 0      # Moins agressif, meilleure qualité
    LOW_BITRATE = 1  # Compromis
    AGGRESSIVE = 2   # Plus agressif, détecte plus facilement
    VERY_AGGRESSIVE = 3  # Le plus agressif

@dataclass
class AudioSegment:
    """Segment audio avec métadonnées."""
    data: np.ndarray
    sample_rate: int
    timestamp: float
    duration: float
    has_speech: bool = False
    energy_level: float = 0.0

class VoiceActivityDetector:
    """Détecteur d'activité vocale utilisant WebRTC VAD."""
    
    def __init__(self, mode: VADMode = VADMode.AGGRESSIVE, sample_rate: int = AudioFormat.SAMPLE_RATE):
        self.logger = logging.getLogger("VAD")
        self.sample_rate = sample_rate
        self.mode = mode
        
        if WEBRTC_VAD_AVAILABLE:
            self.vad = webrtcvad.Vad(mode.value)
            self.logger.info(f"✅ WebRTC VAD initialisé (mode: {mode.name})")
        else:
            self.vad = None
            self.logger.warning("⚠️ WebRTC VAD non disponible, utilisation VAD basique")
    
    def is_speech(self, audio_data: bytes, sample_rate: int = None) -> bool:
        """
        Détermine si l'audio contient de la parole.
        
        Args:
            audio_data: Données audio en bytes (16-bit PCM)
            sample_rate: Taux d'échantillonnage (doit être 8000, 16000, 32000, ou 48000)
            
        Returns:
            True si de la parole est détectée
        """
        if not audio_data:
            return False
            
        sample_rate = sample_rate or self.sample_rate
        
        # Vérifier que le taux d'échantillonnage est supporté par WebRTC VAD
        if sample_rate not in [8000, 16000, 32000, 48000]:
            # Fallback sur détection d'énergie
            return self._energy_based_vad(audio_data)
        
        if self.vad and len(audio_data) >= 320:  # WebRTC VAD nécessite au moins 10ms à 16kHz
            try:
                # WebRTC VAD nécessite des frames de taille spécifique
                frame_length = sample_rate // 100  # 10ms de frame
                frame_bytes = frame_length * 2  # 16-bit = 2 bytes par échantillon
                
                # Traiter par frames de 10ms
                for i in range(0, len(audio_data) - frame_bytes, frame_bytes):
                    frame = audio_data[i:i + frame_bytes]
                    if len(frame) == frame_bytes:
                        if self.vad.is_speech(frame, sample_rate):
                            return True
                return False
                
            except Exception as e:
                self.logger.debug(f"Erreur WebRTC VAD: {e}, fallback sur énergie")
                return self._energy_based_vad(audio_data)
        else:
            return self._energy_based_vad(audio_data)
    
    def _energy_based_vad(self, audio_data: bytes, threshold: float = 0.01) -> bool:
        """VAD basé sur l'énergie audio."""
        try:
            # Convertir en numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Calculer l'énergie RMS
            energy = np.sqrt(np.mean(audio_array ** 2))
            
            return energy > threshold
            
        except Exception as e:
            self.logger.debug(f"Erreur calcul énergie: {e}")
            return False

class AudioCapture:
    """Gestionnaire de capture audio avec VAD intégré."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize AudioCapture with configuration dictionary.
        
        Args:
            config: Configuration dictionary containing audio settings
        """
        self.logger = logging.getLogger("AudioCapture")
        
        # Extract configuration values with defaults
        self.sample_rate = config.get('sample_rate', AudioFormat.SAMPLE_RATE)
        self.channels = config.get('channels', AudioFormat.CHANNELS)
        self.chunk_size = self._calculate_chunk_size(config)
        
        # VAD configuration
        vad_sensitivity = config.get('vad_sensitivity', 2)
        vad_mode_mapping = {0: 'QUALITY', 1: 'LOW_BITRATE', 2: 'AGGRESSIVE', 3: 'VERY_AGGRESSIVE'}
        vad_mode_str = vad_mode_mapping.get(vad_sensitivity, 'AGGRESSIVE')
        
        # Initialize VAD
        vad_mode = getattr(VADMode, vad_mode_str.upper(), VADMode.AGGRESSIVE)
        self.vad = VoiceActivityDetector(vad_mode, self.sample_rate)
        
        # State management
        self.is_recording = False
        self.audio_queue = queue.Queue()
        self.record_thread = None
        self.pyaudio_instance = None
        self.stream = None
        
        # Voice detection state
        self.current_segment = None
        self.last_activity_check = 0
        self.activity_check_interval = 0.1  # Check every 100ms
        
        self.logger.info(f"🎤 AudioCapture initialisé ({config}Hz, {self.channels}ch)")

    def _calculate_chunk_size(self, config: Dict[str, Any]) -> int:
        """Calculate chunk size from configuration."""
        if 'chunk_size' in config:
            return config['chunk_size']
        
        # Calculate from chunk duration if provided
        chunk_duration_ms = config.get('chunk_duration_ms', 30)
        chunk_duration_sec = chunk_duration_ms / 1000.0
        return int(self.sample_rate * chunk_duration_sec)

    def is_voice_detected(self) -> bool:
        """
        Check if voice activity is currently detected.
        This method should be called periodically to check for voice activity.
        
        Returns:
            True if voice activity is detected
        """
        current_time = time.time()
        
        # Throttle checks to avoid excessive processing
        if current_time - self.last_activity_check < self.activity_check_interval:
            return False
        
        self.last_activity_check = current_time
        
        # If not recording, start recording to check for activity
        recording_was_started_here = False
        if not self.is_recording:
            if not self.start_recording():
                return False
            recording_was_started_here = True
        
        # Check if we have recent audio with speech
        segment = self.get_audio_segment(timeout=0.1)
        
        # If we started recording just for this check and no speech detected, stop it
        if recording_was_started_here and (not segment or not segment.has_speech):
            self.stop_recording()
        
        if segment:
            self.current_segment = segment
            return segment.has_speech
        
        return False

    def capture_audio(self) -> Optional[np.ndarray]:
        """
        Capture audio until silence is detected.
        This should be called when voice activity is detected.
        
        Returns:
            Complete audio array or None if capture failed
        """
        self.logger.info("🎤 Starting audio capture...")
        
        # Use the existing capture_until_silence method
        audio_data = self.capture_until_silence(
            max_duration=10.0,
            silence_threshold=1.0,
            speech_start_timeout=0.5  # Quick timeout since we already detected voice
        )
        
        if audio_data is not None:
            self.logger.info(f"✅ Audio captured: {len(audio_data) / self.sample_rate:.2f}s")
        else:
            self.logger.warning("⚠️ No audio captured")
        
        return audio_data

    def stop(self) -> None:
        """Stop audio capture and cleanup resources."""
        self.stop_recording()

    def list_audio_devices(self) -> Dict[int, Dict[str, Any]]:
        """Liste les périphériques audio disponibles."""
        devices = {}
        
        if not PYAUDIO_AVAILABLE:
            self.logger.error("❌ PyAudio non disponible")
            return devices
        
        try:
            audio = pyaudio.PyAudio()
            
            for i in range(audio.get_device_count()):
                device_info = audio.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:  # Périphérique d'entrée
                    devices[i] = {
                        'name': device_info['name'],
                        'channels': device_info['maxInputChannels'],
                        'sample_rate': device_info['defaultSampleRate'],
                        'index': i
                    }
            
            audio.terminate()
            self.logger.info(f"📱 {len(devices)} périphériques audio trouvés")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur listage périphériques: {e}")
        
        return devices
    
    def start_recording(self, device_index: Optional[int] = None) -> bool:
        """
        Démarre l'enregistrement audio.
        
        Args:
            device_index: Index du périphérique audio (None = défaut)
            
        Returns:
            True si l'enregistrement a démarré avec succès
        """
        if not PYAUDIO_AVAILABLE:
            self.logger.error("❌ PyAudio non disponible")
            return False
        
        if self.is_recording:
            # Ne pas logger en warning, c'est normal lors des vérifications
            self.logger.debug("🔄 Enregistrement déjà en cours")
            return True
        
        try:
            self.pyaudio_instance = pyaudio.PyAudio()
            
            # Configuration du stream
            stream_config = {
                'format': AudioFormat.FORMAT,
                'channels': self.channels,
                'rate': self.sample_rate,
                'input': True,
                'frames_per_buffer': self.chunk_size,
            }
            
            if device_index is not None:
                stream_config['input_device_index'] = device_index
            
            self.stream = self.pyaudio_instance.open(**stream_config)
            
            # Démarrer le thread d'enregistrement
            self.is_recording = True
            self.record_thread = threading.Thread(target=self._record_loop, daemon=True)
            self.record_thread.start()
            
            self.logger.debug("🔴 Enregistrement démarré")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erreur démarrage enregistrement: {e}")
            self._cleanup()
            return False
    
    def stop_recording(self) -> None:
        """Arrête l'enregistrement audio."""
        if not self.is_recording:
            return
        
        self.is_recording = False
        
        if self.record_thread:
            self.record_thread.join(timeout=2.0)
        
        self._cleanup()
        # Use debug level for frequently called operations to reduce log noise
        self.logger.debug("⏹️ Enregistrement arrêté")
    
    def _record_loop(self):
        """Boucle d'enregistrement en thread séparé."""
        while self.is_recording and self.stream:
            try:
                # Lire les données audio
                audio_data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                
                # Créer un segment audio
                timestamp = time.time()
                audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                
                # Détecter l'activité vocale
                has_speech = self.vad.is_speech(audio_data, self.sample_rate)
                
                # Calculer l'énergie
                energy = np.sqrt(np.mean(audio_array ** 2)) if len(audio_array) > 0 else 0.0
                
                segment = AudioSegment(
                    data=audio_array,
                    sample_rate=self.sample_rate,
                    timestamp=timestamp,
                    duration=len(audio_array) / self.sample_rate,
                    has_speech=has_speech,
                    energy_level=energy
                )
                
                # Ajouter à la queue
                try:
                    self.audio_queue.put(segment, timeout=0.1)
                except queue.Full:
                    # Queue pleine, ignorer ce segment
                    pass
                    
            except Exception as e:
                if self.is_recording:  # Seulement logger si on devrait encore enregistrer
                    self.logger.error(f"❌ Erreur enregistrement: {e}")
                break
    
    def _cleanup(self):
        """Nettoie les ressources audio."""
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass
            self.stream = None
        
        if self.pyaudio_instance:
            try:
                self.pyaudio_instance.terminate()
            except:
                pass
            self.pyaudio_instance = None
    
    def get_audio_segment(self, timeout: float = 1.0) -> Optional[AudioSegment]:
        """
        Récupère le prochain segment audio.
        
        Args:
            timeout: Timeout en secondes
            
        Returns:
            AudioSegment ou None si timeout
        """
        try:
            return self.audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def get_audio_chunk(self) -> Optional[bytes]:
        """
        Get the next audio chunk as bytes.
        This method is used by the voice state machine for real-time processing.
        
        Returns:
            Audio chunk as bytes or None if no audio available
        """
        segment = self.get_audio_segment(timeout=0.1)
        if segment:
            # Convert float32 array back to int16 bytes
            audio_int16 = (segment.data * 32767).astype(np.int16)
            return audio_int16.tobytes()
        return None

    def capture_until_silence(self, 
                             max_duration: float = 10.0,
                             silence_threshold: float = 1.0,
                             speech_start_timeout: float = 5.0) -> Optional[np.ndarray]:
        """
        Capture audio jusqu'à détecter un silence prolongé.
        
        Args:
            max_duration: Durée maximale d'enregistrement
            silence_threshold: Durée de silence pour arrêter
            speech_start_timeout: Timeout pour détecter le début de parole
            
        Returns:
            Array audio complet ou None si échec
        """
        if not self.start_recording():
            return None
        
        audio_segments = []
        speech_detected = False
        silence_start = None
        start_time = time.time()
        
        try:
            while True:
                current_time = time.time()
                elapsed = current_time - start_time
                
                # Timeout global
                if elapsed > max_duration:
                    self.logger.info(f"⏰ Timeout global ({max_duration}s)")
                    break
                
                # Récupérer segment audio
                segment = self.get_audio_segment(timeout=0.5)
                if not segment:
                    continue
                
                audio_segments.append(segment.data)
                
                # Détecter début de parole
                if segment.has_speech and not speech_detected:
                    speech_detected = True
                    silence_start = None
                    self.logger.debug("🗣️ Début de parole détecté")
                
                # Gérer le silence
                if speech_detected:
                    if segment.has_speech:
                        silence_start = None  # Reset du compteur de silence
                    else:
                        if silence_start is None:
                            silence_start = current_time
                        elif current_time - silence_start > silence_threshold:
                            self.logger.info(f"🔇 Silence détecté ({silence_threshold}s)")
                            break
                else:
                    # Pas encore de parole détectée
                    if elapsed > speech_start_timeout:
                        self.logger.info(f"⏰ Timeout attente parole ({speech_start_timeout}s)")
                        break
            
        finally:
            self.stop_recording()
        
        if not audio_segments:
            self.logger.warning("⚠️ Aucun audio capturé")
            return None
        
        # Concaténer tous les segments
        full_audio = np.concatenate(audio_segments)
        duration = len(full_audio) / self.sample_rate
        
        self.logger.info(f"🎵 Audio capturé: {duration:.2f}s, parole: {speech_detected}")
        
        return full_audio if speech_detected else None
    
    def test_microphone(self, duration: float = 2.0) -> Dict[str, Any]:
        """
        Teste le microphone et retourne des statistiques.
        
        Args:
            duration: Durée du test en secondes
            
        Returns:
            Dictionnaire avec les statistiques du test
        """
        self.logger.info(f"🧪 Test microphone ({duration}s)...")
        
        if not self.start_recording():
            return {'success': False, 'error': 'Impossible de démarrer l\'enregistrement'}
        
        segments = []
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                segment = self.get_audio_segment(timeout=0.5)
                if segment:
                    segments.append(segment)
        finally:
            self.stop_recording()
        
        if not segments:
            return {'success': False, 'error': 'Aucun audio capturé'}
        
        # Calculer les statistiques
        energies = [s.energy_level for s in segments]
        speech_segments = [s for s in segments if s.has_speech]
        
        stats = {
            'success': True,
            'duration': sum(s.duration for s in segments),
            'segments_count': len(segments),
            'speech_segments': len(speech_segments),
            'speech_ratio': len(speech_segments) / len(segments) if segments else 0,
            'avg_energy': np.mean(energies) if energies else 0,
            'max_energy': np.max(energies) if energies else 0,
            'min_energy': np.min(energies) if energies else 0,
        }
        
        self.logger.info(f"✅ Test terminé: {stats['speech_ratio']:.1%} parole, énergie: {stats['avg_energy']:.3f}")
        
        return stats

    def _detect_voice_activity(self, audio_data: bytes) -> 'VoiceActivityMetrics':
        """
        Detect voice activity in audio chunk and return detailed metrics.
        This method is used by the voice state machine for advanced voice detection.
        
        Args:
            audio_data: Audio chunk as bytes
            
        Returns:
            VoiceActivityMetrics with detection results
        """
        from peer.interfaces.sui.domain.models import VoiceActivityMetrics
        
        if not audio_data:
            return VoiceActivityMetrics(
                speech_detected=False,
                energy_level=0.0,
                speech_probability=0.0
            )
        
        try:
            # Basic speech detection using VAD
            speech_detected = self.vad.is_speech(audio_data, self.sample_rate)
            
            # Calculate energy level
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            energy_level = float(np.sqrt(np.mean(audio_array ** 2)))
            
            # Calculate speech probability based on energy and VAD result
            energy_prob = min(1.0, energy_level / 0.1)  # Normalize to reasonable range
            speech_probability = 0.8 * float(speech_detected) + 0.2 * energy_prob
            
            return VoiceActivityMetrics(
                speech_detected=speech_detected,
                energy_level=energy_level,
                speech_probability=speech_probability
            )
            
        except Exception as e:
            self.logger.debug(f"Erreur détection activité vocale: {e}")
            return VoiceActivityMetrics(
                speech_detected=False,
                energy_level=0.0,
                speech_probability=0.0
            )

    def __del__(self):
        """Nettoie les ressources à la suppression de l'objet."""
        if hasattr(self, 'is_recording') and self.is_recording:
            self.stop_recording()
