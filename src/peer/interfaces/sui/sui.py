"""
Module contenant l'interface vocale (SUI) de Peer.

Interface vocale omnisciente avec capacités d'intelligence artificielle avancées,
incluant la détection d'activité vocale (VAD), reconnaissance Whisper optimisée,
analyse contextuelle, assistance proactive et apprentissage adaptatif.
"""

import os
import sys
import time
import threading
import queue
import logging
import re
import json
import math
import datetime
import psutil
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Union
from dataclasses import dataclass, asdict
from collections import deque, defaultdict

# Configuration du logging avancée
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.expanduser('~/.peer/sui.log'), mode='a')
    ]
)

# Importation des dépendances
try:
    import pyaudio
    import numpy as np
    import whisper
    import pyttsx3
    from pydantic import BaseModel
    import webrtcvad  # Pour une meilleure détection d'activité vocale
except ImportError as e:
    print(f"Erreur lors du chargement des dépendances: {e}")
    print("Veuillez installer les dépendances requises:")
    print("  pip install pyaudio numpy pyttsx3 openai-whisper webrtcvad")
    sys.exit(1)

# Importation des modules Peer refactorisés
from peer.core import PeerDaemon, CoreRequest, CoreResponse, CommandType, ResponseType, InterfaceType
from peer.core.protocol import InterfaceAdapter
from peer.infrastructure.adapters.simple_tts_adapter import SimpleTTSAdapter


@dataclass
class SpeechRecognitionResult:
    """Résultat enrichi de reconnaissance vocale."""
    text: str
    confidence: float = 0.0
    language: str = "fr"
    processing_time: float = 0.0
    audio_quality: float = 0.0
    is_command: bool = False
    intent_confidence: float = 0.0


@dataclass 
class VoiceActivityMetrics:
    """Métriques d'activité vocale pour analyse intelligente."""
    speech_detected: bool = False
    energy_level: float = 0.0
    zero_crossing_rate: float = 0.0
    spectral_centroid: float = 0.0
    background_noise_level: float = 0.0
    speech_probability: float = 0.0


@dataclass
class ContextualInfo:
    """Informations contextuelles pour l'assistance intelligente."""
    current_time: datetime.datetime
    session_duration: float
    commands_count: int
    last_commands: List[str]
    user_response_pattern: Dict[str, Any]
    system_performance: Dict[str, float]
    recent_errors: List[str]
    working_directory: str
    active_files: List[str]


