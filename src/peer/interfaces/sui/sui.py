"""
Module contenant l'interface utilisateur vocale (SUI) avec support multi-moteurs STT locaux.
"""
import subprocess
import logging
import threading
import time
import queue
import re
import sys
import os
import json
import platform
import datetime
from typing import List, Dict, Any, Optional, Set

from peer.domain.services.message_service import MessageService
from peer.domain.entities.message_entities import Message
from peer.domain.services.system_check_service import SystemCheckService
from peer.infrastructure.adapters.simple_tts_adapter import SimpleTTSAdapter
from peer.infrastructure.adapters.simple_system_check_adapter import SimpleSystemCheckAdapter

logger = logging.getLogger(__name__)

# Vérifier si psutil est disponible
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    logger.warning("La bibliothèque psutil n'est pas disponible. L'analyse système sera limitée.")
    PSUTIL_AVAILABLE = False

# Vérifier les moteurs STT disponibles
STT_ENGINES = {"whisper": False, "vosk": False, "wav2vec2": False}

# Chemin vers le fichier d'état des moteurs STT
STT_ENGINES_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
                  os.path.dirname(os.path.abspath(__file__)))))), "vepeer", "stt_engines.json")

# Charger l'état des moteurs STT s'il existe
if os.path.exists(STT_ENGINES_FILE):
    try:
        with open(STT_ENGINES_FILE, "r") as f:
            STT_ENGINES = json.load(f)
        logger.info(f"État des moteurs STT chargé: {STT_ENGINES}")
    except Exception as e:
        logger.error(f"Erreur lors du chargement de l'état des moteurs STT: {str(e)}")

# Tentative d'importation de Whisper si disponible
WHISPER_AVAILABLE = False
if STT_ENGINES.get("whisper", False):
    try:
        import whisper
        import numpy as np
        import torch
        import pyaudio
        WHISPER_AVAILABLE = True
        logger.info("Whisper est disponible et sera utilisé pour la reconnaissance vocale.")
    except ImportError:
        logger.warning("Whisper est marqué comme installé mais les bibliothèques ne sont pas disponibles.")
        WHISPER_AVAILABLE = False

# Tentative d'importation de Vosk si disponible
VOSK_AVAILABLE = False
if not WHISPER_AVAILABLE and STT_ENGINES.get("vosk", False):
    try:
        from vosk import Model, KaldiRecognizer
        import pyaudio
        import json
        
        # Chemin vers le modèle Vosk
        VOSK_MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
                         os.path.dirname(os.path.abspath(__file__)))))), "vepeer", "models", "vosk", "vosk-model-fr-0.22")
        
        # Vérifier si le modèle existe
        if os.path.exists(VOSK_MODEL_PATH):
            VOSK_AVAILABLE = True
            logger.info("Vosk est disponible et sera utilisé pour la reconnaissance vocale.")
        else:
            logger.warning(f"Le modèle Vosk n'a pas été trouvé à l'emplacement {VOSK_MODEL_PATH}")
    except ImportError:
        logger.warning("Vosk est marqué comme installé mais les bibliothèques ne sont pas disponibles.")

# Tentative d'importation de Wav2Vec2 si disponible
WAV2VEC2_AVAILABLE = False
if not WHISPER_AVAILABLE and not VOSK_AVAILABLE and STT_ENGINES.get("wav2vec2", False):
    try:
        import torch
        from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
        import soundfile as sf
        import pyaudio
        import numpy as np
        
        # Chemin vers le modèle Wav2Vec2
        WAV2VEC2_MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
                             os.path.dirname(os.path.abspath(__file__)))))), "vepeer", "models", "wav2vec2")
        
        # Vérifier si le modèle existe
        if os.path.exists(WAV2VEC2_MODEL_PATH):
            WAV2VEC2_AVAILABLE = True
            logger.info("Wav2Vec2 est disponible et sera utilisé pour la reconnaissance vocale.")
        else:
            # Si le modèle n'existe pas localement, on essaie de le charger depuis HuggingFace
            try:
                processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-large-xlsr-53-french")
                model = Wav2Vec2ForCTC.from_pretrained("facebook/wav2vec2-large-xlsr-53-french")
                
                # Sauvegarder le modèle localement
                os.makedirs(WAV2VEC2_MODEL_PATH, exist_ok=True)
                processor.save_pretrained(WAV2VEC2_MODEL_PATH)
                model.save_pretrained(WAV2VEC2_MODEL_PATH)
                
                WAV2VEC2_AVAILABLE = True
                logger.info("Wav2Vec2 a été téléchargé et sera utilisé pour la reconnaissance vocale.")
            except Exception as e:
                logger.warning(f"Impossible de télécharger le modèle Wav2Vec2: {str(e)}")
    except ImportError:
        logger.warning("Wav2Vec2 est marqué comme installé mais les bibliothèques ne sont pas disponibles.")

