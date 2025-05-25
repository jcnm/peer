"""
Module contenant l'interface vocale (SUI) de Peer.

Interface vocale refactorisée qui utilise le daemon central
et traduit les commandes vocales en requêtes standardisées.
"""

import os
import sys
import time
import threading
import queue
import logging
import re
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

# Importation des modules Peer refactorisés
from peer.core import PeerDaemon, CoreRequest, CoreResponse, CommandType, ResponseType, InterfaceType
from peer.core.protocol import InterfaceAdapter
from peer.infrastructure.adapters.simple_tts_adapter import SimpleTTSAdapter


class SpeechRecognitionResult(BaseModel):
    """Modèle pour les résultats de reconnaissance vocale."""
    text: str
    confidence: float = 0.0


class SUISpeechAdapter(InterfaceAdapter):
    """
    Adaptateur pour l'interface vocale (SUI) qui traduit
    les commandes vocales en requêtes standardisées pour le core.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("SUISpeechAdapter")
        # Mapping des commandes vocales vers les CommandType
        self.voice_commands = {
            # Français
            "aide": CommandType.HELP,
            "aidez-moi": CommandType.HELP,
            "help": CommandType.HELP,
            "statut": CommandType.STATUS,
            "état": CommandType.STATUS,
            "status": CommandType.STATUS,
            "version": CommandType.VERSION,
            "heure": CommandType.TIME,
            "quelle heure": CommandType.TIME,
            "date": CommandType.DATE,
            "quelle date": CommandType.DATE,
            "echo": CommandType.ECHO,
            "répète": CommandType.ECHO,
            "capacités": CommandType.CAPABILITIES,
            "que peux-tu faire": CommandType.CAPABILITIES,
            "analyser": CommandType.ANALYZE,
            "analyse": CommandType.ANALYZE,
            "expliquer": CommandType.EXPLAIN,
            "explique": CommandType.EXPLAIN,
            
            # Anglais
            "what time": CommandType.TIME,
            "what date": CommandType.DATE,
            "repeat": CommandType.ECHO,
            "capabilities": CommandType.CAPABILITIES,
            "what can you do": CommandType.CAPABILITIES,
            "analyze": CommandType.ANALYZE,
            "explain": CommandType.EXPLAIN,
        }
    
    def translate_to_core(self, speech_input: str) -> CoreRequest:
        """Traduit une commande vocale en requête standardisée"""
        # Normaliser le texte (minuscules, sans ponctuation excessive)
        normalized_input = self._normalize_speech_input(speech_input)
        
        # Extraire la commande et les paramètres
        command, parameters = self._parse_speech_command(normalized_input)
        
        return CoreRequest(
            command=command,
            parameters=parameters,
            context={"original_speech": speech_input, "normalized": normalized_input},
            interface_type=InterfaceType.SUI
        )
    
    def translate_from_core(self, core_response: CoreResponse) -> Dict[str, Any]:
        """Traduit une réponse du core en format adapté à la synthèse vocale"""
        # Adapter le message pour la synthèse vocale
        vocal_message = self._adapt_message_for_speech(core_response.message)
        
        return {
            "vocal_message": vocal_message,
            "should_vocalize": True,
            "original_response": core_response,
            "display_message": core_response.message,  # Pour affichage textuel si nécessaire
            "response_type": core_response.type.value
        }
    
    def get_interface_help(self) -> str:
        """Retourne l'aide spécifique à l'interface vocale"""
        help_text = """Interface Vocale Peer - Commandes disponibles:

Commandes de base:
- "Aide" ou "Help" - Affiche cette aide
- "Statut" ou "Status" - Vérifie l'état du système  
- "Version" - Affiche la version
- "Quelle heure" - Donne l'heure actuelle
- "Quelle date" - Donne la date actuelle

Commandes d'analyse:
- "Analyse [sujet]" - Analyse un sujet donné
- "Explique [concept]" - Explique un concept

Utilitaires:
- "Répète [texte]" - Fait répéter le texte
- "Que peux-tu faire" - Liste les capacités

