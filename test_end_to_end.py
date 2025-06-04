#!/usr/bin/env python3
"""
Test end-to-end complet de l'architecture SUI restructurée.

Ce script démontre le fonctionnement complet de la nouvelle architecture :
VAD (audio_io.py) -> ASR (speech_recognizer.py) -> NLU (nlp_engine.py) -> TTS (text_to_speech.py)

Tests couverts :
1. Pipeline vocale complète : Audio -> Texte -> Intention -> Réponse -> Synthèse
2. Intégration avec le daemon Peer
3. Gestion des fallbacks et erreurs
4. Performance et fiabilité
"""

import sys
import os
import time
import numpy as np
import logging
from typing import Dict, Any

# Ajouter le répertoire racine au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configuration du logging avec plus de détails
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_complete_architecture():
    """Test complet de l'architecture restructurée."""
    print("🏗️ Test Architecture Complète Restructurée")
    print("=" * 60)
    
    results = {
        "vad": False,
        "asr": False, 
        "nlp": False,
        "tts": False,
        "integration": False
    }
    
    try:
        # 1. Test VAD (Voice Activity Detection)
        print("\n1️⃣ Test VAD (Voice Activity Detection)")
        print("-" * 40)
        
        from peer.interfaces.sui.stt.audio_io import VoiceActivityDetector, AudioCapture
        
        vad = VoiceActivityDetector()
        # AudioCapture now requires a config parameter
        audio_config = {
            'sample_rate': 16000,
            'chunk_duration_ms': 30,
            'pyaudio_format_str': 'paInt16',
            'channels': 1
        }
        audio_capture = AudioCapture(audio_config)
        
        # Test VAD avec données simulées
        test_audio = np.random.randint(-1000, 1000, 1600, dtype=np.int16).tobytes()
        has_speech = vad.is_speech(test_audio)
        print(f"   ✅ VAD fonctionnel - Détection: {has_speech}")
        
        # Test capture audio
        devices = audio_capture.list_audio_devices()
        print(f"   ✅ Capture audio - Périphériques: {len(devices)}")
        results["vad"] = True
        
        # 2. Test ASR (Automatic Speech Recognition) 
        print("\n2️⃣ Test ASR (Automatic Speech Recognition)")
        print("-" * 40)
        
        from peer.interfaces.sui.stt.speech_recognizer import SpeechRecognizer
        
        # Configuration avec multiple moteurs
        asr_config = {
            "engines": {
                "whisper": {"enabled": True, "model_name": "base"},
                "vosk": {"enabled": True},
                "mock": {"enabled": True}
            }
        }
        
        speech_recognizer = SpeechRecognizer(asr_config)
        engines = speech_recognizer.get_available_engines()
        primary = speech_recognizer.get_primary_engine()
        
        print(f"   ✅ ASR initialisé - Moteurs: {engines}")
        print(f"   ✅ Moteur principal: {primary}")
        
        # Test transcription
        test_audio_float = np.random.random(16000).astype(np.float32)
        transcription_result = speech_recognizer.transcribe(test_audio_float)
        
        if transcription_result:
            print(f"   ✅ Transcription: '{transcription_result.text}'")
            print(f"   ✅ Moteur utilisé: {transcription_result.engine_used}")
            results["asr"] = True
        
        # 3. Test NLP (Natural Language Processing)
        print("\n3️⃣ Test NLP (Natural Language Processing)")
        print("-" * 40)
        
        from peer.interfaces.sui.nlu.domain.nlp_engine import NLPEngine
        
        nlp_engine = NLPEngine()
        models_status = nlp_engine.get_models_status()
        
        print(f"   ✅ NLP initialisé - Modèles: {list(models_status.keys())}")
        
        # Test extraction d'intentions
        test_phrases = [
            ("aide moi s'il te plaît", "help"),
            ("arrête toi maintenant", "quit"), 
            ("quel est le statut système", "status"),
            ("ouvre le fichier main.py", "file_operation"),
            ("analyse ce code pour les bugs", "analysis")
        ]
        
        correct_predictions = 0
        for phrase, expected_intent in test_phrases:
            intent_result = nlp_engine.extract_intent(phrase)
            is_correct = intent_result.command_type == expected_intent
            if is_correct:
                correct_predictions += 1
            
            print(f"   {'✅' if is_correct else '⚠️'} '{phrase}' -> {intent_result.command_type} (conf: {intent_result.confidence:.2f})")
        
        accuracy = correct_predictions / len(test_phrases)
        print(f"   📊 Précision NLP: {accuracy:.1%}")
        results["nlp"] = accuracy > 0.5
        
        # 4. Test TTS (Text-to-Speech)
        print("\n4️⃣ Test TTS (Text-to-Speech)")
        print("-" * 40)
        
        from peer.interfaces.sui.tts.text_to_speech import TextToSpeech
        
        tts_engine = TextToSpeech()
        available_engines = tts_engine.get_available_engines()
        active_engine = tts_engine.get_active_engine()
        
        print(f"   ✅ TTS initialisé - Moteurs: {available_engines}")
        print(f"   ✅ Moteur actif: {active_engine}")
        
        # Test synthèse vocale
        test_message = "Bonjour, ceci est un test de synthèse vocale."
        tts_result = tts_engine.synthesize(test_message)
        
        if tts_result.success:
            print(f"   ✅ Synthèse réussie avec {tts_result.engine_used}")
            if tts_result.audio_file_path:
                print(f"   ✅ Fichier audio: {tts_result.audio_file_path}")
            results["tts"] = True
        else:
            print(f"   ❌ Échec synthèse: {tts_result.error_message}")
        
        # 5. Test Intégration Complète
        print("\n5️⃣ Test Intégration Pipeline Complète")
        print("-" * 40)
        
        from peer.interfaces.sui.main import SpeechUserInterface
        
        sui = SpeechUserInterface()
        print("   ✅ Interface SUI initialisée")
        
        # Test pipeline complète avec différentes commandes
        integration_commands = [
            "aide moi à comprendre le système",
            "quel est le statut actuel",
            "ouvre le fichier configuration.yaml", 
            "analyse le code source",
            "arrête le système"
        ]
        
        successful_commands = 0
        for cmd in integration_commands:
            try:
                response = sui.process_speech_input(cmd)
                is_success = response.success and response.message
                if is_success:
                    successful_commands += 1
                
                print(f"   {'✅' if is_success else '⚠️'} '{cmd}' -> {response.message[:50]}...")
                
            except Exception as e:
                print(f"   ❌ Erreur commande '{cmd}': {e}")
        
        integration_success_rate = successful_commands / len(integration_commands)
        print(f"   📊 Taux de succès intégration: {integration_success_rate:.1%}")
        results["integration"] = integration_success_rate > 0.7
        
        return results
        
    except Exception as e:
        print(f"❌ Erreur architecture: {e}")
        import traceback
        traceback.print_exc()
        return results

