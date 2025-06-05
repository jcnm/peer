#!/usr/bin/env python3
"""
Interface SUI avec communication orale en temps réel ultra-rapide.

Cette interface permet :
- Communication orale bidirectionnelle en français
- Transcription en temps réel immédiate sans batching
- Affichage continu de ce qui est écouté 
- Expérience utilisateur fluide et réactive
"""

import os
import sys
import time
import threading
import logging
from typing import Optional, Dict, Any
from pathlib import Path
import queue
import numpy as np

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
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, 'src'))
sys.path.insert(0, current_dir)

from peer.interfaces.sui.stt.speech_recognizer import SpeechRecognizer
from peer.interfaces.sui.stt.audio_io import AudioCapture, VoiceActivityDetector, VADMode, AudioFormat
from peer.interfaces.sui.tts.simple_tts_engine import SimpleTTS
from peer.interfaces.sui.domain.models import SpeechRecognitionResult


class RealtimeVoiceInterface:
    """Interface de communication orale en temps réel ultra-rapide."""
    
    def __init__(self):
        self.logger = logging.getLogger("RealtimeVoiceInterface")
        
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
        self.tts_engine: Optional[SimpleTTS] = None
        
        # Buffer audio pour transcription directe
        self.audio_buffer = np.array([], dtype=np.float32)
        self.audio_buffer_lock = threading.Lock()
        self.transcription_thread = None
        self.last_transcription_time = 0
        
        # Affichage
        self.current_transcription = ""
        self.final_transcription = ""
        self.display_lock = threading.Lock()
        
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
        self.logger.info("🚀 Initialisation de l'interface vocale en temps réel ultrarapide")
        
        try:
            # Configuration WhisperX avec modèle small pour bon compromis
            stt_config = {
                'stt_settings': {
                    'engines': {
                        'whisperx': {
                            'enabled': True,
                            'model_name': 'small',  # Modèle équilibré (244 MB)
                            'language': 'fr',
                            'priority': 1,
                            'parameters': {
                                'batch_size': 3,    # Batch modéré
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
        self.logger.info("🎙️ Démarrage de l'interface vocale ultrarapide")
        
        # Message de bienvenue
        welcome_message = (
            "Interface vocale en temps réel démarrée. "
            "Vous pouvez parler et voir la transcription immédiatement. "
            "Dites 'arrêter' pour terminer."
        )
        self._speak_async(welcome_message)
        
        # Afficher l'interface
        self._display_interface()
        
        # Démarrer l'écoute audio et la transcription continue
        self._start_realtime_listening()
        
        # Boucle principale
        self._main_loop()
    
    def stop(self):
        """Arrête l'interface de communication orale."""
        self.running = False
        self.listening = False
        
        if self.audio_capture:
            self.audio_capture.stop_recording()
        
        self.logger.info("🛑 Interface vocale arrêtée")
        
        # Afficher les statistiques finales
        self._display_final_stats()
    
    def _start_realtime_listening(self):
        """Démarre l'écoute audio avec transcription en temps réel."""
        self.listening = True
        
        # Démarrer l'enregistrement
        if not self.audio_capture.start_recording():
            self.logger.error("❌ Impossible de démarrer l'enregistrement audio")
            return
            
        # Thread pour traiter l'audio et transcription continue
        def audio_processing_thread():
            buffer_update_count = 0
            transcription_count = 0
            
            while self.running and self.listening:
                if self.speaking:
                    # Pause pendant que l'IA parle
                    time.sleep(0.1)
                    
                    # Vider la file d'attente audio pour éviter les échos
                    try:
                        while not self.audio_capture.audio_queue.empty():
                            self.audio_capture.audio_queue.get_nowait()
                    except:
                        pass
                    
                    # Réinitialiser le buffer audio après la parole
                    with self.audio_buffer_lock:
                        self.audio_buffer = np.array([], dtype=np.float32)
                        
                    continue
                
                # Récupérer le prochain segment audio
                segment = self.audio_capture.get_audio_segment(timeout=0.1)
                if segment is None:
                    continue
                
                # Vérifier si c'est un écho
                recently_spoke = hasattr(self, '_last_speech_time') and \
                               (time.time() - self._last_speech_time < 1.0)
                
                if recently_spoke and segment.energy_level < 0.01:
                    # Ignorer les segments probablement causés par un écho
                    continue
                
                # Ajouter l'audio au buffer si suffisamment d'énergie
                if segment.has_speech and segment.energy_level >= 0.005:
                    with self.audio_buffer_lock:
                        # Ajouter le nouveau segment au buffer
                        if len(self.audio_buffer) == 0:
                            self.audio_buffer = segment.data.copy()
                        else:
                            # Concaténer mais limiter la taille du buffer à ~3 secondes max
                            # pour garder la transcription rapide
                            self.audio_buffer = np.concatenate([self.audio_buffer, segment.data])
                            if len(self.audio_buffer) > 48000:  # 3 secondes à 16kHz
                                # Garder les 3 dernières secondes
                                self.audio_buffer = self.audio_buffer[-48000:]
                        
                        buffer_update_count += 1
                        
                        # Effectuer une transcription après chaque ajout si suffisamment de temps écoulé
                        # (pour éviter de surcharger le CPU)
                        current_time = time.time()
                        time_since_last = current_time - self.last_transcription_time
                        
                        # Transcrire plus fréquemment (toutes les 200ms)
                        if time_since_last >= 0.2 and len(self.audio_buffer) > 1600:  # au moins 100ms d'audio
                            # Copier le buffer pour éviter les modifications pendant la transcription
                            audio_to_transcribe = self.audio_buffer.copy()
                            
                            # Transcription rapide
                            threading.Thread(
                                target=self._transcribe_audio, 
                                args=(audio_to_transcribe, False),
                                daemon=True
                            ).start()
                            
                            self.last_transcription_time = current_time
                            transcription_count += 1
                
                # Pause détectée ou silence prolongé? Finaliser la transcription
                elif not segment.has_speech and len(self.audio_buffer) > 0:
                    pause_duration = 0.5  # Finaliser après 500ms de silence
                    if time.time() - self.last_transcription_time >= pause_duration:
                        with self.audio_buffer_lock:
                            if len(self.audio_buffer) > 0:
                                # Transcription finale
                                audio_to_transcribe = self.audio_buffer.copy()
                                threading.Thread(
                                    target=self._transcribe_audio, 
                                    args=(audio_to_transcribe, True),
                                    daemon=True
                                ).start()
                                
                                # Réinitialiser le buffer après finalisation
                                self.audio_buffer = np.array([], dtype=np.float32)
                
                # Log périodique
                if buffer_update_count % 100 == 0:
                    self.logger.info(f"📊 Mises à jour buffer: {buffer_update_count}, Transcriptions: {transcription_count}")
        
        # Démarrer le thread de traitement audio
        self.transcription_thread = threading.Thread(target=audio_processing_thread, daemon=True)
        self.transcription_thread.start()
        
        self.logger.info("👂 Écoute et transcription en temps réel démarrées")
    
    def _transcribe_audio(self, audio_data: np.ndarray, is_final: bool):
        """Transcrit l'audio en texte."""
        try:
            start_time = time.time()
            
            # Transcription avec paramètres optimisés pour la vitesse
            result = self.speech_recognizer.transcribe_audio(
                audio_data,
                use_alignment=(is_final)  # Utiliser l'alignement seulement pour les transcriptions finales
            )
            
            processing_time = time.time() - start_time
            
            if result and result.text.strip():
                text = result.text.strip()
                
                # Éviter les échos
                if hasattr(self, '_last_spoken_text') and self._last_spoken_text:
                    similarity = self._text_similarity(text.lower(), self._last_spoken_text.lower())
                    if similarity > 0.5:  # Plus de 50% de similarité = probablement un écho
                        self.logger.info(f"🔇 Écho probable ignoré (similarité {similarity:.2f}): '{text}'")
                        return
                
                # Mettre à jour l'affichage
                with self.display_lock:
                    if is_final:
                        self.final_transcription = text
                        self.current_transcription = ""
                        
                        # Traiter la commande finale
                        self._process_voice_command(text)
                        
                        # Mettre à jour les stats
                        self.session_stats['transcriptions_count'] += 1
                        self.session_stats['words_transcribed'] += len(text.split())
                        
                        self.logger.info(f"✅ Transcription finale ({processing_time:.2f}s): '{text}'")
                    else:
                        self.current_transcription = text
                        self.logger.debug(f"🔤 Transcription partielle ({processing_time:.2f}s): '{text}'")
                
                # Mettre à jour l'affichage
                self._update_display()
                
        except Exception as e:
            self.logger.error(f"❌ Erreur transcription: {e}")
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """
        Calcule la similarité entre deux textes.
        Retourne une valeur entre 0 (complètement différents) et 1 (identiques).
        """
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
            
        common_words = words1.intersection(words2)
        total_unique_words = len(words1.union(words2))
        
        return len(common_words) / total_unique_words if total_unique_words > 0 else 0.0
    
    def _process_voice_command(self, text: str):
        """Traite une commande vocale reçue en répétant simplement le texte."""
        self.logger.info(f"🗣️ Transcription finale: '{text}'")
        
        # Construire la réponse
        response = f"Vous avez dit : {text}"
        
        # Mémoriser le texte parlé pour la détection d'écho
        self._last_spoken_text = response
        
        # Parler la réponse
        self._speak_async(response)
        
        # L'interface retourne automatiquement à l'écoute après que _speak_async ait terminé
        # et que self.speaking soit remis à False.
    
    def _speak_async(self, text: str):
        """Synthèse vocale asynchrone."""
        def speak_worker():
            # Marquer comme parlant pour empêcher l'écoute
            self.speaking = True
            self.logger.info(f"🔊 TTS: '{text}'")
            
            try:
                # Vider le buffer audio avant de parler pour éviter les échos
                with self.audio_buffer_lock:
                    self.audio_buffer = np.array([], dtype=np.float32)
                
                # Effectuer la synthèse vocale
                start_time = time.time()
                result = self.tts_engine.synthesize(text)
                
                if result.success:
                    # Calculer la durée approximative de la parole
                    speech_duration = len(text) / 15.0
                    actual_duration = time.time() - start_time
                    
                    # Attendre un peu après la fin de la parole pour éviter les échos
                    cooldown = max(0.5, speech_duration * 0.2)
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
        print("🎙️ INTERFACE VOCALE ULTRA-RAPIDE - TRANSCRIPTION INSTANTANÉE")
        print("="*80)
        print("📋 Commandes disponibles:")
        print("   • Parlez naturellement, votre voix est transcrite immédiatement")
        print("   • 'aide' - Afficher l'aide")
        print("   • 'heure' - Demander l'heure")
        print("   • 'arrêter' - Terminer l'interface")
        print("\n🔴 ÉTAT: En écoute... Parlez maintenant.\n")
    
    def _update_display(self):
        """Met à jour l'affichage de la transcription."""
        with self.display_lock:
            # Effacer les lignes précédentes
            print("\r" + " " * 100, end="\r")
            
            # Afficher la transcription
            if self.current_transcription:
                print(f"🎤 [En direct]: {self.current_transcription}", end="\r")
            elif self.final_transcription:
                print(f"✅ [Final]: {self.final_transcription}")
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
        session_duration = time.time() - self.session_stats['start_time']
        
        status = (
            f"⏱️ Session: {session_duration:.0f}s | "
            f"📝 Transcriptions: {self.session_stats['transcriptions_count']} | "
            f"📈 Mots: {self.session_stats['words_transcribed']}"
        )
        
        # Afficher en bas de l'écran sans perturber la transcription
        print(f"\n{status}", end="\r")
    
    def _display_final_stats(self):
        """Affiche les statistiques finales."""
        session_duration = time.time() - self.session_stats['start_time']
        
        print("\n\n" + "="*80)
        print("📊 STATISTIQUES DE LA SESSION")
        print("="*80)
        print(f"⏱️ Durée totale: {session_duration:.1f} secondes")
        print(f"📝 Transcriptions finales: {self.session_stats['transcriptions_count']}")
        print(f"📈 Mots transcrits: {self.session_stats['words_transcribed']}")
        
        if self.session_stats['transcriptions_count'] > 0:
            wpm = (self.session_stats['words_transcribed'] * 60) / session_duration
            print(f"🎯 Vitesse moyenne: {wpm:.1f} mots/minute")
        
        print("\n✅ Session terminée. Merci d'avoir utilisé l'interface!")


def main():
    """Point d'entrée principal."""
    try:
        print("🚀 Démarrage de l'interface vocale ultra-rapide...")
        
        # Créer et démarrer l'interface
        interface = RealtimeVoiceInterface()
        interface.start()
        
    except KeyboardInterrupt:
        print("\n⌨️ Arrêt demandé par l'utilisateur")
    except Exception as e:
        print(f"❌ Erreur fatale: {e}")
        logging.error(f"Erreur fatale dans l'interface: {e}")
    
    print("\n👋 Au revoir!")


if __name__ == "__main__":
    main()