Vous pouvez parler naturellement, l'interface comprendra vos intentions."""
        return help_text
    
    def _normalize_speech_input(self, speech_input: str) -> str:
        """Normalise l'entrée vocale pour le traitement"""
        # Convertir en minuscules
        normalized = speech_input.lower().strip()
        
        # Supprimer la ponctuation excessive
        normalized = re.sub(r'[^\w\s\-]', '', normalized)
        
        # Supprimer les espaces multiples
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized
    
    def _parse_speech_command(self, normalized_input: str) -> tuple[CommandType, Dict[str, Any]]:
        """Parse une commande vocale pour extraire la commande et les paramètres"""
        # Rechercher une correspondance directe
        for trigger, command in self.voice_commands.items():
            if trigger in normalized_input:
                # Extraire les paramètres après la commande
                if trigger in normalized_input:
                    parts = normalized_input.split(trigger, 1)
                    if len(parts) > 1 and parts[1].strip():
                        parameters = {"args": parts[1].strip().split()}
                    else:
                        parameters = {}
                    
                    return command, parameters
        
        # Si aucune correspondance directe, essayer d'analyser le contexte
        if any(word in normalized_input for word in ["aide", "help", "aidez"]):
            return CommandType.HELP, {}
        elif any(word in normalized_input for word in ["heure", "time"]):
            return CommandType.TIME, {}
        elif any(word in normalized_input for word in ["date"]):
            return CommandType.DATE, {}
        elif any(word in normalized_input for word in ["répète", "repeat", "echo"]):
            # Extraire le texte à répéter
            for trigger in ["répète", "repeat", "echo"]:
                if trigger in normalized_input:
                    parts = normalized_input.split(trigger, 1)
                    if len(parts) > 1:
                        return CommandType.ECHO, {"args": parts[1].strip().split()}
            return CommandType.ECHO, {}
        
        # Commande inconnue - utiliser QUERY pour analyse générale
        return CommandType.QUERY, {"args": normalized_input.split()}
    
    def _adapt_message_for_speech(self, message: str) -> str:
        """Adapte un message pour la synthèse vocale"""
        # Remplacer certains éléments pour une meilleure prononciation
        adaptations = {
            "Peer": "Pire",  # Meilleure prononciation
            "CLI": "C L I",
            "TUI": "T U I", 
            "SUI": "S U I",
            "API": "A P I",
            "0.2.0": "version zéro point deux point zéro",
            "ERROR": "Erreur",
            "WARNING": "Attention",
            "INFO": "Information",
            "SUCCESS": "Succès"
        }
        
        adapted_message = message
        for original, replacement in adaptations.items():
            adapted_message = adapted_message.replace(original, replacement)
        
        return adapted_message