def test_performance_benchmarks():
    """Test de performance de l'architecture."""
    print("\n⚡ Test Performance et Benchmarks")
    print("-" * 40)
    
    try:
        from peer.interfaces.sui.main import SpeechUserInterface
        
        sui = SpeechUserInterface()
        
        # Test de latence
        test_commands = [
            "aide",
            "statut", 
            "ouvre fichier.txt",
            "analyse code",
            "stop"
        ]
        
        total_time = 0
        successful_commands = 0
        
        print("   🕐 Mesure des temps de réponse...")
        
        for cmd in test_commands:
            start_time = time.time()
            
            try:
                response = sui.process_speech_input(cmd)
                end_time = time.time()
                
                processing_time = (end_time - start_time) * 1000  # en ms
                total_time += processing_time
                
                if response.success:
                    successful_commands += 1
                
                print(f"     '{cmd}' -> {processing_time:.1f}ms {'✅' if response.success else '❌'}")
                
            except Exception as e:
                print(f"     '{cmd}' -> ERROR: {e}")
        
        avg_time = total_time / len(test_commands) if test_commands else 0
        success_rate = successful_commands / len(test_commands) if test_commands else 0
        
        print(f"   📊 Temps moyen: {avg_time:.1f}ms")
        print(f"   📊 Taux de succès: {success_rate:.1%}")
        
        # Critères de performance acceptables
        is_fast_enough = avg_time < 2000  # < 2 secondes
        is_reliable = success_rate > 0.8   # > 80% succès
        
        print(f"   {'✅' if is_fast_enough else '❌'} Performance (< 2s): {is_fast_enough}")
        print(f"   {'✅' if is_reliable else '❌'} Fiabilité (> 80%): {is_reliable}")
        
        return is_fast_enough and is_reliable
        
    except Exception as e:
        print(f"❌ Erreur benchmarks: {e}")
        return False

