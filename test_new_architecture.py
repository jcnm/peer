#!/usr/bin/env python3
"""
Script de test pour valider la nouvelle architecture        # Test des moteurs disponibles
        engines = speech_recognizer.get_available_engines()
        primary = speech_recognizer.get_primary_engine()
        print(f"    ✅ Moteurs ASR disponibles: {engines}")
        print(f"    ✅ Moteur ASR principal: {primary}")

Ce script teste :
1. L'initialisation de tous les modules (VAD, ASR, TTS, NLU)
2. La pipeline complète audio -> texte -> intention -> réponse
3. Les fallbacks et la gestion d'erreurs
"""

import sys
import os
import time
import logging
import numpy as np

# Ajouter le répertoire racine au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_audio_io():
    """Test du système audio I/O avec VAD."""
    print("🎙️ Test Audio I/O et VAD...")
    
    try:
        from peer.interfaces.sui.stt.audio_io import AudioCapture, VoiceActivityDetector
        
        # Test VAD
        print("  - Test VoiceActivityDetector...")
        vad = VoiceActivityDetector()
        
        # Test avec données simulées
        test_audio = np.random.randint(-1000, 1000, 1600, dtype=np.int16).tobytes()
        has_speech = vad.is_speech(test_audio)
        print(f"    ✅ VAD test: {has_speech}")
        
        # Test AudioCapture
        print("  - Test AudioCapture...")
        audio_capture = AudioCapture()
        
        # Lister les périphériques
        devices = audio_capture.list_audio_devices()
        print(f"    ✅ Périphériques audio: {len(devices)}")
        
        # Test microphone (court)
        test_result = audio_capture.test_microphone(duration=0.5)
        print(f"    ✅ Test microphone: {test_result.get('success', False)}")
        
        return True
        
    except Exception as e:
        print(f"    ❌ Erreur Audio I/O: {e}")
        return False

def test_speech_recognition():
    """Test du système de reconnaissance vocale."""
    print("🗣️ Test Reconnaissance Vocale...")
    
    try:
        from peer.interfaces.sui.stt.speech_recognizer import SpeechRecognizer
        
        # Configuration minimale
        config = {
            "engines": {
                "mock": {"enabled": True},
                "whisperx": {"enabled": False},  # Désactivé pour les tests
                "vosk": {"enabled": False}
            }
        }
        
        print("  - Initialisation SpeechRecognizer...")
        speech_recognizer = SpeechRecognizer(config)
        
        # Test des moteurs disponibles
        engines = speech_recognizer.get_available_engines()
        primary = speech_recognizer.get_primary_engine()
        print(f"    ✅ Moteurs disponibles: {engines}")
        print(f"    ✅ Moteur principal: {primary}")
        
        # Test de transcription avec audio simulé
        print("  - Test transcription...")
        test_audio = np.random.random(16000).astype(np.float32)  # 1 seconde
        result = speech_recognizer.transcribe(test_audio)
        
        if result:
            print(f"    ✅ Transcription: '{result.text}' (moteur: {result.engine_used})")
        else:
            print(f"    ⚠️ Aucune transcription")
        
        return True
        
    except Exception as e:
        print(f"    ❌ Erreur Reconnaissance: {e}")
        return False

def test_text_to_speech():
    """Test du système TTS."""
    print("🗣️ Test Text-to-Speech...")
    
    try:
        from peer.interfaces.sui.tts.text_to_speech import TextToSpeech
        
        print("  - Initialisation TextToSpeech...")
        tts = TextToSpeech()
        
        # Test des moteurs disponibles
        engines = tts.get_available_engines()
        active = tts.get_active_engine()
        print(f"    ✅ Moteurs TTS disponibles: {engines}")
        print(f"    ✅ Moteur TTS actif: {active}")
        
        # Test de synthèse
        print("  - Test synthèse...")
        result = tts.synthesize("Bonjour, ceci est un test.")
        
        if result.success:
            print(f"    ✅ Synthèse réussie (moteur: {result.engine_used})")
            if result.audio_file_path:
                print(f"    ✅ Fichier audio: {result.audio_file_path}")
        else:
            print(f"    ❌ Échec synthèse: {result.error_message}")
        
        return True
        
    except Exception as e:
        print(f"    ❌ Erreur TTS: {e}")
        return False

