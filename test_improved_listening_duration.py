#!/usr/bin/env python3
"""
Test d'amélioration de la durée d'écoute pour l'interface vocale en temps réel.

Ce script teste si les modifications apportées à l'interface vocale permettent
de capturer des phrases plus longues sans interruption prématurée.
"""

import os
import sys
import time
import logging
import threading
from pathlib import Path

# Configuration pour éviter les warnings OMP
os.environ["OMP_NUM_THREADS"] = "1"

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Ajouter le chemin source pour l'importation
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, 'src'))
sys.path.insert(0, current_dir)

# Importer après avoir configuré les chemins
from peer.interfaces.sui.stt.speech_recognizer import SpeechRecognizer
from peer.interfaces.sui.stt.audio_io import AudioCapture, VoiceActivityDetector, VADMode, AudioFormat
from peer.interfaces.sui.stt.continuous_speech_manager import ContinuousSpeechManager

class ListeningDurationTest:
    """Test de la durée d'écoute améliorée."""
    
    def __init__(self):
        self.logger = logging.getLogger("ListeningDurationTest")
        self.running = False
        self.transcriptions = []
        self.transcription_times = []
        self.test_phrases = [
            "Ceci est un test pour vérifier si l'interface peut capturer des phrases plus longues sans interruption prématurée.",
            "La durée d'écoute a été augmentée pour permettre de capturer des phrases complètes, même avec des pauses naturelles.",
            "Les modifications incluent l'augmentation de la durée maximale des batchs, l'ajustement du seuil de pause, et l'optimisation des mécanismes de détection de fin de phrase.",
            "Maintenant nous allons tester si ces modifications fonctionnent correctement et si l'interface peut transcrire cette longue phrase sans la couper en plusieurs morceaux.",
        ]
        
        # Initialiser les composants
        self._init_components()
    
    def _init_components(self):
        """Initialise les composants nécessaires pour le test."""
        self.logger.info("🚀 Initialisation des composants de test")
        
        try:
            # Configuration WhisperX 
            stt_config = {
                'stt_settings': {
                    'engines': {
                        'whisperx': {
                            'enabled': True,
                            'model_name': 'base',
                            'language': 'fr',
                            'priority': 1,
                            'parameters': {
                                'batch_size': 8,
                                'task': 'transcribe',
                                'language': 'french'
                            }
                        }
                    }
                }
            }
            
            # Initialiser le recognizer
            self.speech_recognizer = SpeechRecognizer(stt_config)
            self.logger.info("✅ Speech recognizer initialisé")
            
            # Initialiser la capture audio
            audio_config = {
                'sample_rate': AudioFormat.SAMPLE_RATE,
                'channels': AudioFormat.CHANNELS,
                'chunk_size': AudioFormat.CHUNK_SIZE,
                'vad_sensitivity': 3
            }
            self.audio_capture = AudioCapture(audio_config)
            self.logger.info("✅ Capture audio initialisée")
            
            # Initialiser le VAD
            self.vad = VoiceActivityDetector(mode=VADMode.VERY_AGGRESSIVE)
            self.logger.info("✅ VAD initialisé")
            
            # Initialiser le gestionnaire de parole continue avec les paramètres améliorés
            self.speech_manager = ContinuousSpeechManager(
                speech_recognizer=self.speech_recognizer,
                pause_threshold=1.2,      # Pause plus longue pour permettre des pauses naturelles
                min_segment_duration=0.05, # Segments très courts pour capturer toute parole
                max_batch_duration=10.0,   # Batches plus longs pour capturer des phrases complètes
                transcription_callback=self._on_transcription_received
            )
            self.logger.info("✅ Gestionnaire de parole continue initialisé")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de l'initialisation: {e}")
            raise
    
    def _on_transcription_received(self, text: str, is_final: bool):
        """Callback appelé quand une transcription est reçue."""
        if is_final and text.strip():
            self.logger.info(f"✅ Transcription finale: '{text}'")
            self.transcriptions.append(text)
            self.transcription_times.append(time.time())
    
    def start_test(self):
        """Démarre le test d'écoute."""
        self.running = True
        self.logger.info("🎙️ Démarrage du test d'écoute")
        
        # Démarrer les composants
        self.speech_manager.start()
        
        # Démarrer l'écoute audio
        if not self.audio_capture.start_recording():
            self.logger.error("❌ Impossible de démarrer l'enregistrement audio")
            return False
        
        # Thread pour traiter les segments audio
        audio_thread = threading.Thread(target=self._audio_processing_loop, daemon=True)
        audio_thread.start()
        
        self.logger.info("👂 Test d'écoute démarré. Parlez dans le microphone...")
        self.logger.info("📝 Nous allons mesurer combien de temps il faut pour transcrire une phrase complète.")
        
        # Attendre les résultats pendant 60 secondes
        test_duration = 60  # secondes
        start_time = time.time()
        
        while time.time() - start_time < test_duration and self.running:
            time.sleep(0.5)
            
            # Afficher les résultats intermédiaires s'il y en a
            if len(self.transcriptions) > 0 and time.time() - start_time > 10:
                self._display_current_results()
        
        # Arrêter les composants
        self.stop_test()
        
        # Afficher les résultats finaux
        self._display_final_results()
        
        return True
    
    def stop_test(self):
        """Arrête le test d'écoute."""
        self.running = False
        
        if self.speech_manager:
            self.speech_manager.stop()
        
        if self.audio_capture:
            self.audio_capture.stop_recording()
        
        self.logger.info("🛑 Test d'écoute arrêté")
    
    def _audio_processing_loop(self):
        """Boucle de traitement des segments audio."""
        segment_count = 0
        speech_count = 0
        
        while self.running:
            # Récupérer le prochain segment audio
            segment = self.audio_capture.get_audio_segment(timeout=0.5)
            if segment is None:
                continue
            
            segment_count += 1
            if segment.has_speech:
                speech_count += 1
                
                # Envoyer au gestionnaire de parole continue
                try:
                    self.speech_manager.add_audio_segment(segment.data, segment.has_speech)
                except Exception as e:
                    self.logger.error(f"❌ Erreur traitement audio: {e}")
            
            # Log périodique
            if segment_count % 50 == 0:
                self.logger.info(f"📊 Segments traités: {segment_count}, avec parole: {speech_count}")
    
    def _display_current_results(self):
        """Affiche les résultats intermédiaires du test."""
        self.logger.info("\n--- Résultats intermédiaires ---")
        self.logger.info(f"Nombre de transcriptions: {len(self.transcriptions)}")
        
        if len(self.transcriptions) > 0:
            self.logger.info(f"Dernière transcription: {self.transcriptions[-1]}")
            
            # Calculer les délais entre les transcriptions
            if len(self.transcription_times) > 1:
                delays = [self.transcription_times[i] - self.transcription_times[i-1] 
                          for i in range(1, len(self.transcription_times))]
                self.logger.info(f"Délai moyen entre transcriptions: {sum(delays)/len(delays):.2f}s")
    
    def _display_final_results(self):
        """Affiche les résultats finaux du test."""
        self.logger.info("\n" + "="*80)
        self.logger.info("📊 RÉSULTATS DU TEST D'ÉCOUTE")
        self.logger.info("="*80)
        
        self.logger.info(f"Nombre total de transcriptions: {len(self.transcriptions)}")
        
        if len(self.transcriptions) > 0:
            self.logger.info("\n--- Transcriptions capturées ---")
            for i, text in enumerate(self.transcriptions):
                self.logger.info(f"{i+1}. {text}")
            
            # Calculer la longueur moyenne des transcriptions en mots
            word_counts = [len(t.split()) for t in self.transcriptions]
            avg_word_count = sum(word_counts) / len(word_counts)
            self.logger.info(f"\nLongueur moyenne des transcriptions: {avg_word_count:.1f} mots")
            
            # Calculer les délais entre les transcriptions
            if len(self.transcription_times) > 1:
                delays = [self.transcription_times[i] - self.transcription_times[i-1] 
                          for i in range(1, len(self.transcription_times))]
                self.logger.info(f"Délai moyen entre transcriptions: {sum(delays)/len(delays):.2f}s")
        
        self.logger.info("\n✅ Test d'écoute terminé. Analyse des résultats:")
        
        if len(self.transcriptions) == 0:
            self.logger.info("❌ Aucune transcription capturée. Vérifiez le microphone et les paramètres audio.")
        elif avg_word_count < 5:
            self.logger.info("⚠️ Les transcriptions sont très courtes. Des améliorations supplémentaires peuvent être nécessaires.")
        elif avg_word_count >= 10:
            self.logger.info("✅ Les transcriptions sont suffisamment longues. Les modifications semblent efficaces!")
        else:
            self.logger.info("⚠️ Les transcriptions sont de longueur moyenne. Des ajustements supplémentaires pourraient être bénéfiques.")


def main():
    """Point d'entrée principal."""
    try:
        print("\n🚀 Démarrage du test d'amélioration de la durée d'écoute...")
        
        # Créer et démarrer le test
        test = ListeningDurationTest()
        test.start_test()
        
    except KeyboardInterrupt:
        print("\n⌨️ Test interrompu par l'utilisateur")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        logging.error(f"Erreur dans le test: {e}")
    
    print("\n👋 Test terminé.")


if __name__ == "__main__":
    main()
