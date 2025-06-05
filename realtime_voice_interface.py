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
    level=logging.DEBUG,  # Changé de INFO à DEBUG pour plus de détails
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.expanduser('~/.peer/sui_realtime.log'), mode='a')
    ]
)

# Ajouter le chemin source pour l'importation
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, 'src'))
sys.path.insert(0, current_dir)

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
        self._last_speech_time = 0  # Pour suivre quand l'IA a fini de parler
        self._last_spoken_text = ""  # Pour détecter les échos
        
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
            audio_config = {
                'sample_rate': AudioFormat.SAMPLE_RATE,
                'channels': AudioFormat.CHANNELS,
                'chunk_size': AudioFormat.CHUNK_SIZE,
                'vad_sensitivity': 3  # Mode VERY_AGGRESSIVE pour maximiser la détection
            }
            self.audio_capture = AudioCapture(audio_config)
            self.logger.info("✅ Capture audio initialisée")
            
            # Initialiser le VAD (Voice Activity Detection)
            self.vad = VoiceActivityDetector(mode=VADMode.VERY_AGGRESSIVE)
            self.logger.info("✅ VAD initialisé")
            
            # Initialiser le gestionnaire de parole continue
            self.speech_manager = ContinuousSpeechManager(
                speech_recognizer=self.speech_recognizer,
                pause_threshold=0.9,      # Seuil de pause réduit pour être plus réactif aux pauses
                min_segment_duration=0.05, # Segments courts pour capturer toute parole
                max_batch_duration=5.0,   # Batches plus courts pour réduire la latence
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
            self.audio_capture.stop_recording()
        
        self.logger.info("🛑 Interface de communication orale arrêtée")
        
        # Afficher les statistiques finales
        self._display_final_stats()
    
    def _start_audio_listening(self):
        """Démarre l'écoute audio avec traitement en temps réel."""
        self.listening = True
        
        # Démarrer l'enregistrement
        if not self.audio_capture.start_recording():
            self.logger.error("❌ Impossible de démarrer l'enregistrement audio")
            return
        
        # Thread pour traiter les segments audio en continu
        def audio_processing_loop():
            """Boucle de traitement des segments audio."""
            segment_count = 0
            speech_count = 0
            
            while self.running and self.listening:
                if self.speaking:
                    # Pause complète pendant que l'IA parle
                    time.sleep(0.1)
                    
                    # Vider la file d'attente audio pour éviter les segments capturés pendant la parole
                    try:
                        while not self.audio_capture.audio_queue.empty():
                            self.audio_capture.audio_queue.get_nowait()
                    except:
                        pass
                        
                    continue
                
                # Récupérer le prochain segment audio
                segment = self.audio_capture.get_audio_segment(timeout=0.5)
                if segment is None:
                    continue
                
                # Détecter les segments trop faibles qui pourraient être des échos
                # Ignorer les segments de faible énergie juste après avoir parlé
                recently_spoke = hasattr(self, '_last_speech_time') and \
                               (time.time() - self._last_speech_time < 1.0)
                
                if recently_spoke and segment.energy_level < 0.01:
                    # Ignorer les segments probablement causés par un écho
                    self.logger.debug(f"🔇 Écho potentiel ignoré: énergie={segment.energy_level:.4f}")
                    continue
                
                segment_count += 1
                if segment.has_speech:
                    # Appliquer un seuil d'énergie plus élevé juste après avoir parlé
                    energy_threshold = 0.005
                    if recently_spoke:
                        energy_threshold = 0.015  # Seuil plus élevé après parole
                    
                    if segment.energy_level >= energy_threshold:
                        speech_count += 1
                        self.logger.debug(f"🎤 Segment valide: énergie={segment.energy_level:.4f}")
                    else:
                        # Forcer has_speech à False pour les segments de faible énergie
                        segment.has_speech = False
                        self.logger.debug(f"🔇 Segment ignoré (énergie trop faible): {segment.energy_level:.4f}")
                        continue
                
                # Log périodique pour diagnostiquer
                if segment_count % 50 == 0:
                    self.logger.info(f"📊 Segments traités: {segment_count}, avec parole: {speech_count}")
                    # Forcer la finalisation uniquement si nécessaire
                    if self.speech_manager and hasattr(self.speech_manager, 'current_batch'):
                        current_batch = self.speech_manager.current_batch
                        if current_batch and time.time() - current_batch.last_activity_time > 1.0:
                            self.logger.info("🔄 Finalisation forcée après pause détectée")
                            self.speech_manager.force_finalize_current_batch()
                
                # Détecter les pauses naturelles pour finaliser rapidement
                last_segment_time = getattr(segment, 'end_time', time.time())
                pause_since_last = time.time() - last_segment_time
                if pause_since_last > 1.0 and not segment.has_speech and self.speech_manager and hasattr(self.speech_manager, 'force_finalize_current_batch'):
                    # Finaliser si une pause de plus de 1s est détectée
                    self.speech_manager.force_finalize_current_batch()
                    self.logger.info(f"🔄 Finalisation forcée après pause de {pause_since_last:.1f}s")
                
                # Convertir en format approprié pour le gestionnaire de parole
                # Le segment contient déjà les données en float32
                audio_np = segment.data
                has_speech = segment.has_speech
                
                self.logger.debug(f"🎤 Segment audio: {len(audio_np)} échantillons, parole={has_speech}, énergie={segment.energy_level:.3f}")
                
                # Envoyer au gestionnaire de parole continue
                try:
                    self.speech_manager.add_audio_segment(audio_np, has_speech)
                except Exception as e:
                    self.logger.error(f"❌ Erreur traitement audio: {e}")
        
        # Démarrer le thread de traitement audio
        audio_thread = threading.Thread(target=audio_processing_loop, daemon=True)
        audio_thread.start()
        
        self.logger.info("👂 Écoute audio démarrée")
    
    def _on_transcription_received(self, text: str, is_final: bool):
        """Callback appelé quand une transcription est reçue."""
        # Ignorer les transcriptions vides ou trop courtes
        if not text or len(text.strip()) < 2:
            self.logger.debug(f"⏭️ Transcription ignorée (trop courte): '{text}'")
            return
            
        # Ignorer les transcriptions qui ressemblent à des échos de ce que l'IA vient de dire
        if hasattr(self, '_last_spoken_text') and self._last_spoken_text:
            # Calculer la similarité entre la transcription et la dernière chose dite par l'IA
            similarity = self._text_similarity(text.lower(), self._last_spoken_text.lower())
            
            # Si la transcription ressemble beaucoup à ce que l'IA vient de dire, l'ignorer
            if similarity > 0.5:  # Plus de 50% de similarité = probablement un écho
                self.logger.info(f"🔇 Écho probable ignoré (similarité {similarity:.2f}): '{text}'")
                return
        
        with self.transcription_display_lock:
            if is_final:
                # Transcription finale
                self.last_final_transcription = text
                self.current_transcription = ""
                
                # Mettre à jour les stats
                self.session_stats['transcriptions_count'] += 1
                self.session_stats['words_transcribed'] += len(text.split())
                
                self.logger.info(f"✅ Transcription finale: '{text}'")
                
                # Traiter la commande
                self._process_voice_command(text)
                
            else:
                # Transcription partielle
                self.current_transcription = text
        
        # Mettre à jour l'affichage
        self._update_display()
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """
        Calcule la similarité entre deux textes.
        Retourne une valeur entre 0 (complètement différents) et 1 (identiques).
        """
        # Méthode simple: vérifier combien de mots sont communs
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
            
        common_words = words1.intersection(words2)
        total_unique_words = len(words1.union(words2))
        
        return len(common_words) / total_unique_words if total_unique_words > 0 else 0.0
    
    def _process_voice_command(self, text: str):
        """Traite une commande vocale reçue."""
        text_lower = text.lower().strip()
        
        self.logger.info(f"🗣️ Commande reçue: '{text}'")
        
        # Commandes spéciales
        if any(word in text_lower for word in ['arrêter', 'arrêt', 'stop', 'quitter']):
            response = "D'accord, j'arrête l'interface. Au revoir!"
            self._last_spoken_text = response  # Mémoriser pour éviter l'écho
            self._speak_async(response)
            # Attendre que la synthèse termine avant d'arrêter
            time.sleep(2)
            self.stop()
            return
        
        if any(word in text_lower for word in ['aide', 'help', 'aidez-moi']):
            response = (
                "Je vous écoute en continu et transcris ce que vous dites. "
                "Vous pouvez parler naturellement, je gère les pauses. "
                "Dites 'arrêter' pour terminer l'interface."
            )
            self._last_spoken_text = response  # Mémoriser pour éviter l'écho
            self._speak_async(response)
            return
        
        if any(word in text_lower for word in ['heure', 'temps', 'quelle heure']):
            import datetime
            now = datetime.datetime.now()
            response = f"Il est {now.strftime('%H heures %M')}."
            self._last_spoken_text = response  # Mémoriser pour éviter l'écho
            self._speak_async(response)
            return
        
        if any(word in text_lower for word in ['statistiques', 'stats', 'métriques']):
            stats = self.speech_manager.get_stats()
            response = (
                f"Statistiques de la session: "
                f"{stats['segments_processed']} segments traités, "
                f"{stats['batches_completed']} batches transcrits, "
                f"{self.session_stats['transcriptions_count']} transcriptions finales."
            )
            self._last_spoken_text = response  # Mémoriser pour éviter l'écho
            self._speak_async(response)
            return
        
        # Réponse générale
        response = f"J'ai entendu: {text}. Comment puis-je vous aider?"
        self._last_spoken_text = response  # Mémoriser pour éviter l'écho
        self._speak_async(response)
    
    def _speak_async(self, text: str):
        """Synthèse vocale asynchrone."""
        def speak_worker():
            # Marquer comme parlant pour empêcher l'écoute
            self.speaking = True
            self.logger.info(f"🔊 TTS: '{text}'")
            
            try:
                # Vider la file d'attente audio avant de parler pour éviter les échos
                if hasattr(self.audio_capture, 'audio_queue'):
                    try:
                        while not self.audio_capture.audio_queue.empty():
                            self.audio_capture.audio_queue.get_nowait()
                    except:
                        pass
                
                # Effectuer la synthèse vocale
                start_time = time.time()
                result = self.tts_engine.synthesize(text)
                
                if result.success:
                    # Calculer la durée approximative de la parole (~ 15 caractères/seconde)
                    speech_duration = len(text) / 15.0
                    actual_duration = time.time() - start_time
                    
                    # Attendre un peu après la fin de la parole pour éviter les échos
                    # Au moins 500ms ou 20% de la durée de parole, selon le plus grand
                    cooldown = max(0.5, speech_duration * 0.2)
                    self.logger.debug(f"⏱️ Attente post-parole: {cooldown:.2f}s")
                    time.sleep(cooldown)
                    
                    # Marquer le temps de fin de parole pour la détection d'écho
                    self._last_speech_time = time.time()
                else:
                    self.logger.error(f"❌ Erreur TTS: {result.message}")
            except Exception as e:
                self.logger.error(f"❌ Erreur TTS: {e}")
            finally:
                # Réinitialiser l'état de parole
                self.speaking = False
                self.logger.debug("🎙️ Reprise de l'écoute")
        
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
            print("\r" + " " * 100, end="\r")
            
            # Afficher la transcription
            if self.current_transcription:
                print(f"📝 [En cours]: {self.current_transcription}", end="\r")
            elif self.last_final_transcription:
                print(f"✅ [Final]: {self.last_final_transcription}")
                print("🔴 En écoute...", end="\r")
    
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
                f"⏱️ Session: {session_duration:.0f}s | "
                f"📊 Segments: {stats['segments_processed']} | "
                f"📝 Transcriptions: {self.session_stats['transcriptions_count']} | "
                f"📈 Mots: {self.session_stats['words_transcribed']}"
            )
            
            # Afficher en bas de l'écran sans perturber la transcription
            print(f"\n{status}", end="\r")
    
    def _display_final_stats(self):
        """Affiche les statistiques finales."""
        session_duration = time.time() - self.session_stats['start_time']
        stats = self.speech_manager.get_stats() if self.speech_manager else {}
        
        print("\n\n" + "="*80)
        print("📊 STATISTIQUES DE LA SESSION")
        print("="*80)
        print(f"⏱️ Durée totale: {session_duration:.1f} secondes")
        print(f"📝 Transcriptions finales: {self.session_stats['transcriptions_count']}")
        print(f"📈 Mots transcrits: {self.session_stats['words_transcribed']}")
        print(f"🔄 Segments traités: {stats.get('segments_processed', 0)}")
        print(f"📦 Batches complétés: {stats.get('batches_completed', 0)}")
        print(f"⚡ Temps moy. transcription: {stats.get('avg_transcription_time', 0):.2f}s")
        
        if self.session_stats['transcriptions_count'] > 0:
            wpm = (self.session_stats['words_transcribed'] * 60) / session_duration
            print(f"🎯 Vitesse moyenne: {wpm:.1f} mots/minute")
        
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
        print(f"❌ Erreur fatale: {e}")
        logging.error(f"Erreur fatale dans l'interface: {e}")
    
    print("\n👋 Au revoir!")


if __name__ == "__main__":
    main()