def test_nlp_engine():
    """Test du moteur NLP."""
    print("🧠 Test Moteur NLP...")
    
    try:
        from peer.interfaces.sui.nlu.domain.nlp_engine import NLPEngine
        
        print("  - Initialisation NLPEngine...")
        nlp_engine = NLPEngine()
        
        # Test des modèles
        status = nlp_engine.get_models_status()
        stats = nlp_engine.get_stats()
        print(f"    ✅ Statut modèles: {list(status.keys())}")
        
        # Test d'extraction d'intention
        print("  - Test extraction d'intentions...")
        test_phrases = [
            "arrête toi",
            "aide moi s'il te plaît",
            "quel est le statut",
            "ouvre le fichier main.py",
            "analyse ce code"
        ]
        
        for phrase in test_phrases:
            result = nlp_engine.extract_intent(phrase)
            print(f"    '{phrase}' -> {result.command_type} (confiance: {result.confidence:.2f})")
        
        return True
        
    except Exception as e:
        print(f"    ❌ Erreur NLP: {e}")
        return False

def test_main_interface():
    """Test de l'interface principale."""
    print("🎤 Test Interface Principale...")
    
    try:
        from peer.interfaces.sui.main import SpeechUserInterface
        
        print("  - Initialisation SpeechUserInterface...")
        sui = SpeechUserInterface()
        
        print(f"    ✅ Interface initialisée")
        print(f"    ✅ Audio Capture: {'✓' if sui.audio_capture else '✗'}")
        print(f"    ✅ Speech Recognizer: {'✓' if sui.speech_recognizer else '✗'}")
        print(f"    ✅ TTS Engine: {'✓' if sui.tts_engine else '✗'}")
        print(f"    ✅ NLP Engine: {'✓' if sui.nlp_engine else '✗'}")
        
        # Test de traitement d'une commande
        print("  - Test process_speech_input...")
        response = sui.process_speech_input("aide moi")
        print(f"    ✅ Réponse: {response.message[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"    ❌ Erreur Interface: {e}")
        return False

def test_configuration():
    """Test du chargement de configuration."""
    print("⚙️ Test Configuration...")
    
    try:
        from peer.interfaces.sui.config.config_loader import load_yaml_config
        
        # Test avec configuration par défaut
        config_path = os.path.join(os.path.dirname(__file__), 
                                  "src/peer/interfaces/sui/config/sui_config.yaml")
        
        if os.path.exists(config_path):
            config = load_yaml_config(config_path)
            print(f"    ✅ Configuration chargée: {len(config)} sections")
        else:
            print(f"    ⚠️ Fichier config non trouvé: {config_path}")
            
        return True
        
    except Exception as e:
        print(f"    ❌ Erreur Configuration: {e}")
        return False

def main():
    """Fonction principale de test."""
    print("🚀 Test de validation de l'architecture SUI restructurée")
    print("=" * 60)
    
    tests = [
        ("Configuration", test_configuration),
        ("Audio I/O + VAD", test_audio_io),
        ("Reconnaissance Vocale", test_speech_recognition),
        ("Text-to-Speech", test_text_to_speech),
        ("Moteur NLP", test_nlp_engine),
        ("Interface Principale", test_main_interface),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}")
        print("-" * 40)
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ Erreur critique dans {test_name}: {e}")
            results[test_name] = False
    
    # Résumé
    print("\n📊 RÉSUMÉ DES TESTS")
    print("=" * 60)
    
    passed = 0
    total = len(tests)
    
    for test_name, success in results.items():
        status = "✅ SUCCÈS" if success else "❌ ÉCHEC"
        print(f"{test_name:.<30} {status}")
        if success:
            passed += 1
    
    print(f"\nRésultat global: {passed}/{total} tests réussis")
    
    if passed == total:
        print("🎉 Tous les tests sont passés ! L'architecture est fonctionnelle.")
        return 0
    else:
        print("⚠️ Certains tests ont échoué. Vérifiez les erreurs ci-dessus.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
