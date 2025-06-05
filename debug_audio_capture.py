#!/usr/bin/env python3
"""
Script de débogage pour tester la capture audio et la détection d'activité vocale.
"""

import os
import sys
import time
import logging

# Configuration
logging.basicConfig(level=logging.DEBUG)

# Ajouter le chemin source
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, 'src'))
sys.path.insert(0, current_dir)

from peer.interfaces.sui.stt.audio_io import AudioCapture, VoiceActivityDetector, VADMode, AudioFormat

def test_audio_capture():
    """Test simple de la capture audio."""
    print("🧪 Test de capture audio...")
    
    # Configuration audio
    audio_config = {
        'sample_rate': AudioFormat.SAMPLE_RATE,
        'channels': AudioFormat.CHANNELS,
        'chunk_size': AudioFormat.CHUNK_SIZE,
        'vad_sensitivity': 2
    }
    
    try:
        # Initialiser la capture
        audio_capture = AudioCapture(audio_config)
        print("✅ AudioCapture initialisé")
        
        # Lister les périphériques
        devices = audio_capture.list_audio_devices()
        print(f"📱 Périphériques audio trouvés: {len(devices)}")
        for idx, device in devices.items():
            print(f"  {idx}: {device['name']}")
        
        # Test du microphone
        print("\n🎤 Test du microphone (3 secondes)...")
        mic_test = audio_capture.test_microphone(duration=3.0)
        print(f"📊 Résultats du test: {mic_test}")
        
        # Test de capture en temps réel
        print("\n🎙️ Test de capture en temps réel (10 secondes)...")
        print("Parlez maintenant pour tester la détection...")
        
        if not audio_capture.start_recording():
            print("❌ Impossible de démarrer l'enregistrement")
            return
        
        segments_received = 0
        speech_segments = 0
        start_time = time.time()
        
        while time.time() - start_time < 10.0:
            segment = audio_capture.get_audio_segment(timeout=0.5)
            if segment:
                segments_received += 1
                if segment.has_speech:
                    speech_segments += 1
                    print(f"🗣️ Parole détectée! Énergie: {segment.energy_level:.3f}")
                else:
                    print(f"🔇 Silence. Énergie: {segment.energy_level:.3f}")
            else:
                print("⏱️ Timeout - aucun segment reçu")
        
        audio_capture.stop_recording()
        
        print(f"\n📈 Résultats:")
        print(f"   Segments totaux: {segments_received}")
        print(f"   Segments avec parole: {speech_segments}")
        print(f"   Ratio parole: {speech_segments/segments_received*100:.1f}%" if segments_received > 0 else "   Aucun segment reçu")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_audio_capture()