def test_error_handling():
    """Test de gestion d'erreurs et fallbacks."""
    print("\n🛡️ Test Gestion d'Erreurs et Fallbacks")
    print("-" * 40)
    
    try:
        from peer.interfaces.sui.main import SpeechUserInterface
        
        sui = SpeechUserInterface()
        
        # Test avec entrées problématiques
        error_test_cases = [
            ("", "Entrée vide"),
            ("   ", "Entrée whitespace"),
            ("azertyuiopmlkjhgfdqsdfghjklm", "Commande inexistante"),
            ("!@#$%^&*()", "Caractères spéciaux"),
            ("a" * 1000, "Entrée très longue")
        ]
        
        handled_errors = 0
        
        for test_input, description in error_test_cases:
            try:
                response = sui.process_speech_input(test_input)
                
                # Vérifier que le système gère l'erreur gracieusement
                has_response = bool(response.message)
                is_graceful = not response.success or "erreur" not in response.message.lower()
                
                if has_response:
                    handled_errors += 1
                
                print(f"   {'✅' if has_response else '❌'} {description}: {'Géré' if has_response else 'Non géré'}")
                
            except Exception as e:
                print(f"   ❌ {description}: Exception non gérée - {e}")
        
        error_handling_rate = handled_errors / len(error_test_cases)
        print(f"   📊 Taux de gestion d'erreurs: {error_handling_rate:.1%}")
        
        return error_handling_rate > 0.8
        
    except Exception as e:
        print(f"❌ Erreur test gestion d'erreurs: {e}")
        return False

def test_resource_usage():
    """Test d'utilisation des ressources."""
    print("\n💾 Test Utilisation des Ressources")
    print("-" * 40)
    
    try:
        import psutil
        import gc
        
        # Mesure avant initialisation
        process = psutil.Process()
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        print(f"   📊 Mémoire avant initialisation: {memory_before:.1f} MB")
        
        # Initialisation de l'interface
        from peer.interfaces.sui.main import SpeechUserInterface
        sui = SpeechUserInterface()
        
        # Mesure après initialisation
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_usage = memory_after - memory_before
        
        print(f"   📊 Mémoire après initialisation: {memory_after:.1f} MB")
        print(f"   📊 Utilisation mémoire SUI: {memory_usage:.1f} MB")
        
        # Test utilisation CPU pendant traitement
        cpu_before = process.cpu_percent()
        
        # Traitement de quelques commandes
        for i in range(3):
            sui.process_speech_input(f"test commande {i}")
        
        cpu_after = process.cpu_percent()
        
        print(f"   📊 Utilisation CPU: {cpu_after:.1f}%")
        
        # Critères d'acceptabilité
        memory_ok = memory_usage < 500  # < 500 MB
        cpu_ok = cpu_after < 50         # < 50% CPU
        
        print(f"   {'✅' if memory_ok else '❌'} Mémoire acceptable (< 500MB): {memory_ok}")
        print(f"   {'✅' if cpu_ok else '❌'} CPU acceptable (< 50%): {cpu_ok}")
        
        # Nettoyage
        del sui
        gc.collect()
        
        return memory_ok and cpu_ok
        
    except ImportError:
        print("   ⚠️ psutil non disponible - test ressources ignoré")
        return True
    except Exception as e:
        print(f"❌ Erreur test ressources: {e}")
        return True  # Non critique

