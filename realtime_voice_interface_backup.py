#!/usr/bin/env python3
"""
Interface SUI avec communication orale en temps réel utilisant WhisperX.

Cette interface permet :
- Communication orale bidirectionnelle en français
- Transcription en temps réel avec gestion des pauses
- Affichage progressif de la transcription
- Batching intelligent des segments de parole
- Gestion des interruptions et reprises
"""

import os
import sys
import time
import threading
import logging
from typing import Optional, Dict, Any
from pathlib import Path

# Configuration pour éviter les warnings OMP
os.environ["OMP_NUM_THREADS"] = "1"

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.expanduser('~/.peer/sui_realtime.log'), mode='a')
    ]
)

# Ajouter le chemin source pour l'importation
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from peer.interfaces.sui.stt.speech_recognizer import SpeechRecognizer
from peer.interfaces.sui.stt.audio_io import AudioCapture, VoiceActivityDetector, VADMode, AudioFormat
from peer.interfaces.sui.stt.continuous_speech_manager import ContinuousSpeechManager
from peer.interfaces.sui.tts.simple_tts_engine import SimpleTTS
from peer.interfaces.sui.domain.models import SpeechRecognitionResult


class RealTimeSpeechInterface:
    """Interface de communication orale en temps réel avec WhisperX."""
    
    def __init__(self):
        self.logger = logging.getLogger("RealTimeSpeechInterface")
        
        # État de l'interface
        self.running = False
        self.listening = False
        self.speaking = False
        
        # Composants
        self.speech_recognizer: Optional[SpeechRecognizer] = None
        self.audio_capture: Optional[AudioCapture] = None
        self.vad: Optional[VoiceActivityDetector] = None
        self.speech_manager: Optional[ContinuousSpeechManager] = None
        self.tts_engine: Optional[SimpleTTS] = None
        
        # Affichage
        self.current_transcription = ""
        self.last_final_transcription = ""
        self.transcription_display_lock = threading.Lock()
        
        # Métriques
        self.session_stats = {
            'start_time': time.time(),
            'total_speech_time': 0.0,
            'transcriptions_count': 0,
            'words_transcribed': 0
        }
        
        self._init_components()
    
    def _init_components(self):
        """Initialise tous les composants nécessaires."""
        self.logger.info("🚀 Initialisation de l'interface de communication orale en temps réel")
        
        try:
            # Configuration WhisperX optimisée pour le temps réel
            stt_config = {
                'stt_settings': {
                    'engines': {
                        'whisperx': {
                            'enabled': True,
                            'model_name': 'base',  # Modèle rapide pour temps réel
                            'language': 'fr',
                            'priority': 1,
                            'parameters': {
                                'batch_size': 8,    # Batch plus petit pour vitesse
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
            self.audio_capture = AudioCapture(
                sample_rate=AudioFormat.SAMPLE_RATE,
                channels=AudioFormat.CHANNELS,
                chunk_size=AudioFormat.CHUNK_SIZE
            )
            self.logger.info("✅ Capture audio initialisée")
            
            # Initialiser le VAD (Voice Activity Detection)
            self.vad = VoiceActivityDetector(mode=VADMode.AGGRESSIVE)
            self.logger.info("✅ VAD initialisé")
            
            # Initialiser le gestionnaire de parole continue
            self.speech_manager = ContinuousSpeechManager(
                speech_recognizer=self.speech_recognizer,
                pause_threshold=1.2,      # Pause plus courte pour temps réel
                min_segment_duration=0.2, # Segments plus courts
                max_batch_duration=8.0,   # Batches plus courts
                transcription_callback=self._on_transcription_received
            )
            self.logger.info("✅ Gestionnaire de parole continue initialisé")
            
            # Initialiser le TTS pour les réponses
            from peer.interfaces.sui.tts.base import TTSConfig, TTSEngineType
            tts_config = TTSConfig(
                engine_type=TTSEngineType.SIMPLE,
                language='fr',
                voice='Audrey (Premium)'
            )
            self.tts_engine = SimpleTTS(tts_config)
            self.logger.info("✅ Moteur TTS initialisé")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de l'initialisation: {e}")
            raise
    
    def start(self):
        """Démarre l'interface de communication orale."""
        if self.running:
            self.logger.warning("Interface déjà en cours")
            return
        
        self.running = True
        self.logger.info("🎙️ Démarrage de l'interface de communication orale")
        
        # Démarrer les composants
        self.speech_manager.start()
        
        # Message de bienvenue
        welcome_message = (
            "Interface de communication orale avec WhisperX démarrée. "
            "Vous pouvez maintenant parler et voir la transcription en temps réel. "
            "Dites 'arrêter' pour terminer."
        )
        self._speak_async(welcome_message)
        
        # Afficher l'interface
        self._display_interface()
        
        # Démarrer l'écoute audio
        self._start_audio_listening()
        
        # Boucle principale avec affichage temps réel
        self._main_loop()
    
    def stop(self):
        """Arrête l'interface de communication orale."""
        self.running = False
        self.listening = False
        
        if self.speech_manager:
            self.speech_manager.stop()
        
        if self.audio_capture:
            self.audio_capture.stop()
        
        self.logger.info("🛑 Interface de communication orale arrêtée")
        
        # Afficher les statistiques finales
        self._display_final_stats()
    
    def _start_audio_listening(self):
        """Démarre l'écoute audio avec traitement en temps réel."""
        self.listening = True
        
        def audio_callback(audio_data, sample_rate):
            """Callback appelé pour chaque chunk audio."""
            if not self.running or self.speaking:
                return
            
            # Convertir en numpy array
            import numpy as np
            audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Détecter l'activité vocale
            has_speech = self.vad.is_speech(audio_data, sample_rate)
            
            # Envoyer au gestionnaire de parole continue
            if has_speech or len(audio_np) > 0:
                self.speech_manager.add_audio_segment(audio_np, has_speech)
        
        # Démarrer la capture avec callback
        self.audio_capture.start_streaming(callback=audio_callback)
        self.logger.info("👂 Écoute audio démarrée")
    
    def _on_transcription_received(self, text: str, is_final: bool):
        """Callback appelé quand une transcription est reçue."""
        with self.transcription_display_lock:
            if is_final:
                # Transcription finale
                self.last_final_transcription = text
                self.current_transcription = ""
                
                # Mettre à jour les stats
                self.session_stats['transcriptions_count'] += 1
                self.session_stats['words_transcribed'] += len(text.split())
                
                # Traiter la commande
                self._process_voice_command(text)
                
            else:
                # Transcription partielle
                self.current_transcription = text
        
        # Mettre à jour l'affichage
        self._update_display()
    
    def _process_voice_command(self, text: str):
        """Traite une commande vocale reçue."""
        text_lower = text.lower().strip()
        
        self.logger.info(f\"🗣️ Commande reçue: '{text}'\"")
        
        # Commandes spéciales
        if any(word in text_lower for word in ['arrêter', 'arrêt', 'stop', 'quitter']):
            self._speak_async("D'accord, j'arrête l'interface. Au revoir!")
            # Attendre que la synthèse termine avant d'arrêter
            time.sleep(2)
            self.stop()
            return
        
        if any(word in text_lower for word in ['aide', 'help', 'aidez-moi']):
            response = (
                \"Je vous écoute en continu et transcris ce que vous dites. \"\n                \"Vous pouvez parler naturellement, je gère les pauses. \"\n                \"Dites 'arrêter' pour terminer l'interface.\"
            )
            self._speak_async(response)
            return
        
        if any(word in text_lower for word in ['heure', 'temps', 'quelle heure']):
            import datetime
            now = datetime.datetime.now()
            response = f\"Il est {now.strftime('%H heures %M')}.\"
            self._speak_async(response)
            return
        
        if any(word in text_lower for word in ['statistiques', 'stats', 'métriques']):
            stats = self.speech_manager.get_stats()
            response = (
                f\"Statistiques de la session: \"\n                f\"{stats['segments_processed']} segments traités, \"\n                f\"{stats['batches_completed']} batches transcrits, \"\n                f\"{self.session_stats['transcriptions_count']} transcriptions finales.\"
            )
            self._speak_async(response)
            return
        
        # Réponse générale
        response = f\"J'ai entendu: {text}. Comment puis-je vous aider?\"
        self._speak_async(response)
    
    def _speak_async(self, text: str):
        """Synthèse vocale asynchrone."""
        def speak_worker():
            self.speaking = True
            try:
                self.tts_engine.speak(text)
            except Exception as e:
                self.logger.error(f\"❌ Erreur TTS: {e}")
            finally:
                self.speaking = False
        
        threading.Thread(target=speak_worker, daemon=True).start()
    
    def _display_interface(self):
        """Affiche l'interface utilisateur."""
        print("\n" + "="*80)
        print("🎙️ INTERFACE DE COMMUNICATION ORALE TEMPS RÉEL - WHISPERX")
        print("="*80)
        print("📋 Commandes disponibles:")
        print("   • Parlez naturellement, je vous écoute en continu")
        print("   • 'aide' - Afficher l'aide")
        print("   • 'heure' - Demander l'heure")
        print("   • 'statistiques' - Voir les métriques")
        print("   • 'arrêter' - Terminer l'interface")
        print("\n🔴 ÉTAT: En écoute... Vous pouvez commencer à parler.\n")
    
    def _update_display(self):
        """Met à jour l'affichage de la transcription."""
        with self.transcription_display_lock:
            # Effacer les lignes précédentes
            print("\\r\" + \" \" * 100, end=\"\\r")
            
            # Afficher la transcription
            if self.current_transcription:
                print(f\"📝 [En cours]: {self.current_transcription}\", end=\"\\r")
            elif self.last_final_transcription:
                print(f\"✅ [Final]: {self.last_final_transcription}")
                print("🔴 En écoute...\", end=\"\\r")
    
    def _main_loop(self):
        """Boucle principale de l'interface."""
        try:
            while self.running:
                time.sleep(0.1)
                
                # Mise à jour périodique de l'affichage
                if time.time() % 5 < 0.1:  # Toutes les 5 secondes
                    self._show_status()
                
        except KeyboardInterrupt:
            print("\n⌨️ Interruption clavier détectée")
            self.stop()
    
    def _show_status(self):
        """Affiche le statut périodique."""
        if self.speech_manager:
            stats = self.speech_manager.get_stats()
            session_duration = time.time() - self.session_stats['start_time']
            
            status = (
                f\"⏱️ Session: {session_duration:.0f}s | \"\n                f\"📊 Segments: {stats['segments_processed']} | \"\n                f\"📝 Transcriptions: {self.session_stats['transcriptions_count']} | \"\n                f\"📈 Mots: {self.session_stats['words_transcribed']}\"
            )
            
            # Afficher en bas de l'écran sans perturber la transcription
            print(f\"\n{status}\", end=\"\\r")
    
    def _display_final_stats(self):
        """Affiche les statistiques finales."""
        session_duration = time.time() - self.session_stats['start_time']
        stats = self.speech_manager.get_stats() if self.speech_manager else {}
        
        print("\n\n" + "="*80)
        print("📊 STATISTIQUES DE LA SESSION")
        print("="*80)
        print(f\"⏱️ Durée totale: {session_duration:.1f} secondes")
        print(f\"📝 Transcriptions finales: {self.session_stats['transcriptions_count']}")
        print(f\"📈 Mots transcrits: {self.session_stats['words_transcribed']}")
        print(f\"🔄 Segments traités: {stats.get('segments_processed', 0)}")
        print(f\"📦 Batches complétés: {stats.get('batches_completed', 0)}")
        print(f\"⚡ Temps moy. transcription: {stats.get('avg_transcription_time', 0):.2f}s")
        
        if self.session_stats['transcriptions_count'] > 0:
            wpm = (self.session_stats['words_transcribed'] * 60) / session_duration
            print(f\"🎯 Vitesse moyenne: {wpm:.1f} mots/minute")
        
        print("\n✅ Session terminée. Merci d'avoir utilisé l'interface!")


def main():
    """Point d'entrée principal."""
    try:
        print("🚀 Démarrage de l'interface de communication orale temps réel...")
        
        # Créer et démarrer l'interface
        interface = RealTimeSpeechInterface()
        interface.start()
        
    except KeyboardInterrupt:
        print("\n⌨️ Arrêt demandé par l'utilisateur")
    except Exception as e:
        print(f\"❌ Erreur fatale: {e}")
        logging.error(f\"Erreur fatale dans l'interface: {e}")
    
    print("\n👋 Au revoir!")


if __name__ == \"__main__\":
    main()
