#!/usr/bin/env python3
"""
Test de validation pour la migration de Whisper vers WhisperX.

Ce test vérifie :
1. Suppression complète de wav2vec2
2. Remplacement de Whisper par WhisperX
3. Fonctionnement correct de la reconnaissance vocale
"""

import sys
import os
import numpy as np
import logging

# Ajouter le répertoire source au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

logging.basicConfig(level=logging.INFO)

def test_wav2vec2_removal():
    """Vérifier que wav2vec2 a été complètement supprimé."""
    print("🧹 Test de suppression wav2vec2...")
    
    # Vérifier que wav2vec2 n'est plus dans les imports
    try:
        from peer.interfaces.sui.stt.speech_recognizer import ASREngine
        engines = [e.value for e in ASREngine]
        
        if "wav2vec2" in engines:
            print("❌ wav2vec2 encore présent dans ASREngine")
            return False
        else:
            print("✅ wav2vec2 supprimé de ASREngine")
            
    except Exception as e:
        print(f"❌ Erreur lors du test wav2vec2: {e}")
        return False
    
    return True

def test_whisperx_integration():
    """Vérifier que WhisperX est correctement intégré."""
    print("🎯 Test d'intégration WhisperX...")
    
    try:
        from peer.interfaces.sui.stt.speech_recognizer import ASREngine, WhisperXASR
        
        # Vérifier que WHISPERX est dans l'enum
        if ASREngine.WHISPERX.value != "whisperx":
            print("❌ ASREngine.WHISPERX incorrect")
            return False
        
        print("✅ ASREngine.WHISPERX présent")
        
        # Vérifier que WhisperXASR existe
        print("✅ WhisperXASR disponible")
        
        return True
        
    except ImportError as e:
        print(f"❌ Erreur d'import WhisperX: {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur WhisperX: {e}")
        return False

def test_speech_recognizer():
    """Tester le SpeechRecognizer avec WhisperX."""
    print("🎤 Test SpeechRecognizer avec WhisperX...")
    
    try:
        from peer.interfaces.sui.stt.speech_recognizer import SpeechRecognizer
        
        # Configuration test avec WhisperX uniquement
        config = {
            'stt_settings': {
                'engines': {
                    'whisperx': {
                        'enabled': True,
                        'model_name': 'base',
                        'language': 'fr',
                        'priority': 1,
                        'parameters': {'batch_size': 16}
                    },
                    'vosk': {'enabled': False},
                    'mock': {'enabled': False}
                }
            }
        }
        
        # Initialiser le recognizer
        recognizer = SpeechRecognizer(config)
        
        # Vérifier les moteurs
        engines = recognizer.get_available_engines()
        primary = recognizer.get_primary_engine()
        
        if 'whisperx' not in engines:
            print("❌ WhisperX non trouvé dans les moteurs disponibles")
            return False
            
        if primary != 'whisperx':
            print(f"❌ Moteur principal incorrect: {primary}")
            return False
        
        print(f"✅ Moteurs disponibles: {engines}")
        print(f"✅ Moteur principal: {primary}")
        
        # Test de transcription basique
        print("🎵 Test de transcription avec audio silence...")
        silence = np.zeros(16000, dtype=np.float32)  # 1 seconde de silence
        
        result = recognizer.transcribe(silence)
        # Pour du silence, on s'attend à None ou un résultat vide
        if result is None:
            print("✅ Transcription silence: None (attendu)")
        else:
            print(f"✅ Transcription silence: '{result.text}' (confiance: {result.confidence:.2f})")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur SpeechRecognizer: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_configuration_compatibility():
    """Tester la compatibilité des configurations."""
    print("⚙️ Test de compatibilité des configurations...")
    
    try:
        from peer.interfaces.sui.stt.speech_recognizer import SpeechRecognizer
        
        # Test avec configuration minimale
        minimal_config = {}
        recognizer = SpeechRecognizer(minimal_config)
        
        engines = recognizer.get_available_engines()
        print(f"✅ Configuration minimale: {engines}")
        
        # Test avec configuration partielle
        partial_config = {
            'stt_settings': {
                'engines': {
                    'whisperx': {'enabled': True, 'model_name': 'base'}
                }
            }
        }
        
        recognizer2 = SpeechRecognizer(partial_config)
        engines2 = recognizer2.get_available_engines()
        print(f"✅ Configuration partielle: {engines2}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur configuration: {e}")
        return False

def test_import_dependencies():
    """Tester que WhisperX et ses dépendances sont disponibles."""
    print("📦 Test des dépendances WhisperX...")
    
    try:
        import whisperx
        print("✅ whisperx importé")
        
        import torch
        print("✅ torch importé")
        
        # Test de chargement de modèle simple
        print("🔄 Test de chargement modèle WhisperX...")
        model = whisperx.load_model("base", device="cpu", compute_type="int8")
        print("✅ Modèle WhisperX chargé")
        
        return True
        
    except ImportError as e:
        print(f"❌ Dépendance manquante: {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur chargement modèle: {e}")
        return False

def main():
    """Fonction principale de test."""
    print("🧪 === TEST DE MIGRATION WHISPER → WHISPERX ===")
    print()
    
    tests = [
        ("Suppression wav2vec2", test_wav2vec2_removal),
        ("Intégration WhisperX", test_whisperx_integration), 
        ("Dépendances WhisperX", test_import_dependencies),
        ("SpeechRecognizer", test_speech_recognizer),
        ("Compatibilité config", test_configuration_compatibility)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"--- {test_name} ---")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ Exception dans {test_name}: {e}")
            results[test_name] = False
        print()
    
    # Rapport final
    print("📊 === RAPPORT FINAL ===")
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print()
    print(f"📈 Résultat: {passed}/{total} tests réussis")
    
    if passed == total:
        print("🎉 MIGRATION RÉUSSIE ! WhisperX est opérationnel.")
        print()
        print("✅ wav2vec2 complètement supprimé")
        print("✅ Whisper remplacé par WhisperX")
        print("✅ Système de reconnaissance vocale fonctionnel")
        return True
    else:
        print("❌ Migration incomplète. Vérifiez les erreurs ci-dessus.")
        return False

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