# Tentative d'importation de PyAudio pour la capture audio
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    logger.warning("PyAudio n'est pas disponible. La capture audio sera désactivée.")
    PYAUDIO_AVAILABLE = False


class SUI:
    """
    Interface utilisateur vocale pour l'application Peer.
    
    Cette classe gère l'interface utilisateur vocale et expose
    les fonctionnalités principales de l'application via des commandes vocales.
    Utilise différents moteurs STT locaux selon leur disponibilité.
    """
    
    def __init__(self):
        """Initialise l'interface SUI."""
        # Initialiser les adaptateurs
        self.tts_adapter = SimpleTTSAdapter()
        self.tts_adapter.initialize()
        
        self.system_check_adapter = SimpleSystemCheckAdapter()
        
        # Initialiser les services
        self.message_service = MessageService(self.tts_adapter)
        self.system_check_service = SystemCheckService(self.system_check_adapter)
        
        # État de l'interface
        self.running = False
        self.is_speaking = False
        self.is_listening = False
        self.command_queue = queue.Queue()
        self.error_count = 0
        self.max_consecutive_errors = 3
        self.last_time_announcement = 0
        
        # Initialiser les moteurs STT
        self.whisper_model = None
        self.vosk_model = None
        self.vosk_recognizer = None
        self.wav2vec2_processor = None
        self.wav2vec2_model = None
        
        # Initialiser Whisper si disponible
        if WHISPER_AVAILABLE:
            try:
                self.whisper_model = whisper.load_model("base")
                logger.info("Modèle Whisper chargé avec succès")
            except Exception as e:
                logger.error(f"Erreur lors du chargement du modèle Whisper: {str(e)}")
                self.whisper_model = None
        
        # Initialiser Vosk si disponible
        if VOSK_AVAILABLE:
            try:
                self.vosk_model = Model(VOSK_MODEL_PATH)
                logger.info("Modèle Vosk chargé avec succès")
            except Exception as e:
                logger.error(f"Erreur lors du chargement du modèle Vosk: {str(e)}")
                self.vosk_model = None
        
        # Initialiser Wav2Vec2 si disponible
        if WAV2VEC2_AVAILABLE:
            try:
                self.wav2vec2_processor = Wav2Vec2Processor.from_pretrained(WAV2VEC2_MODEL_PATH)
                self.wav2vec2_model = Wav2Vec2ForCTC.from_pretrained(WAV2VEC2_MODEL_PATH)
                logger.info("Modèle Wav2Vec2 chargé avec succès")
            except Exception as e:
                logger.error(f"Erreur lors du chargement du modèle Wav2Vec2: {str(e)}")
                self.wav2vec2_processor = None
                self.wav2vec2_model = None
        
        # Configuration de PyAudio pour la capture audio
        if PYAUDIO_AVAILABLE:
            self.audio_format = pyaudio.paInt16
            self.channels = 1
            self.rate = 16000
            self.chunk = 1024
            self.audio = pyaudio.PyAudio()
        
        # Définir les commandes vocales
        self.commands = {
            r"comment (?:ça|sa) va": self.check_system,
            r"comment vas-tu": self.check_system,
            r"tout va bien": self.check_system,
            r"(?:quitter|arrêter|stop)": self.quit
        }
        
        # Mutex pour l'accès aux ressources partagées
        self.lock = threading.Lock()
    
    def run(self):
        """Exécute l'interface SUI."""
        if not PYAUDIO_AVAILABLE:
            print("PyAudio n'est pas disponible. L'interface SUI ne peut pas fonctionner.")
            return
        
        if not self.whisper_model and not self.vosk_model and not (self.wav2vec2_processor and self.wav2vec2_model):
            print("Aucun moteur de reconnaissance vocale n'est disponible.")
            print("Veuillez installer l'un des moteurs suivants:")
            print("  - Whisper (OpenAI): pip install openai-whisper torch")
            print("  - Vosk: pip install vosk")
            print("  - Wav2Vec2 (Meta): pip install transformers torch torchaudio soundfile")
            return
        
        # Analyser la machine au démarrage
        self._analyze_system()
        
        # Afficher et vocaliser le message de bienvenue
        welcome_message = self.message_service.get_welcome_message()
        print(welcome_message.content)
        
        with self.lock:
            self.is_speaking = True
        self.message_service.vocalize_message(welcome_message)
        with self.lock:
            self.is_speaking = False
        
        # Démarrer la boucle d'écoute dans un thread séparé
        self.running = True
        listen_thread = threading.Thread(target=self._listen_loop)
        listen_thread.daemon = True
        listen_thread.start()
        
        # Démarrer le thread d'annonce de l'heure
        time_thread = threading.Thread(target=self._time_announcement_loop)
        time_thread.daemon = True
        time_thread.start()
        
        # Boucle principale
        try:
            while self.running:
                try:
                    # Traiter les commandes dans la file d'attente
                    command = self.command_queue.get(timeout=0.1)
                    self._process_command(command)
                except queue.Empty:
                    pass
                
                # Afficher l'indicateur d'écoute
                self._update_listening_indicator()
                
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nArrêt de l'interface SUI...")
        finally:
            self.running = False
            if PYAUDIO_AVAILABLE:
                self.audio.terminate()
    
    def _analyze_system(self):
        """Analyse les performances de la machine et affiche un commentaire humoristique."""
        # Récupérer les informations système
        cpu_count = os.cpu_count() or 1
        cpu_percent = 0
        memory_gb = 4
        cuda_available = False
        
        if PSUTIL_AVAILABLE:
            try:
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                memory_gb = memory.total / (1024 ** 3)
            except Exception as e:
                logger.error(f"Erreur lors de l'analyse système avec psutil: {str(e)}")
        
        # Vérifier si CUDA est disponible pour PyTorch
        if WHISPER_AVAILABLE or WAV2VEC2_AVAILABLE:
            try:
                cuda_available = torch.cuda.is_available()
            except Exception as e:
                logger.error(f"Erreur lors de la vérification de CUDA: {str(e)}")
        
        # Préparer le message d'analyse
        system_info = f"Système: {platform.system()} {platform.release()}\n"
        system_info += f"Processeur: {cpu_count} cœurs (utilisation: {cpu_percent}%)\n"
        system_info += f"Mémoire: {memory_gb:.1f} Go\n"
        system_info += f"Accélération GPU: {'Disponible' if cuda_available else 'Non disponible'}\n"
        
        # Information sur le système de reconnaissance vocale
        if self.whisper_model:
            system_info += "Reconnaissance vocale: Whisper (OpenAI) - 100% local\n"
        elif self.vosk_model:
            system_info += "Reconnaissance vocale: Vosk - 100% local\n"
        elif self.wav2vec2_processor and self.wav2vec2_model:
            system_info += "Reconnaissance vocale: Wav2Vec2 (Meta) - 100% local\n"
        else:
            system_info += "Reconnaissance vocale: Non disponible\n"
        
        # Commentaire humoristique sur les performances
        humor_message = ""
        if cpu_count >= 8 and memory_gb >= 16 and cuda_available:
            humor_message = "Wow, quelle machine puissante ! Je me sens comme un poisson dans l'eau ici."
        elif cpu_count >= 4 and memory_gb >= 8:
            humor_message = "Votre machine est correcte, je devrais pouvoir travailler confortablement."
        elif cpu_count >= 2 and memory_gb >= 4:
            humor_message = "Je me sens un peu à l'étroit, mais je ferai de mon mieux !"
        else:
            humor_message = "Je vais être honnête, je me sens comme dans un studio parisien ici... très à l'étroit !"
        
        # Afficher et vocaliser l'analyse
        print("\n=== Analyse du système ===")
        print(system_info)
        print(humor_message)
        print("=========================\n")
        self._diagnose_audio_system()
        with self.lock:
            self.is_speaking = True
        self.tts_adapter.speak(humor_message)
        with self.lock:
            self.is_speaking = False
    
    def _diagnose_audio_system(self):
        """Diagnostic complet du système audio."""
        print("=== Diagnostic du système audio ===")
        
        # Test 1: Commande say
        print("1. Test de la commande 'say':")
        try:
            result = subprocess.run(["say", "-v", "?"], capture_output=True, timeout=5)
            if result.returncode == 0:
                print("   ✓ Commande 'say' disponible")
                voices = result.stdout.decode().strip().split('\n')[:3]
                for voice in voices:
                    print(f"   - {voice}")
            else:
                print("   ✗ Commande 'say' non fonctionnelle")
        except Exception as e:
            print(f"   ✗ Erreur: {str(e)}")
        
        # Test 2: pyttsx3
        print("\n2. Test de pyttsx3:")
        try:
            import pyttsx3
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            print(f"   ✓ pyttsx3 disponible avec {len(voices) if voices else 0} voix")
            if voices:
                for i, voice in enumerate(voices[:3]):
                    print(f"   - {voice.name} ({voice.id})")
        except Exception as e:
            print(f"   ✗ pyttsx3 non disponible: {str(e)}")
        
        print("================================\n")
        # Test 3: PyAudio
        print("3. Test de PyAudio:")
        if PYAUDIO_AVAILABLE:
            try:
                audio = pyaudio.PyAudio()
                print("   ✓ PyAudio disponible")
                print(f"   - Version: {audio.get_version()}")
                print(f"   - Nombre de périphériques: {audio.get_device_count()}")
                audio.terminate()
            except Exception as e:
                print(f"   ✗ Erreur lors de l'initialisation de PyAudio: {str(e)}")
        else:
            print("   ✗ PyAudio n'est pas disponible")
        print("================================\n")
        # Test 4: Vérification des moteurs STT
        print("4. Vérification des moteurs STT:")
        if WHISPER_AVAILABLE:
            print("   ✓ Whisper est disponible")
        else:
            print("   ✗ Whisper n'est pas disponible")
        if VOSK_AVAILABLE:
            print("   ✓ Vosk est disponible")
        else:
            print("   ✗ Vosk n'est pas disponible")
        if WAV2VEC2_AVAILABLE:
            print("   ✓ Wav2Vec2 est disponible")
        else:
            print("   ✗ Wav2Vec2 n'est pas disponible")
        # Enregistrer l'état des moteurs STT
        with open(STT_ENGINES_FILE, "w") as f:
            json.dump({
                "whisper": WHISPER_AVAILABLE,
                "vosk": VOSK_AVAILABLE,
                "wav2vec2": WAV2VEC2_AVAILABLE
            }, f, indent=4)
        print("================================\n")
        # Test 5: Vérification de l'accélération GPU
        print("5. Vérification de l'accélération GPU:")
        if WHISPER_AVAILABLE or WAV2VEC2_AVAILABLE:
            cuda_available = torch.cuda.is_available()
            if cuda_available:
                print("   ✓ Accélération GPU disponible")
                print(f"   - Nombre de GPU: {torch.cuda.device_count()}")
                for i in range(torch.cuda.device_count()):
                    print(f"   - GPU {i}: {torch.cuda.get_device_name(i)}")
            else:
                print("   ✗ Accélération GPU non disponible")
        else:
            print("   ✗ Aucun moteur STT nécessitant l'accélération GPU n'est disponible")
        print("================================\n")

    def _update_listening_indicator(self):
        """Affiche un indicateur visuel de l'état d'écoute."""
        with self.lock:
            is_listening = self.is_listening
            is_speaking = self.is_speaking
        
        # Effacer la ligne actuelle
        sys.stdout.write("\r" + " " * 50 + "\r")
        
        if is_speaking:
            sys.stdout.write("🔊 Peer parle... (dites 'quitter' pour arrêter) ")
        elif is_listening:
            sys.stdout.write("🎤 Écoute active...(dites: 'comment ça va ? pour avoir l'état du système)' ")
        else:
            sys.stdout.write("⏳ En attente... (Interprétation de votre commande - vous pouvez poursuivre) ")
        
        sys.stdout.flush()
    
    def _time_announcement_loop(self):
        """Boucle d'annonce de l'heure chaque minute."""
        while self.running:
            current_time = time.time()
            # Vérifier si une minute s'est écoulée depuis la dernière annonce
            if current_time - self.last_time_announcement >= 60:
                self.last_time_announcement = current_time
                self._announce_time()
            time.sleep(1)
    
    def _announce_time(self):
        """Annonce l'heure actuelle."""
        now = datetime.datetime.now()
        time_str = now.strftime("%H:%M")
        
        # Formater le message en français
        hour = now.hour
        minute = now.minute
        
        if minute == 0:
            time_message = f"Il est {hour} heure{'s' if hour > 1 else ''} pile."
        else:
            time_message = f"Il est {hour} heure{'s' if hour > 1 else ''} {minute}."
        
        print(f"\n{time_message}")
        
        # Vocaliser l'heure seulement si on n'est pas déjà en train de parler
        with self.lock:
            if not self.is_speaking:
                self.is_speaking = True
                self.tts_adapter.speak(time_message)
        with self.lock:
            self.is_speaking = True
    def _listen_loop(self):
        """Boucle d'écoute pour la reconnaissance vocale."""
        if self.whisper_model:
            self._listen_with_whisper()
        elif self.vosk_model:
            self._listen_with_vosk()
        elif self.wav2vec2_processor and self.wav2vec2_model:
            self._listen_with_wav2vec2()
        else:
            print("Aucun moteur de reconnaissance vocale n'est disponible.")
    
    def _listen_with_whisper(self):
        """Boucle d'écoute utilisant Whisper."""
        stream = self.audio.open(
            format=self.audio_format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )
        
        print("Écoute des commandes vocales avec Whisper... (dites 'Comment ça va' pour vérifier l'état du système)")
        
        while self.running:
            try:
                with self.lock:
                    self.is_listening = True
                
                # Enregistrer l'audio pendant 3 secondes
                frames = []
                for _ in range(0, int(self.rate / self.chunk * 3)):
                    data = stream.read(self.chunk, exception_on_overflow=False)
                    frames.append(data)
                
                with self.lock:
                    self.is_listening = False
                
                # Convertir les données audio en format numpy pour Whisper
                audio_data = b''.join(frames)
                audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                
                # Transcrire l'audio avec Whisper
                result = self.whisper_model.transcribe(audio_np, language="fr", fp16=False)
                text = result["text"].strip().lower()
                
                if text:
                    print(f"\nCommande reconnue: {text}")
                    self.command_queue.put(text)
                    self.error_count = 0  # Réinitialiser le compteur d'erreurs
            
            except Exception as e:
                with self.lock:
                    self.is_listening = False
                self.error_count += 1
                
                if self.error_count <= 1:  # Afficher l'erreur une seule fois
                    print(f"\nErreur lors de la reconnaissance vocale avec Whisper: {str(e)}")
                
                # Si trop d'erreurs consécutives, attendre plus longtemps
                if self.error_count > self.max_consecutive_errors:
                    time.sleep(5)  # Attendre plus longtemps avant de réessayer
                else:
                    time.sleep(1)
    
    def _listen_with_vosk(self):
        """Boucle d'écoute utilisant Vosk."""
        # Initialiser le recognizer Vosk
        self.vosk_recognizer = KaldiRecognizer(self.vosk_model, self.rate)
        
        stream = self.audio.open(
            format=self.audio_format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )
        
        print("Écoute des commandes vocales avec Vosk... (dites 'Comment ça va' pour vérifier l'état du système)")
        
        while self.running:
            try:
                with self.lock:
                    self.is_listening = True
                
                # Lire les données audio
                data = stream.read(self.chunk, exception_on_overflow=False)
                
                # Traiter les données avec Vosk
                if self.vosk_recognizer.AcceptWaveform(data):
                    with self.lock:
                        self.is_listening = False
                    
                    # Obtenir le résultat
                    result = json.loads(self.vosk_recognizer.Result())
                    text = result.get("text", "").strip().lower()
                    
                    if text:
                        print(f"\nCommande reconnue: {text}")
                        self.command_queue.put(text)
                        self.error_count = 0  # Réinitialiser le compteur d'erreurs
                else:
                    # Résultat partiel, continuer l'écoute
                    partial = json.loads(self.vosk_recognizer.PartialResult())
                    partial_text = partial.get("partial", "")
                    if partial_text:
                        # Vérifier si la commande "quitter" est dans le résultat partiel
                        if "quitter" in partial_text or "arrêter" in partial_text or "stop" in partial_text:
                            with self.lock:
                                self.is_listening = False
                            print(f"\nCommande reconnue: {partial_text}")
                            self.command_queue.put(partial_text)
                            self.error_count = 0
            
            except Exception as e:
                with self.lock:
                    self.is_listening = False
                self.error_count += 1
                
                if self.error_count <= 1:  # Afficher l'erreur une seule fois
                    print(f"\nErreur lors de la reconnaissance vocale avec Vosk: {str(e)}")
                
                # Si trop d'erreurs consécutives, attendre plus longtemps
                if self.error_count > self.max_consecutive_errors:
                    time.sleep(5)  # Attendre plus longtemps avant de réessayer
                else:
                    time.sleep(1)
    
    def _listen_with_wav2vec2(self):
        """Boucle d'écoute utilisant Wav2Vec2."""
        stream = self.audio.open(
            format=self.audio_format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )
        
        print("Écoute des commandes vocales avec Wav2Vec2... (dites 'Comment ça va' pour vérifier l'état du système)")
        
        while self.running:
            try:
                with self.lock:
                    self.is_listening = True
                
                # Enregistrer l'audio pendant 3 secondes
                frames = []
                for _ in range(0, int(self.rate / self.chunk * 3)):
                    data = stream.read(self.chunk, exception_on_overflow=False)
                    frames.append(data)
                
                with self.lock:
                    self.is_listening = False
                
                # Convertir les données audio en format numpy pour Wav2Vec2
                audio_data = b''.join(frames)
                audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                
                # Traiter l'audio avec Wav2Vec2
                inputs = self.wav2vec2_processor(audio_np, sampling_rate=self.rate, return_tensors="pt", padding=True)
                with torch.no_grad():
                    logits = self.wav2vec2_model(inputs.input_values).logits
                
                # Décoder la sortie
                predicted_ids = torch.argmax(logits, dim=-1)
                transcription = self.wav2vec2_processor.batch_decode(predicted_ids)[0].lower()
                
                if transcription:
                    print(f"\nCommande reconnue: {transcription}")
                    self.command_queue.put(transcription)
                    self.error_count = 0  # Réinitialiser le compteur d'erreurs
            
            except Exception as e:
                with self.lock:
                    if not self.is_speaking:
                        self.is_speaking = True
                    self.error_count += 1
                
                if self.error_count <= 1:  # Afficher l'erreur une seule fois
                    print(f"\nErreur lors de la reconnaissance vocale avec Wav2Vec2: {str(e)}")
                
                # Si trop d'erreurs consécutives, attendre plus longtemps
                if self.error_count > self.max_consecutive_errors:
                    time.sleep(5)  # Attendre plus longtemps avant de réessayer
                else:
                    time.sleep(1)
    
    def _process_command(self, command_text: str):
        """
        Traite une commande vocale.
        
        Args:
            command_text: Texte de la commande vocale
        """
        # Vérifier si c'est une commande pour quitter pendant que le système parle
        if self.is_speaking and any(re.search(pattern, command_text, re.IGNORECASE) for pattern in [r"(?:quitter|arrêter|stop)"]):
            self.quit()
            return
        
        # Traiter les commandes normales
        for pattern, action in self.commands.items():
            if re.search(pattern, command_text, re.IGNORECASE):
                action()
                return
        
        # Commande non reconnue
        print("\nCommande non reconnue: " + command_text)
        with self.lock:
            if not self.is_speaking:
                self.is_speaking = True
            self.tts_adapter.speak("Je n'ai pas compris cette commande.")
        with self.lock:
            self.is_speaking = False
    
    def check_system(self):
        """Vérifie et vocalise l'état du système."""
        status = self.system_check_service.check_system()
        message = self.system_check_service.get_status_message()
        
        # Vocaliser le message
        with self.lock:
            if not self.is_speaking:
                self.is_speaking = True
            self.tts_adapter.speak(message)
        with self.lock:
            self.is_speaking = False
        
        # Afficher les détails
        print("\n" + message)
        print("\nDétails des composants:")
        for component, details in status.components_status.items():
            status_str = "✓" if details.get("status", False) else "✗"
            print(f"{status_str} {component}: {details.get('message', '')}")
    
    def quit(self):
        """Quitte l'interface SUI."""
        print("\nFermeture de l'interface SUI...")
        with self.lock:
            if not self.is_speaking:
                self.is_speaking = True
            self.tts_adapter.speak("Au revoir!")
        with self.lock:
            self.is_speaking = False
        self.running = False


def main():
    """Point d'entrée principal pour l'interface SUI."""
    try:
        sui = SUI()
        sui.run()
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de la SUI: {str(e)}")


if __name__ == "__main__":
    main()