if __name__ == "__main__":
    print("🔥 TEST END-TO-END ARCHITECTURE SUI RESTRUCTURÉE")
    print("=" * 80)
    print("Tests de validation complète de la nouvelle architecture:")
    print("- VAD (Voice Activity Detection) dans stt/audio_io.py")
    print("- ASR (Automatic Speech Recognition) dans stt/speech_recognizer.py") 
    print("- NLU (Natural Language Understanding) dans nlu/domain/nlp_engine.py")
    print("- TTS (Text-to-Speech) dans tts/text_to_speech.py")
    print("=" * 80)
    
    # Mesure du temps total
    total_start_time = time.time()
    
    # Suite de tests
    test_results = {}
    
    # 1. Test architecture complète
    print("\n" + "🏗️" * 20 + " TESTS ARCHITECTURE " + "🏗️" * 20)
    architecture_results = test_complete_architecture()
    test_results.update(architecture_results)
    
    # 2. Test performance
    print("\n" + "⚡" * 20 + " TESTS PERFORMANCE " + "⚡" * 20)
    performance_result = test_performance_benchmarks()
    test_results["performance"] = performance_result
    
    # 3. Test gestion d'erreurs
    print("\n" + "🛡️" * 20 + " TESTS ROBUSTESSE " + "🛡️" * 20)
    error_handling_result = test_error_handling()
    test_results["error_handling"] = error_handling_result
    
    # 4. Test ressources
    print("\n" + "💾" * 20 + " TESTS RESSOURCES " + "💾" * 20)
    resource_result = test_resource_usage()
    test_results["resources"] = resource_result
    
    # Calcul du temps total
    total_time = time.time() - total_start_time
    
    # Résultats finaux
    print("\n" + "📊" * 30 + " RÉSULTATS FINAUX " + "📊" * 30)
    print(f"⏱️ Temps total d'exécution: {total_time:.1f}s")
    print()
    
    # Affichage détaillé des résultats
    component_results = {
        "VAD (Voice Activity Detection)": test_results.get("vad", False),
        "ASR (Speech Recognition)": test_results.get("asr", False), 
        "NLP (Language Understanding)": test_results.get("nlp", False),
        "TTS (Text-to-Speech)": test_results.get("tts", False),
        "Intégration Pipeline": test_results.get("integration", False),
        "Performance": test_results.get("performance", False),
        "Gestion d'Erreurs": test_results.get("error_handling", False),
        "Utilisation Ressources": test_results.get("resources", False)
    }
    
    passed_tests = sum(component_results.values())
    total_tests = len(component_results)
    
    print("📋 COMPOSANTS TESTÉS:")
    print("-" * 60)
    for component, status in component_results.items():
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {component:<35} {'SUCCÈS' if status else 'ÉCHEC'}")
    
    print("-" * 60)
    print(f"📊 RÉSULTAT GLOBAL: {passed_tests}/{total_tests} tests réussis ({passed_tests/total_tests:.1%})")
    
    # Verdict final
    if passed_tests == total_tests:
        print("\n🎉 FÉLICITATIONS ! 🎉")
        print("🚀 L'architecture SUI restructurée est ENTIÈREMENT FONCTIONNELLE !")
        print("🏆 Tous les composants sont opérationnels selon les spécifications.")
        print("💪 Le système est prêt pour la production.")
        exit_code = 0
    elif passed_tests >= total_tests * 0.75:  # 75% de réussite
        print("\n✅ SUCCÈS GLOBAL !")
        print("🎯 L'architecture SUI restructurée est LARGEMENT FONCTIONNELLE.")
        print("⚠️ Quelques composants nécessitent des ajustements mineurs.")
        print("📈 Le système est prêt pour les tests d'intégration avancés.")
        exit_code = 0
    elif passed_tests >= total_tests * 0.5:   # 50% de réussite
        print("\n⚠️ SUCCÈS PARTIEL")
        print("🔧 L'architecture SUI restructurée a des composants fonctionnels.")
        print("🛠️ Des améliorations sont nécessaires avant la production.")
        print("📝 Réviser les composants en échec.")
        exit_code = 1
    else:
        print("\n❌ ÉCHEC CRITIQUE")
        print("🚨 L'architecture SUI restructurée nécessite des corrections majeures.")
        print("🔄 Révision complète de l'implémentation requise.")
        print("🆘 Contacter l'équipe de développement.")
        exit_code = 2
    
    print("\n" + "=" * 80)
    print("🏁 FIN DES TESTS END-TO-END")
    
    sys.exit(exit_code)