class SUI:
    """
    Interface utilisateur vocale (Speech User Interface) pour Peer.
    Version refactorisée qui utilise le daemon central.
    """
    
    def __init__(self, daemon: Optional[PeerDaemon] = None):
        """Initialise l'interface vocale."""
        self.logger = logging.getLogger("SUI")
        self.logger.info("Initialisation de l'interface vocale refactorisée...")
        
        # Initialisation du daemon central
        self.daemon = daemon or PeerDaemon()
        self.adapter = SUISpeechAdapter()
        
        # Créer une session pour cette interface
        self.session_id = self.daemon.create_session(InterfaceType.SUI)
        
        # Initialisation du TTS
        self.tts_adapter = SimpleTTSAdapter()
        self.tts_lock = threading.Lock()
        
        # Variables d'état
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
        engines_available = []
        
        # Vérifier Whisper
        try:
            import whisper
            engines_available.append("whisper")
            self.logger.info("Moteur Whisper disponible")
        except ImportError:
            self.logger.warning("Moteur Whisper non disponible")
        
        # Sélectionner le moteur
        if "whisper" in engines_available:
            self._init_whisper()
        else:
            self.logger.error("Aucun moteur de reconnaissance vocale disponible.")
            print("Veuillez installer Whisper: pip install openai-whisper torch")
    
    def _init_whisper(self):
        """Initialise le moteur Whisper."""
        try:
            self.logger.info("Initialisation du moteur Whisper...")
            self.speech_recognition_engine = "whisper"
            self.whisper_model = whisper.load_model("base")
            self.logger.info("Moteur Whisper initialisé avec succès")
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement de Whisper: {e}")
            self.speech_recognition_engine = None
    
    def start(self):
        """Démarre l'interface vocale."""
        if self.running:
            self.logger.warning("L'interface vocale est déjà en cours")
            return
        
        self.running = True
        self.logger.info("Démarrage de l'interface vocale...")
        
        # Vérifier le moteur de reconnaissance vocale
        if not self.speech_recognition_engine:
            self.vocalize("Aucun moteur de reconnaissance vocale disponible. Mode dégradé activé.")
        
        # Démarrer les threads
        self.listen_thread = threading.Thread(target=self._listen_loop)
        self.command_thread = threading.Thread(target=self._command_loop)
        
        self.listen_thread.daemon = True
        self.command_thread.daemon = True
        
        self.listen_thread.start()
        self.command_thread.start()
        
        # Message de bienvenue via le daemon
        welcome_request = CoreRequest(
            command=CommandType.HELP,
            session_id=self.session_id,
            interface_type=InterfaceType.SUI,
            context={"welcome": True}
        )
        
        try:
            response = self.daemon.execute_command(welcome_request)
            adapted_response = self.adapter.translate_from_core(response)
            
            welcome_msg = "Interface vocale Peer démarrée. " + adapted_response.get("vocal_message", "Comment puis-je vous aider?")
            self.vocalize(welcome_msg)
        except Exception as e:
            self.logger.error(f"Erreur lors du message de bienvenue: {e}")
            self.vocalize("Interface vocale Peer démarrée.")
        
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
        
        # Terminer la session
        if hasattr(self, 'session_id'):
            self.daemon.end_session(self.session_id)
        
        self.vocalize("Interface vocale arrêtée. À bientôt!")
    
    def _listen_loop(self):
        """Boucle d'écoute en continu."""
        self.logger.info("Démarrage de la boucle d'écoute...")
        
        if not self.speech_recognition_engine:
            self.logger.warning("Pas de moteur de reconnaissance vocale. Boucle d'écoute en mode simulation.")
            return
        
        # Initialiser PyAudio
        try:
            audio = pyaudio.PyAudio()
            
            # Configuration audio
            CHUNK = 1024
            FORMAT = pyaudio.paInt16
            CHANNELS = 1
            RATE = 16000
            
            # Ouvrir le stream audio
            stream = audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK
            )
            
            self.logger.info("Stream audio ouvert, écoute en cours...")
            
            while self.running:
                if not self.speaking:  # Ne pas écouter pendant que l'IA parle
                    try:
                        # Lire les données audio
                        audio_data = stream.read(CHUNK, exception_on_overflow=False)
                        
                        # Traitement simple de détection d'activité vocale
                        audio_np = np.frombuffer(audio_data, dtype=np.int16)
                        volume = np.sqrt(np.mean(audio_np**2))
                        
                        # Seuil de détection (à ajuster selon l'environnement)
                        if volume > 500:  # Seuil arbitraire
                            self._process_audio_chunk(audio_data)
                    
                    except Exception as e:
                        self.logger.error(f"Erreur lors de la lecture audio: {e}")
                
                time.sleep(0.01)  # Petite pause
        
        except Exception as e:
            self.logger.error(f"Erreur dans la boucle d'écoute: {e}")
        finally:
            if 'stream' in locals():
                stream.stop_stream()
                stream.close()
            if 'audio' in locals():
                audio.terminate()
    
    def _process_audio_chunk(self, audio_data):
        """Traite un chunk audio pour reconnaissance vocale."""
        # Implémentation simplifiée - dans une version complète,
        # on accumulerait les chunks jusqu'à détecter une pause
        pass
    
    def _command_loop(self):
        """Boucle de traitement des commandes."""
        self.logger.info("Démarrage de la boucle de commandes...")
        
        while self.running:
            try:
                # Attendre une commande (timeout pour vérifier self.running)
                try:
                    speech_text = self.command_queue.get(timeout=1.0)
                    self._process_speech_command(speech_text)
                    self.command_queue.task_done()
                except queue.Empty:
                    continue
            except Exception as e:
                self.logger.error(f"Erreur dans la boucle de commandes: {e}")
    
    def _process_speech_command(self, speech_text: str):
        """Traite une commande vocale."""
        self.logger.info(f"Traitement de la commande vocale: {speech_text}")
        
        try:
            # Traduire la commande vocale en requête standardisée
            request = self.adapter.translate_to_core(speech_text)
            request.session_id = self.session_id
            
            # Exécuter via le daemon
            response = self.daemon.execute_command(request)
            
            # Traduire la réponse pour l'interface vocale
            adapted_response = self.adapter.translate_from_core(response)
            
            # Vocaliser la réponse
            if adapted_response.get("should_vocalize", True):
                vocal_message = adapted_response.get("vocal_message", "Commande exécutée.")
                self.vocalize(vocal_message)
            
            self.logger.info(f"Commande vocale traitée avec succès")
            
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement de la commande vocale: {e}")
            self.vocalize("Désolé, je n'ai pas pu traiter votre demande.")
    
    def vocalize(self, text: str):
        """Synthétise et joue un texte."""
        if not text.strip():
            return
        
        with self.tts_lock:
            self.speaking = True
            try:
                self.logger.info(f"Vocalisation: {text}")
                self.tts_adapter.speak(text)
            except Exception as e:
                self.logger.error(f"Erreur lors de la vocalisation: {e}")
                print(f"[TTS Error] {text}")  # Fallback en mode texte
            finally:
                self.speaking = False
    
    def simulate_voice_command(self, command_text: str):
        """Simule une commande vocale (pour les tests)."""
        self.logger.info(f"Simulation de commande vocale: {command_text}")
        self.command_queue.put(command_text)


def main():
    """Point d'entrée principal pour l'interface SUI."""
    try:
        sui = SUI()
        
        # Afficher les informations de démarrage
        print("=== Interface Vocale Peer (SUI) ===")
        print("Appuyez sur Ctrl+C pour arrêter")
        print("Pour tester, vous pouvez utiliser les commandes simulées:")
        print("  - aide")
        print("  - quelle heure")
        print("  - statut")
        print()
        
        # Démarrer l'interface
        sui.start()
        
    except KeyboardInterrupt:
        print("\nArrêt demandé par l'utilisateur")
    except Exception as e:
        print(f"Erreur fatale: {e}")
        logging.error(f"Erreur fatale dans SUI: {e}")


if __name__ == "__main__":
    main()
