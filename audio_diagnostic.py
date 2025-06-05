#!/usr/bin/env python3
"""
Script de diagnostic pour l'audio avec VAD et traitement des segments.
"""
import os
import sys
import time
import threading
import logging
import queue
import numpy as np

# Configuration du logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("AudioDiagnostic")

# Ajouter le chemin source pour l'importation
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, 'src'))
sys.path.insert(0, current_dir)

try:
    from peer.interfaces.sui.stt.audio_io import AudioCapture, AudioFormat, VADMode
    logger.info("✅ Modules audio importés avec succès")
except ImportError as e:
    logger.error(f"❌ Erreur d'importation: {e}")
    sys.exit(1)

def test_audio_capture_vad():
    """Test complet de capture et VAD."""
    logger.info("🎤 Test de la capture audio avec VAD")
    
    # Configuration audio
    audio_config = {
        'sample_rate': AudioFormat.SAMPLE_RATE,
        'channels': AudioFormat.CHANNELS,
        'chunk_size': AudioFormat.CHUNK_SIZE,
        'vad_sensitivity': 2  # Mode AGGRESSIVE
    }
    
    # Créer et démarrer la capture
    audio_capture = AudioCapture(audio_config)
    
    # Tenter d'afficher les périphériques disponibles
    try:
        devices = audio_capture.list_audio_devices()
        logger.info(f"📋 Périphériques audio ({len(devices)}):")
        for idx, device in devices.items():
            logger.info(f"  {idx}: {device['name']} (canaux: {device.get('max_input_channels', 'N/A')})")
    except Exception as e:
        logger.warning(f"⚠️ Impossible de lister les périphériques: {e}")
    
    logger.info("🔄 Démarrage du test de capture...")
    
    # Test initial du microphone
    mic_stats = audio_capture.test_microphone(duration=3.0)
    logger.info(f"📊 Statistiques micro: {mic_stats}")
    
    if not mic_stats['success'] or mic_stats['avg_energy'] < 0.001:
        logger.error("❌ Test du microphone échoué - Niveau audio trop faible")
        return
    
    # Démarrer l'enregistrement
    logger.info("🔴 Démarrage de l'enregistrement...")
    if not audio_capture.start_recording():
        logger.error("❌ Impossible de démarrer l'enregistrement")
        return
    
    # File d'attente pour stocker les données audio
    segments_queue = queue.Queue()
    stats = {
        'total_segments': 0,
        'speech_segments': 0,
    }
    
    # Thread pour traiter les segments
    def process_segments():
        last_stats_time = time.time()
        
        logger.info("🎧 En attente de segments audio...")
        try:
            while True:
                # Récupérer un segment
                segment = audio_capture.get_audio_segment(timeout=1.0)
                if segment is None:
                    continue
                
                # Mettre à jour les statistiques
                stats['total_segments'] += 1
                if segment.has_speech:
                    stats['speech_segments'] += 1
                
                # Mettre en queue pour analyse
                segments_queue.put(segment)
                
                # Afficher périodiquement les statistiques
                now = time.time()
                if now - last_stats_time > 2.0:
                    speech_ratio = (stats['speech_segments'] / stats['total_segments']) if stats['total_segments'] > 0 else 0
                    logger.info(f"📊 Segments: {stats['total_segments']}, avec parole: {stats['speech_segments']} ({speech_ratio:.1%})")
                    last_stats_time = now
                
        except KeyboardInterrupt:
            logger.info("🛑 Arrêt demandé")
        except Exception as e:
            logger.error(f"❌ Erreur: {e}")
    
    # Démarrer le thread de traitement
    thread = threading.Thread(target=process_segments, daemon=True)
    thread.start()
    
    logger.info("🗣️ Veuillez parler pour tester la détection de parole...")
    logger.info("⌨️ Appuyez sur Ctrl+C pour arrêter le test")
    
    try:
        # Laisser le test s'exécuter
        thread.join()
    except KeyboardInterrupt:
        logger.info("🛑 Test interrompu par l'utilisateur")
    finally:
        # Arrêter l'enregistrement
        audio_capture.stop_recording()
        
        # Afficher les statistiques finales
        if stats['total_segments'] > 0:
            speech_ratio = stats['speech_segments'] / stats['total_segments']
            logger.info(f"📊 STATISTIQUES FINALES:")
            logger.info(f"   Segments totaux: {stats['total_segments']}")
            logger.info(f"   Segments avec parole: {stats['speech_segments']} ({speech_ratio:.1%})")
        else:
            logger.warning("⚠️ Aucun segment audio n'a été capturé")
    
    logger.info("✅ Test terminé")

if __name__ == "__main__":
    try:
        logger.info("🚀 Démarrage des tests de diagnostic audio")
        test_audio_capture_vad()
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
