#!/usr/bin/env python3
"""
Test de validation de l'interface vocale temps réel avec WhisperX.

Ce script teste :
- L'importation de tous les modules
- L'initialisation des composants
- La fonctionnalité de base du gestionnaire de parole continue
"""

import os
import sys
import time
import numpy as np
import tempfile
import subprocess

# Ajouter le chemin source
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test l'importation de tous les modules nécessaires."""
    print("📦 Test des importations...")
    
    try:
        from peer.interfaces.sui.stt.speech_recognizer import SpeechRecognizer
        print("✅ SpeechRecognizer importé")
        
        from peer.interfaces.sui.stt.audio_io import AudioCapture, VoiceActivityDetector
        print("✅ AudioCapture et VAD importés")
        
        from peer.interfaces.sui.stt.continuous_speech_manager import ContinuousSpeechManager
        print("✅ ContinuousSpeechManager importé")
        
        from peer.interfaces.sui.tts.simple_tts_engine import SimpleTTS
        print("✅ SimpleTTS importé")
        
        return True
        
    except ImportError as e:
        print(f"❌ Erreur d'importation: {e}")
        return False

def test_speech_recognizer():
    """Test l'initialisation du speech recognizer."""
    print("\n🎙️ Test du speech recognizer...")
    
    try:
        from peer.interfaces.sui.stt.speech_recognizer import SpeechRecognizer
        
        # Configuration test
        config = {
            'stt_settings': {
                'engines': {
                    'whisperx': {
                        'enabled': True,
                        'model_name': 'base',
                        'language': 'fr',
                        'priority': 1,
                        'parameters': {
                            'batch_size': 8,
                            'task': 'transcribe'
                        }
                    }
                }
            }
        }
        
        recognizer = SpeechRecognizer(config)
        print("✅ SpeechRecognizer initialisé")
        
        # Test avec audio synthétique
        sample_rate = 16000
        duration = 1.0  # 1 seconde
        audio_data = np.random.random(int(sample_rate * duration)).astype(np.float32) * 0.1
        
        result = recognizer.transcribe(audio_data)
        print(f"✅ Transcription test effectuée (résultat: {result is not None})")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur speech recognizer: {e}")
        return False

def test_continuous_speech_manager():
    """Test le gestionnaire de parole continue."""
    print("\n🔄 Test du gestionnaire de parole continue...")
    
    try:
        from peer.interfaces.sui.stt.speech_recognizer import SpeechRecognizer
        from peer.interfaces.sui.stt.continuous_speech_manager import ContinuousSpeechManager
        
        # Configuration test
        config = {
            'stt_settings': {
                'engines': {
                    'whisperx': {
                        'enabled': True,
                        'model_name': 'base',
                        'language': 'fr',
                        'priority': 1
                    }
                }
            }
        }
        
        recognizer = SpeechRecognizer(config)
        
        # Callback test
        transcriptions_received = []
        def test_callback(text, is_final):
            transcriptions_received.append((text, is_final))
            print(f"📝 Transcription reçue: '{text}' (final: {is_final})")
        
        # Créer le gestionnaire
        manager = ContinuousSpeechManager(
            speech_recognizer=recognizer,
            pause_threshold=0.5,  # Plus court pour test
            transcription_callback=test_callback
        )
        
        print("✅ ContinuousSpeechManager créé")
        
        # Démarrer le gestionnaire
        manager.start()
        print("✅ Gestionnaire démarré")
        
        # Simuler quelques segments audio
        for i in range(3):
            audio_data = np.random.random(8000).astype(np.float32) * 0.1  # 0.5s d'audio
            manager.add_audio_segment(audio_data, has_speech=True)
            time.sleep(0.1)
        
        # Attendre un peu pour le traitement
        time.sleep(2)
        
        # Arrêter le gestionnaire
        manager.stop()
        print("✅ Gestionnaire arrêté")
        
        # Vérifier les stats
        stats = manager.get_stats()
        print(f"📊 Stats: {stats['segments_processed']} segments traités")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur gestionnaire: {e}")
        return False

def test_tts_engine():
    """Test le moteur TTS."""
    print("\n🔊 Test du moteur TTS...")
    
    try:
        from peer.interfaces.sui.tts.simple_tts_engine import SimpleTTS
        from peer.interfaces.sui.tts.base import TTSConfig, TTSEngineType
        
        tts_config = TTSConfig(
            engine_type=TTSEngineType.SIMPLE,
            language='fr',
            voice='Audrey (Premium)'
        )
        tts = SimpleTTS(tts_config)
        print("✅ SimpleTTS initialisé")
        
        # Test de synthèse (sans jouer le son)
        test_text = "Ceci est un test de synthèse vocale française."
        print(f"🗣️ Test synthèse: '{test_text}'")
        
        # Note: On ne fait pas synthesize() ici pour éviter le son pendant les tests
        print("✅ TTS prêt pour la synthèse")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur TTS: {e}")
        return False

def test_audio_generation():
    """Test la génération d'audio français pour validation."""
    print("\n🎵 Test génération audio français...")
    
    try:
        # Générer un échantillon audio français avec say
        test_text = "Bonjour, test de reconnaissance vocale française."
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_file = f.name
        
        # Utiliser say pour générer l'audio
        cmd = [
            'say', '-v', 'Audrey (Premium)', '-o', temp_file, 
            '--file-format=WAVE', '--data-format=LEI16@16000', 
            test_text
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(temp_file):
            file_size = os.path.getsize(temp_file)
            print(f"✅ Audio généré: {file_size} bytes")
            
            # Nettoyer
            os.unlink(temp_file)
            return True
        else:
            print(f"❌ Échec génération audio: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur génération audio: {e}")
        return False

def main():
    """Test principal."""
    print("🚀 VALIDATION DE L'INTERFACE VOCALE TEMPS RÉEL WHISPERX")
    print("=" * 60)
    
    tests = [
        ("Importations", test_imports),
        ("Speech Recognizer", test_speech_recognizer),
        ("Gestionnaire Parole Continue", test_continuous_speech_manager),
        ("Moteur TTS", test_tts_engine),
        ("Génération Audio", test_audio_generation)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 TEST: {test_name}")
        print("-" * 40)
        
        try:
            success = test_func()
            results.append((test_name, success))
            
            if success:
                print(f"✅ {test_name}: RÉUSSI")
            else:
                print(f"❌ {test_name}: ÉCHEC")
                
        except Exception as e:
            print(f"💥 {test_name}: ERREUR - {e}")
            results.append((test_name, False))
    
    # Rapport final
    print("\n" + "=" * 60)
    print("📊 RAPPORT FINAL DE VALIDATION")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ RÉUSSI" if success else "❌ ÉCHEC"
        print(f"{test_name:.<40} {status}")
    
    print("-" * 60)
    print(f"Score final: {passed}/{total} tests réussis ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 VALIDATION COMPLÈTE RÉUSSIE!")
        print("✅ L'interface vocale temps réel est prête à être utilisée.")
        print("\n🚀 Pour lancer l'interface:")
        print("   ./run_realtime_voice.sh")
    else:
        print(f"\n⚠️ {total-passed} test(s) ont échoué.")
        print("🔧 Vérifiez l'installation et les dépendances.")
    
    return passed == total

if __name__ == "__main__":
    main()
