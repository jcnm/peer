"""
Enhanced Voice Interface State Machine for Peer SUI.

This module implements an intelligent voice processing system with continuous listening,
smart silence detection, and proper state management.

États de la machine:
- IDLE: En attente d'activation
- LISTENING: Écoute active avec détection de silence
- PROCESSING: Traitement STT et NLP
- INTENT_VALIDATION: Confirmation utilisateur
- AWAIT_RESPONSE: Attente de la réponse du démon
"""

import os
import time
import threading
import queue
import logging
import enum
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from collections import deque

import numpy as np

from peer.interfaces.sui.stt.audio_io import AudioCapture
from peer.interfaces.sui.stt.speech_recognizer import SpeechRecognizer
from peer.interfaces.sui.nlu.domain.nlp_engine import NLPEngine
from peer.interfaces.sui.tts.text_to_speech import TextToSpeech
from peer.interfaces.sui.domain.models import SpeechRecognitionResult, VoiceActivityMetrics


class VoiceInterfaceState(enum.Enum):
    """États de la machine à états vocale."""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    INTENT_VALIDATION = "intent_validation"
    AWAIT_RESPONSE = "await_response"


@dataclass
class AudioBuffer:
    """Buffer audio avec métadonnées."""
    data: bytes
    timestamp: float
    is_speech: bool = False
    energy_level: float = 0.0


@dataclass
class IntentContext:
    """Contexte d'une intention extraite."""
    text: str
    intent_type: str
    parameters: Dict[str, Any]
    confidence: float
    summary: str = ""


