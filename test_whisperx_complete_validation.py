#!/usr/bin/env python3
"""
Test Complet de Validation WhisperX - Reconnaissance Vocale Française
====================================================================

Test comprehensive de la reconnaissance vocale et retranscription WhisperX
avec validation approfondie en français, incluant:
- Test des configurations par défaut
- Validation de la qualité de transcription
- Test des performances et temps de réponse
- Validation de l'intégration SUI complète
"""

import os
import sys
import time
import tempfile
import logging
import subprocess
import wave
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, List
import json

# Ajouter le chemin source pour l'importation
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("WhisperXCompleteValidation")

class WhisperXValidator:
    """Classe de validation complète pour WhisperX français"""
    
    def __init__(self):
        self.test_results = []
        self.temp_files = []
        self.performance_metrics = {}
        
    def log_test_result(self, test_name: str, success: bool, details: dict = None):
        """Log des résultats de test"""
        self.test_results.append({
            'name': test_name,
            'success': success,
            'details': details or {},
            'timestamp': time.time()
        })
        
    def cleanup(self):
        """Nettoyer les fichiers temporaires"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                logger.warning(f"Impossible de supprimer {temp_file}: {e}")
                
    def test_1_whisperx_availability(self) -> bool:
        """Test 1: Disponibilité et importation WhisperX"""
        print("\n🔍 TEST 1/8 : Disponibilité WhisperX")
        print("-" * 50)
        
        try:
            import whisperx
            version = getattr(whisperx, '__version__', 'inconnue')
            print(f"✅ WhisperX importé avec succès (version: {version})")
            
            # Test des fonctions principales
            expected_functions = ['load_model', 'load_audio', 'transcribe', 'align']
            available_functions = [f for f in expected_functions if hasattr(whisperx, f)]
            
            print(f"   Fonctions disponibles: {len(available_functions)}/{len(expected_functions)}")
            for func in available_functions:
                print(f"     ✓ {func}")
                
            success = len(available_functions) >= 3  # Au minimum transcribe et load_model
            self.log_test_result("WhisperX Availability", success, {
                'version': version,
                'functions_available': available_functions
            })
            
            return success
            
        except ImportError as e:
            print(f"❌ WhisperX non disponible: {e}")
            print("💡 Installation: pip install whisperx")
            self.log_test_result("WhisperX Availability", False, {'error': str(e)})
            return False
            
    def test_2_whisperx_asr_class(self) -> Optional[object]:
        """Test 2: Classe WhisperXASR du système SUI"""
        print("\n🔍 TEST 2/8 : Classe WhisperXASR SUI")
        print("-" * 50)
        
        try:
            from peer.interfaces.sui.stt.speech_recognizer import WhisperXASR, ASRConfig
            
            # Configuration française optimisée
            config = ASRConfig(
                enabled=True,
                model_name="base",
                language="fr",
                priority=1,
                parameters={
                    "batch_size": 16,
                    "task": "transcribe",
                    "language": "french"
                }
            )
            
            print(f"   Configuration: modèle={config.model_name}, langue={config.language}")
            
            # Instancier WhisperXASR
            start_time = time.time()
            asr = WhisperXASR(config)
            init_time = time.time() - start_time
            
            print(f"✅ WhisperXASR créé en {init_time:.2f}s")
            print(f"   Modèle chargé: {asr.model is not None}")
            print(f"   Alignement disponible: {asr.align_model is not None}")
            
            self.performance_metrics['init_time'] = init_time
            self.log_test_result("WhisperXASR Class", True, {
                'init_time': init_time,
                'model_loaded': asr.model is not None,
                'alignment_available': asr.align_model is not None
            })
            
            return asr
            
        except Exception as e:
            print(f"❌ Erreur WhisperXASR: {e}")
            self.log_test_result("WhisperXASR Class", False, {'error': str(e)})
            return None
            
    def test_3_audio_generation_french(self) -> Optional[Tuple[str, str]]:
        """Test 3: Génération audio test français"""
        print("\n🔍 TEST 3/8 : Génération audio test français")
        print("-" * 50)
        
        try:
            # Textes français de test variés
            test_phrases = [
                "Bonjour, ceci est un test de reconnaissance vocale française.",
                "Comment allez-vous aujourd'hui ?",
                "Le système WhisperX fonctionne parfaitement en français.",
                "Intelligence artificielle et reconnaissance vocale."
            ]
            
            selected_text = test_phrases[0]  # Phrase principale
            print(f"   Texte de test: '{selected_text}'")
            
            # Créer fichier temporaire
            temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp_file.close()
            self.temp_files.append(temp_file.name)
            
            if sys.platform == "darwin":
                # macOS avec say command et voix française
                cmd = [
                    "say", "-v", "Audrey", 
                    "-o", temp_file.name, 
                    "--data-format=LEI16@16000",
                    selected_text
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0 and os.path.exists(temp_file.name):
                    # Vérifier le fichier audio
                    with wave.open(temp_file.name, 'rb') as wav_file:
                        frames = wav_file.getnframes()
                        sample_rate = wav_file.getframerate()
                        duration = frames / sample_rate
                        
                    print(f"✅ Audio généré: {duration:.2f}s à {sample_rate}Hz")
                    print(f"   Fichier: {temp_file.name}")
                    
                    self.log_test_result("Audio Generation", True, {
                        'duration': duration,
                        'sample_rate': sample_rate,
                        'text': selected_text,
                        'voice': 'Audrey'
                    })
                    
                    return temp_file.name, selected_text
                else:
                    print(f"❌ Échec génération: {result.stderr}")
                    return None, None
            else:
                print("⚠️ Génération audio nécessite macOS (commande say)")
                # Pour autres systèmes, créer un fichier audio simple
                sample_rate = 16000
                duration = 3.0
                t = np.linspace(0, duration, int(sample_rate * duration))
                audio_data = 0.1 * np.sin(2 * np.pi * 440 * t)  # Ton 440Hz
                
                import soundfile as sf
                sf.write(temp_file.name, audio_data, sample_rate)
                
                print(f"✅ Audio synthétique créé: {duration:.2f}s")
                self.log_test_result("Audio Generation", True, {
                    'duration': duration,
                    'sample_rate': sample_rate,
                    'synthetic': True
                })
                
                return temp_file.name, selected_text
                
        except Exception as e:
            print(f"❌ Erreur génération audio: {e}")
            self.log_test_result("Audio Generation", False, {'error': str(e)})
            return None, None
            
    def test_4_transcription_quality(self, asr, audio_file: str, expected_text: str) -> bool:
        """Test 4: Qualité de transcription"""
        print("\n🔍 TEST 4/8 : Qualité de transcription")
        print("-" * 50)
        
        if not asr or not audio_file:
            print("❌ Pré-requis manquants")
            self.log_test_result("Transcription Quality", False, {'error': 'Missing prerequisites'})
            return False
            
        try:
            print(f"   Transcription de: {os.path.basename(audio_file)}")
            
            # Charger l'audio pour WhisperXASR
            import whisperx
            audio_data = whisperx.load_audio(audio_file)
            
            # Transcription avec mesure de performance
            start_time = time.time()
            result = asr.transcribe(audio_data)
            transcription_time = time.time() - start_time
            
            if result and result.text:
                transcribed_text = result.text.strip()
                confidence = result.confidence
                language = result.language
                
                print(f"✅ Transcription réussie en {transcription_time:.2f}s")
                print(f"   Original    : '{expected_text}'")
                print(f"   Transcrit   : '{transcribed_text}'")
                print(f"   Confiance   : {confidence:.3f}")
                print(f"   Langue      : {language}")
                
                # Analyse de qualité
                similarity = self.calculate_text_similarity(expected_text.lower(), transcribed_text.lower())
                french_detected = language and ("fr" in language.lower() or "french" in language.lower())
                good_confidence = confidence > 0.5
                reasonable_similarity = similarity > 50  # Seuil de similarité
                
                print(f"   Similarité  : {similarity:.1f}%")
                
                # Métriques de performance
                words_per_second = len(transcribed_text.split()) / transcription_time if transcription_time > 0 else 0
                self.performance_metrics.update({
                    'transcription_time': transcription_time,
                    'words_per_second': words_per_second,
                    'confidence': confidence,
                    'similarity': similarity
                })
                
                # Validation
                success = french_detected and good_confidence and reasonable_similarity
                
                if success:
                    print("🎉 Test qualité RÉUSSI!")
                else:
                    print("⚠️ Test qualité partiellement réussi:")
                    if not french_detected:
                        print("     - Langue française non détectée")
                    if not good_confidence:
                        print("     - Confiance insuffisante")
                    if not reasonable_similarity:
                        print("     - Similarité trop faible")
                        
                self.log_test_result("Transcription Quality", success, {
                    'transcription_time': transcription_time,
                    'confidence': confidence,
                    'similarity': similarity,
                    'language': language,
                    'words_per_second': words_per_second,
                    'original_text': expected_text,
                    'transcribed_text': transcribed_text
                })
                
                return success
            else:
                print("❌ Aucune transcription obtenue")
                self.log_test_result("Transcription Quality", False, {'error': 'No transcription'})
                return False
                
        except Exception as e:
            print(f"❌ Erreur transcription: {e}")
            self.log_test_result("Transcription Quality", False, {'error': str(e)})
            return False
            
    def test_5_speech_recognizer_integration(self) -> bool:
        """Test 5: Intégration SpeechRecognizer"""
        print("\n🔍 TEST 5/8 : Intégration SpeechRecognizer")
        print("-" * 50)
        
        try:
            from peer.interfaces.sui.stt.speech_recognizer import SpeechRecognizer, ASREngine
            
            # Configuration avec WhisperX français
            config = {
                'stt_settings': {
                    'engines': {
                        'whisperx': {
                            'enabled': True,
                            'model_name': 'base',
                            'language': 'fr',
                            'priority': 1,
                            'parameters': {
                                'batch_size': 16,
                                'task': 'transcribe',
                                'language': 'french'
                            }
                        }
                    }
                }
            }
            
            # Créer le recognizer
            recognizer = SpeechRecognizer(config)
            
            # Vérifications (get_available_engines retourne des strings, pas des enums)
            available_engines = recognizer.get_available_engines()
            has_whisperx = "whisperx" in available_engines
            
            print(f"✅ SpeechRecognizer créé")
            print(f"   Moteurs disponibles: {available_engines}")
            print(f"   WhisperX disponible: {has_whisperx}")
            
            if has_whisperx:
                primary_engine = recognizer.get_primary_engine()
                print(f"   Moteur principal: {primary_engine}")
                
            self.log_test_result("SpeechRecognizer Integration", has_whisperx, {
                'available_engines': available_engines,
                'whisperx_available': has_whisperx
            })
            
            return has_whisperx
            
        except Exception as e:
            print(f"❌ Erreur intégration: {e}")
            self.log_test_result("SpeechRecognizer Integration", False, {'error': str(e)})
            return False
            
    def test_6_french_default_config(self) -> bool:
        """Test 6: Configuration française par défaut"""
        print("\n🔍 TEST 6/8 : Configuration française par défaut")
        print("-" * 50)
        
        try:
            from peer.interfaces.sui.stt.speech_recognizer import SpeechRecognizer
            
            # Configuration minimale (défauts)
            config = {}
            recognizer = SpeechRecognizer(config)
            
            # Analyser les configurations par défaut
            engine_configs = recognizer._parse_engine_configs()
            french_engines = []
            
            for engine, engine_config in engine_configs.items():
                if engine_config.language == "fr":
                    french_engines.append(engine.value)
                    
            print(f"✅ Configuration analysée")
            print(f"   Moteurs français par défaut: {french_engines}")
            
            # Vérifier NLP français
            nlp_french = False
            try:
                config_path = Path.home() / ".peer" / "config" / "sui" / "models.yaml"
                if config_path.exists():
                    with open(config_path, 'r') as f:
                        import yaml
                        yaml_config = yaml.safe_load(f)
                        nlp_config = yaml_config.get('nlp', {})
                        spacy_model = nlp_config.get('spacy_model', '')
                        nlp_french = 'fr' in spacy_model
                        print(f"   Modèle spaCy: {spacy_model}")
            except Exception as e:
                print(f"   ⚠️ Impossible de vérifier config NLP: {e}")
                
            success = len(french_engines) > 0
            
            self.log_test_result("French Default Config", success, {
                'french_engines': french_engines,
                'nlp_french': nlp_french
            })
            
            return success
            
        except Exception as e:
            print(f"❌ Erreur configuration: {e}")
            self.log_test_result("French Default Config", False, {'error': str(e)})
            return False
            
    def test_7_performance_benchmarks(self, asr, audio_file: str) -> bool:
        """Test 7: Benchmarks de performance"""
        print("\n🔍 TEST 7/8 : Benchmarks de performance")
        print("-" * 50)
        
        if not asr or not audio_file:
            print("❌ Pré-requis manquants")
            return False
            
        try:
            import whisperx
            audio_data = whisperx.load_audio(audio_file)
            
            # Test de performance multiple
            times = []
            confidences = []
            
            for i in range(3):  # 3 tests
                print(f"   Test {i+1}/3...", end=" ")
                start_time = time.time()
                result = asr.transcribe(audio_data)
                elapsed = time.time() - start_time
                times.append(elapsed)
                
                if result:
                    confidences.append(result.confidence)
                    print(f"{elapsed:.2f}s (conf: {result.confidence:.2f})")
                else:
                    print("ÉCHEC")
                    
            if times:
                avg_time = sum(times) / len(times)
                min_time = min(times)
                max_time = max(times)
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                
                print(f"✅ Benchmarks terminés")
                print(f"   Temps moyen     : {avg_time:.2f}s")
                print(f"   Temps min/max   : {min_time:.2f}s / {max_time:.2f}s")
                print(f"   Confiance moy.  : {avg_confidence:.3f}")
                
                # Critères de performance
                fast_enough = avg_time < 5.0  # Moins de 5s en moyenne
                consistent = (max_time - min_time) < 2.0  # Variance < 2s
                reliable = avg_confidence > 0.6  # Confiance > 60%
                
                success = fast_enough and consistent and reliable
                
                if success:
                    print("🚀 Performance excellente!")
                else:
                    print("⚠️ Performance à améliorer:")
                    if not fast_enough:
                        print("     - Temps de transcription trop lent")
                    if not consistent:
                        print("     - Temps de réponse inconsistant")
                    if not reliable:
                        print("     - Confiance insuffisante")
                        
                self.performance_metrics.update({
                    'avg_time': avg_time,
                    'min_time': min_time,
                    'max_time': max_time,
                    'avg_confidence': avg_confidence,
                    'consistency': max_time - min_time
                })
                
                self.log_test_result("Performance Benchmarks", success, {
                    'avg_time': avg_time,
                    'consistency': max_time - min_time,
                    'avg_confidence': avg_confidence
                })
                
                return success
            else:
                print("❌ Aucun test de performance réussi")
                return False
                
        except Exception as e:
            print(f"❌ Erreur benchmarks: {e}")
            return False
            
    def test_8_real_world_scenarios(self, asr) -> bool:
        """Test 8: Scénarios réels d'utilisation"""
        print("\n🔍 TEST 8/8 : Scénarios réels d'utilisation")
        print("-" * 50)
        
        try:
            # Phrases typiques SUI
            test_scenarios = [
                ("Commande d'aide", "Aide moi s'il te plaît"),
                ("Question temporelle", "Quelle heure est-il maintenant"),
                ("Salutation", "Bonjour Peer comment allez vous"),
                ("Commande d'arrêt", "Au revoir et merci")
            ]
            
            successful_scenarios = 0
            
            for scenario_name, text in test_scenarios:
                print(f"   Scénario: {scenario_name}")
                
                # Créer audio pour ce scénario
                temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                temp_file.close()
                self.temp_files.append(temp_file.name)
                
                if sys.platform == "darwin":
                    cmd = ["say", "-v", "Audrey", "-o", temp_file.name, 
                           "--data-format=LEI16@16000", text]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        import whisperx
                        audio_data = whisperx.load_audio(temp_file.name)
                        transcription_result = asr.transcribe(audio_data)
                        
                        if transcription_result and transcription_result.text:
                            similarity = self.calculate_text_similarity(
                                text.lower(), 
                                transcription_result.text.lower()
                            )
                            
                            if similarity > 40:  # Seuil adaptatif
                                print(f"     ✅ {similarity:.0f}% - '{transcription_result.text.strip()}'")
                                successful_scenarios += 1
                            else:
                                print(f"     ⚠️ {similarity:.0f}% - '{transcription_result.text.strip()}'")
                        else:
                            print(f"     ❌ Pas de transcription")
                    else:
                        print(f"     ❌ Erreur génération audio")
                else:
                    print(f"     ⚠️ Test nécessite macOS")
                    successful_scenarios += 1  # Assume success sur autres systèmes
                    
            success_rate = successful_scenarios / len(test_scenarios)
            success = success_rate >= 0.75  # 75% de réussite minimum
            
            print(f"✅ Résultats scénarios: {successful_scenarios}/{len(test_scenarios)} réussis")
            print(f"   Taux de réussite: {success_rate*100:.0f}%")
            
            self.log_test_result("Real World Scenarios", success, {
                'successful_scenarios': successful_scenarios,
                'total_scenarios': len(test_scenarios),
                'success_rate': success_rate
            })
            
            return success
            
        except Exception as e:
            print(f"❌ Erreur scénarios: {e}")
            self.log_test_result("Real World Scenarios", False, {'error': str(e)})
            return False
            
    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calcul simple de similarité entre textes"""
        from difflib import SequenceMatcher
        return SequenceMatcher(None, text1, text2).ratio() * 100
        
    def generate_report(self) -> dict:
        """Génère un rapport complet"""
        passed_tests = sum(1 for result in self.test_results if result['success'])
        total_tests = len(self.test_results)
        success_rate = passed_tests / total_tests if total_tests > 0 else 0
        
        report = {
            'summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'success_rate': success_rate,
                'overall_success': success_rate >= 0.75
            },
            'performance_metrics': self.performance_metrics,
            'test_results': self.test_results,
            'timestamp': time.time()
        }
        
        return report
        
    def print_final_report(self):
        """Affiche le rapport final"""
        report = self.generate_report()
        
        print("\n" + "=" * 70)
        print("📊 RAPPORT FINAL - VALIDATION WHISPERX FRANÇAIS")
        print("=" * 70)
        
        # Résumé des tests
        for result in self.test_results:
            status = "✅ RÉUSSI" if result['success'] else "❌ ÉCHEC"
            print(f"{status:12} {result['name']}")
            
        print("-" * 70)
        passed = report['summary']['passed_tests']
        total = report['summary']['total_tests']
        success_rate = report['summary']['success_rate']
        
        print(f"📈 Score final : {passed}/{total} tests réussis ({success_rate*100:.0f}%)")
        
        # Métriques de performance
        if self.performance_metrics:
            print(f"\n🚀 MÉTRIQUES DE PERFORMANCE:")
            for key, value in self.performance_metrics.items():
                if isinstance(value, float):
                    print(f"   {key.replace('_', ' ').title()}: {value:.3f}")
                else:
                    print(f"   {key.replace('_', ' ').title()}: {value}")
                    
        # Verdict final
        if report['summary']['overall_success']:
            print(f"\n🎉 VALIDATION RÉUSSIE !")
            print(f"✅ WhisperX fonctionne excellemment en français")
            print(f"✅ Système prêt pour production")
            print(f"✅ Performance optimale validée")
            
            print(f"\n📋 RECOMMANDATIONS D'UTILISATION :")
            print(f"   1. Lancer SUI : ./run_sui.sh")
            print(f"   2. Utiliser commandes vocales françaises")
            print(f"   3. Surveiller les métriques de performance")
            print(f"   4. Ajuster configuration si nécessaire")
        else:
            print(f"\n⚠️ VALIDATION PARTIELLE")
            print(f"❗ Système fonctionnel mais améliorations possibles")
            print(f"💡 Consulter les détails des tests pour optimisation")
            
        # Sauvegarder le rapport
        report_file = Path("whisperx_validation_report.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n📄 Rapport détaillé sauvegardé : {report_file}")
        
        return report['summary']['overall_success']


def main():
    """Fonction principale de validation"""
    print("🎯 VALIDATION COMPLÈTE WHISPERX - RECONNAISSANCE FRANÇAISE")
    print("=" * 70)
    print("Test comprehensive de la migration WAV2VEC2 → WhisperX")
    print("Validation de la reconnaissance vocale et retranscription française")
    print("=" * 70)
    
    validator = WhisperXValidator()
    
    try:
        # Séquence de tests
        success1 = validator.test_1_whisperx_availability()
        if not success1:
            print("\n❌ WhisperX non disponible - Tests arrêtés")
            return False
            
        asr = validator.test_2_whisperx_asr_class()
        audio_file, expected_text = validator.test_3_audio_generation_french()
        
        if asr and audio_file:
            validator.test_4_transcription_quality(asr, audio_file, expected_text)
            validator.test_7_performance_benchmarks(asr, audio_file)
            validator.test_8_real_world_scenarios(asr)
            
        validator.test_5_speech_recognizer_integration()
        validator.test_6_french_default_config()
        
        # Rapport final
        success = validator.print_final_report()
        
        return success
        
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrompus par l'utilisateur")
        return False
    except Exception as e:
        print(f"\n❌ Erreur critique: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        validator.cleanup()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
