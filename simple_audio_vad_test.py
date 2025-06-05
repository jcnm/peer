#!/usr/bin/env python3
"""
Script simple de diagnostic audio avec VAD.
"""
import os
import sys
import time
import pyaudio
import webrtcvad
import numpy as np
import queue
import threading
import logging
from enum import Enum

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SimpleAudioTest")

class VADMode(Enum):
    """Modes de sensibilité pour la détection d'activité vocale."""
    QUALITY = 0      # Qualité (moins sensible)
    LOW_BITRATE = 1  # Bas débit (sensibilité moyenne)
    AGGRESSIVE = 2   # Agressif (sensibilité élevée)
    VERY_AGGRESSIVE = 3  # Très agressif (très sensible)

class VoiceActivityDetector:
    """Détecteur d'activité vocale utilisant WebRTC VAD."""
    
    def __init__(self, mode=VADMode.AGGRESSIVE, sample_rate=16000):
        """
        Initialize le détecteur d'activité vocale.
        
        Args:
            mode: Mode de sensibilité VAD
            sample_rate: Taux d'échantillonnage (16kHz, 32kHz ou 48kHz)
        """
        self.logger = logging.getLogger("VAD")
        
        # Valider le sample rate
        if sample_rate not in [8000, 16000, 32000, 48000]:
            self.logger.warning(f"⚠️ Sample rate {sample_rate} non supporté par WebRTC VAD, utilisation de 16000Hz")
            sample_rate = 16000
        
        # Valider le mode VAD
        if isinstance(mode, VADMode):
            mode_value = mode.value
        else:
            mode_value = int(mode)
            if mode_value not in [0, 1, 2, 3]:
                self.logger.warning(f"⚠️ Mode VAD {mode} invalide, utilisation du mode AGGRESSIVE (2)")
                mode_value = 2
        
        # Initialiser le VAD
        self.vad = webrtcvad.Vad(mode_value)
        self.sample_rate = sample_rate
        self.logger.debug(f"✅ VAD initialisé (mode={mode_value}, sample_rate={sample_rate}Hz)")
    
    def is_speech(self, audio_frame, sample_rate=None) -> bool:
        """
        Détecte si un frame audio contient de la parole.
        
        Args:
            audio_frame: Frame audio (bytes)
            sample_rate: Taux d'échantillonnage optionnel
            
        Returns:
            True si de la parole est détectée
        """
        if sample_rate is None:
            sample_rate = self.sample_rate
        
        try:
            return self.vad.is_speech(audio_frame, sample_rate)
        except Exception as e:
            self.logger.error(f"❌ Erreur VAD: {e}")
            return False

def test_simple_audio_vad():
    """Test simple d'audio avec VAD."""
    logger.info("🎤 Test simple d'audio avec VAD")
    
    # Configuration audio
    SAMPLE_RATE = 16000
    CHANNELS = 1
    CHUNK_SIZE = 480  # 30ms à 16kHz
    FORMAT = pyaudio.paInt16
    
    # Initialiser le VAD
    vad = VoiceActivityDetector(mode=VADMode.AGGRESSIVE, sample_rate=SAMPLE_RATE)
    
    # Initialiser PyAudio
    p = pyaudio.PyAudio()
    
    # Afficher les périphériques
    logger.info("📋 Périphériques audio disponibles:")
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info.get('maxInputChannels', 0) > 0:
            logger.info(f"  {i}: {info.get('name')} (canaux: {info.get('maxInputChannels')})")
    
    # Ouvrir le stream
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK_SIZE
    )
    
    logger.info("🔴 Enregistrement démarré. Parlez dans le micro...")
    logger.info("⌨️ Appuyez sur Ctrl+C pour arrêter")
    
    stats = {
        'total_frames': 0,
        'speech_frames': 0,
        'last_stats_time': time.time()
    }
    
    try:
        while True:
            # Lire un chunk audio
            audio_data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
            
            # Analyser avec VAD
            has_speech = vad.is_speech(audio_data, SAMPLE_RATE)
            
            # Calculer le niveau d'énergie
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            energy = np.sqrt(np.mean(audio_array.astype(np.float64) ** 2))
            
            # Mettre à jour les statistiques
            stats['total_frames'] += 1
            if has_speech:
                stats['speech_frames'] += 1
                logger.info(f"🗣️ Parole détectée! Énergie: {energy:.2f}")
            
            # Afficher périodiquement les statistiques
            now = time.time()
            if now - stats['last_stats_time'] > 2.0:
                speech_ratio = (stats['speech_frames'] / stats['total_frames']) if stats['total_frames'] > 0 else 0
                logger.info(f"📊 Frames: {stats['total_frames']}, avec parole: {stats['speech_frames']} ({speech_ratio:.1%})")
                stats['last_stats_time'] = now
            
            # Pause courte
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        logger.info("🛑 Test interrompu par l'utilisateur")
    finally:
        # Nettoyage
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        # Afficher les statistiques finales
        if stats['total_frames'] > 0:
            speech_ratio = stats['speech_frames'] / stats['total_frames']
            logger.info(f"📊 STATISTIQUES FINALES:")
            logger.info(f"   Frames totaux: {stats['total_frames']}")
            logger.info(f"   Frames avec parole: {stats['speech_frames']} ({speech_ratio:.1%})")
        else:
            logger.warning("⚠️ Aucun frame audio n'a été capturé")
    
    logger.info("✅ Test terminé")

if __name__ == "__main__":
    try:
        logger.info("🚀 Démarrage du test audio simple avec VAD")
        test_simple_audio_vad()
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