class VoiceStateMachine:
    """Machine à états pour le traitement vocal intelligent."""
    
    def __init__(self,
                 audio_capture: AudioCapture,
                 speech_recognizer: SpeechRecognizer,
                 nlp_engine: NLPEngine,
                 tts_engine: TextToSpeech,
                 peer_daemon=None):
        """
        Initialise la machine à états vocale.
        
        Args:
            audio_capture: Système de capture audio
            speech_recognizer: Moteur de reconnaissance vocale
            nlp_engine: Moteur de compréhension du langage naturel
            tts_engine: Moteur de synthèse vocale
            peer_daemon: Démon Peer pour exécution des commandes
        """
        self.logger = logging.getLogger("VoiceStateMachine")
        
        # Composants
        self.audio_capture = audio_capture
        self.speech_recognizer = speech_recognizer
        self.nlp_engine = nlp_engine
        self.tts_engine = tts_engine
        self.peer_daemon = peer_daemon
        
        # État de la machine
        self.state = VoiceInterfaceState.IDLE
        self.is_running = False
        
        # Configuration des seuils de silence
        self.short_silence_ms = 600    # Court silence en ms
        self.long_silence_ms = 1200    # Long silence en ms
        self.max_audio_duration_s = 30  # Durée max d'écoute en secondes
        
        # Buffers audio
        self.audio_buffer: List[AudioBuffer] = []
        self.text_fragments: List[str] = []
        
        # Contexte actuel
        self.current_intent: Optional[IntentContext] = None
        self.intent_history: List[IntentContext] = []
        
        # Contrôleurs de silence
        self.silence_timer = 0.0
        self.last_speech_time = 0.0
        
        # Threads
        self.processing_thread: Optional[threading.Thread] = None
        self.listening_thread: Optional[threading.Thread] = None
        
        # Files d'attente
        self.command_queue = queue.Queue()
        self.global_command_queue = queue.Queue()
        
        # Commandes globales
        self.global_commands = ["stop", "arrête", "cancel", "annule", "wait", "attends", "resume", "reprends", "restart", "recommence"]
        
        # Handler de commandes (peut être défini après l'initialisation)
        self.command_handler: Optional[Callable] = None
        
        # Statistiques
        self.commands_processed = 0
        
        self.logger.info("🎛️ Machine à états vocale initialisée")
    
    @property
    def current_state(self) -> VoiceInterfaceState:
        """Retourne l'état actuel de la machine."""
        return self.state
    
    def start(self):
        """Démarre la machine à états vocale."""
        if self.is_running:
            self.logger.warning("⚠️ La machine à états est déjà en cours d'exécution")
            return
        
        self.is_running = True
        self.state = VoiceInterfaceState.IDLE
        
        # Démarrer les threads
        self.listening_thread = threading.Thread(target=self._listening_loop, daemon=True)
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        
        self.listening_thread.start()
        self.processing_thread.start()
        
        self.logger.info("🎛️ Machine à états vocale démarrée")
        self.say("Interface vocale Peer prête. Vous pouvez commencer à parler.")
    
    def stop(self):
        """Arrête la machine à états vocale."""
        self.is_running = False
        self.state = VoiceInterfaceState.IDLE
        
        # Attendre l'arrêt des threads
        if self.listening_thread and self.listening_thread.is_alive():
            self.listening_thread.join(timeout=2.0)
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=2.0)
        
        self.logger.info("🎛️ Machine à états vocale arrêtée")
    
    def say(self, text: str, priority: int = 0):
        """Synthèse vocale avec gestion des priorités."""
        try:
            if self.tts_engine:
                self.logger.info(f"🔊 TTS: {text}")
                result = self.tts_engine.synthesize(text)
                if not result.success:
                    self.logger.warning(f"⚠️ Échec TTS: {result.error_message}")
            else:
                self.logger.warning("⚠️ Moteur TTS non disponible")
        except Exception as e:
            self.logger.error(f"❌ Erreur TTS: {e}")
    
    def _listening_loop(self):
        """Boucle d'écoute continue."""
        self.logger.info("🎧 Boucle d'écoute démarrée")
        
        while self.is_running:
            try:
                # Vérifier les commandes globales
                self._check_global_commands()
                
                # Machine à états
                if self.state == VoiceInterfaceState.IDLE:
                    self._handle_idle_state()
                elif self.state == VoiceInterfaceState.LISTENING:
                    self._handle_listening_state()
                elif self.state == VoiceInterfaceState.INTENT_VALIDATION:
                    self._handle_intent_validation_state()
                
                # Petite pause pour éviter une surcharge CPU
                time.sleep(0.05)
                
            except Exception as e:
                self.logger.error(f"❌ Erreur dans la boucle d'écoute: {e}")
                time.sleep(0.5)
        
        self.logger.info("🎧 Boucle d'écoute terminée")
    
    def _processing_loop(self):
        """Boucle de traitement des commandes."""
        self.logger.info("🧠 Boucle de traitement démarrée")
        
        while self.is_running:
            try:
                # Traiter les commandes en attente
                try:
                    command_data = self.command_queue.get(timeout=1.0)
                    self._process_command(command_data)
                    self.command_queue.task_done()
                except queue.Empty:
                    continue
                    
            except Exception as e:
                self.logger.error(f"❌ Erreur dans la boucle de traitement: {e}")
                time.sleep(0.5)
        
        self.logger.info("🧠 Boucle de traitement terminée")
    
    def _handle_idle_state(self):
        """Gère l'état IDLE - détection d'activation vocale."""
        if self.detect_hotword() or self.manual_trigger():
            self.state = VoiceInterfaceState.LISTENING
            self.start_microphone()
            self.logger.info("🎤 Transition vers LISTENING")
    
    def _handle_listening_state(self):
        """Gère l'état LISTENING - écoute active avec détection de silence."""
        current_time = time.time()
        
        # Capturer un chunk audio
        audio_chunk = self._record_audio_chunk()
        if not audio_chunk:
            return
        
        # Analyser le chunk
        audio_buffer = AudioBuffer(
            data=audio_chunk,
            timestamp=current_time,
            energy_level=self._calculate_energy(audio_chunk)
        )
        
        # Détecter l'activité vocale
        vad_result = self._detect_voice_activity(audio_chunk)
        audio_buffer.is_speech = vad_result.speech_detected
        
        self.audio_buffer.append(audio_buffer)
        
        if self.is_short_silence():
            # Court silence - traiter le chunk par STT
            self._send_to_stt(audio_chunk)
            self.silence_timer = 0
        elif self.is_long_silence():
            # Long silence - finaliser le traitement
            self._transition_to_processing()
        else:
            # Parole continue
            self.silence_timer += 0.05  # Correspond au sleep dans la boucle
            self.last_speech_time = current_time
        
        # Vérifier la durée maximale
        if len(self.audio_buffer) > 0:
            total_duration = current_time - self.audio_buffer[0].timestamp
            if total_duration > self.max_audio_duration_s:
                self.logger.info("⏰ Durée maximale atteinte, traitement forcé")
                self._transition_to_processing()
    
    def _handle_intent_validation_state(self):
        """Gère l'état INTENT_VALIDATION - confirmation utilisateur."""
        if not self.current_intent:
            self.state = VoiceInterfaceState.IDLE
            return
        
        # Écouter la réponse de confirmation
        audio_chunk = self._record_audio_chunk()
        if audio_chunk and self._detect_voice_activity(audio_chunk).speech_detected:
            confirmation_result = self._listen_for_confirmation_or_interrupt()
            
            if confirmation_result == "yes":
                self.stop_microphone()
                self.intent_history.append(self.current_intent)
                self._send_to_daemon(self.current_intent)
                self.state = VoiceInterfaceState.AWAIT_RESPONSE
            elif confirmation_result in ["no", "cancel"]:
                self.stop_microphone()
                self.say("D'accord, j'annule la demande.")
                self.state = VoiceInterfaceState.IDLE
                self.current_intent = None
            elif confirmation_result in self.global_commands:
                self._handle_global_command(confirmation_result)
                self.state = VoiceInterfaceState.IDLE
            else:
                self.stop_microphone()
                self.say("Je n'ai pas bien compris, peux-tu répéter ?")
                self.state = VoiceInterfaceState.LISTENING
    
    def _transition_to_processing(self):
        """Transition vers l'état PROCESSING."""
        self.stop_microphone()
        self.state = VoiceInterfaceState.PROCESSING
        
        # Mettre le traitement en queue
        processing_data = {
            'type': 'speech_processing',
            'audio_buffer': self.audio_buffer.copy(),
            'text_fragments': self.text_fragments.copy()
        }
        self.command_queue.put(processing_data)
        
        # Réinitialiser les buffers
        self.audio_buffer.clear()
        self.text_fragments.clear()
        self.silence_timer = 0
    
    def _process_command(self, command_data: Dict[str, Any]):
        """Traite une commande selon son type."""
        command_type = command_data.get('type')
        
        if command_type == 'speech_processing':
            self._process_speech_command(command_data)
        elif command_type == 'global_command':
            self._handle_global_command(command_data.get('command'))
        else:
            self.logger.warning(f"⚠️ Type de commande inconnu: {command_type}")
    
    def _process_speech_command(self, command_data: Dict[str, Any]):
        """Traite une commande vocale complète."""
        try:
            self.say("Laisse-moi comprendre ce que tu veux dire…")
            
            # Étape 1: Transcription STT
            text_fragments = command_data.get('text_fragments', [])
            full_text = self._concatenate_text_fragments(text_fragments)
            
            if not full_text.strip():
                self.say("Désolé, je n'ai pas compris ce que tu as dit.")
                self.state = VoiceInterfaceState.IDLE
                return
            
            self.logger.info(f"📝 Texte complet: {full_text}")
            
            # Étape 2: Analyse NLP
            nlp_output = self._run_nlp(full_text)
            if not nlp_output:
                self.say("Désolé, je n'ai pas pu analyser ta demande.")
                self.state = VoiceInterfaceState.IDLE
                return
            
            # Étape 3: Extraction d'intention NLU
            intent = self._run_nlu(nlp_output)
            if not intent:
                self.say("Désolé, je n'ai pas compris ton intention.")
                self.state = VoiceInterfaceState.IDLE
                return
            
            self.current_intent = intent
            
            # Étape 4: Confirmation utilisateur
            self.state = VoiceInterfaceState.INTENT_VALIDATION
            self.say(f"Tu veux faire ceci : {intent.summary}, c'est bien ça ?")
            self.start_microphone()
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors du traitement de la commande vocale: {e}")
            self.say("Désolé, une erreur s'est produite lors du traitement.")
            self.state = VoiceInterfaceState.IDLE
    
    def _send_to_daemon(self, intent: IntentContext):
        """Envoie l'intention au démon Peer avec feedback vocal amélioré."""
        try:
            if not self.peer_daemon:
                self.say("Le service Peer n'est pas disponible. Je ne peux pas traiter votre demande.")
                self.state = VoiceInterfaceState.IDLE
                return
            
            # Announce what we're doing
            self.say(f"Je traite votre demande : {intent.summary}")
            
            # Utiliser le command_handler si disponible
            if self.command_handler:
                self.logger.info(f"📤 Utilisation du command_handler: {intent.intent_type}")
                
                # Créer un objet similaire à celui attendu par le handler
                class MockIntentResult:
                    def __init__(self, intent_context):
                        self.command_type = intent_context.intent_type
                        self.parameters = intent_context.parameters
                        self.confidence = intent_context.confidence
                
                mock_intent = MockIntentResult(intent)
                
                # Announce the processing step
                self.say("Je transmets votre commande au système principal.")
                
                response_message = self.command_handler(mock_intent, intent.text)
                
                # Incrémenter les statistiques
                self.commands_processed += 1
                
                if response_message:
                    # Provide detailed feedback about what was accomplished
                    completion_feedback = self._generate_completion_feedback(intent, response_message)
                    self.say(completion_feedback)
                else:
                    self.say("La commande a été traitée mais aucun résultat spécifique n'est disponible.")
                
                self.state = VoiceInterfaceState.IDLE
                return
            
            # Fallback vers la simulation si pas de handler
            self.logger.info(f"📤 Envoi au démon: {intent.intent_type}")
            self.say("Je transmets votre demande au système. Veuillez patienter un moment.")
            self.state = VoiceInterfaceState.AWAIT_RESPONSE
            threading.Timer(2.0, self._simulate_daemon_response).start()
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de l'envoi au démon: {e}")
            self.say(f"Désolé, une erreur s'est produite lors du traitement de votre demande : {str(e)}")
            self.state = VoiceInterfaceState.IDLE
    
    def _generate_completion_feedback(self, intent: IntentContext, response_message: str) -> str:
        """Generate detailed feedback about what was accomplished."""
        intent_type = intent.intent_type.lower()
        
        # Create context-aware feedback based on the intent type
        feedback_templates = {
            "help": "J'ai récupéré les informations d'aide. Voici ce que j'ai trouvé :",
            "status": "J'ai vérifié le statut du système. Voici les informations :",
            "time": "J'ai consulté l'horloge système. Il est actuellement :",
            "date": "J'ai vérifié la date. Nous sommes le :",
            "version": "J'ai consulté les informations de version. Voici les détails :",
            "capabilities": "J'ai listé mes capacités. Voici ce que je peux faire :",
            "echo": "J'ai bien reçu votre message et je le répète :",
            "quit": "J'ai initié la procédure d'arrêt. Le système va s'arrêter maintenant.",
            "analyze": "J'ai terminé l'analyse. Voici les résultats :",
            "analysis": "L'analyse est terminée. Voici ce que j'ai découvert :",
        }
        
        prefix = feedback_templates.get(intent_type, "J'ai traité votre demande. Voici le résultat :")
        
        # Combine the contextual prefix with the actual response
        if response_message and response_message.strip():
            return f"{prefix} {response_message}"
        else:
            return f"{prefix} La commande a été exécutée avec succès."
    
    def _simulate_daemon_response(self):
        """Simule une réponse du démon (à remplacer par la vraie implémentation)."""
        response = {
            'success': True,
            'message': 'Commande exécutée avec succès',
            'details': 'Détails de l\'exécution...'
        }
        
        self.say(f"Voici le résultat : {response['message']}")
        self.logger.info(f"📋 Détails: {response['details']}")
        self.state = VoiceInterfaceState.IDLE
    
    # Méthodes utilitaires
    
    def detect_hotword(self) -> bool:
        """Détecte un mot d'activation."""
        # TODO: Implémenter la détection de hotword
        return False
    
    def manual_trigger(self) -> bool:
        """Déclenchement manuel (toujours actif pour l'instant)."""
        return True
    
    def start_microphone(self):
        """Active le microphone."""
        if self.audio_capture:
            try:
                self.audio_capture.start_recording()
                self.logger.debug("🎤 Microphone activé")
            except Exception as e:
                self.logger.error(f"❌ Erreur activation microphone: {e}")
    
    def stop_microphone(self):
        """Désactive le microphone."""
        if self.audio_capture:
            try:
                self.audio_capture.stop_recording()
                self.logger.debug("🎤 Microphone désactivé")
            except Exception as e:
                self.logger.error(f"❌ Erreur désactivation microphone: {e}")
    
    def _record_audio_chunk(self) -> Optional[bytes]:
        """Enregistre un chunk audio."""
        try:
            if self.audio_capture and self.audio_capture.is_recording:
                return self.audio_capture.get_audio_chunk()
        except Exception as e:
            self.logger.error(f"❌ Erreur enregistrement chunk: {e}")
        return None
    
    def _calculate_energy(self, audio_data: bytes) -> float:
        """Calcule l'énergie d'un chunk audio."""
        try:
            if not audio_data:
                return 0.0
            audio_np = np.frombuffer(audio_data, dtype=np.int16)
            return float(np.sqrt(np.mean(audio_np.astype(np.float64) ** 2)))
        except Exception:
            return 0.0
    
    def _detect_voice_activity(self, audio_data: bytes) -> VoiceActivityMetrics:
        """Détecte l'activité vocale dans un chunk."""
        try:
            if self.audio_capture:
                # Utiliser la méthode VAD existante
                return self.audio_capture._detect_voice_activity(audio_data)
        except Exception as e:
            self.logger.error(f"❌ Erreur VAD: {e}")
        
        # Fallback simple basé sur l'énergie
        energy = self._calculate_energy(audio_data)
        return VoiceActivityMetrics(
            speech_detected=energy > 300,  # Seuil simple
            energy_level=energy,
            speech_probability=min(1.0, energy / 1000.0)
        )
    
    def is_short_silence(self) -> bool:
        """Vérifie si on a un court silence."""
        return self.silence_timer > (self.short_silence_ms / 1000.0)
    
    def is_long_silence(self) -> bool:
        """Vérifie si on a un long silence."""
        return self.silence_timer > (self.long_silence_ms / 1000.0)
    
    def _send_to_stt(self, audio_chunk: bytes):
        """Envoie un chunk audio au STT."""
        try:
            if self.speech_recognizer:
                # Conversion des bytes en numpy array
                audio_np = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0
                result = self.speech_recognizer.transcribe(audio_np)
                if result and result.text.strip():
                    self.text_fragments.append(result.text.strip())
                    self.logger.debug(f"📝 Fragment STT: {result.text}")
        except Exception as e:
            self.logger.error(f"❌ Erreur STT: {e}")
    
    def _concatenate_text_fragments(self, fragments: List[str]) -> str:
        """Concatène les fragments de texte."""
        return " ".join(fragment.strip() for fragment in fragments if fragment.strip())
    
    def _run_nlp(self, text: str) -> Optional[Dict[str, Any]]:
        """Exécute l'analyse NLP."""
        try:
            if self.nlp_engine:
                # TODO: Adapter selon l'interface NLP réelle
                return {"processed_text": text, "entities": [], "sentiment": "neutral"}
        except Exception as e:
            self.logger.error(f"❌ Erreur NLP: {e}")
        return None
    
    def _run_nlu(self, nlp_output: Dict[str, Any]) -> Optional[IntentContext]:
        """Exécute l'extraction d'intention."""
        try:
            if self.nlp_engine:
                # TODO: Utiliser la vraie méthode d'extraction d'intention
                text = nlp_output.get("processed_text", "")
                intent_result = self.nlp_engine.extract_intent(text)
                
                if intent_result:
                    return IntentContext(
                        text=text,
                        intent_type=intent_result.command_type,
                        parameters=intent_result.parameters,
                        confidence=intent_result.confidence,
                        summary=f"{intent_result.command_type} ({', '.join(str(v) for v in intent_result.parameters.values())})"
                    )
        except Exception as e:
            self.logger.error(f"❌ Erreur NLU: {e}")
        return None
    
    def _listen_for_confirmation_or_interrupt(self) -> str:
        """Écoute une réponse de confirmation ou une commande globale."""
        try:
            # TODO: Implémenter l'écoute de confirmation
            # Pour l'instant, retourner une réponse simulée
            return "yes"
        except Exception as e:
            self.logger.error(f"❌ Erreur écoute confirmation: {e}")
            return "error"
    
    def _check_global_commands(self):
        """Vérifie les commandes globales."""
        try:
            # TODO: Implémenter la détection de commandes globales
            pass
        except Exception as e:
            self.logger.error(f"❌ Erreur vérification commandes globales: {e}")
    
    def _handle_global_command(self, command: str):
        """Traite une commande globale."""
        command = command.lower().strip()
        
        if command in ["stop", "arrête"]:
            self.say("D'accord, j'arrête.")
            self.stop()
        elif command in ["cancel", "annule"]:
            self.say("Commande annulée.")
            self._cancel_last_intent()
            self.state = VoiceInterfaceState.IDLE
        elif command in ["wait", "attends"]:
            self._pause_processing()
            self.say("En pause, dis 'reprends' pour continuer.")
        elif command in ["resume", "reprends"]:
            self._resume_processing()
            self.say("Je reprends.")
        elif command in ["restart", "recommence"]:
            self.state = VoiceInterfaceState.IDLE
            self.say("Redémarrage de l'interface vocale.")
    
    def _cancel_last_intent(self):
        """Annule la dernière intention."""
        if self.current_intent:
            self.logger.info(f"🚫 Intention annulée: {self.current_intent.summary}")
            self.current_intent = None
    
    def _pause_processing(self):
        """Met en pause le traitement."""
        # TODO: Implémenter la pause
        pass
    
    def _resume_processing(self):
        """Reprend le traitement."""
        # TODO: Implémenter la reprise
        pass
```
</copilot-edited-file>
