"""
Module contenant l'interface vocale (SUI) de Peer.
"""

import os
import sys
import time
import threading
import queue
import logging
from typing import Optional, List, Dict, Any

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Importation des dépendances
try:
    import pyaudio
    import numpy as np
    import whisper
    import pyttsx3
    from pydantic import BaseModel
except ImportError as e:
    print(f"Erreur lors du chargement des dépendances: {e}")
    print("Veuillez installer les dépendances requises:")
    print("  pip install pyaudio numpy pyttsx3")
    sys.exit(1)

# Importation des modules Peer
from peer.domain.services.message_service import MessageService
from peer.domain.services.system_check_service import SystemCheckService
from peer.domain.services.command_service import CommandService
from peer.domain.ports.tts_port import TTSPort
from peer.infrastructure.adapters.simple_tts_adapter import SimpleTTSAdapter
from peer.domain.ports.system_check_port import SystemCheckPort
from peer.infrastructure.adapters.simple_system_check_adapter import SimpleSystemCheckAdapter

class SpeechRecognitionResult(BaseModel):
    """Modèle pour les résultats de reconnaissance vocale."""
    text: str
    confidence: float = 0.0

class SUI:
    """
    Interface utilisateur vocale (Speech User Interface) pour Peer.
    Permet d'interagir avec Peer par la voix.
    """
    
    def __init__(self):
        """Initialise l'interface vocale."""
        self.logger = logging.getLogger("SUI")
        self.logger.info("Initialisation de l'interface vocale...")
        
        # Initialisation des services
        self.message_service = MessageService()
        self.system_check_service = SystemCheckService(SimpleSystemCheckAdapter())
        self.command_service = CommandService()  # Service centralisé de commandes
        
        # Initialisation du TTS
        self.tts_adapter = SimpleTTSAdapter()
        self.tts_lock = threading.Lock()  # Verrou pour éviter les conflits TTS
        
        # Initialisation des variables d'état
        self.running = False
        self.listening = False
        self.speaking = False
        self.speech_recognition_engine = None
        self.audio_stream = None
        self.command_queue = queue.Queue()
        
        # Initialisation du moteur de reconnaissance vocale
        self._init_speech_recognition()
    
    def _init_speech_recognition(self):
        """Initialise le moteur de reconnaissance vocale."""
        # Vérifier les moteurs disponibles
        engines_available = []
        
        # Vérifier Whisper
        try:
            import whisper
            engines_available.append("whisper")
            self.logger.info("Moteur Whisper disponible")
        except ImportError:
            self.logger.warning("Moteur Whisper non disponible")
        
        # Vérifier Vosk
        try:
            import vosk
            engines_available.append("vosk")
            self.logger.info("Moteur Vosk disponible")
        except ImportError:
            self.logger.warning("Moteur Vosk non disponible")
        
        # Vérifier Wav2Vec2
        try:
            import transformers
            import torch
            import torchaudio
            engines_available.append("wav2vec2")
            self.logger.info("Moteur Wav2Vec2 disponible")
        except ImportError:
            self.logger.warning("Moteur Wav2Vec2 non disponible")
        
        # Sélectionner le moteur
        if "whisper" in engines_available:
            self._init_whisper()
        elif "vosk" in engines_available:
            self._init_vosk()
        elif "wav2vec2" in engines_available:
            self._init_wav2vec2()
        else:
            self.logger.error("Aucun moteur de reconnaissance vocale n'est disponible.")
            print("Aucun moteur de reconnaissance vocale n'est disponible.")
            print("Veuillez installer l'un des moteurs suivants:")
            print("  - Whisper (OpenAI): pip install openai-whisper torch")
            print("  - Vosk: pip install vosk")
            print("  - Wav2Vec2 (Meta): pip install transformers torch torchaudio soundfile")
    
    def _init_whisper(self):
        """Initialise le moteur Whisper."""
        try:
            self.logger.info("Initialisation du moteur Whisper...")
            self.speech_recognition_engine = "whisper"
            self.whisper_model = whisper.load_model("base")
            self.logger.info("Moteur Whisper initialisé avec succès")
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement du modèle Whisper: {e}")
            print(f"Erreur lors du chargement du modèle Whisper: {e}")
            self.speech_recognition_engine = None
    
    def _init_vosk(self):
        """Initialise le moteur Vosk."""
        try:
            import vosk
            self.logger.info("Initialisation du moteur Vosk...")
            self.speech_recognition_engine = "vosk"
            # Implémentation à compléter
            self.logger.info("Moteur Vosk initialisé avec succès")
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation de Vosk: {e}")
            self.speech_recognition_engine = None
    
    def _init_wav2vec2(self):
        """Initialise le moteur Wav2Vec2."""
        try:
            import transformers
            self.logger.info("Initialisation du moteur Wav2Vec2...")
            self.speech_recognition_engine = "wav2vec2"
            # Implémentation à compléter
            self.logger.info("Moteur Wav2Vec2 initialisé avec succès")
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation de Wav2Vec2: {e}")
            self.speech_recognition_engine = None
    
    def start(self):
        """Démarre l'interface vocale."""
        if self.running:
            self.logger.warning("L'interface vocale est déjà en cours d'exécution")
            return
        
        self.running = True
        self.logger.info("Démarrage de l'interface vocale...")
        
        # Vérifier si un moteur de reconnaissance vocale est disponible
        if not self.speech_recognition_engine:
            self.vocalize("Aucun moteur de reconnaissance vocale n'est disponible. L'interface vocale fonctionnera en mode dégradé.")
        
        # Démarrer les threads
        self.listen_thread = threading.Thread(target=self._listen_loop)
        self.command_thread = threading.Thread(target=self._command_loop)
        
        self.listen_thread.daemon = True
        self.command_thread.daemon = True
        
        self.listen_thread.start()
        self.command_thread.start()
        
        # Message de bienvenue
        self.vocalize("Interface vocale de Peer démarrée. Comment puis-je vous aider?")
        
        # Boucle principale
        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.logger.info("Interruption clavier détectée")
            self.stop()
    
    def stop(self):
        """Arrête l'interface vocale."""
        if not self.running:
            return
        
        self.logger.info("Arrêt de l'interface vocale...")
        self.running = False
        
        # Arrêter l'écoute
        self.listening = False
        
        # Attendre la fin des threads
        if hasattr(self, 'listen_thread') and self.listen_thread.is_alive():
            self.listen_thread.join(timeout=2)
        
        if hasattr(self, 'command_thread') and self.command_thread.is_alive():
            self.command_thread.join(timeout=2)
        
        # Fermer le flux audio
        if self.audio_stream:
            self.audio_stream.close()
        
        self.logger.info("Interface vocale arrêtée")
    
    def _listen_loop(self):
        """Boucle d'écoute pour la reconnaissance vocale."""
        self.logger.info("Démarrage de la boucle d'écoute...")
        
        # Initialiser PyAudio
        p = pyaudio.PyAudio()
        
        # Ouvrir le flux audio
        self.audio_stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=4096
        )
        
        self.listening = True
        
        # Boucle d'écoute
        while self.running and self.listening:
            # Ne pas écouter pendant la synthèse vocale
            if self.speaking:
                time.sleep(0.1)
                continue
            
            try:
                # Enregistrer l'audio
                frames = []
                silent_frames = 0
                recording = False
                
                # Enregistrer jusqu'à détecter un silence
                for _ in range(100):  # ~10 secondes
                    if not self.running or not self.listening:
                        break
                    
                    data = self.audio_stream.read(4096, exception_on_overflow=False)
                    frames.append(data)
                    
                    # Détecter l'activité vocale (implémentation simplifiée)
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    volume = np.abs(audio_data).mean()
                    
                    if volume > 500:  # Seuil d'activité vocale
                        recording = True
                        silent_frames = 0
                    elif recording:
                        silent_frames += 1
                        if silent_frames > 10:  # ~1 seconde de silence
                            break
                
                # Traiter l'audio si une activité vocale a été détectée
                if recording and frames:
                    # Convertir les frames en un seul buffer audio
                    audio_data = b''.join(frames)
                    
                    # Reconnaître la parole
                    result = self._recognize_speech(audio_data)
                    
                    if result and result.text:
                        self.logger.info(f"Parole reconnue: {result.text}")
                        
                        # Ajouter la commande à la file d'attente
                        self.command_queue.put(result.text)
            
            except Exception as e:
                self.logger.error(f"Erreur lors de l'écoute: {e}")
                time.sleep(1)  # Pause en cas d'erreur
        
        # Fermer le flux audio
        if self.audio_stream:
            self.audio_stream.close()
            self.audio_stream = None
        
        p.terminate()
        self.logger.info("Boucle d'écoute terminée")
    
    def _recognize_speech(self, audio_data) -> Optional[SpeechRecognitionResult]:
        """
        Reconnaît la parole à partir des données audio.
        
        Args:
            audio_data: Données audio à reconnaître
            
        Returns:
            SpeechRecognitionResult: Résultat de la reconnaissance vocale
        """
        if not self.speech_recognition_engine:
            return None
        
        try:
            if self.speech_recognition_engine == "whisper":
                return self._recognize_with_whisper(audio_data)
            elif self.speech_recognition_engine == "vosk":
                return self._recognize_with_vosk(audio_data)
            elif self.speech_recognition_engine == "wav2vec2":
                return self._recognize_with_wav2vec2(audio_data)
            else:
                self.logger.error(f"Moteur de reconnaissance vocale non pris en charge: {self.speech_recognition_engine}")
                return None
        except Exception as e:
            self.logger.error(f"Erreur lors de la reconnaissance vocale: {e}")
            return None
    
    def _recognize_with_whisper(self, audio_data) -> SpeechRecognitionResult:
        """
        Reconnaît la parole avec Whisper.
        
        Args:
            audio_data: Données audio à reconnaître
            
        Returns:
            SpeechRecognitionResult: Résultat de la reconnaissance vocale
        """
        # Convertir les données audio en tableau numpy
        audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        
        # Reconnaître la parole
        result = self.whisper_model.transcribe(audio_np, language="fr")
        
        return SpeechRecognitionResult(
            text=result["text"].strip(),
            confidence=0.0  # Whisper ne fournit pas de score de confiance
        )
    
    def _recognize_with_vosk(self, audio_data) -> SpeechRecognitionResult:
        """
        Reconnaît la parole avec Vosk.
        
        Args:
            audio_data: Données audio à reconnaître
            
        Returns:
            SpeechRecognitionResult: Résultat de la reconnaissance vocale
        """
        # Implémentation à compléter
        return SpeechRecognitionResult(
            text="Not Implemented: Reconnaissance vocale avec Vosk",
            confidence=0.0
        )
    
    def _recognize_with_wav2vec2(self, audio_data) -> SpeechRecognitionResult:
        """
        Reconnaît la parole avec Wav2Vec2.
        
        Args:
            audio_data: Données audio à reconnaître
            
        Returns:
            SpeechRecognitionResult: Résultat de la reconnaissance vocale
        """
        # Implémentation à compléter
        return SpeechRecognitionResult(
            text="Not Implemented: Reconnaissance vocale avec Wav2Vec2",
            confidence=0.0
        )
    
    def _command_loop(self):
        """Boucle de traitement des commandes."""
        self.logger.info("Démarrage de la boucle de traitement des commandes...")
        
        while self.running:
            try:
                # Récupérer une commande de la file d'attente
                command = self.command_queue.get(timeout=1)
                
                # Traiter la commande
                self._process_command(command)
                
                # Marquer la commande comme traitée
                self.command_queue.task_done()
            
            except queue.Empty:
                # Pas de commande dans la file d'attente
                pass
            except Exception as e:
                self.logger.error(f"Erreur lors du traitement des commandes: {e}")
        
        self.logger.info("Boucle de traitement des commandes terminée")
    
    def _process_command(self, command: str):
        """
        Traite une commande vocale.
        
        Args:
            command: Commande à traiter
        """
        self.logger.info(f"Traitement de la commande: {command}")
        
        # Commandes spéciales
        if command.lower() in ["quitter", "exit", "stop", "arrêter"]:
            self.vocalize("Arrêt de l'interface vocale")
            self.stop()
            return
        
        # Déléguer la commande au service de commandes centralisé
        try:
            # Extraire les arguments de la commande
            parts = command.split()
            cmd = parts[0] if parts else ""
            args = parts[1:] if len(parts) > 1 else []
            
            # Exécuter la commande via le service centralisé
            result = self.command_service.execute_command(command, args)
            
            # Vocaliser le résultat
            self.vocalize(result)
        except Exception as e:
            error_msg = f"Erreur lors du traitement de la commande: {e}"
            self.logger.error(error_msg)
            self.vocalize(f"Je n'ai pas compris cette commande.")
    
    def vocalize(self, text: str):
        """
        Vocalise un texte.
        
        Args:
            text: Texte à vocaliser
        """
        if not text:
            return
        
        # Acquérir le verrou pour éviter les conflits
        with self.tts_lock:
            try:
                self.speaking = True
                self.tts_adapter.speak(text)
            except Exception as e:
                self.logger.error(f"Erreur lors de la vocalisation: {e}")
                print(f"TTS (erreur): {text}")
            finally:
                self.speaking = False

def main():
    """Point d'entrée principal de l'interface vocale."""
    sui = SUI()
    try:
        sui.start()
    except KeyboardInterrupt:
        sui.stop()
    except Exception as e:
        print(f"Erreur: {e}")
        sui.stop()

if __name__ == "__main__":
    main()
