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
import numpy as np
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Union
from dataclasses import dataclass, asdict
from collections import deque, defaultdict

# Fix OMP warning: "Forking a process while a parallel region is active is potentially unsafe."
os.environ["OMP_NUM_THREADS"] = "1"

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
    # Dépendances pour l'IA intelligente avec BERT
    from transformers import AutoTokenizer, AutoModel, pipeline
    import torch
    import torch.nn.functional as F
except ImportError as e:
    print(f"Erreur lors du chargement des dépendances: {e}")
    print("Veuillez installer les dépendances requises:")
    print("  pip install pyaudio numpy pyttsx3 openai-whisper webrtcvad transformers torch")
    sys.exit(1)

# Importation des modules Peer refactorisés
from peer.core import PeerDaemon, CoreRequest, CoreResponse, CommandType, ResponseType, InterfaceType
from peer.core.protocol import InterfaceAdapter
from peer.infrastructure.adapters.simple_tts_adapter import SimpleTTSAdapter

# Import du nouveau moteur NLP hybride
try:
    from .nlp_engine import HybridNLPEngine
    NLP_ENGINE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Moteur NLP hybride non disponible: {e}")
    NLP_ENGINE_AVAILABLE = False


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
    d'analyse contextuelle et assistance proactive utilisant BERT.
    
    Architecture IA : Premier niveau d'agent intelligent qui analyse
    les commandes vocales avec BERT et transmet les instructions
    non-reconnues à l'agent IA central.
    """
    
    def __init__(self):
        super().__init__(InterfaceType.SUI)
        self.logger = logging.getLogger("IntelligentSUISpeechAdapter")
        
        # Initialisation du nouveau moteur NLP hybride
        self._init_hybrid_nlp_engine()
        
        # Architecture IA avec BERT (fallback si moteur hybride indisponible)
        if not hasattr(self, 'nlp_engine') or not self.nlp_engine:
            self._init_bert_intelligence()
        
        # Mapping étendu des commandes vocales pour rétrocompatibilité
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
            
            # Commandes d'arrêt et de politesse
            "arrête": CommandType.QUIT,
            "arrête": CommandType.QUIT,
            "stop": CommandType.QUIT,
            "quitter": CommandType.QUIT,
            "quit": CommandType.QUIT,
            "au revoir": CommandType.QUIT,
            "merci": CommandType.QUIT,
            "c'est bon": CommandType.QUIT,
            "ça suffit": CommandType.QUIT,
            "tu peux t'arrêter": CommandType.QUIT,
            "arrête-toi": CommandType.QUIT,
            "merci pour ton aide": CommandType.QUIT,
            "merci beaucoup": CommandType.QUIT,
            "c'est parfait": CommandType.QUIT,
            "fini": CommandType.QUIT,
            "terminé": CommandType.QUIT,
            "bye": CommandType.QUIT,
            "goodbye": CommandType.QUIT,
            "see you": CommandType.QUIT,
            "à bientôt": CommandType.QUIT,
            "bonne journée": CommandType.QUIT,
            "bonne soirée": CommandType.QUIT,
            
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
    
    def _init_hybrid_nlp_engine(self):
        """Initialise le moteur NLP hybride robuste."""
        try:
            if NLP_ENGINE_AVAILABLE:
                self.logger.info("🧠 Initialisation du moteur NLP hybride...")
                self.nlp_engine = HybridNLPEngine()
                self.hybrid_nlp_enabled = True
                
                # Compatibilité avec l'ancien système BERT
                stats = self.nlp_engine.get_performance_stats()
                models = stats.get("models_available", {})
                self.bert_enabled = models.get("bert", False)
                
                self.logger.info("✅ Moteur NLP hybride initialisé avec succès")
                
                # Afficher les modèles disponibles
                available_models = [name for name, available in models.items() if available]
                self.logger.info(f"📊 Modèles NLP disponibles: {', '.join(available_models) if available_models else 'Aucun'}")
                
            else:
                self.logger.warning("⚠️ Moteur NLP hybride non disponible")
                self.nlp_engine = None
                self.hybrid_nlp_enabled = False
                self.bert_enabled = False
                
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de l'initialisation du moteur NLP hybride: {e}")
            self.nlp_engine = None
            self.hybrid_nlp_enabled = False
            self.bert_enabled = False
    
    def _init_bert_intelligence(self):
        """Initialise l'intelligence BERT pour l'interprétation des commandes vocales."""
        try:
            self.logger.info("🧠 Initialisation de l'agent IA BERT pour SUI...")
            
            # Liste des modèles par ordre de préférence
            models_to_try = [
                "bert-base-multilingual-cased",  # Modèle multilingue incluant le français
                "distilbert-base-multilingual-cased",  # Version plus légère
                "bert-base-uncased"  # Fallback anglais
            ]
            
            model_loaded = False
            for model_name in models_to_try:
                try:
                    self.logger.info(f"📥 Tentative de chargement: {model_name}")
                    
                    # Tokenizer et modèle BERT avec configuration compatible
                    self.bert_tokenizer = AutoTokenizer.from_pretrained(model_name)
                    
                    # Configuration du modèle pour éviter les problèmes de compatibilité
                    try:
                        # Essayer sans spécifier de device
                        self.bert_model = AutoModel.from_pretrained(
                            model_name,
                            output_hidden_states=True,
                            output_attentions=False
                        )
                        # Mettre en mode évaluation
                        self.bert_model.eval()
                    except Exception as model_error:
                        self.logger.warning(f"⚠️ Erreur modèle {model_name}: {model_error}")
                        # Essayer une configuration plus simple
                        self.bert_model = AutoModel.from_pretrained(model_name)
                        self.bert_model.eval()
                    
                    model_loaded = True
                    self.logger.info(f"✅ Modèle chargé avec succès: {model_name}")
                    break
                except Exception as e:
                    self.logger.warning(f"⚠️ Échec chargement {model_name}: {e}")
                    continue
            
            if not model_loaded:
                raise Exception("Aucun modèle BERT disponible")
            
            
            # Pipeline de classification d'intention optimisé
            try:
                self.intent_classifier = pipeline(
                    "text-classification",
                    model=self.bert_tokenizer.name_or_path,
                    tokenizer=self.bert_tokenizer,
                    return_all_scores=True
                )
                self.logger.info("🎯 Pipeline de classification initialisé")
            except Exception as e:
                self.logger.warning(f"⚠️ Pipeline de classification non disponible, utilisation de l'analyse directe: {e}")
                self.intent_classifier = None
            
            # Configuration IA intelligente
            self.bert_config = {
                "max_length": 512,
                "confidence_threshold": 0.7,
                "intent_mapping": self._build_intent_mapping(),
                "context_window": 3,  # Historique des 3 dernières commandes pour le contexte
                "semantic_similarity_threshold": 0.8
            }
            
            # Cache pour les embeddings fréquents
            self.embedding_cache = {}
            self.frequent_patterns = {}
            
            # Intelligence adaptative
            self.adaptive_learning = True
            self.command_success_rate = defaultdict(float)
            self.user_interaction_patterns = defaultdict(list)
            
            self.logger.info("✅ Agent IA BERT initialisé avec succès")
            self.bert_enabled = True
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de l'initialisation BERT: {e}")
            self.logger.warning("🔄 Basculement vers l'analyse traditionnelle par mots-clés")
            self.bert_enabled = False
            self.bert_tokenizer = None
            self.bert_model = None
            self.intent_classifier = None
    
    def _build_intent_mapping(self) -> Dict[str, CommandType]:
        """Construit le mapping des intentions BERT vers les CommandType."""
        return {
            # Intentions d'aide et information
            "help_request": CommandType.HELP,
            "information_query": CommandType.HELP,
            "capability_inquiry": CommandType.CAPABILITIES,
            "tutorial_request": CommandType.HELP,
            
            # Intentions de statut et surveillance
            "status_check": CommandType.STATUS,
            "health_inquiry": CommandType.STATUS,
            "performance_check": CommandType.STATUS,
            "monitoring_request": CommandType.STATUS,
            
            # Intentions d'analyse et traitement
            "analysis_request": CommandType.ANALYZE,
            "examination_request": CommandType.ANALYZE,
            "inspection_request": CommandType.ANALYZE,
            "evaluation_request": CommandType.ANALYZE,
            
            # Intentions d'amélioration et suggestions
            "optimization_request": CommandType.SUGGEST,
            "improvement_request": CommandType.SUGGEST,
            "enhancement_request": CommandType.SUGGEST,
            "recommendation_request": CommandType.SUGGEST,
            
            # Intentions d'explication
            "explanation_request": CommandType.EXPLAIN,
            "clarification_request": CommandType.EXPLAIN,
            "description_request": CommandType.EXPLAIN,
            
            # Intentions temporelles
            "time_inquiry": CommandType.TIME,
            "date_inquiry": CommandType.DATE,
            "temporal_request": CommandType.TIME,
            
            # Intentions d'écho et répétition
            "repetition_request": CommandType.ECHO,
            "echo_request": CommandType.ECHO,
            
            # Intentions d'arrêt (gardées pour compatibilité)
            "termination_request": CommandType.QUIT,
            "farewell_intent": CommandType.QUIT,
            "stop_request": CommandType.QUIT,
            
            # Intention par défaut pour les requêtes complexes
            "general_query": CommandType.PROMPT,
            "complex_request": CommandType.PROMPT,
            "unstructured_input": CommandType.PROMPT
        }
    
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
        
        # Gestion spéciale pour les nouvelles réponses de quit avec confirmation
        response_data = {
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
        
        # Gestion des nouvelles réponses avec confirmation intelligente
        if hasattr(core_response, 'data') and core_response.data:
            response_params = core_response.data
            
            # DIRECT_QUIT avec confirmation nécessaire
            if response_params.get("confirmation_needed") and response_params.get("confirmation_message"):
                response_data.update({
                    "requires_confirmation": True,
                    "confirmation_message": response_params.get("confirmation_message"),
                    "confirmation_type": "precision_request",
                    "original_command_type": "DIRECT_QUIT" if "direct_quit" in response_params.get("reason", "") else "SOFT_QUIT",
                    "reason": response_params.get("reason", ""),
                    "vocal_message": response_params.get("confirmation_message")
                })
                
            # SOFT_QUIT avec demande de précision
            elif response_params.get("precision_needed"):
                response_data.update({
                    "requires_confirmation": True,
                    "confirmation_message": response_params.get("confirmation_message", "Souhaitez-vous que je m'arrête ?"),
                    "confirmation_type": "soft_quit_clarification",
                    "original_command_type": "SOFT_QUIT",
                    "reason": response_params.get("reason", ""),
                    "vocal_message": response_params.get("confirmation_message", "Souhaitez-vous que je m'arrête ?")
                })
                
            # Séquences de commandes avec SOFT_QUIT
            elif response_params.get("is_command_sequence"):
                command_sequence = response_params.get("command_sequence", [])
                sequence_description = response_params.get("sequence_description", "")
                
                response_data.update({
                    "is_command_sequence": True,
                    "command_sequence": command_sequence,
                    "sequence_description": sequence_description,
                    "vocal_message": sequence_description,
                    "requires_confirmation": response_params.get("confirmation_needed", False)
                })
                
                if response_params.get("confirmation_needed"):
                    response_data.update({
                        "confirmation_message": response_params.get("confirmation_message", "Comment souhaitez-vous procéder ?"),
                        "confirmation_type": "command_sequence_clarification"
                    })
            
            # DIRECT_QUIT immédiat (fin de phrase)
            elif response_params.get("immediate_quit"):
                response_data.update({
                    "immediate_quit": True,
                    "should_vocalize": True,
                    "vocal_message": "Au revoir !"
                })
        
        return response_data
    
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
        """
        Analyse intelligente des commandes avec moteur NLP hybride - Agent IA de premier niveau.
        
        Architecture : SUI comme agent IA intelligent qui extrait les commandes
        et opérations, puis transmet les instructions non-reconnues à l'agent central.
        
        Priorités d'analyse:
        1. Détection d'arrêt poli (priorité absolue)
        2. Moteur NLP hybride (efficace et robuste)
        3. BERT legacy (si hybride indisponible)
        4. Correspondance directe (rétrocompatibilité)
        5. Analyse contextuelle et sémantique
        6. Transmission à l'agent IA central
        """
        
        # PRIORITÉ 1: Détection des intentions d'arrêt polies (toujours en priorité absolue)
        if self._detect_polite_quit_intent(normalized_input):
            self.logger.info(f"🛑 Intention d'arrêt polie détectée: '{normalized_input}'")
            return CommandType.QUIT, {"intent": "polite_quit", "full_text": normalized_input}
        
        # PRIORITÉ 2: Moteur NLP hybride (nouveau système efficace)
        if self.hybrid_nlp_enabled and self.nlp_engine:
            try:
                nlp_result = self.nlp_engine.extract_intent(normalized_input, context)
                if nlp_result and nlp_result.confidence >= 0.7:
                    parameters = {
                        "full_text": normalized_input,
                        "nlp_confidence": nlp_result.confidence,
                        "nlp_method": nlp_result.method_used,
                        "processing_time": nlp_result.processing_time,
                        "fallback_used": nlp_result.fallback_used,
                        **nlp_result.parameters
                    }
                    self.logger.info(f"🧠 NLP Hybride: {nlp_result.command_type.value} (confiance: {nlp_result.confidence:.2f}, méthode: {nlp_result.method_used})")
                    return nlp_result.command_type, parameters
                else:
                    self.logger.debug(f"🔍 NLP hybride: confiance insuffisante ({nlp_result.confidence:.2f})")
            except Exception as e:
                self.logger.warning(f"⚠️ Erreur moteur NLP hybride: {e}")
        
        # PRIORITÉ 3: Intelligence artificielle BERT legacy (si hybride indisponible)
        if self.bert_enabled:
            bert_result = self._analyze_with_bert_intelligence(normalized_input, context)
            if bert_result:
                command_type, parameters = bert_result
                self.logger.info(f"🧠 BERT legacy: {command_type.value} (confiance: {parameters.get('bert_confidence', 0):.2f})")
                return command_type, parameters
        
        # PRIORITÉ 4: Rétrocompatibilité - Recherche de correspondance directe
        # Amélioration: Correspondance plus stricte pour éviter les faux positifs
        for trigger, command in self.voice_commands.items():
            # Correspondance exacte ou au début pour éviter les conflits
            if (normalized_input == trigger or 
                normalized_input.startswith(trigger + " ") or
                (len(trigger) > 3 and trigger in normalized_input and 
                 len(normalized_input.split()) <= 3)):  # Commandes courtes seulement
                
                parameters = self._extract_parameters(normalized_input, trigger, context)
                parameters["fallback_method"] = "direct_mapping"
                self.command_patterns[command.value] += 1
                self.logger.debug(f"🔄 Correspondance directe trouvée: {trigger} -> {command.value}")
                return command, parameters
        
        # PRIORITÉ 5: Analyse contextuelle avancée (fallback)
        if self.user_preferences.get("context_awareness", True):
            contextual_command = self._analyze_contextual_intent(normalized_input, context)
            if contextual_command:
                command_type, parameters = contextual_command
                parameters["fallback_method"] = "contextual_analysis"
                self.logger.debug(f"🎯 Analyse contextuelle: {command_type.value}")
                return command_type, parameters
        
        # PRIORITÉ 6: Analyse par mots-clés sémantiques (fallback)
        semantic_command = self._analyze_semantic_intent(normalized_input)
        if semantic_command:
            command_type, parameters = semantic_command
            parameters["fallback_method"] = "semantic_keywords"
            self.logger.debug(f"🔍 Analyse sémantique: {command_type.value}")
            return command_type, parameters
        
        # PRIORITÉ 7: Transmission à l'agent IA central (commande par défaut)
        self.logger.info(f"🤖 Transmission à l'agent IA central: '{normalized_input}'")
        return CommandType.PROMPT, {
            "args": normalized_input.split(), 
            "full_text": normalized_input, 
            "unrecognized_input": normalized_input,
            "ai_agent_request": True,
            "processing_method": "central_ai_agent"
        }
    
    def _analyze_with_bert_intelligence(self, normalized_input: str, context: Dict[str, Any]) -> Optional[Tuple[CommandType, Dict[str, Any]]]:
        """
        Analyse intelligente avec BERT pour comprendre l'intention utilisateur.
        
        Retourne None si BERT ne peut pas identifier une intention claire,
        permettant aux méthodes fallback de prendre le relais.
        """
        try:
            self.logger.debug(f"🧠 Analyse BERT de: '{normalized_input}'")
            
            # Préparer le contexte enrichi pour BERT
            enriched_input = self._prepare_bert_context(normalized_input, context)
            
            # Analyser l'intention avec BERT
            intent_result = self._bert_intent_classification(enriched_input)
            
            if not intent_result:
                self.logger.debug("🤷 BERT n'a pas identifié d'intention claire")
                return None
            
            intent, confidence = intent_result
            
            # Vérifier le seuil de confiance
            if confidence < self.bert_config["confidence_threshold"]:
                self.logger.debug(f"🔽 Confiance BERT trop faible: {confidence:.2f} < {self.bert_config['confidence_threshold']}")
                return None
            
            # Mapper l'intention vers CommandType
            command_type = self.bert_config["intent_mapping"].get(intent)
            if not command_type:
                self.logger.debug(f"❓ Intention BERT non mappée: {intent}")
                return None
            
            # Extraire les paramètres avec BERT
            parameters = self._bert_extract_parameters(normalized_input, intent, context)
            parameters.update({
                "bert_intent": intent,
                "bert_confidence": confidence,
                "processing_method": "bert_intelligence",
                "ai_processing": True
            })
            
            # Apprentissage adaptatif
            if self.adaptive_learning:
                self._update_bert_learning(normalized_input, intent, confidence)
            
            return command_type, parameters
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de l'analyse BERT: {e}")
            return None
    
    def _prepare_bert_context(self, normalized_input: str, context: Dict[str, Any]) -> str:
        """Prépare le contexte enrichi pour l'analyse BERT."""
        try:
            # Contexte de base
            enriched_parts = [normalized_input]
            
            # Ajouter l'historique récent si disponible
            if hasattr(self, 'command_history') and self.command_history:
                recent_commands = list(self.command_history)[-self.bert_config["context_window"]:]
                if recent_commands:
                    recent_texts = [cmd.get("text", "") for cmd in recent_commands if cmd.get("text")]
                    if recent_texts:
                        context_text = " | ".join(recent_texts[-2:])  # 2 dernières commandes
                        enriched_parts.insert(0, f"Contexte: {context_text}")
            
            # Ajouter des indices temporels si pertinents
            current_hour = datetime.datetime.now().hour
            if 6 <= current_hour < 12:
                time_context = "matinée"
            elif 12 <= current_hour < 18:
                time_context = "après-midi"
            else:
                time_context = "soirée"
            
            enriched_parts.append(f"Moment: {time_context}")
            
            # Combiner le contexte enrichi
            enriched_input = " ".join(enriched_parts)
            
            # Limiter la longueur pour BERT
            if len(enriched_input) > self.bert_config["max_length"]:
                enriched_input = enriched_input[:self.bert_config["max_length"]]
            
            return enriched_input
            
        except Exception as e:
            self.logger.warning(f"⚠️ Erreur lors de la préparation du contexte BERT: {e}")
            return normalized_input
    
    def _bert_intent_classification(self, enriched_input: str) -> Optional[Tuple[str, float]]:
        """Classification d'intention avec BERT."""
        try:
            # Utiliser les patterns d'entraînement pour classifier l'intention
            # Pour cette implémentation, nous utiliserons une analyse par similarité sémantique
            
            # Obtenir les embeddings BERT pour l'entrée
            input_embedding = self._get_bert_embedding(enriched_input)
            
            if input_embedding is None:
                return None
            
            # Comparer avec les patterns d'intention connus
            best_intent = None
            best_score = 0.0
            
            # Patterns d'intention basés sur des exemples d'entraînement
            intention_patterns = self._get_intention_training_patterns()
            
            for intent, patterns in intention_patterns.items():
                for pattern in patterns:
                    pattern_embedding = self._get_bert_embedding(pattern)
                    if pattern_embedding is not None:
                        # Calculer la similarité cosine
                        similarity = self._cosine_similarity(input_embedding, pattern_embedding)
                        if similarity > best_score:
                            best_score = similarity
                            best_intent = intent
            
            # Retourner le meilleur match si la similarité est suffisante
            if best_score >= self.bert_config["semantic_similarity_threshold"]:
                return best_intent, best_score
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de la classification BERT: {e}")
            return None
    
    def _get_bert_embedding(self, text: str) -> Optional[np.ndarray]:
        """Obtient l'embedding BERT pour un texte."""
        try:
            # Vérifier le cache d'abord
            if text in self.embedding_cache:
                return self.embedding_cache[text]
            
            # Vérifier que le modèle est disponible
            if not self.bert_model or not self.bert_tokenizer:
                return None
            
            # Tokeniser et obtenir l'embedding
            inputs = self.bert_tokenizer(
                text, 
                return_tensors="pt", 
                padding=True, 
                truncation=True, 
                max_length=512
            )
            
            with torch.no_grad():
                outputs = self.bert_model(**inputs)
                # Utiliser la moyenne des dernières couches cachées
                if hasattr(outputs, 'last_hidden_state'):
                    embedding = outputs.last_hidden_state.mean(dim=1).squeeze()
                else:
                    # Fallback pour d'autres types de sorties
                    embedding = outputs[0].mean(dim=1).squeeze()
                
                # Convertir en numpy
                if hasattr(embedding, 'numpy'):
                    embedding_np = embedding.numpy()
                else:
                    embedding_np = np.array(embedding)
            
            # Mettre en cache (limiter la taille du cache)
            if len(self.embedding_cache) < 1000:
                self.embedding_cache[text] = embedding_np
            
            return embedding_np
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de la génération d'embedding BERT: {e}")
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de la génération d'embedding BERT: {e}")
            return None
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calcule la similarité cosine entre deux vecteurs."""
        try:
            # Normaliser les vecteurs
            vec1_norm = vec1 / np.linalg.norm(vec1)
            vec2_norm = vec2 / np.linalg.norm(vec2)
            
            # Calculer le produit scalaire (similarité cosine)
            similarity = np.dot(vec1_norm, vec2_norm)
            return float(similarity)
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors du calcul de similarité: {e}")
            return 0.0
    
    def _get_intention_training_patterns(self) -> Dict[str, List[str]]:
        """Retourne les patterns d'entraînement pour chaque intention."""
        return {
            "help_request": [
                "aide-moi s'il te plaît",
                "j'ai besoin d'aide",
                "comment faire",
                "peux-tu m'aider",
                "je ne sais pas comment"
            ],
            "analysis_request": [
                "analyse ce code",
                "examine ce fichier",
                "vérifie cette fonction",
                "regarde ça",
                "peux-tu analyser"
            ],
            "optimization_request": [
                "optimise ce code",
                "améliore la performance",
                "rends ça plus efficace",
                "comment optimiser",
                "suggestions d'amélioration"
            ],
            "explanation_request": [
                "explique-moi comment ça marche",
                "que fait cette fonction",
                "comment ça fonctionne",
                "peux-tu expliquer",
                "décris-moi"
            ],
            "status_check": [
                "quel est le statut",
                "comment ça va",
                "état du système",
                "tout va bien",
                "vérification du statut"
            ],
            "termination_request": [
                "merci pour ton aide tu peux t'arrêter",
                "c'est bon merci",
                "tu peux arrêter maintenant",
                "merci beaucoup c'est parfait",
                "arrête-toi maintenant"
            ],
            "time_inquiry": [
                "quelle heure est-il",
                "donne-moi l'heure",
                "il est quelle heure",
                "l'heure actuelle",
                "temps maintenant"
            ],
            "general_query": [
                "dis-moi quelque chose",
                "raconte-moi",
                "information sur",
                "parle-moi de",
                "qu'est-ce que tu penses"
            ]
        }
    
    def _cosine_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calcule la similarité cosine entre deux embeddings."""
        try:
            # Normaliser les vecteurs
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            # Calculer la similarité cosine
            similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors du calcul de similarité: {e}")
            return 0.0
    
    def _get_intention_training_patterns(self) -> Dict[str, List[str]]:
        """Retourne les patterns d'entraînement pour chaque intention."""
        return {
            "help_request": [
                "aide-moi", "j'ai besoin d'aide", "comment faire", "peux-tu m'aider",
                "je ne sais pas", "aide", "help", "assistance", "support"
            ],
            "status_check": [
                "comment ça va", "état du système", "tout va bien", "statut",
                "ça marche", "fonctionne", "status", "état", "santé du système"
            ],
            "analysis_request": [
                "analyse ça", "regarde ça", "vérifie", "examine", "contrôle",
                "peux-tu analyser", "étudie", "inspecte", "évalue"
            ],
            "optimization_request": [
                "optimise", "améliore", "rends plus rapide", "accélère",
                "perfectionne", "optimise les performances", "rends meilleur"
            ],
            "explanation_request": [
                "explique-moi", "qu'est-ce que", "comment ça marche", "dis-moi",
                "peux-tu expliquer", "clarification", "describe", "tell me"
            ],
            "time_inquiry": [
                "quelle heure", "il est quelle heure", "l'heure", "temps",
                "what time", "heure actuelle", "heure qu'il est"
            ],
            "date_inquiry": [
                "quelle date", "quel jour", "date d'aujourd'hui", "what date",
                "calendrier", "date actuelle", "jour"
            ],
            "general_query": [
                "je voudrais", "peux-tu", "est-ce que tu peux", "j'aimerais",
                "comment", "pourquoi", "quand", "où", "que", "qui"
            ]
        }
    
    def _bert_extract_parameters(self, normalized_input: str, intent: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extrait les paramètres avec l'aide de BERT."""
        parameters = {
            "full_text": normalized_input,
            "context": context,
            "extracted_entities": [],
            "intent_details": {}
        }
        
        try:
            # Extraction basique des entités nommées
            words = normalized_input.split()
            
            # Détecter les éléments spécifiques selon l'intention
            if intent in ["analysis_request", "optimization_request"]:
                # Chercher des mots-clés techniques
                tech_keywords = ["fichier", "code", "fonction", "variable", "classe", "méthode"]
                found_tech = [word for word in words if any(keyword in word.lower() for keyword in tech_keywords)]
                if found_tech:
                    parameters["target_elements"] = found_tech
            
            elif intent in ["explanation_request"]:
                # Chercher ce qui doit être expliqué
                
                self.frequent_patterns[intent].append({
                    "text": normalized_input,
                    "confidence": confidence,
                    "timestamp": time.time()
                })
                
                # Limiter la taille des patterns fréquents
                if len(self.frequent_patterns[intent]) > 20:
                    # Garder les 20 patterns avec la meilleure confiance
                    self.frequent_patterns[intent] = sorted(
                        self.frequent_patterns[intent], 
                        key=lambda x: x["confidence"], 
                        reverse=True
                    )[:20]
            
        except Exception as e:
            self.logger.warning(f"⚠️ Erreur lors de la mise à jour de l'apprentissage: {e}")
    
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
        """Analyse sémantique très sélective - privilégie la transmission à l'agent central."""
        
        # STRATÉGIE: Être très conservateur pour éviter les faux positifs
        # Laisser l'agent central gérer les requêtes complexes
        
        # Ne traiter que des commandes TRÈS simples et directes
        if len(normalized_input.split()) > 3:
            return None  # Trop complexe, laisser à l'agent central
        
        # Patterns ultra-simples uniquement (mots seuls ou très courts)
        ultra_simple_patterns = {
            CommandType.HELP: ["aide", "help"],
            CommandType.STATUS: ["statut", "état", "status"],
            CommandType.TIME: ["heure", "time"],
        }
        
        # Correspondance exacte pour des mots très simples uniquement
        for command_type, patterns in ultra_simple_patterns.items():
            for pattern in patterns:
                if normalized_input.strip() == pattern:
                    return command_type, {"intent": "ultra_simple_match", "full_text": normalized_input}
        
        # Tout le reste va à l'agent central
        return None
    
    def _detect_polite_quit_intent(self, normalized_input: str) -> bool:
        """Détecte les intentions d'arrêt polies avec logique très stricte pour éviter les faux positifs."""
        import re
        
        # EXCLUSIONS STRICTES : Si ces patterns sont présents, ce n'est JAMAIS un quit
        exclusion_patterns = [
            # Demandes d'aide explicites
            r"(?:aide|help|aidez?[-\s]moi|assiste[-\s]moi)",
            r"(?:explique|expliquer|comment|pourquoi|que fait|comment faire)",
            r"(?:analyse|analyser|examine|examiner|regarde|vérifie)",
            r"(?:optimise|optimiser|améliore|améliorer|suggère|suggérer)",
            r"(?:peux[-\s]tu|pourrais[-\s]tu|tu peux).+(?:aide|expliquer|analyser|optimiser|faire)",
            r"(?:dis[-\s]moi|montre[-\s]moi|raconte[-\s]moi)",
            # Actions spécifiques demandées
            r"(?:code|fichier|fonction|classe|variable|méthode|projet)",
            r"(?:débug|debug|erreur|problème|bug)",
            r"(?:créer|créé|modifier|modifie|ajouter|ajoute)",
            # Phrases mixtes avec remerciement + demande
            r"merci.+(?:aide|analyse|explique|optimise|montre|dis|fait|peux)"
        ]
        
        # Si n'importe quel pattern d'exclusion correspond, ce n'est PAS un quit
        for pattern in exclusion_patterns:
            if re.search(pattern, normalized_input, re.IGNORECASE):
                return False
        
        # PATTERNS D'ARRÊT TRÈS SPÉCIFIQUES - seulement si aucune exclusion
        strict_quit_patterns = [
            # Remerciements de fin SANS demande d'action
            r"^merci\s+(?:beaucoup|bien|pour\s+tout|c'est\s+parfait|c'est\s+bon)$",
            r"^(?:c'est\s+parfait|c'est\s+bon|parfait|excellent)\s*(?:merci)?$",
            r"^merci\s+(?:tu\s+peux\s+t'arrêter|pour\s+ton\s+aide)$",
            
            # Formules d'au revoir claires
            r"^(?:au\s+revoir|à\s+bientôt|bye|goodbye|bonne\s+journée|bonne\s+soirée)$",
            
            # Demandes d'arrêt explicites
            r"^(?:arrête|stop|tu\s+peux\s+arrêter|arrête[-\s]toi)(?:\s+maintenant|\s+stp|\s+merci)?$",
            r"^(?:ça\s+suffit|c'est\s+tout|j'ai\s+fini)(?:\s+merci)?$",
            
            # Combinaisons très spécifiques de politesse + arrêt
            r"merci\s+(?:tu\s+peux\s+(?:partir|te\s+reposer|t'en\s+aller)|pour\s+tout\s+au\s+revoir)",
            r"(?:très\s+bien|excellent)\s+merci\s+(?:arrête|tu\s+peux\s+arrêter)"
        ]
        
        # Vérifier les patterns d'arrêt très stricts uniquement
        for pattern in strict_quit_patterns:
            if re.search(pattern, normalized_input, re.IGNORECASE):
                return True
        
        # Logique supplémentaire pour "merci" seul avec satisfaction finale
        if "merci" in normalized_input:
            # Mots qui indiquent une satisfaction/fin
            satisfaction_words = ["exactement", "ce qu'il me fallait", "c'est tout", "pour tout", "beaucoup"]
            # Mots qui indiquent clairement une demande continue
            continuation_words = ["pour", "de", "explique", "analyse", "optimise", "comment", "peux-tu", "aide"]
            
            has_satisfaction = any(word in normalized_input for word in satisfaction_words)
            has_continuation = any(word in normalized_input for word in continuation_words)
            
            # Si "merci" + satisfaction ET PAS de continuation, c'est probablement un quit
            if has_satisfaction and not has_continuation:
                return True
        
        return False

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
        
        # Système de confirmation intelligent
        self._await_confirmation = False
        self._confirmation_context = None
        
        # Initialisation des composants
        self._init_advanced_speech_recognition()
        self._init_voice_activity_detection()
        self._init_audio_isolation()
        self._enable_advanced_features()
    
    def _init_advanced_speech_recognition(self):
        """Initialise le moteur de reconnaissance vocale Whisper avec le meilleur modèle possible."""
        try:
            self.logger.info("🧠 Initialisation de Whisper avec modèle de qualité...")
            
            # Utiliser le meilleur modèle Whisper possible pour la qualité
            available_memory = psutil.virtual_memory().available / (1024**3)  # GB
            
            # Cache pour les modèles déjà téléchargés
            cached_models = []
            whisper_cache = os.path.expanduser("~/.cache/whisper")
            if os.path.exists(whisper_cache):
                cached_models = [d for d in os.listdir(whisper_cache) if os.path.isdir(os.path.join(whisper_cache, d))]
            
            # Sélection de modèle basée sur la mémoire disponible et modèles en cache
            model_size = "base"  # Modèle par défaut (équilibre performance/qualité)
            
            # Essayer d'utiliser medium en priorité (meilleur rapport qualité/performance)
            if available_memory > 8 or any(m.startswith("medium") for m in cached_models):
                model_size = "medium"  # Bon compromis qualité/performance
                self.logger.info("⚡ Utilisation du modèle Whisper medium (haute qualité)")
            # Sinon utiliser small si mémoire suffisante
            elif available_memory > 4 or any(m.startswith("small") for m in cached_models):
                model_size = "small"  # Qualité correcte
                self.logger.info("🔧 Utilisation du modèle Whisper small")
            else:
                self.logger.info("⚠️ Utilisation du modèle Whisper base (mémoire limitée)")
            
            # Charger le modèle avec optimisations
            self.logger.info(f"⏳ Chargement du modèle Whisper {model_size}...")
            self.whisper_model = whisper.load_model(
                model_size, 
                device="cpu", 
                in_memory=True,
                download_root=os.path.expanduser("~/.cache/whisper")
            )
            self.speech_recognition_engine = "whisper"
            
            # Préchauffer le modèle avec un échantillon vide
            self.logger.info("🔥 Préchauffage du modèle Whisper pour accélérer la première reconnaissance...")
            empty_sample = np.zeros(1600, dtype=np.float32)  # 0.1s d'audio vide
            self.whisper_model.transcribe(
                empty_sample, language="fr", temperature=0.0,
                best_of=1, beam_size=1, fp16=False
            )
            
            self.logger.info(f"✅ Whisper {model_size} initialisé avec succès pour une reconnaissance de qualité")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de l'initialisation de Whisper: {e}")
            self.speech_recognition_engine = None
            
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
    
    def _adapt_to_user_patterns(self):
        """Analyse les patterns d'utilisation utilisateur et adapte l'interface."""
        try:
            if not self.command_history:
                return
            
            # Analyser les commandes les plus fréquentes
            command_frequency = defaultdict(int)
            for command in self.command_history:
                if isinstance(command, dict) and 'command' in command:
                    command_frequency[command['command']] += 1
            
            # Adapter les seuils de reconnaissance selon l'historique
            total_commands = len(self.command_history)
            if total_commands > 10:
                # Si l'utilisateur utilise beaucoup de commandes, être plus sensible
                self.energy_threshold = max(400, self.energy_threshold * 0.9)
                self.logger.info(f"🎯 Seuil d'énergie adapté à {self.energy_threshold:.0f} basé sur l'usage")
            
            # Identifier les préférences temporelles (si implémenté)
            recent_commands = list(self.command_history)[-20:] if len(self.command_history) > 20 else list(self.command_history)
            if recent_commands:
                # Analyser les patterns récents pour optimiser les réponses
                self.logger.debug(f"📊 Dernières commandes analysées: {len(recent_commands)}")
                
        except Exception as e:
            self.logger.warning(f"⚠️ Erreur lors de l'adaptation aux patterns utilisateur: {e}")
    
    def _load_user_preferences(self) -> Dict[str, Any]:
        """Charge les préférences utilisateur en utilisant l'adaptateur pour éviter la duplication de code."""
        if hasattr(self.adapter, '_load_user_preferences'):
            # Utiliser la méthode de l'adaptateur pour éviter la duplication de code
            preferences = self.adapter._load_user_preferences()
            # Mettre à jour les préférences de l'adaptateur pour la synchronisation
            if hasattr(self.adapter, 'user_preferences'):
                self.adapter.user_preferences.update(preferences)
            return preferences
        else:
            # Fallback si l'adaptateur n'a pas la méthode (ne devrait pas arriver)
            self.logger.warning("L'adaptateur n'a pas de méthode _load_user_preferences, utilisation des préférences par défaut")
            return {
                "response_style": "balanced",
                "voice_speed": 1.0,
                "voice_volume": 0.8,
                "language_preference": "fr",
                "proactive_assistance": True,
                "context_awareness": True,
                "learning_mode": True,
                "notification_level": "normal"
            }
    
    def _save_user_preferences(self, preferences: Dict[str, Any]):
        """Sauvegarde les préférences utilisateur."""
        try:
            preferences_path = Path.home() / '.peer' / 'sui_preferences.json'
            preferences_path.parent.mkdir(exist_ok=True)
            with open(preferences_path, 'w', encoding='utf-8') as f:
                json.dump(preferences, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde des préférences: {e}")
    
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
        """Démarre l'interface vocale omnisciente avec approche talkie-walkie."""
        if self.running:
            self.logger.warning("⚠️ L'interface vocale est déjà en cours")
            return
        
        self.running = True
        self.logger.info("🚀 Démarrage de l'interface vocale omnisciente avec mode talkie-walkie...")
        
        # Vérifier la disponibilité des moteurs
        if not self.speech_recognition_engine:
            self._safe_vocalize("Attention: aucun moteur de reconnaissance vocale disponible. Mode dégradé activé.")
            return
        
        # Démarrer les threads principaux avec approche talkie-walkie
        self.listen_thread = threading.Thread(target=self._walkie_talkie_loop, daemon=True)
        self.command_thread = threading.Thread(target=self._intelligent_command_loop, daemon=True)
        
        self.listen_thread.start()
        self.command_thread.start()
        
        # Message d'accueil personnalisé
        welcome_message = self._generate_personalized_greeting()
        self._safe_vocalize(welcome_message)
        
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
        if hasattr(self.adapter, 'user_preferences'):
            self._save_user_preferences(self.adapter.user_preferences)
        else:
            # Utiliser la méthode de l'adaptateur directement si elle existe
            if hasattr(self.adapter, '_save_user_preferences'):
                self.adapter._save_user_preferences()
        
        # Terminer la session
        if hasattr(self, 'session_id'):
            self.daemon.end_session(self.session_id)
        
        # Message de fin personnalisé avec vocalisation sécurisée
        farewell_message = self._generate_personalized_farewell()
        self._safe_vocalize(farewell_message)
        
        self.logger.info("✅ Interface vocale arrêtée avec succès")
    
    def _walkie_talkie_loop(self):
        """Boucle talkie-walkie : écoute uniquement quand l'assistant ne parle pas."""
        self.logger.info("📻 Démarrage du mode talkie-walkie...")
        self._update_visual_status("🎙️ Mode talkie-walkie activé")
        
        # Variables d'état simples
        audio = None
        stream = None
        
        try:
            # Configuration audio simplifiée (OMP_NUM_THREADS déjà défini au début du fichier)
            audio = pyaudio.PyAudio()
            stream = audio.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            self.listening = True
            self.logger.info("🎙️ Microphone initialisé pour le mode talkie-walkie")
            
            while self.running:
                try:
                    # Mode talkie-walkie : N'écouter QUE si pas en train de parler
                    if self.speaking or self.paused:
                        time.sleep(0.1)
                        continue
                    
                    # Respecter la période de silence après TTS pour éviter l'écho
                    if self.speech_end_time > 0:
                        time_since_speech = time.time() - self.speech_end_time
                        if time_since_speech < self.min_silence_after_speech:
                            time.sleep(0.1)
                            continue
                    
                    # Indiquer qu'on écoute
                    if self.show_visual_indicators:
                        self._update_visual_status("🎙️ À vous (parlez maintenant)")
                    
                    # Session d'écoute unique jusqu'à détection de parole complète
                    speech_audio = self._record_single_speech_session(stream)
                    
                    if speech_audio and len(speech_audio) > 0:
                        # Traiter immédiatement la parole détectée
                        self._process_speech_immediately(speech_audio)
                        
                        # Attendre que le traitement soit terminé avant de reprendre l'écoute
                        time.sleep(0.5)
                    else:
                        # Courte pause si aucune parole détectée
                        time.sleep(0.2)
                        
                except KeyboardInterrupt:
                    self.logger.info("⌨️ Interruption clavier dans la boucle talkie-walkie")
                    break
                except Exception as e:
                    self.logger.error(f"❌ Erreur dans la boucle talkie-walkie: {e}")
                    time.sleep(1.0)  # Pause en cas d'erreur pour éviter la surcharge
            
        except Exception as e:
            self.logger.error(f"❌ Erreur fatale dans la boucle d'écoute: {e}")
        finally:
            # Nettoyage propre des ressources audio
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                    self.logger.debug("🔇 Stream audio fermé")
                except:
                    pass
            if audio:
                try:
                    audio.terminate()
                    self.logger.debug("🔇 PyAudio terminé")
                except:
                    pass
            self.listening = False
            self._update_visual_status("🔇 Écoute arrêtée")
            self.logger.info("👂 Boucle talkie-walkie terminée")
    
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
    
    def _update_performance_metrics(self, recognition_result: SpeechRecognitionResult):
        """Met à jour les métriques de performance du système."""
        try:
            # Mettre à jour le temps de traitement moyen
            if hasattr(recognition_result, 'processing_time'):
                processing_time = recognition_result.processing_time
                self.performance_metrics["response_time"] = processing_time
                
                # Alerter si le temps de traitement est anormalement long
                if processing_time > 5.0:
                    self.logger.warning(f"⚠️ Temps de traitement anormalement long: {processing_time:.2f}s")
                    # Ajuster la stratégie de reconnaissance en cas de lenteur
                    self._adjust_recognition_strategy(processing_time)
                
            # Mettre à jour la précision de reconnaissance
            if hasattr(recognition_result, 'confidence'):
                confidence = recognition_result.confidence
                # Ajuster progressivement la précision estimée
                self.recognition_accuracy = 0.9 * self.recognition_accuracy + 0.1 * confidence
                
                # Alerter si la confiance est faible
                if confidence < 0.4:
                    self.logger.debug(f"⚠️ Confiance de reconnaissance faible: {confidence:.2f}")
                
            # Mettre à jour d'autres métriques système
            self.performance_metrics["cpu_usage"] = psutil.cpu_percent(interval=0.1)
            self.performance_metrics["memory_usage"] = psutil.virtual_memory().percent
            
            # Ajuster les seuils de reconnaissance si nécessaire
            if self.total_commands > 10 and hasattr(recognition_result, 'audio_quality'):
                audio_quality = recognition_result.audio_quality
                
                if audio_quality < 0.5:
                    # Si la qualité audio est faible, ajuster les seuils
                    self.energy_threshold = min(1200, self.energy_threshold * 1.05)
                    self.logger.debug(f"🔊 Augmentation du seuil d'énergie à {self.energy_threshold:.0f} (qualité audio faible)")
                elif audio_quality > 0.8 and self.energy_threshold > 600:
                    # Si la qualité audio est bonne, réduire le seuil pour mieux capter les paroles douces
                    self.energy_threshold = max(500, self.energy_threshold * 0.95)
                    self.logger.debug(f"🔉 Réduction du seuil d'énergie à {self.energy_threshold:.0f} (qualité audio bonne)")
        
        except Exception as e:
            self.logger.warning(f"⚠️ Erreur lors de la mise à jour des métriques: {e}")
    
    def _adjust_recognition_strategy(self, processing_time: float):
        """Ajuste la stratégie de reconnaissance en fonction des performances passées."""
        try:
            # Si le traitement est trop lent (> 5s), simplifier la stratégie
            if processing_time > 5.0:
                # Enregistrer l'événement de performance
                if not hasattr(self, 'slow_recognitions'):
                    self.slow_recognitions = 0
                self.slow_recognitions += 1
                
                # Si problèmes récurrents de performance, ajuster la stratégie
                if self.slow_recognitions > 3:
                    self.logger.warning("⚠️ Performance lente récurrente, simplification de la stratégie de reconnaissance")
                    
                    # Vérifier si un modèle plus léger est disponible
                    current_model = getattr(self.whisper_model, 'model_size', 'unknown')
                    
                    if current_model == "medium" or current_model == "large":
                        self.logger.info("🔄 Tentative de passage à un modèle plus léger...")
                        try:
                            # Libérer la mémoire du modèle actuel
                            import gc
                            del self.whisper_model
                            gc.collect()
                            
                            # Charger un modèle plus léger
                            new_model = "small" if current_model == "medium" else "base"
                            self.logger.info(f"⏳ Chargement du modèle Whisper {new_model}...")
                            self.whisper_model = whisper.load_model(new_model, device="cpu", in_memory=True)
                            self.logger.info(f"✅ Passage au modèle {new_model} réussi")
                            
                            # Réinitialiser le compteur
                            self.slow_recognitions = 0
                        except Exception as e:
                            self.logger.error(f"❌ Erreur lors du changement de modèle: {e}")
        
        except Exception as e:
            self.logger.warning(f"⚠️ Erreur lors de l'ajustement de la stratégie: {e}")
    
    def _process_complete_speech(self, speech_frames: List[bytes]):
        """Traite une séquence complète de parole détectée."""
        try:
            if not speech_frames:
                return
            
            # Combiner tous les frames
            complete_audio = b''.join(speech_frames)
            
            # Vérifier si l'audio est trop court pour être significatif
            if len(complete_audio) < 4000:  # Moins de ~0.25 seconde
                self.logger.debug("🔇 Séquence audio trop courte, probablement un bruit")
                return
            
            # Vérifier si l'audio est trop long (peut causer des problèmes de performance)
            if len(complete_audio) > 1920000:  # Plus de 60 secondes @ 16kHz
                self.logger.warning(f"⚠️ Audio très long ({len(complete_audio)/16000:.1f}s), découpage pour éviter les problèmes de performance")
                # Conserver uniquement les 30 premières secondes
                complete_audio = complete_audio[:960000]
            
            # Reconnaissance vocale avec protection contre les timeouts
            self.logger.info(f"🎤 Traitement audio de {len(complete_audio)/16000:.1f}s...")
            start_time = time.time()
            
            # Utiliser un thread séparé avec timeout pour éviter les blocages
            recognition_thread = threading.Thread(
                target=self._recognition_worker,
                args=(complete_audio,)
            )
            recognition_thread.daemon = True
            
            # File d'attente pour récupérer le résultat
            result_queue = queue.Queue()
            self.recognition_worker_queue = result_queue
            
            # Démarrer la reconnaissance
            recognition_thread.start()
            
            # Attendre le résultat avec timeout
            try:
                recognition_result = result_queue.get(timeout=20.0)  # 20 secondes max
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
                else:
                    self.logger.debug("🔇 Aucun texte reconnu dans la séquence audio")
            
            except queue.Empty:
                self.logger.warning("⚠️ Timeout lors de la reconnaissance vocale (>20s)")
                # Si un modèle plus léger est disponible, suggérer de l'utiliser la prochaine fois
                if hasattr(self.whisper_model, 'model_size'):
                    if self.whisper_model.model_size in ["medium", "large"]:
                        self.logger.info("💡 Considérer l'utilisation d'un modèle plus léger pour améliorer les performances")
                        # Force model downgrade after multiple timeouts
                        self._adjust_recognition_strategy(25.0)  # Simuler un temps très long
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors du traitement de la parole: {e}")
    
    def _recognition_worker(self, audio_data: bytes):
        """Thread worker pour la reconnaissance vocale avec timeout."""
        try:
            # Obtenir le résultat
            result = self._recognize_speech_whisper(audio_data)
            
            # Mettre le résultat dans la file d'attente si elle existe toujours
            if hasattr(self, 'recognition_worker_queue') and self.recognition_worker_queue:
                self.recognition_worker_queue.put(result)
        
        except Exception as e:
            self.logger.error(f"❌ Erreur dans le worker de reconnaissance: {e}")
            # Mettre None dans la file d'attente pour indiquer une erreur
            if hasattr(self, 'recognition_worker_queue') and self.recognition_worker_queue:
                self.recognition_worker_queue.put(None)
    
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
            
            # Vérifier si l'audio est trop court ou trop silencieux
            if len(audio_np) < 1600 or np.max(np.abs(audio_np)) < 0.01:
                self.logger.debug("🔇 Audio trop court ou trop silencieux pour reconnaissance")
                return None
            
            # Mesurer le temps de traitement
            start_time = time.time()
            
            # Optimiser la taille de l'audio pour accélérer la reconnaissance
            # Si l'audio est très long, on peut le sous-échantillonner
            if len(audio_np) > 480000:  # Plus de 30 secondes
                # Garder uniquement les N premières secondes pour accélérer
                audio_np = audio_np[:480000]
                self.logger.debug("⏱️ Audio tronqué pour accélérer la reconnaissance")
            
            # Whisper transcription avec options optimisées
            result = self.whisper_model.transcribe(
                audio_np,
                language="fr",  # Forcer le français pour de meilleures performances
                task="transcribe",
                temperature=0.0,  # Déterministe
                best_of=1,        # Plus rapide
                beam_size=1,      # Plus rapide
                condition_on_previous_text=False,  # Plus rapide sans contexte
                suppress_tokens=[-1],  # Supprimer les tokens spéciaux
                fp16=False,            # Éviter l'avertissement FP16 sur CPU
                initial_prompt="Commande en français: "  # Aide à orienter la reconnaissance
            )
            
            # Mesurer le temps de traitement
            processing_time = time.time() - start_time
            
            text = result["text"].strip()
            if text:
                # Estimer la confiance basée sur la durée et la clarté
                confidence = self._estimate_confidence(audio_np, text)
                audio_quality = self._assess_audio_quality(audio_np)
                
                self.logger.debug(f"🔍 Reconnaissance en {processing_time:.2f}s (confiance: {confidence:.2f}, qualité: {audio_quality:.2f})")
                
                return SpeechRecognitionResult(
                    text=text,
                    confidence=confidence,
                    language="fr",
                    audio_quality=audio_quality,
                    processing_time=processing_time
                )
            
        except Exception as e:
            self.logger.error(f"❌ Erreur Whisper: {e}")
        
        return None
    
    def _estimate_confidence(self, audio_np: np.ndarray, text: str) -> float:
        """Estime la confiance de la reconnaissance basée sur plusieurs facteurs."""
        try:
            # 1. Facteur qualité audio
            audio_quality = self._assess_audio_quality(audio_np)
            
            # 2. Facteur longueur du texte (textes plus longs = plus fiables)
            text_length = len(text)
            text_length_factor = min(1.0, text_length / 30)
            
            # 3. Facteur mots reconnaissables
            # Liste étendue de mots courants en français bien reconnus par Whisper
            confidence_words = [
                "aide", "bonjour", "merci", "oui", "non", "comment", "quoi", "où", "quand",
                "pourquoi", "salut", "peer", "pardon", "okay", "ok", "bien", "stop",
                "analyser", "expliquer", "arrête", "version", "statut"
            ]
            
            words_in_text = text.lower().split()
            recognized_words = sum(1 for word in confidence_words if word in words_in_text)
            word_confidence = min(1.0, recognized_words / max(1, len(words_in_text)))
            
            # 4. Facteur caractères spéciaux (moins il y en a, plus c'est fiable)
            special_chars = sum(1 for c in text if not (c.isalnum() or c.isspace()))
            special_char_penalty = max(0.0, 1.0 - (special_chars / max(1, len(text))))
            
            # Combinaison pondérée des facteurs
            confidence = (
                audio_quality * 0.35 +
                text_length_factor * 0.25 +
                word_confidence * 0.25 +
                special_char_penalty * 0.15
            )
            
            # Assurer une plage raisonnable
            return min(1.0, max(0.2, confidence))
            
        except Exception as e:
            self.logger.debug(f"Erreur estimation confiance: {e}")
            return 0.7  # Confiance par défaut
    
    def _assess_audio_quality(self, audio_np: np.ndarray) -> float:
        """Évalue la qualité de l'audio en utilisant plusieurs métriques."""
        try:
            # Vérifier si l'audio est vide ou trop court
            if len(audio_np) < 1600 or np.max(np.abs(audio_np)) < 0.01:
                return 0.2
            
            # 1. Signal-to-noise ratio approximatif
            signal_power = np.mean(audio_np**2)
            if signal_power < 1e-6:  # Presque silencieux
                return 0.2
            
            # 2. Calculer le SNR basé sur la variance du signal
            background_noise = np.var(audio_np[:min(1600, len(audio_np))])  # Bruit de fond au début
            snr = 10 * np.log10(signal_power / max(1e-10, background_noise))
            snr_quality = min(1.0, max(0.0, (snr + 10) / 40))
            
            # 3. Calculer l'amplitude du signal (dynamique)
            amplitude = np.max(np.abs(audio_np)) - np.min(np.abs(audio_np))
            amplitude_quality = min(1.0, amplitude * 5)
            
            # 4. Régularité du signal (faible variance = plus constant, plus fiable)
            chunk_size = min(1600, len(audio_np) // 8)
            chunks = [audio_np[i:i+chunk_size] for i in range(0, len(audio_np), chunk_size)]
            chunk_powers = [np.mean(chunk**2) for chunk in chunks if len(chunk) == chunk_size]
            power_variance = np.var(chunk_powers) if chunk_powers else 1.0
            regularity = min(1.0, max(0.0, 1.0 - power_variance))
            
            # Combinaison pondérée
            quality = (
                snr_quality * 0.5 +
                amplitude_quality * 0.3 +
                regularity * 0.2
            )
            
            # Ajustement final
            return min(1.0, max(0.2, quality))
            
        except Exception as e:
            self.logger.debug(f"Erreur évaluation audio: {e}")
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

            # Gestion spéciale des confirmations en attente
            if hasattr(self, '_await_confirmation') and self._await_confirmation:
                self._process_confirmation_response(speech_text)
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

            # Gestion spéciale des nouvelles réponses avec confirmation
            if adapted_response.get("immediate_quit"):
                # DIRECT_QUIT immédiat (fin de phrase) - arrêt sans confirmation
                self._safe_vocalize(adapted_response.get("vocal_message", "Au revoir !"))
                self.stop()
                return
                
            elif adapted_response.get("requires_confirmation"):
                # Demande de confirmation intelligente
                self._handle_confirmation_request(adapted_response, speech_text)
                return
                
            elif adapted_response.get("is_command_sequence"):
                # Séquence de commandes détectée
                self._handle_command_sequence(adapted_response)
                return

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
        
        # Lancer la vocalisation dans un thread séparé avec timeout généreux
        thread = threading.Thread(target=tts_thread, daemon=True)
        thread.start()
        
        # Attendre avec timeout étendu de 120 secondes pour permettre de longs messages
        # Le système central peut générer des messages de toute longueur
        if not tts_completed.wait(timeout=120.0):
            self.logger.error("⏰ Timeout TTS étendu - vocalisation abandonnée après 2 minutes")
            return
        
        # Vérifier s'il y a eu une erreur
        if tts_error[0]:
            raise tts_error[0]

    def _safe_vocalize(self, text: str):
        """Vocalisation sécurisée avec protection anti-récursion améliorée."""
        if not text or not text.strip():
            return
            
        # Protection stricte contre la récursion TTS
        if hasattr(self, '_tts_recursion_depth'):
            if self._tts_recursion_depth > 1:
                self.logger.warning(f"🚫 Récursion TTS détectée (niveau {self._tts_recursion_depth}) - message ignoré: {text[:50]}...")
                return
        
        try:
            # Marquer qu'on va parler AVANT de commencer
            self.speaking = True
            start_time = time.time()
            
            # Vocaliser directement avec la méthode sécurisée pour éviter la récursion
            self._safe_tts_speak(text)
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de la vocalisation sécurisée: {e}")
            # En cas d'erreur, ne pas essayer de re-vocaliser pour éviter la récursion
            if self.show_visual_indicators:
                self._update_visual_status(f"❌ [Erreur TTS silencieuse] {text[:30]}...")
        finally:
            # S'assurer que speaking est remis à False
            self.speaking = False

    def _handle_command_error(self, error: Exception):
        """Gère les erreurs de commande sans risque de récursion TTS."""
        error_msg = str(error)
        self.logger.error(f"❌ Erreur de commande: {error_msg}")
        
        # Affichage visuel UNIQUEMENT pour éviter la récursion TTS
        if self.show_visual_indicators:
            self._update_visual_status(f"❌ Erreur: {error_msg[:50]}...")
        
        # Log pour debugging mais pas de vocalisation
        self.logger.debug(f"Erreur de commande détaillée: {error}")

    def _handle_confirmation_request(self, adapted_response: dict, original_text: str):
        """Gère les demandes de confirmation intelligentes pour les commandes d'arrêt ambiguës."""
        self.logger.info(f"Demande de confirmation reçue pour: {original_text}")
        
        # Extraire les informations de la réponse
        confirmation_message = adapted_response.get("vocal_message", "Voulez-vous vraiment arrêter ?")
        quit_type = adapted_response.get("quit_type", "SOFT_QUIT")
        detected_commands = adapted_response.get("detected_commands", [])
        
        # Vocaliser la demande de confirmation
        self._safe_vocalize(confirmation_message)
        
        # Attendre une réponse de confirmation
        self.logger.debug("Attente de confirmation utilisateur...")
        
        # Configurer une écoute spéciale pour la confirmation
        if hasattr(self, '_await_confirmation'):
            self._await_confirmation = True
            self._confirmation_context = {
                "original_text": original_text,
                "quit_type": quit_type,
                "detected_commands": detected_commands,
                "timeout": time.time() + 30  # 30 secondes de timeout
            }
        else:
            # Fallback: traiter comme une commande normale avec contexte
            self.logger.warning("Système de confirmation non disponible - traitement direct")
            if quit_type == "DIRECT_QUIT":
                self._safe_vocalize("Au revoir !")
                self.stop()

    def _handle_command_sequence(self, adapted_response: dict):
        """Gère l'exécution de séquences de commandes détectées."""
        commands = adapted_response.get("command_sequence", [])
        sequence_message = adapted_response.get("vocal_message", "Plusieurs commandes détectées.")
        
        self.logger.info(f"Traitement de séquence de {len(commands)} commandes")
        
        # Vocaliser le message d'introduction de la séquence
        self._safe_vocalize(sequence_message)
        
        # Exécuter chaque commande de la séquence
        for i, command_info in enumerate(commands):
            try:
                command_type = command_info.get("command")
                command_text = command_info.get("text", "")
                command_confidence = command_info.get("confidence", 0.0)
                
                self.logger.debug(f"Exécution commande {i+1}/{len(commands)}: {command_type} (confiance: {command_confidence:.2f})")
                
                # Créer une requête pour cette commande spécifique
                from peer.core.api import CoreRequest, CommandType
                
                # Mapper le type de commande
                core_command_type = getattr(CommandType, command_type.upper(), CommandType.PROMPT)
                
                request = CoreRequest(
                    command=core_command_type,
                    text=command_text,
                    session_id=self.session_id,
                    metadata={
                        "source": "sequence",
                        "sequence_position": i + 1,
                        "sequence_total": len(commands),
                        "confidence": command_confidence
                    }
                )
                
                # Exécuter la commande via le daemon
                response = self.daemon.execute_command(request)
                
                # Traiter la réponse
                if response and response.text:
                    # Vocaliser la réponse si approprié
                    if core_command_type != CommandType.QUIT:  # Éviter la vocalisation pour les quits
                        self._safe_vocalize(response.text)
                
                # Pause courte entre les commandes
                if i < len(commands) - 1:  # Pas de pause après la dernière commande
                    time.sleep(0.5)
                    
            except Exception as e:
                self.logger.error(f"Erreur lors de l'exécution de la commande {i+1}: {e}")
                self._safe_vocalize(f"Erreur lors de l'exécution de la commande {i+1}")

    def _process_confirmation_response(self, response_text: str):
        """Traite la réponse de l'utilisateur à une demande de confirmation."""
        if not hasattr(self, '_confirmation_context'):
            self.logger.warning("Réponse de confirmation reçue mais pas de contexte disponible")
            self._await_confirmation = False
            return
        
        context = self._confirmation_context
        response_lower = response_text.lower().strip()
        
        # Vérifier le timeout
        if time.time() > context.get("timeout", 0):
            self.logger.info("Timeout de confirmation - annulation")
            self._safe_vocalize("Timeout de confirmation. Action annulée.")
            self._await_confirmation = False
            delattr(self, '_confirmation_context')
            return
        
        # Analyser la réponse de confirmation
        positive_responses = [
            "oui", "yes", "ok", "d'accord", "confirme", "confirmer",
            "vas-y", "allez-y", "go", "continue", "arrête", "stop",
            "ferme", "quit", "quitte", "bye", "au revoir", "c'est ça"
        ]
        
        negative_responses = [
            "non", "no", "annule", "annuler", "cancel", "pas maintenant",
            "pas encore", "attends", "stop", "ne fais pas", "n'arrête pas"
        ]
        
        is_positive = any(pos in response_lower for pos in positive_responses)
        is_negative = any(neg in response_lower for neg in negative_responses)
        
        self.logger.info(f"Réponse de confirmation: '{response_text}' -> positive: {is_positive}, negative: {is_negative}")
        
        if is_positive and not is_negative:
            # Confirmation positive
            quit_type = context.get("quit_type", "SOFT_QUIT")
            
            if quit_type == "DIRECT_QUIT":
                self._safe_vocalize("D'accord, j'arrête.")
                self.stop()
            elif quit_type == "SOFT_QUIT":
                self._safe_vocalize("D'accord, au revoir !")
                self.stop()
            else:
                # Exécuter les commandes détectées
                commands = context.get("detected_commands", [])
                if commands:
                    self._safe_vocalize("D'accord, j'exécute les commandes.")
                    # Créer une réponse de séquence simulée
                    sequence_response = {
                        "command_sequence": commands,
                        "vocal_message": "Exécution des commandes confirmées."
                    }
                    self._handle_command_sequence(sequence_response)
                
        elif is_negative:
            # Confirmation négative
            self._safe_vocalize("D'accord, je continue.")
            
        else:
            # Réponse ambiguë - redemander
            self._safe_vocalize("Je n'ai pas bien compris. Pouvez-vous dire 'oui' ou 'non' ?")
            # Prolonger le timeout
            context["timeout"] = time.time() + 15
            return  # Ne pas nettoyer le contexte, attendre une nouvelle réponse
        
        # Nettoyer le contexte de confirmation
        self._await_confirmation = False
        if hasattr(self, '_confirmation_context'):
            delattr(self, '_confirmation_context')

    def _record_single_speech_session(self, stream) -> Optional[bytes]:
        """Enregistre une session de parole unique jusqu'à détection complète."""
        if not stream:
            return None
            
        try:
            audio_data = b''
            frames_recorded = 0
            max_frames = int(self.sample_rate * 10 / self.chunk_size)  # Max 10 secondes
            speech_detected = False
            silence_frames = 0
            max_silence_frames = int(self.sample_rate * 2 / self.chunk_size)  # 2 secondes de silence
            
            self.logger.debug("🎙️ Début de session d'écoute...")
            
            while frames_recorded < max_frames and self.running:
                # Vérifier si on doit arrêter d'écouter (si on commence à parler)
                if self.speaking or self.paused:
                    self.logger.debug("🔇 Arrêt d'écoute - assistant en train de parler")
                    break
                
                try:
                    # Lire un chunk audio
                    chunk = stream.read(self.chunk_size, exception_on_overflow=False)
                    if not chunk:
                        break
                        
                    audio_data += chunk
                    frames_recorded += 1
                    
                    # Analyser le chunk pour détecter la parole
                    audio_np = np.frombuffer(chunk, dtype=np.int16)
                    # Calcul d'énergie sécurisé pour éviter les valeurs invalides
                    if len(audio_np) > 0:
                        mean_squared = np.mean(audio_np.astype(np.float64)**2)
                        energy = np.sqrt(max(0, mean_squared))  # Éviter les valeurs négatives
                    else:
                        energy = 0.0
                    
                    # Détecter l'activité vocale
                    if energy > self.energy_threshold:
                        speech_detected = True
                        silence_frames = 0
                        if self.show_visual_indicators:
                            self._update_visual_status("🎙️ Parole détectée...")
                    else:
                        if speech_detected:
                            silence_frames += 1
                            
                    # Si on a détecté de la parole et qu'on a maintenant du silence, arrêter
                    if speech_detected and silence_frames > max_silence_frames:
                        self.logger.debug("🔇 Fin de parole détectée (silence prolongé)")
                        break
                        
                except Exception as e:
                    self.logger.error(f"❌ Erreur lors de la lecture audio: {e}")
                    break
            
            # Retourner les données audio si on a détecté de la parole
            if speech_detected and len(audio_data) > 0:
                self.logger.debug(f"✅ Session d'écoute terminée - {len(audio_data)} bytes enregistrés")
                return audio_data
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Erreur dans la session d'écoute: {e}")
            return None

    def _process_speech_immediately(self, audio_data: bytes):
        """Traite immédiatement la parole détectée."""
        if not audio_data:
            return
            
        try:
            # Indiquer qu'on traite
            if self.show_visual_indicators:
                self._update_visual_status("🧠 Traitement de la parole...")
            
            # Reconnaissance vocale
            recognition_result = self._recognize_speech_whisper(audio_data)
            
            if recognition_result and recognition_result.text:
                speech_text = recognition_result.text.strip()
                
                if speech_text:
                    self.logger.info(f"🎯 Parole reconnue: '{speech_text}'")
                    
                    # Mettre en queue pour traitement
                    self.command_queue.put(speech_text)
                    
                    # Mettre à jour les métriques
                    self._update_performance_metrics(recognition_result)
                else:
                    self.logger.debug("🔇 Parole reconnue mais texte vide")
            else:
                self.logger.debug("🔇 Aucune parole reconnue clairement")
                
        except Exception as e:
            self.logger.error(f"❌ Erreur lors du traitement immédiat: {e}")
    
    def _generate_personalized_greeting(self) -> str:
        """Génère un message d'accueil personnalisé complet basé sur l'heure et l'historique."""
        import datetime
        
        current_hour = datetime.datetime.now().hour
        
        # Message d'accueil personnalisé
        if current_hour < 12:
            time_greeting = "Bonjour"
        elif current_hour < 18:
            time_greeting = "Bon après-midi"
        else:
            time_greeting = "Bonsoir"
        
        # Message complet et informatif - le système central génère des messages de toute longueur
        greeting_parts = [
            f"{time_greeting} ! Interface vocale Peer omnisciente activée et prête.",
            "Je dispose d'une reconnaissance vocale de haute qualité avec Whisper",
            "et je peux traiter des messages de toute longueur sans restriction.",
            "Vous pouvez me parler naturellement ou dire 'aide' pour découvrir mes commandes.",
            "Mon système d'isolation audio évite l'auto-écoute et je gère intelligemment les interruptions.",
            "Je suis à votre service pour toute tâche ou question."
        ]
        
        return " ".join(greeting_parts)
    
    def _generate_personalized_farewell(self) -> str:
        """Génère un message d'adieu personnalisé complet."""
        import datetime
        
        current_hour = datetime.datetime.now().hour
        
        # Message basé sur l'heure
        if 6 <= current_hour < 18:
            farewell = "Bonne journée"
        elif 18 <= current_hour < 22:
            farewell = "Bonne soirée"
        else:
            farewell = "Bonne nuit"
        
        # Ajouter des informations détaillées sur la session si disponible
        session_info = ""
        if hasattr(self, 'total_commands') and self.total_commands > 0:
            session_info = f" Nous avons traité {self.total_commands} commandes ensemble durant cette session."
        
        # Message complet sans restriction de longueur
        farewell_parts = [
            "Interface vocale Peer omnisciente en cours d'arrêt.",
            session_info,
            "La reconnaissance vocale de haute qualité et le traitement intelligent ont été désactivés.",
            f"{farewell} et merci d'avoir utilisé Peer !",
            "À bientôt pour une nouvelle session productive."
        ]
        
        return " ".join(farewell_parts)

    def _monitor_system_health(self):
        """Surveille l'état du système et les performances."""
        try:
           
            # Vérification basique de la santé du système
            import psutil
            
            # Monitorer l'utilisation CPU (si trop élevée, réduire la fréquence de traitement)
            cpu_percent = psutil.cpu_percent(interval=None)
            if cpu_percent > 80:
                self.logger.warning(f"⚠️ CPU élevé: {cpu_percent}%")
            
            # Monitorer la mémoire
            memory = psutil.virtual_memory()
            if memory.percent > 85:
                self.logger.warning(f"⚠️ Mémoire élevée: {memory.percent}%")
            
            # Vérifier que les threads principaux sont toujours actifs
            if hasattr(self, 'listen_thread') and not self.listen_thread.is_alive():
                self.logger.error("❌ Thread d'écoute arrêté")
            
            if hasattr(self, 'command_thread') and not self.command_thread.is_alive():
                self.logger.error("❌ Thread de commandes arrêté")
                
        except Exception as e:
            self.logger.debug(f"Erreur lors du monitoring: {e}")

def main():
    """Point d'entrée principal de l'interface vocale omnisciente."""
    try:
        print("=== Interface Vocale Omnisciente Peer (SUI) ===")
        print("🎙️ Démarrage de l'interface vocale avec capacités d'IA avancées...")
        print("⚡ Mode talkie-walkie activé pour éviter l'auto-écoute")
        print("🧠 Reconnaissance vocale Whisper optimisée pour le français")
        print("🔄 Assistance proactive et apprentissage adaptatif")
        print("Appuyez sur Ctrl+C pour arrêter")
        print()

        # Créer et démarrer l'interface SUI
        sui = OmniscientSUI()
        sui.start()

        # Maintenir l'application en vie
        try:
            while sui.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n🛑 Arrêt demandé par l'utilisateur")
            sui.stop()

    except KeyboardInterrupt:
        print("\n🛑 Arrêt demandé par l'utilisateur")
    except Exception as e:
        print(f"❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        logging.error(f"Erreur fatale dans SUI omnisciente: {e}")


if __name__ == "__main__":
    main()
