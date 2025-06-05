#!/usr/bin/env python3
"""
Script de debug simple pour tester la capture audio.
"""

import os
import sys
import time
import logging

# Configuration simple des logs
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

try:
    import pyaudio
    print("✅ PyAudio disponible")
except ImportError:
    print("❌ PyAudio non disponible")
    sys.exit(1)

try:
    import webrtcvad
    print("✅ WebRTC VAD disponible")
except ImportError:
    print("❌ WebRTC VAD non disponible")
    sys.exit(1)

try:
    import numpy as np
    print("✅ NumPy disponible")
except ImportError:
    print("❌ NumPy non disponible")
    sys.exit(1)

def test_basic_audio():
    """Test de base de PyAudio."""
    print("\n🎤 Test de base PyAudio...")
    
    pa = pyaudio.PyAudio()
    
    # Lister les périphériques
    print("\n📋 Périphériques audio disponibles:")
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:
            print(f"  {i}: {info['name']} (channels: {info['maxInputChannels']})")
    
    # Test d'enregistrement basique
    sample_rate = 16000
    chunk_size = 1024
    duration = 3
    
    print(f"\n🔴 Enregistrement de {duration} secondes...")
    
    stream = pa.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=sample_rate,
        input=True,
        frames_per_buffer=chunk_size
    )
    
    frames = []
    for _ in range(int(sample_rate / chunk_size * duration)):
        data = stream.read(chunk_size, exception_on_overflow=False)
        frames.append(data)
        
        # Analyser le niveau audio
        audio_np = np.frombuffer(data, dtype=np.int16)
        level = np.abs(audio_np).mean()
        if level > 500:
            print(f"🔊 Signal détecté: {level}")
    
    stream.stop_stream()
    stream.close()
    pa.terminate()
    
    print("✅ Test PyAudio terminé")

def test_vad():
    """Test de VAD simple."""
    print("\n🎙️ Test WebRTC VAD...")
    
    vad = webrtcvad.Vad(2)  # Mode agressif
    
    # Test avec audio vide
    silent_frame = b'\x00' * 320  # 320 bytes = 20ms à 16kHz
    result = vad.is_speech(silent_frame, 16000)
    print(f"Silence détecté comme parole: {result}")
    
    print("✅ Test VAD terminé")

if __name__ == "__main__":
    print("🚀 Tests de diagnostic audio")
    
    try:
        test_basic_audio()
        test_vad()
        print("\n✅ Tous les tests passés avec succès!")
    except Exception as e:
        print(f"\n❌ Erreur lors des tests: {e}")
        import traceback
        traceback.print_exc()