class IntelligentSUISpeechAdapter(InterfaceAdapter):
    """
    Adaptateur intelligent pour l'interface vocale (SUI) avec capacités
    d'analyse contextuelle et assistance proactive.
    """
    
    def __init__(self):
        super().__init__(InterfaceType.SUI)
        self.logger = logging.getLogger("IntelligentSUISpeechAdapter")
        
        # Mapping étendu des commandes vocales
        self.voice_commands = {
            # Commandes de base français
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
            
            # Commandes avancées français (mapping vers les commandes existantes)
            "optimise": CommandType.SUGGEST,  # Optimisation = suggestion d'améliorations
            "améliore": CommandType.SUGGEST,
            "suggère": CommandType.SUGGEST,
            "recommande": CommandType.SUGGEST,
            "vérifie": CommandType.ANALYZE,  # Vérification = analyse
            "contrôle": CommandType.ANALYZE,
            "corrige": CommandType.SUGGEST,  # Correction = suggestion de fixes
            "répare": CommandType.SUGGEST,
            "nettoie": CommandType.SUGGEST,  # Nettoyage = suggestion de refactoring
            "organise": CommandType.SUGGEST,
            "monitore": CommandType.STATUS,  # Monitoring = statut
            "surveille": CommandType.STATUS,
            "alerte": CommandType.STATUS,    # Alertes = statut/info
            "notifie": CommandType.STATUS,
            
            # Commandes anglaises
            "what time": CommandType.TIME,
            "what date": CommandType.DATE,
            "repeat": CommandType.ECHO,
            "capabilities": CommandType.CAPABILITIES,
            "what can you do": CommandType.CAPABILITIES,
            "analyze": CommandType.ANALYZE,
            "explain": CommandType.EXPLAIN,
            "optimize": CommandType.SUGGEST,
            "improve": CommandType.SUGGEST,
            "suggest": CommandType.SUGGEST,
            "recommend": CommandType.SUGGEST,
            "check": CommandType.ANALYZE,
            "validate": CommandType.ANALYZE,
            "fix": CommandType.SUGGEST,
            "repair": CommandType.SUGGEST,
            "clean": CommandType.SUGGEST,
            "organize": CommandType.SUGGEST,
            "monitor": CommandType.STATUS,
            "watch": CommandType.STATUS,
            "alert": CommandType.STATUS,
            "notify": CommandType.STATUS,
        }
        
        # Historique intelligent des commandes
        self.command_history = deque(maxlen=50)
        self.command_patterns = defaultdict(int)
        self.response_times = deque(maxlen=20)
        self.user_preferences = self._load_user_preferences()
    
    def _load_user_preferences(self) -> Dict[str, Any]:
        """Charge les préférences utilisateur depuis le fichier de configuration."""
        try:
            preferences_path = Path.home() / '.peer' / 'sui_preferences.json'
            if preferences_path.exists():
                with open(preferences_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"Impossible de charger les préférences: {e}")
        
        # Préférences par défaut
        return {
            "response_style": "balanced",  # concise, balanced, detailed
            "voice_speed": 1.0,
            "voice_volume": 0.8,
            "language_preference": "fr",
            "proactive_assistance": True,
            "context_awareness": True,
            "learning_mode": True,
            "notification_level": "normal"  # minimal, normal, verbose
        }
    
    def _save_user_preferences(self):
        """Sauvegarde les préférences utilisateur."""
        try:
            preferences_path = Path.home() / '.peer' / 'sui_preferences.json'
            preferences_path.parent.mkdir(exist_ok=True)
            with open(preferences_path, 'w', encoding='utf-8') as f:
                json.dump(self.user_preferences, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde des préférences: {e}")
    
    def translate_to_core(self, speech_input: str, context: Dict[str, Any] = None) -> CoreRequest:
        """Traduit une commande vocale en requête standardisée avec analyse contextuelle."""
        # Normaliser le texte
        normalized_input = self._normalize_speech_input(speech_input)
        
        # Analyser l'intention et extraire les paramètres
        command, parameters = self._parse_intelligent_speech_command(normalized_input, context or {})
        
        # Enrichir avec des informations contextuelles
        enriched_context = {
            "original_speech": speech_input,
            "normalized": normalized_input,
            "timestamp": datetime.datetime.now().isoformat(),
            "user_preferences": self.user_preferences,
            "command_history": list(self.command_history)[-5:],  # Les 5 dernières commandes
            "session_context": context or {}
        }
        
        # Enregistrer dans l'historique
        self.command_history.append({
            "text": speech_input,
            "command": command.value,
            "timestamp": time.time(),
            "context": context or {}
        })
        
        return CoreRequest(
            command=command,
            parameters=parameters,
            context=enriched_context,
            interface_type=InterfaceType.SUI
        )
    
    def translate_from_core(self, core_response: CoreResponse) -> Dict[str, Any]:
        """Traduit une réponse du core en format adapté avec personnalisation intelligente."""
        # Adapter le message selon le style de réponse préféré
        vocal_message = self._adapt_message_for_intelligent_speech(
            core_response.message, 
            self.user_preferences.get("response_style", "balanced")
        )
        
        # Ajouter des suggestions proactives si approprié
        proactive_suggestions = []
        if self.user_preferences.get("proactive_assistance", True):
            proactive_suggestions = self._generate_proactive_suggestions(core_response)
        
        return {
            "vocal_message": vocal_message,
            "should_vocalize": True,
            "original_response": core_response,
            "display_message": core_response.message,
            "response_type": core_response.type.value,
            "proactive_suggestions": proactive_suggestions,
            "voice_settings": {
                "speed": self.user_preferences.get("voice_speed", 1.0),
                "volume": self.user_preferences.get("voice_volume", 0.8)
            }
        }
    
    def _normalize_speech_input(self, speech_input: str) -> str:
        """Normalisation avancée de l'entrée vocale."""
        # Convertir en minuscules et supprimer espaces excessifs
        normalized = speech_input.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Corrections phonétiques courantes
        phonetic_corrections = {
            "pire": "peer",
            "père": "peer", 
            "pair": "peer",
            "per": "peer",
            "c l i": "cli",
            "t u i": "tui",
            "s u i": "sui",
            "a p i": "api"
        }
        
        for incorrect, correct in phonetic_corrections.items():
            normalized = normalized.replace(incorrect, correct)
        
        return normalized
    
    def _parse_intelligent_speech_command(self, normalized_input: str, context: Dict[str, Any]) -> Tuple[CommandType, Dict[str, Any]]:
        """Analyse intelligente des commandes avec prise en compte du contexte."""
        
        # Recherche de correspondance directe
        for trigger, command in self.voice_commands.items():
            if trigger in normalized_input:
                parameters = self._extract_parameters(normalized_input, trigger, context)
                self.command_patterns[command.value] += 1
                return command, parameters
        
        # Analyse contextuelle avancée
        if self.user_preferences.get("context_awareness", True):
            contextual_command = self._analyze_contextual_intent(normalized_input, context)
            if contextual_command:
                return contextual_command
        
        # Analyse par mots-clés sémantiques
        semantic_command = self._analyze_semantic_intent(normalized_input)
        if semantic_command:
            return semantic_command
        
        # Commande par défaut - requête générale
        return CommandType.QUERY, {"args": normalized_input.split(), "full_text": normalized_input}
    
    def _extract_parameters(self, normalized_input: str, trigger: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extraction intelligente des paramètres d'une commande."""
        parameters = {}
        
        # Extraire le texte après le déclencheur
        if trigger in normalized_input:
            parts = normalized_input.split(trigger, 1)
            if len(parts) > 1 and parts[1].strip():
                remaining_text = parts[1].strip()
                parameters["args"] = remaining_text.split()
                parameters["full_text"] = remaining_text
        
        # Ajouter le contexte
        parameters["context"] = context
        parameters["trigger"] = trigger
        
        return parameters
    
    def _analyze_contextual_intent(self, normalized_input: str, context: Dict[str, Any]) -> Optional[Tuple[CommandType, Dict[str, Any]]]:
        """Analyse l'intention basée sur le contexte de la session."""
        
        # Analyser l'historique récent des commandes
        recent_commands = [cmd["command"] for cmd in list(self.command_history)[-3:]]
        
        # Si beaucoup de commandes d'aide récemment, proposer un tutoriel
        if recent_commands.count("HELP") >= 2:
            return CommandType.CAPABILITIES, {"intent": "extended_help", "context": context}
        
        # Si erreurs récentes, proposer de l'aide pour résoudre
        if any("error" in str(cmd).lower() for cmd in recent_commands):
            if any(word in normalized_input for word in ["aide", "help", "problème", "error"]):
                return CommandType.HELP, {"intent": "error_assistance", "context": context}
        
        # Analyse temporelle
        current_hour = datetime.datetime.now().hour
        if current_hour < 9 or current_hour > 18:
            if "statut" in normalized_input or "état" in normalized_input:
                return CommandType.STATUS, {"intent": "off_hours_check", "context": context}
        
        return None
    
    def _analyze_semantic_intent(self, normalized_input: str) -> Optional[Tuple[CommandType, Dict[str, Any]]]:
        """Analyse sémantique pour détecter l'intention."""
        
        # Mots-clés pour différents types d'intentions
        intent_patterns = {
            CommandType.HELP: ["aide", "help", "comment", "how", "pourquoi", "why"],
            CommandType.STATUS: ["état", "status", "va", "marche", "fonctionne", "work"],
            CommandType.ANALYZE: ["regarde", "examine", "vérifie", "check", "analyse", "analyze"],
            CommandType.EXPLAIN: ["explique", "explain", "dis-moi", "tell me", "qu'est-ce", "what"],
            CommandType.SUGGEST: ["optimise", "optimize", "améliore", "improve", "accélère", "faster", "répare", "fix", "corrige", "correct", "résout", "solve"]
        }
        
        for command_type, keywords in intent_patterns.items():
            if any(keyword in normalized_input for keyword in keywords):
                return command_type, {"intent": "semantic_match", "full_text": normalized_input}
        
        return None
    
    def _adapt_message_for_intelligent_speech(self, message: str, response_style: str) -> str:
        """Adaptation intelligente du message selon le style de réponse."""
        
        # Adaptation de base pour la prononciation
        adapted_message = self._basic_speech_adaptation(message)
        
        # Adapter selon le style demandé
        if response_style == "concise":
            adapted_message = self._make_concise(adapted_message)
        elif response_style == "detailed":
            adapted_message = self._make_detailed(adapted_message)
        # "balanced" est le style par défaut, pas de modification supplémentaire
        
        return adapted_message
    
    def _basic_speech_adaptation(self, message: str) -> str:
        """Adaptations de base pour la synthèse vocale."""
        adaptations = {
            "Peer": "Pire",
            "CLI": "C L I",
            "TUI": "T U I", 
            "SUI": "S U I",
            "API": "A P I",
            "0.2.0": "version zéro point deux point zéro",
            "ERROR": "Erreur",
            "WARNING": "Attention",
            "INFO": "Information",
            "SUCCESS": "Succès",
            "OK": "D'accord",
            "NOK": "Pas bon"
        }
        
        adapted_message = message
        for original, replacement in adaptations.items():
            adapted_message = adapted_message.replace(original, replacement)
        
        return adapted_message
    
    def _make_concise(self, message: str) -> str:
        """Rend le message plus concis."""
        # Supprimer les phrases explicatives longues
        sentences = message.split('.')
        if len(sentences) > 2:
            # Garder seulement les 2 premières phrases principales
            return '. '.join(sentences[:2]) + '.'
        return message
    
    def _make_detailed(self, message: str) -> str:
        """Enrichit le message avec plus de détails."""
        # Ajouter des informations contextuelles
        detailed_message = message
        
        if "succès" in message.lower() or "success" in message.lower():
            detailed_message += " Tout fonctionne parfaitement."
        elif "erreur" in message.lower() or "error" in message.lower():
            detailed_message += " Je peux vous aider à résoudre ce problème si vous le souhaitez."
        
        return detailed_message
    
    def _generate_proactive_suggestions(self, core_response: CoreResponse) -> List[str]:
        """Génère des suggestions proactives basées sur la réponse."""
        suggestions = []
        
        # Suggestions basées sur le type de réponse
        if core_response.type == ResponseType.ERROR:
            suggestions.append("Voulez-vous que j'analyse l'erreur en détail ?")
            suggestions.append("Je peux proposer des solutions pour corriger ce problème.")
        
        elif core_response.type == ResponseType.SUCCESS:
            suggestions.append("Souhaitez-vous optimiser cette opération ?")
            suggestions.append("Je peux analyser la performance si vous voulez.")
        
        # Suggestions basées sur l'historique
        if len(self.command_history) > 5:
            common_commands = self._get_most_common_commands()
            if common_commands:
                suggestions.append(f"Vous utilisez souvent '{common_commands[0]}'. Voulez-vous l'optimiser ?")
        
        return suggestions[:2]  # Limiter à 2 suggestions
    
    def _get_most_common_commands(self) -> List[str]:
        """Retourne les commandes les plus fréquemment utilisées."""
        return sorted(self.command_patterns.keys(), key=self.command_patterns.get, reverse=True)[:3]
    
    def get_interface_help(self) -> str:
        """Retourne l'aide complète avec informations sur les capacités intelligentes."""
        help_text = """Interface Vocale Intelligente Peer - Capacités Omniscientes

🎯 COMMANDES DE BASE:
- "Aide" / "Help" - Affiche cette aide
- "Statut" / "Status" - Vérifie l'état du système  
- "Version" - Affiche la version
- "Quelle heure" - Donne l'heure actuelle
- "Quelle date" - Donne la date actuelle

🧠 COMMANDES INTELLIGENTES:
- "Analyse [sujet]" - Analyse approfondie avec suggestions
- "Explique [concept]" - Explications contextuelles
- "Optimise" - Optimisation automatique
- "Suggère" - Recommandations intelligentes
- "Vérifie" - Contrôles proactifs
- "Monitore" - Surveillance continue

🎛️ PERSONNALISATION:
- Style de réponse: concis, équilibré, détaillé
- Vitesse et volume de la voix ajustables
- Assistance proactive activable/désactivable
- Apprentissage des préférences utilisateur

🤖 INTELLIGENCE CONTEXTUELLE:
- Compréhension du contexte de session
- Suggestions proactives basées sur l'historique
- Adaptation aux patterns d'utilisation
- Assistance predictive pour résoudre les problèmes

Je comprends le langage naturel et m'adapte à vos habitudes d'utilisation."""
        return help_text

    def format_help(self, help_data) -> str:
        """Formate l'aide pour la sortie vocale (version concise)."""
        if isinstance(help_data, str):
            return help_data
        
        commands = help_data.get('commands', {}) if isinstance(help_data, dict) else {}
        
        # Pour la voix, fournir un résumé des commandes principales
        main_commands = ['help', 'status', 'time', 'date', 'echo', 'analyze']
        help_text = "Commandes principales disponibles: "
        
        available_main = [cmd for cmd in main_commands if cmd in commands]
        help_text += ', '.join(available_main)
        
        help_text += ". Dites 'aide' suivi du nom d'une commande pour plus de détails."
        return help_text
    
    def format_error(self, error_response) -> str:
        """Formate les erreurs pour la sortie vocale."""
        if hasattr(error_response, 'message'):
            return f"Erreur: {error_response.message}"
        elif isinstance(error_response, dict):
            message = error_response.get('message', 'Erreur inconnue')
            return f"Erreur: {message}"
        elif isinstance(error_response, str):
            return f"Erreur: {error_response}"
        else:
            return f"Erreur: {str(error_response)}"


class OmniscientSUI:
    """
    Interface utilisateur vocale omnisciente avec capacités d'IA avancées.
    
    Cette classe implémente une interface vocale intelligente qui:
    - Écoute en continu avec détection d'activité vocale (VAD)
    - Reconnaît la parole avec Whisper optimisé pour le français
    - Analyse le contexte et fournit une assistance proactive
    - Apprend des habitudes utilisateur et s'adapte
    - Intègre des modèles intelligents pour une expérience naturelle
    """
    def __init__(self, daemon: Optional[PeerDaemon] = None):
        """Initialise l'interface vocale omnisciente."""
        self.logger = logging.getLogger("OmniscientSUI")
        self.logger.info("🚀 Initialisation de l'interface vocale omnisciente...")
        
        # Initialisation du daemon et adaptateur
        self.daemon = daemon or PeerDaemon()
        self.adapter = IntelligentSUISpeechAdapter()
        
        # Session et TTS
        self.session_id = self.daemon.create_session(InterfaceType.SUI)
        self.tts_adapter = SimpleTTSAdapter()
        self.tts_lock = threading.Lock()
        
        # Variables d'état principal
        self.running = False
        self.listening = False
        self.speaking = False
        self.paused = False
        
        # Variables audio avancées
        self.audio_stream = None
        self.vad = None  # Voice Activity Detector
        self.vad_enabled = True
        self.audio_buffer = deque(maxlen=32)  # Buffer circulaire pour l'audio
        self.noise_threshold = 500  # Seuil de bruit adaptatif
        self.energy_threshold = 800  # Seuil d'énergie pour la détection vocale
        
        # Intelligence et contexte
        self.command_queue = queue.Queue()
        self.context_queue = queue.Queue()
        self.session_start_time = time.time()
        self.command_history = deque(maxlen=100)
        self.response_style = "balanced"  # concise, balanced, detailed
        
        # Métriques de performance
        self.avg_response_time = 0.0
        self.recognition_accuracy = 0.95
        self.interruption_count = 0
        self.total_commands = 0
        
        # Variables pour l'analyse contextuelle
        self.last_context_analysis = time.time()
        self.context_analysis_interval = 30.0  # Analyser le contexte toutes les 30s
        self.performance_metrics = {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "disk_usage": 0.0,
            "response_time": 0.0
        }
        
        # Variables pour l'audio avancé
        self.sample_rate = 16000
        self.chunk_size = 1024
        self.audio_format = pyaudio.paInt16
        self.channels = 1
        self.record_seconds = 5  # Durée max d'enregistrement continu
        
        # Variables pour l'isolation audio et éviter la boucle infinie d'auto-écoute
        self.output_device_index = None  # Index du périphérique de sortie
        self.input_device_index = None   # Index du périphérique d'entrée
        self.audio_isolation_enabled = True
        self.min_silence_after_speech = 1.0  # Secondes de silence avant de réécouter
        self.speech_end_time = 0.0  # Timestamp de fin de vocalisation
        
        # Indicateurs visuels d'état
        self.current_status = "🔄 Initialisation..."
        self.status_lock = threading.Lock()
        self.show_visual_indicators = True
        
        # Initialisation des composants
        self._init_advanced_speech_recognition()
        self._init_voice_activity_detection()
        self._init_audio_isolation()
        self._enable_advanced_features()
    
    def _init_advanced_speech_recognition(self):
        """Initialise le moteur de reconnaissance vocale Whisper optimisé."""
        try:
            self.logger.info("🧠 Initialisation de Whisper optimisé pour le français...")
            
            # Utiliser un modèle Whisper adapté selon les ressources disponibles
            available_memory = psutil.virtual_memory().available / (1024**3)  # GB
            
            if available_memory > 8:
                model_size = "medium"
                self.logger.info("💪 Mémoire suffisante: utilisation du modèle Whisper medium")
            elif available_memory > 4:
                model_size = "small"
                self.logger.info("⚡ Mémoire modérée: utilisation du modèle Whisper small")
            else:
                model_size = "base"
                self.logger.info("🔧 Mémoire limitée: utilisation du modèle Whisper base")
            
            # Charger le modèle avec fp16=False pour éviter l'avertissement FP16 sur CPU
            self.whisper_model = whisper.load_model(model_size, device="cpu", in_memory=True)
            self.speech_recognition_engine = "whisper"
            self.logger.info(f"✅ Whisper {model_size} initialisé avec succès")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de l'initialisation de Whisper: {e}")
            self.speech_recognition_engine = None
    
    def _init_voice_activity_detection(self):
        """Initialise le détecteur d'activité vocale (VAD)."""
        try:
            # Initialiser WebRTC VAD
            self.vad = webrtcvad.Vad(2)  # Agressivité modérée (0-3)
            self.logger.info("🎙️ Détecteur d'activité vocale (VAD) initialisé")
        except Exception as e:
            self.logger.warning(f"⚠️ VAD non disponible, utilisation de la détection d'énergie simple: {e}")
            self.vad = None

    def _init_audio_isolation(self):
        """Initialise l'isolation audio pour éviter l'auto-écoute."""
        try:
            audio = pyaudio.PyAudio()
            
            # Lister les périphériques audio disponibles
            self._list_audio_devices(audio)
            
            # Essayer de trouver des périphériques d'entrée et sortie différents
            self._setup_separate_audio_devices(audio)
            
            audio.terminate()
            self.logger.info("🔇 Isolation audio configurée")
            
        except Exception as e:
            self.logger.warning(f"⚠️ Impossible de configurer l'isolation audio: {e}")
            self.audio_isolation_enabled = False

    def _list_audio_devices(self, audio):
        """Liste les périphériques audio disponibles."""
        self.logger.info("📱 Périphériques audio disponibles:")
        for i in range(audio.get_device_count()):
            info = audio.get_device_info_by_index(i)
            device_type = []
            if info['maxInputChannels'] > 0:
                device_type.append("INPUT")
            if info['maxOutputChannels'] > 0:
                device_type.append("OUTPUT")
            self.logger.info(f"  {i}: {info['name']} ({'/'.join(device_type)})")

    def _setup_separate_audio_devices(self, audio):
        """Configure des périphériques d'entrée et sortie séparés si possible."""
        try:
            # Par défaut, utiliser le périphérique par défaut
            default_input = None
            default_output = None
            
            # Chercher des périphériques spécifiques
            for i in range(audio.get_device_count()):
                info = audio.get_device_info_by_index(i)
                name = info['name'].lower()
                
                # Préférer les micros intégrés ou USB pour l'entrée
                if info['maxInputChannels'] > 0 and self.input_device_index is None:
                    if any(keyword in name for keyword in ['usb', 'headset', 'micro', 'built-in mic']):
                        self.input_device_index = i
                        self.logger.info(f"🎤 Périphérique d'entrée sélectionné: {info['name']}")
                
                # Préférer les haut-parleurs ou casques pour la sortie
                if info['maxOutputChannels'] > 0 and self.output_device_index is None:
                    if any(keyword in name for keyword in ['speaker', 'headphone', 'built-in output']):
                        self.output_device_index = i
                        self.logger.info(f"🔊 Périphérique de sortie sélectionné: {info['name']}")
            
            # Si aucun périphérique spécifique trouvé, utiliser les périphériques par défaut
            if self.input_device_index is None:
                self.input_device_index = audio.get_default_input_device_info()['index']
            if self.output_device_index is None:
                self.output_device_index = audio.get_default_output_device_info()['index']
                
        except Exception as e:
            self.logger.warning(f"⚠️ Erreur lors de la configuration des périphériques: {e}")

    def _update_visual_status(self, status: str):
        """Met à jour l'indicateur visuel d'état."""
        with self.status_lock:
            self.current_status = status
            if self.show_visual_indicators:
                print(f"\r{status}", end='', flush=True)
    
    def _detect_command_intent(self, text: str) -> Optional[str]:
        """Détecte l'intention de commande dans le texte reconnu."""
        if not text:
            return None
            
        text_lower = text.lower().strip()
        
        # Commandes directes
        direct_commands = {
            'aide': 'HELP',
            'help': 'HELP', 
            'version': 'VERSION',
            'statut': 'STATUS',
            'status': 'STATUS',
            'temps': 'TIME',
            'time': 'TIME',
            'heure': 'TIME',
            'date': 'DATE',
            'arrêt': 'STOP',
            'stop': 'STOP',
            'pause': 'PAUSE',
            'continuer': 'CONTINUE',
            'continue': 'CONTINUE'
        }
        
        for cmd_word, intent in direct_commands.items():
            if cmd_word in text_lower:
                return intent
        
        # Détection basée sur des mots-clés
        if any(word in text_lower for word in ['analyser', 'analyze', 'vérifier', 'check']):
            return 'ANALYZE'
        elif any(word in text_lower for word in ['suggérer', 'suggest', 'améliorer', 'improve', 'optimiser', 'optimize']):
            return 'SUGGEST'
        elif any(word in text_lower for word in ['expliquer', 'explain', 'que fait', 'what does']):
            return 'EXPLAIN'
        elif any(word in text_lower for word in ['créer', 'create', 'nouveau', 'new']):
            return 'CREATE'
        elif any(word in text_lower for word in ['modifier', 'modify', 'changer', 'change', 'éditer', 'edit']):
            return 'EDIT'
        elif any(word in text_lower for word in ['supprimer', 'delete', 'remove', 'effacer']):
            return 'DELETE'
        elif any(word in text_lower for word in ['rechercher', 'search', 'find', 'chercher']):
            return 'SEARCH'
        
        # Si aucune intention spécifique n'est détectée, considérer comme une requête générale
        if len(text_lower) > 5:  # Éviter les très courtes phrases
            return 'QUERY'
            
        return None
    
    def _enable_advanced_features(self):
        """Active les fonctionnalités avancées d'intelligence."""
        try:
            # Démarrer l'analyse contextuelle en arrière-plan
            self._start_continuous_context_analysis()
            
            # Initialiser l'apprentissage adaptatif
            self._initialize_adaptive_learning()
            
            # Réglage automatique des seuils audio
            self._auto_adjust_audio_thresholds()
            
            self.logger.info("🤖 Fonctionnalités d'intelligence avancées activées")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de l'activation des fonctionnalités avancées: {e}")
    
    def _start_continuous_context_analysis(self):
        """Démarre l'analyse continue du contexte en arrière-plan."""
        def context_analysis_loop():
            while self.running:
                try:
                    if time.time() - self.last_context_analysis > self.context_analysis_interval:
                        context = self._analyze_current_context()
                        self.context_queue.put(context)
                        self.last_context_analysis = time.time()
                        
                        # Fournir une assistance proactive si nécessaire
                        if context and self.adapter.user_preferences.get("proactive_assistance", True):
                            self._provide_proactive_assistance(context)
                
                except Exception as e:
                    self.logger.error(f"Erreur dans l'analyse contextuelle: {e}")
                
                time.sleep(5)  # Vérifier toutes les 5 secondes
        
        context_thread = threading.Thread(target=context_analysis_loop, daemon=True)
        context_thread.start()
    
    def _initialize_adaptive_learning(self):
        """Initialise le système d'apprentissage adaptatif."""
        # Analyser les patterns d'utilisation existants
        if self.command_history:
            self._adapt_to_user_patterns()
        
        # Charger les préférences utilisateur
        self._load_user_preferences()
        
        self.logger.info("📚 Système d'apprentissage adaptatif initialisé")
    
    def _auto_adjust_audio_thresholds(self):
        """Ajuste automatiquement les seuils audio selon l'environnement."""
        try:
            # Mesurer le niveau de bruit ambiant
            background_noise = self._measure_background_noise()
            
            # Ajuster les seuils en conséquence
            self.noise_threshold = max(300, background_noise * 1.5)
            self.energy_threshold = max(600, background_noise * 2.5)
            
            self.logger.info(f"🔧 Seuils audio ajustés - Bruit: {self.noise_threshold:.0f}, Énergie: {self.energy_threshold:.0f}")
            
        except Exception as e:
            self.logger.warning(f"⚠️ Impossible d'ajuster les seuils audio: {e}")
    
    def _measure_background_noise(self) -> float:
        """Mesure le niveau de bruit ambiant pour ajuster les seuils."""
        try:
            # Enregistrer un échantillon court du bruit ambiant
            audio = pyaudio.PyAudio()
            stream = audio.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            noise_samples = []
            for _ in range(10):  # 10 échantillons
                data = stream.read(self.chunk_size, exception_on_overflow=False)
                audio_np = np.frombuffer(data, dtype=np.int16)
                noise_level = np.sqrt(np.mean(audio_np**2))
                noise_samples.append(noise_level)
                time.sleep(0.1)
            
            stream.close()
            audio.terminate()
            
            return np.mean(noise_samples)
            
        except Exception as e:
            self.logger.warning(f"Erreur lors de la mesure du bruit: {e}")
            return 400.0  # Valeur par défaut
    
    def start(self):
        """Démarre l'interface vocale omnisciente."""
        if self.running:
            self.logger.warning("⚠️ L'interface vocale est déjà en cours")
            return
        
        self.running = True
        self.logger.info("🚀 Démarrage de l'interface vocale omnisciente...")
        
        # Vérifier la disponibilité des moteurs
        if not self.speech_recognition_engine:
            self.vocalize("Attention: aucun moteur de reconnaissance vocale disponible. Mode dégradé activé.")
            return
        
        # Démarrer les threads principaux
        self.listen_thread = threading.Thread(target=self._continuous_listen_loop, daemon=True)
        self.command_thread = threading.Thread(target=self._intelligent_command_loop, daemon=True)
        
        self.listen_thread.start()
        self.command_thread.start()
        
        # Message d'accueil personnalisé
        welcome_message = self._generate_personalized_greeting()
        self.vocalize(welcome_message)
        
        # Boucle principale avec surveillance
        try:
            while self.running:
                self._monitor_system_health()
                time.sleep(1.0)
        except KeyboardInterrupt:
            self.logger.info("⌨️ Interruption clavier détectée")
            self.stop()
    
    def stop(self):
        """Arrête l'interface vocale de manière gracieuse."""
        if not self.running:
            return
        
        self.logger.info("🛑 Arrêt de l'interface vocale omnisciente...")
        self.running = False
        
        # Sauvegarder les préférences apprises
        self._save_user_preferences()
        
        # Terminer la session
        if hasattr(self, 'session_id'):
            self.daemon.end_session(self.session_id)
        
        # Message de fin personnalisé
        farewell_message = self._generate_personalized_farewell()
        self.vocalize(farewell_message)
        
        self.logger.info("✅ Interface vocale arrêtée avec succès")
    
    def _continuous_listen_loop(self):
        """Boucle d'écoute continue avec détection d'activité vocale avancée et isolation audio renforcée."""
        self.logger.info("👂 Démarrage de l'écoute continue avancée...")
        self._update_visual_status("🎙️ J'écoute")
        
        try:
            audio = pyaudio.PyAudio()
            
            # Utiliser le périphérique d'entrée configuré pour l'isolation
            device_index = self.input_device_index if self.audio_isolation_enabled else None
            
            stream = audio.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.chunk_size
            )
            
            self.listening = True
            speech_frames = []
            in_speech = False
            silence_count = 0
            
            # Variables pour l'isolation audio renforcée
            last_tts_end = 0
            background_noise_level = 0
            noise_samples = []
            
            while self.running:
                # Isolation temporelle STRICTE - ne pas écouter pendant et après TTS
                current_time = time.time()
                
                # Vérification multi-niveaux pour éviter l'auto-écoute
                if self._should_skip_listening(current_time):
                    time.sleep(0.05)  # Pause courte pendant les périodes bloquées
                    continue
                
                try:
                    # Lire un chunk audio
                    audio_data = stream.read(self.chunk_size, exception_on_overflow=False)
                    
                    # Analyser l'activité vocale avec filtrage intelligent
                    vad_result = self._detect_voice_activity_filtered(audio_data, background_noise_level)
                    
                    # Mettre à jour le niveau de bruit de fond
                    noise_samples.append(vad_result.energy_level)
                    if len(noise_samples) > 50:  # Garder les 50 derniers échantillons
                        noise_samples.pop(0)
                        background_noise_level = sum(noise_samples) / len(noise_samples)
                    
                    if vad_result.speech_detected:
                        if not in_speech:
                            # Validation supplémentaire avant de considérer comme parole
                            if self._validate_real_speech(vad_result, background_noise_level):
                                in_speech = True
                                speech_frames = []
                                self.logger.debug("🎤 Début de parole validé")
                                self._update_visual_status("🧠 J'essaie de comprendre ta demande")
                                
                                # Gestion des interruptions avec validation stricte
                                if self.speaking:
                                    if self._handle_potential_interruption(audio_data):
                                        # Si c'est une vraie interruption, arrêter d'écouter temporairement
                                        time.sleep(0.5)
                                        continue
                        
                        speech_frames.append(audio_data)
                        silence_count = 0
                    else:
                        if in_speech:
                            silence_count += 1
                            speech_frames.append(audio_data)  # Inclure un peu de silence
                            
                            # Si suffisamment de silence, traiter la parole
                            if silence_count > 20:  # ~2 secondes de silence pour plus de sécurité
                                if not self.paused and len(speech_frames) > 10:  # Minimum de données
                                    self._process_complete_speech(speech_frames)
                                in_speech = False
                                speech_frames = []
                                silence_count = 0
                                self._update_visual_status("🎙️ J'écoute")
                    
                    # Mettre à jour le buffer circulaire pour l'analyse
                    self.audio_buffer.append(vad_result)
                    
                except Exception as e:
                    self.logger.error(f"❌ Erreur lors de l'écoute: {e}")
                    time.sleep(0.1)
            
        except Exception as e:
            self.logger.error(f"❌ Erreur fatale dans la boucle d'écoute: {e}")
        finally:
            if 'stream' in locals():
                stream.close()
            if 'audio' in locals():
                audio.terminate()
            self.listening = False
            self._update_visual_status("🔇 Écoute arrêtée")
            self.logger.info("👂 Écoute terminée")
    
    def _should_skip_listening(self, current_time: float) -> bool:
        """Détermine si on doit ignorer l'écoute pour éviter l'auto-détection."""
        # Période de blocage après TTS
        if self.audio_isolation_enabled and self.speech_end_time > 0:
            time_since_speech = current_time - self.speech_end_time
            if time_since_speech < self.min_silence_after_speech:
                return True
        
        # Ne pas écouter si on est en train de parler
        if self.speaking:
            return True
        
        # Période de grâce après récursion TTS
        if hasattr(self, '_tts_recursion_depth') and self._tts_recursion_depth > 0:
            return True
        
        return False
    
    def _detect_voice_activity_filtered(self, audio_data: bytes, background_noise: float) -> VoiceActivityMetrics:
        """Détecte l'activité vocale avec filtrage intelligent du bruit de fond et auto-audio."""
        # Détecter l'activité vocale normale
        vad_result = self._detect_voice_activity(audio_data)
        
        # Filtrage intelligent
        if vad_result.speech_detected:
            # Ignorer si le niveau est trop proche du bruit de fond
            if background_noise > 0 and vad_result.energy_level < background_noise * 1.8:
                vad_result.speech_detected = False
                vad_result.speech_probability *= 0.3
            
            # Ignorer si on vient de finir de parler
            if self.speech_end_time > 0:
                time_since_speech = time.time() - self.speech_end_time
                if time_since_speech < 1.0:  # 1 seconde de sécurité
                    vad_result.speech_detected = False
                    vad_result.speech_probability *= 0.2
                    self.logger.debug(f"🛡️ Audio ignoré - trop proche de la fin TTS ({time_since_speech:.2f}s)")
        
        return vad_result
    
    def _validate_real_speech(self, vad_result: VoiceActivityMetrics, background_noise: float) -> bool:
        """Valide que l'activité détectée est de la vraie parole utilisateur."""
        # Seuils de validation
        min_energy_ratio = 2.5  # L'énergie doit être au moins 2.5x le bruit de fond
        min_speech_probability = 0.7
        
        # Vérifier l'énergie par rapport au bruit de fond
        if background_noise > 0:
            energy_ratio = vad_result.energy_level / background_noise
            if energy_ratio < min_energy_ratio:
                return False
        
        # Vérifier la probabilité de parole
        if vad_result.speech_probability < min_speech_probability:
            return False
        
        # Vérifier qu'on n'est pas dans une période de blocage TTS
        if self._should_skip_listening(time.time()):
            return False
        
        return True
    
    def _detect_voice_activity(self, audio_data: bytes) -> VoiceActivityMetrics:
        """Détecte l'activité vocale avec analyse avancée."""
        try:
            # Vérifier que les données audio sont valides
            if not audio_data or len(audio_data) == 0:
                return VoiceActivityMetrics()
            
            # Convertir en numpy array
            audio_np = np.frombuffer(audio_data, dtype=np.int16)
            
            # Vérifier que l'array n'est pas vide
            if len(audio_np) == 0:
                return VoiceActivityMetrics()
            
            # Calculer les métriques audio avec vérifications robustes
            # Calculer l'énergie avec protection contre les valeurs invalides
            energy_squared = audio_np.astype(np.float64)**2  # Utiliser float64 pour éviter l'overflow
            mean_energy = np.mean(energy_squared)
            
            # Vérifier si la valeur est valide pour sqrt
            if np.isnan(mean_energy) or mean_energy < 0:
                energy_level = 0.0
            else:
                energy_level = np.sqrt(mean_energy)
            
            # Zero crossing rate avec vérification
            if len(audio_np) > 1:
                zero_crossing_rate = np.mean(np.diff(np.sign(audio_np)) != 0)
            else:
                zero_crossing_rate = 0.0
            
            # Spectral centroid (approximation simple) avec vérifications
            spectral_centroid = 0.0
            try:
                fft = np.fft.fft(audio_np)
                freqs = np.fft.fftfreq(len(fft), 1/self.sample_rate)
                magnitude = np.abs(fft)
                
                # Prendre seulement la première moitié (fréquences positives)
                half_len = len(magnitude) // 2
                if half_len > 0:
                    magnitude_sum = np.sum(magnitude[:half_len])
                    if magnitude_sum > 0:  # Éviter division par zéro
                        spectral_centroid = np.sum(freqs[:half_len] * magnitude[:half_len]) / magnitude_sum
            except:
                spectral_centroid = 0.0
            
            # Détection VAD
            speech_detected = False
            speech_probability = 0.0
            
            if self.vad and len(audio_data) == 2 * self.chunk_size:  # VAD nécessite une taille spécifique
                try:
                    # WebRTC VAD
                    speech_detected = self.vad.is_speech(audio_data, self.sample_rate)
                    speech_probability = 0.9 if speech_detected else 0.1
                except:
                    # Fallback vers détection d'énergie
                    speech_detected = energy_level > self.energy_threshold
                    speech_probability = min(1.0, max(0.0, energy_level / max(self.energy_threshold, 1.0)))
            else:
                # Détection basée sur l'énergie et ZCR
                speech_detected = (energy_level > self.energy_threshold and 
                                   zero_crossing_rate > 0.01 and 
                                   spectral_centroid > 500)
                speech_probability = min(1.0, max(0.0, energy_level / max(self.energy_threshold, 1.0)))
            
            return VoiceActivityMetrics(
                speech_detected=speech_detected,
                energy_level=energy_level,
                zero_crossing_rate=zero_crossing_rate,
                spectral_centroid=spectral_centroid,
                background_noise_level=self.noise_threshold,
                speech_probability=speech_probability
            )
            
        except Exception as e:
            self.logger.error(f"Erreur dans la détection VAD: {e}")
            return VoiceActivityMetrics()
    
    def _process_complete_speech(self, speech_frames: List[bytes]):
        """Traite une séquence complète de parole détectée."""
        try:
            if not speech_frames:
                return
            
            # Combiner tous les frames
            complete_audio = b''.join(speech_frames)
            
            # Reconnaissance vocale
            start_time = time.time()
            recognition_result = self._recognize_speech_whisper(complete_audio)
            processing_time = time.time() - start_time
            
            if recognition_result and recognition_result.text.strip():
                recognition_result.processing_time = processing_time
                
                # Enregistrer les métriques
                self._update_performance_metrics(recognition_result)
                
                # Afficher les indicateurs visuels pour le résultat de reconnaissance
                if self.show_visual_indicators:
                    self._update_visual_status(f"💬 ({processing_time:.1f}s) [{recognition_result.text}]")
                
                self.logger.info(f"🗣️ Parole reconnue ({processing_time:.2f}s): {recognition_result.text}")
                
                # Détecter si c'est une commande reconnue et afficher l'indicateur approprié
                detected_command = self._detect_command_intent(recognition_result.text)
                if detected_command and self.show_visual_indicators:
                    self._update_visual_status(f"🎯 [{detected_command}]")
                
                # Ajouter à la queue de commandes
                self.command_queue.put(recognition_result.text)
                
                # Indicateur visuel de traitement de la commande
                if self.show_visual_indicators:
                    self._update_visual_status("⚙️ Traitement en cours...")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors du traitement de la parole: {e}")
    
    def _handle_potential_interruption(self, audio_data: bytes):
        """Gère les interruptions vocales potentielles pendant que Peer parle."""
        try:
            # Reconnaissance rapide pour détecter les commandes d'interruption
            audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Utiliser Whisper en mode rapide pour une détection d'interruption
            result = self.whisper_model.transcribe(
                audio_np,
                language="fr",
                temperature=0.0,
                best_of=1,
                beam_size=1,
                # patience=0.5,  # Ne pas utiliser patience avec beam_size=1
                suppress_tokens=[-1],
                fp16=False  # Éviter l'avertissement FP16 sur CPU
            )
            
            text = result["text"].strip().lower()
            
            if not text:
                return
            
            # Commandes d'interruption reconnues
            interruption_commands = [
                "stop", "arrête", "arrête", "tais-toi", "silence", "chut",
                "attends", "attend", "pause", "moins fort", "plus doucement",
                "parle moins fort", "baisse le volume", "ferme-la",
                "ça suffit", "stop ça", "interromps", "interrompt"
            ]
            
            # Vérifier si c'est une commande d'interruption
            is_interruption = any(cmd in text for cmd in interruption_commands)
            
            if is_interruption:
                self.logger.info(f"🛑 Interruption détectée: {text}")
                self.interruption_count += 1
                
                # Arrêter immédiatement la synthèse vocale
                if hasattr(self.tts_adapter, 'stop_speaking'):
                    self.tts_adapter.stop_speaking()
                
                self.speaking = False
                
                # Répondre à l'interruption
                if "moins fort" in text or "baisse" in text or "doucement" in text:
                    self.vocalize("D'accord, je baisse le volume.")
                elif "pause" in text or "attends" in text:
                    self.paused = True
                    self.vocalize("Mise en pause. Dites 'continue' pour reprendre.")
                elif "silence" in text or "tais-toi" in text or "chut" in text:
                    self.paused = True
                    # Ne pas répondre vocalement dans ce cas
                else:
                    self.vocalize("D'accord, j'arrête.")
                
                # Marquer comme traité
                return True
            
            # Si ce n'est pas une interruption, mais que le volume est élevé, 
            # cela pourrait être l'utilisateur qui essaie de parler par-dessus
            vad_result = self._detect_voice_activity(audio_data)
            if vad_result.speech_probability > 0.8 and vad_result.energy_level > self.energy_threshold * 1.5:
                self.logger.debug("🔊 Détection d'une tentative de prise de parole")
                # Réduire légèrement le volume de Peer pour permettre à l'utilisateur de parler
                if hasattr(self.tts_adapter, 'reduce_volume'):
                    self.tts_adapter.reduce_volume()
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors du traitement de l'interruption: {e}")
            return False
    
    def _recognize_speech_whisper(self, audio_data: bytes) -> Optional[SpeechRecognitionResult]:
        """Reconnaissance vocale avec Whisper optimisé."""
        try:
            # Convertir en numpy array
            audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Whisper transcription avec options optimisées
            result = self.whisper_model.transcribe(
                audio_np,
                language="fr",  # Forcer le français pour de meilleures performances
                task="transcribe",
                temperature=0.0,  # Déterministe
                best_of=1,  # Plus rapide
                beam_size=1,  # Plus rapide
                # patience=1.0,  # Ne pas utiliser patience avec beam_size=1
                suppress_tokens=[-1],  # Supprimer les tokens spéciaux
                fp16=False  # Éviter l'avertissement FP16 sur CPU
            )
            
            text = result["text"].strip()
            if text:
                # Estimer la confiance basée sur la durée et la clarté
                confidence = self._estimate_confidence(audio_np, text)
                
                return SpeechRecognitionResult(
                    text=text,
                    confidence=confidence,
                    language="fr",
                    audio_quality=self._assess_audio_quality(audio_np)
                )
            
        except Exception as e:
            self.logger.error(f"❌ Erreur Whisper: {e}")
        
        return None
    
    def _estimate_confidence(self, audio_np: np.ndarray, text: str) -> float:
        """Estime la confiance de la reconnaissance."""
        try:
            # Facteurs de confiance
            audio_quality = self._assess_audio_quality(audio_np)
            text_length_factor = min(1.0, len(text) / 20)  # Textes plus longs = plus fiables
            
            # Mots de confiance (mots courants bien reconnus)
            confidence_words = ["aide", "bonjour", "merci", "oui", "non", "comment", "quoi", "où", "quand"]
            word_confidence = sum(1 for word in confidence_words if word in text.lower()) / max(1, len(text.split()))
            
            # Combinaison des facteurs
            confidence = (audio_quality * 0.4 + text_length_factor * 0.3 + word_confidence * 0.3)
            
            return min(1.0, max(0.1, confidence))
            
        except:
            return 0.7  # Confiance par défaut
    
    def _assess_audio_quality(self, audio_np: np.ndarray) -> float:
        """Évalue la qualité de l'audio."""
        try:
            # Signal-to-noise ratio approximatif
            signal_power = np.mean(audio_np**2)
            if signal_power == 0:
                return 0.1
            
            # Ratio signal/bruit basé sur la variance
            snr = 10 * np.log10(signal_power / max(1e-10, np.var(audio_np)))
            
            # Normaliser entre 0 et 1
            quality = min(1.0, max(0.1, (snr + 10) / 50))
            
            return quality
            
        except:
            return 0.7  # Qualité par défaut
    
    def _intelligent_command_loop(self):
        """Boucle de traitement intelligent des commandes vocales reconnues."""
        self.logger.info("🧠 Boucle de traitement des commandes démarrée...")
        while self.running:
            try:
                try:
                    speech_text = self.command_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                if not speech_text or not speech_text.strip():
                    continue
                self._process_speech_command(speech_text)
                self.command_queue.task_done()
            except Exception as e:
                self.logger.error(f"Erreur dans la boucle de commandes: {e}")

    def _process_speech_command(self, speech_text: str):
        """Traite une commande vocale reconnue et transmet au daemon IA avec protection anti-récursion."""
        self.logger.info(f"Traitement de la commande vocale: {speech_text}")
        start_time = time.time()
        
        # Protection anti-récursion au niveau des commandes
        if hasattr(self, '_command_recursion_depth'):
            self._command_recursion_depth += 1
            if self._command_recursion_depth > 3:
                self.logger.warning("🚫 Prévention de récursion de commande - abandon du traitement")
                self._command_recursion_depth -= 1
                return
        else:
            self._command_recursion_depth = 1
        
        try:
            # Vérifier les commandes de contrôle de l'interface d'abord
            speech_lower = speech_text.lower().strip()
            
            # Gestion de la reprise après pause
            if self.paused and any(cmd in speech_lower for cmd in ["continue", "reprendre", "reprise", "va-y", "allez-y"]):
                self.paused = False
                self._safe_vocalize("Je reprends.")
                return
            
            # Gestion des commandes de pause
            if any(cmd in speech_lower for cmd in ["pause", "attends", "attend"]):
                self.paused = True
                self._safe_vocalize("Mise en pause. Dites 'continue' pour reprendre.")
                return
            
            # Si en pause, ignorer les autres commandes sauf celles de reprise
            if self.paused:
                self.logger.debug("Interface en pause, commande ignorée")
                return
            
            # Vérifier si on n'est pas déjà en train de traiter une commande critique
            if hasattr(self, '_processing_critical_command') and self._processing_critical_command:
                self.logger.debug("🔄 Commande critique en cours, nouvelle commande mise en attente")
                # Mettre la commande dans une queue de priorité basse
                threading.Timer(2.0, lambda: self.command_queue.put(speech_text)).start()
                return
            
            # Marquer le début du traitement critique
            self._processing_critical_command = True
            
            # Traduire la commande vocale en requête standardisée enrichie
            request = self.adapter.translate_to_core(speech_text)
            request.session_id = self.session_id

            # Exécuter via le daemon (agent IA)
            response = self.daemon.execute_command(request)

            # Traduire la réponse pour l'interface vocale
            adapted_response = self.adapter.translate_from_core(response)

            # Vocaliser la réponse avec protection anti-récursion
            if adapted_response.get("should_vocalize", True):
                vocal_message = adapted_response.get("vocal_message", "Commande exécutée.")
                self._safe_vocalize(vocal_message)

            # Suggestions proactives avec limitation
            suggestions = adapted_response.get("proactive_suggestions", [])
            if suggestions and len(suggestions) <= 2:  # Limiter le nombre de suggestions
                for suggestion in suggestions:
                    self._safe_vocalize(suggestion)

            # Mise à jour des métriques
            elapsed = time.time() - start_time
            self.avg_response_time = (self.avg_response_time * self.total_commands + elapsed) / (self.total_commands + 1)
            self.total_commands += 1

        except Exception as e:
            self.logger.error(f"Erreur lors du traitement de la commande vocale: {e}")
            # Gestion d'erreur avec protection anti-récursion triple
            self._handle_command_error(e)
            
        finally:
            # Nettoyer les flags de protection
            if hasattr(self, '_processing_critical_command'):
                self._processing_critical_command = False
            if hasattr(self, '_command_recursion_depth'):
                self._command_recursion_depth -= 1

    def vocalize(self, text: str):
        """Synthétise et joue un texte avec gestion intelligente des interruptions et prévention des boucles."""
        if not text or not text.strip():
            return
        
        # Vérifier si on n'est pas déjà dans une boucle TTS récursive
        if hasattr(self, '_tts_recursion_depth'):
            self._tts_recursion_depth += 1
            if self._tts_recursion_depth > 2:
                self.logger.warning("🚫 Prévention de récursion TTS - abandon de la vocalisation")
                self._tts_recursion_depth -= 1
                return
        else:
            self._tts_recursion_depth = 1
        
        with self.tts_lock:
            # Marquer le début de la vocalisation AVANT d'émettre le son
            self.speaking = True
            start_time = time.time()
            
            # Isolation préventive : bloquer l'écoute immédiatement
            self._set_tts_blocking_period(start_time, text)
            
            try:
                # Indicateur visuel de début de vocalisation
                if self.show_visual_indicators:
                    self._update_visual_status(f"🔊 {text[:50]}{'...' if len(text) > 50 else ''}")
                
                self.logger.info(f"Vocalisation: {text}")
                
                # Vocaliser avec timeout pour éviter les blocages
                self._safe_tts_speak(text)
                
            except Exception as e:
                self.logger.error(f"Erreur lors de la vocalisation: {e}")
                # Fallback visuel SILENCIEUX en cas d'erreur TTS pour éviter récursion
                if self.show_visual_indicators:
                    self._update_visual_status("❌ Erreur de synthèse vocale (silencieux)")
                else:
                    print(f"[TTS Error - Silent] {text}")
                    
            finally:
                # Marquer la fin de vocalisation avec délai de sécurité étendu
                self.speaking = False
                self.speech_end_time = time.time() + 0.5  # Buffer de 500ms supplémentaire
                duration = self.speech_end_time - start_time
                self.logger.debug(f"🔇 Fin de vocalisation marquée à {self.speech_end_time} (durée: {duration:.2f}s)")
                
                # Réduire la profondeur de récursion
                if hasattr(self, '_tts_recursion_depth'):
                    self._tts_recursion_depth -= 1
                
                # Indicateur visuel de retour à l'écoute avec délai
                if self.show_visual_indicators and not self.paused:
                    # Petit délai pour s'assurer que l'audio est complètement fini
                    threading.Timer(0.8, lambda: self._update_visual_status("🎙️ J'écoute")).start()
    
    def _set_tts_blocking_period(self, start_time: float, text: str):
        """Définit une période de blocage étendue pour éviter l'auto-écoute."""
        # Estimer la durée de vocalisation basée sur la longueur du texte
        estimated_duration = max(2.0, len(text) * 0.1)  # ~100ms par caractère, minimum 2s
        
        # Ajouter un buffer de sécurité pour l'écho système
        safety_buffer = 1.5
        
        # Marquer le temps de fin estimé avec buffer
        self.speech_end_time = start_time + estimated_duration + safety_buffer
        self.logger.debug(f"🛡️ Période de blocage TTS: {estimated_duration + safety_buffer:.2f}s")
    
    def _safe_tts_speak(self, text: str):
        """Vocalisation sécurisée avec timeout et gestion d'erreurs robuste."""
        import threading
        import time
        
        tts_completed = threading.Event()
        tts_error = [None]  # Liste pour permettre la modification dans le thread
        
        def tts_thread():
            try:
                self.tts_adapter.speak(text)
                tts_completed.set()
            except Exception as e:
                tts_error[0] = e
                tts_completed.set()
        
        # Lancer la vocalisation dans un thread séparé avec timeout
        thread = threading.Thread(target=tts_thread, daemon=True)
        thread.start()
        
        # Attendre avec timeout de 30 secondes maximum
        if not tts_completed.wait(timeout=30.0):
            self.logger.error("⏰ Timeout TTS - vocalisation abandonnée")
            return
        
        # Vérifier s'il y a eu une erreur
        if tts_error[0]:
            raise tts_error[0]

    def _update_performance_metrics(self, recognition_result: SpeechRecognitionResult):
        """Met à jour les métriques de performance et d'apprentissage."""
        self.performance_metrics["response_time"] = recognition_result.processing_time
        self.performance_metrics["recognition_confidence"] = recognition_result.confidence
        self.performance_metrics["audio_quality"] = recognition_result.audio_quality
        self.command_history.append(recognition_result.text)

    def _analyze_current_context(self) -> ContextualInfo:
        """Analyse le contexte courant pour l'assistance intelligente."""
        return ContextualInfo(
            current_time=datetime.datetime.now(),
            session_duration=time.time() - self.session_start_time,
            commands_count=len(self.command_history),
            last_commands=list(self.command_history)[-5:],
            user_response_pattern={},  # À enrichir selon l'apprentissage
            system_performance={
                "cpu": psutil.cpu_percent(),
                "memory": psutil.virtual_memory().percent,
                "disk": psutil.disk_usage("/").percent
            },
            recent_errors=[],
            working_directory=os.getcwd(),
            active_files=[]
        )

    def _provide_proactive_assistance(self, context: ContextualInfo):
        """Fournit une assistance proactive basée sur le contexte."""
        # Exemple : proposer un tutoriel si beaucoup d'erreurs ou d'hésitations
        if context.commands_count > 3 and any("aide" in cmd.lower() for cmd in context.last_commands):
            self.vocalize("Je remarque que vous demandez souvent de l'aide. Voulez-vous un tutoriel interactif ou une explication détaillée ?")

    def _adapt_to_user_patterns(self):
        """Adapte le comportement selon les patterns utilisateur."""
        # À enrichir : analyse des habitudes pour personnaliser l'expérience
        pass

    def _generate_personalized_greeting(self) -> str:
        """Génère un message d'accueil personnalisé selon le contexte."""
        hour = datetime.datetime.now().hour
        if hour < 12:
            return "Bonjour, prêt à coder ! Comment puis-je vous aider ?"
        elif hour < 18:
            return "Bon après-midi, que souhaitez-vous accomplir aujourd'hui ?"
        else:
            return "Bonsoir, besoin d'aide pour avancer sur votre projet ?"

    def _generate_personalized_farewell(self) -> str:
        """Génère un message de fin personnalisé."""
        return "Interface vocale Peer arrêtée. À bientôt et bon codage !"

    def _monitor_system_health(self):
        """Surveille la santé du système et ajuste le comportement si besoin."""
        # Exemple : si CPU > 90%, prévenir l'utilisateur
        cpu = psutil.cpu_percent()
        if cpu > 90:
            self.vocalize("Attention, l'utilisation du processeur est très élevée.")

    def _save_user_preferences(self):
        """Sauvegarde les préférences utilisateur via l'adaptateur."""
        self.adapter._save_user_preferences()

    def _load_user_preferences(self):
        """Charge les préférences utilisateur via l'adaptateur."""
        self.adapter._load_user_preferences()


def main():
    """
    Point d'entrée principal pour lancer l'interface vocale omnisciente SUI.
    
    Cette fonction initialise et démarre l'interface vocale avec toutes ses capacités
    d'intelligence artificielle avancées:
    - Détection d'activité vocale (VAD)
    - Reconnaissance Whisper optimisée
    - Analyse contextuelle et assistance proactive
    - Apprentissage adaptatif
    - Intégration complète avec le daemon IA
    """
    print("=" * 60)
    print("🎤 Interface Vocale Omnisciente SUI - Peer AI Assistant")
    print("=" * 60)
    print("Initialisation de l'interface vocale avancée...")
    
    # Configuration du logging pour l'exécution standalone
    logger = logging.getLogger("SUI-Main")
    
    try:
        # Création du répertoire de configuration si nécessaire
        config_dir = Path.home() / ".peer"
        config_dir.mkdir(exist_ok=True)
        
        logger.info("Démarrage de l'interface vocale omnisciente SUI")
        
        # Initialisation de l'interface SUI
        sui = OmniscientSUI()
        
        print("✅ Interface vocale initialisée avec succès !")
        print("\n📋 Fonctionnalités disponibles:")
        print("  • Reconnaissance vocale en continu avec Whisper")
        print("  • Détection d'activité vocale avancée (WebRTC VAD)")
        print("  • Commandes SUI directes (volume, vitesse, pause)")
        print("  • Transmission intelligente des requêtes au daemon IA")
        print("  • Analyse contextuelle et assistance proactive")
        print("  • Apprentissage adaptatif des préférences utilisateur")
        print("  • Synthèse vocale avec gestion des interruptions")
        
        print("\n🎯 Commandes SUI directes disponibles:")
        print("  • 'volume haut/bas' - Ajuster le volume")
        print("  • 'vitesse normale/lente/rapide' - Ajuster la vitesse de parole")
        print("  • 'répète' - Répéter la dernière réponse")
        print("  • 'pause/arrêt' - Mettre en pause ou arrêter")
        print("  • 'aide' - Obtenir de l'aide")
        
        print("\n🤖 Toutes les autres requêtes seront transmises au daemon IA pour:")
        print("  • Génération et modification de code")
        print("  • Analyse de projets et debugging")
        print("  • Assistance technique avancée")
        print("  • Gestion de fichiers et configurations")
        
        print("\n🎤 Dites 'Peer' ou commencez à parler...")
        print("   Appuyez sur Ctrl+C pour arrêter l'interface")
        print("=" * 60)
        
        # Démarrage de l'interface vocale
        sui.start()
        
        # Boucle principale - maintient l'interface active
        try:
            while sui.listening:
                time.sleep(0.5)
                # Vérification périodique de la santé du système
                sui._monitor_system_health()
        except KeyboardInterrupt:
            print("\n\n🛑 Arrêt demandé par l'utilisateur...")
            logger.info("Arrêt de l'interface vocale sur demande utilisateur")
        
    except Exception as e:
        logger.error(f"Erreur critique lors du démarrage de SUI: {e}")
        print(f"\n❌ Erreur critique: {e}")
        print("\n🔧 Suggestions de dépannage:")
        print("  1. Vérifiez que votre microphone est connecté et fonctionnel")
        print("  2. Assurez-vous que les dépendances audio sont installées:")
        print("     pip install pyaudio numpy pyttsx3 openai-whisper webrtcvad")
        print("  3. Vérifiez les permissions d'accès au microphone")
        print("  4. Consultez les logs détaillés dans ~/.peer/sui.log")
        return 1
    
    finally:
        # Nettoyage et fermeture propre
        try:
            if 'sui' in locals():
                print("🔄 Arrêt de l'interface vocale...")
                sui.stop()
                print("✅ Interface vocale arrêtée proprement")
            logger.info("Interface vocale SUI fermée")
        except Exception as e:
            logger.error(f"Erreur lors de la fermeture: {e}")
            print(f"⚠️  Erreur lors de la fermeture: {e}")
    
    print("👋 Au revoir et bon codage !")
    return 0


if __name__ == "__main__":
    """
    Lancement direct du script SUI.
    
    Usage:
        python -m peer.interfaces.sui.sui
        ou
        python /path/to/sui.py
    """
    exit_code = main()
    sys.exit(exit_code)
