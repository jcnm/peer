"""
Module principal du moteur NLP (Natural Language Processing) pour NLU.

Ce module déplace la logique NLU depuis nlu_engine.py vers le nouveau
nlp_engine.py selon la restructuration demandée.

Architecture:
1. Modèles légers rapides (spaCy + patterns)
2. Sentence Transformers pour la similarité sémantique
3. BERT comme option avancée (avec fallback robuste)
4. Classification par mots-clés intelligents
5. Analyse contextuelle adaptive
"""

import os
import sys
import time
import logging
import re
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
from collections import defaultdict, deque
import numpy as np
import spacy
from sentence_transformers import SentenceTransformer

# Configuration des variables d'environnement pour éviter les warnings
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Import des modèles de domaine
from peer.interfaces.sui.nlu.domain.models import (
    IntentResult, 
    NLUMethod, 
    NLUModelStatus, 
    NLUPerformanceStats,
    IntentPattern,
    NLUContext
)

# Import du chargeur de configuration
from peer.interfaces.sui.nlu.config.config_loader import load_nlu_config

# Initialisation du logger
logger = logging.getLogger(__name__)


class NLPEngine:
    """
    Moteur NLP principal pour le traitement du langage naturel.
    
    Combine plusieurs approches pour assurer une fiabilité maximale:
    - Patterns prédéfinis pour les commandes courantes
    - Modèles de similarité sémantique
    - Classification hybride avec fallbacks
    - Analyse contextuelle adaptive
    """
    
    def __init__(self, config: Optional[Union[str, Dict[str, Any]]] = None, peer_daemon_instance=None):
        """
        Initialise le moteur NLP.
        
        Args:
            config: Chemin vers le fichier de configuration NLU ou dictionnaire de configuration
            peer_daemon_instance: Instance du daemon peer
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("🧠 Initialisation du moteur NLP...")
        self.peer_daemon = peer_daemon_instance

        self.config = self._load_configuration(config)
        self.nlp_spacy: Optional[spacy.Language] = None
        self.sentence_transformer: Optional[SentenceTransformer] = None
        self.intent_patterns: Dict[str, Dict[str, Any]] = {}  # Updated type hint and default value

        self._initialize_models()
        self._load_intent_patterns()
        self.logger.info("✅ Moteur NLP initialisé avec succès")
    
    def _load_configuration(self, config_input: Optional[Union[str, Dict[str, Any]]]) -> Dict[str, Any]:
        """Charge la configuration NLP à partir d'un chemin de fichier, d'un dictionnaire ou utilise les valeurs par défaut."""
        default_config = self._get_default_nlp_config()

        if isinstance(config_input, dict):
            self.logger.info("⚙️ Using provided dictionary as NLP configuration.")
            merged_config = default_config.copy()
            merged_config.update(config_input)
            if 'intent_patterns_path' in merged_config and not os.path.isabs(merged_config['intent_patterns_path']):
                pass
            return merged_config
        elif isinstance(config_input, str):
            if os.path.exists(config_input):
                self.logger.info(f"⚙️ Loading NLP configuration from {config_input}...")
                try:
                    with open(config_input, 'r', encoding='utf-8') as f:
                        loaded_config = yaml.safe_load(f)
                    if not isinstance(loaded_config, dict):
                        self.logger.error(f"❌ NLP Config file {config_input} is not a valid dictionary. Using defaults.")
                        return default_config
                    
                    merged_config = default_config.copy()
                    merged_config.update(loaded_config)
                    if 'intent_patterns_path' in merged_config and not os.path.isabs(merged_config['intent_patterns_path']):
                        pass
                    return merged_config
                except Exception as e:
                    self.logger.error(f"❌ Error loading NLP config from {config_input}: {e}. Using defaults.")
                    return default_config
            else:
                self.logger.warning(f"⚠️ NLP Config file {config_input} not found. Using default configuration.")
                return default_config
        else:
            self.logger.info("⚙️ No NLP configuration path or dictionary provided. Using default configuration.")
            return default_config

    def _get_default_nlp_config(self) -> Dict[str, Any]:
        """Retourne la configuration NLP par défaut."""
        intent_patterns_default_path = "config/intent_patterns.json"
        return {
            "spacy_model_name": "fr_core_news_sm",
            "sentence_transformer_model_name": "sentence-transformers/all-MiniLM-L6-v2",
            "intent_patterns_path": intent_patterns_default_path,
            "similarity_threshold": 0.7,
            "use_gpu": False,
            "language": "fr"
        }

    def _initialize_models(self):
        """Initialise les modèles NLP disponibles."""
        self.logger.info("🔄 Initialisation des modèles NLP...")
        
        # Initialiser spaCy
        self._init_spacy()
        
        # Initialiser Sentence Transformers
        self._init_sentence_transformers()
        
        # Initialiser BERT (optionnel)
        if self.config.get("models", {}).get("bert", {}).get("enabled", False):
            self._init_bert()
        
        self.logger.info("✅ Initialisation des modèles terminée")
    
    def _load_intent_patterns(self):
        """
        Charge les patterns d'intention directement depuis la configuration chargée (self.config).
        Les patterns sont attendus sous la clé "intent_patterns" dans self.config.
        """
        loaded_patterns = self.config.get("intent_patterns")

        if isinstance(loaded_patterns, dict):
            self.intent_patterns = loaded_patterns
            self.logger.info(f"✅ Intent patterns loaded directly from configuration: {len(self.intent_patterns)} categories.")
            
            # Optionnel: Compiler les expressions régulières ici si nécessaire, comme dans l'ancienne version de NLUEngine
            for command_type, pattern_data in self.intent_patterns.items():
                if "patterns" in pattern_data and isinstance(pattern_data["patterns"], list):
                    compiled_patterns = []
                    for pattern_str in pattern_data["patterns"]:
                        try:
                            compiled_patterns.append(re.compile(pattern_str, re.IGNORECASE))
                        except re.error as e:
                            self.logger.warning(f"⚠️ Invalid regex pattern for {command_type}: '{pattern_str}'. Error: {e}")
                    pattern_data["compiled_patterns"] = compiled_patterns
                    self.logger.debug(f"Compiled {len(compiled_patterns)} regex patterns for intent '{command_type}'.")

        elif loaded_patterns is not None:
            self.logger.warning(f"⚠️ 'intent_patterns' in NLP config is not a dictionary. Found type: {type(loaded_patterns)}. No patterns loaded.")
            self.intent_patterns = {}
        else:
            self.logger.warning("⚠️ No 'intent_patterns' found in NLP configuration. No patterns loaded.")
            self.intent_patterns = {}

    def _init_spacy(self):
        """Initialise le modèle spaCy."""
        try:
            model_name = self.config.get("spacy_model_name", "fr_core_news_sm")
            self.spacy_nlp = spacy.load(model_name)
            self.logger.info(f"✅ spaCy {model_name} chargé")
        except Exception as e:
            self.logger.warning(f"⚠️ spaCy non disponible: {e}")
            self.spacy_nlp = None
    
    def _init_sentence_transformers(self):
        """Initialise Sentence Transformers."""
        try:
            model_name = self.config.get("sentence_transformer_model_name", "sentence-transformers/all-MiniLM-L6-v2")
            self.sentence_transformer = SentenceTransformer(model_name)
            self.logger.info(f"✅ SentenceTransformer {model_name} chargé")
        except Exception as e:
            self.logger.warning(f"⚠️ SentenceTransformer non disponible: {e}")
            self.sentence_transformer = None

    def extract_intent(self, text: str, context: Dict[str, Any] = None) -> IntentResult:
        """
        Extrait l'intention du texte d'entrée.
        
        Args:
            text: Texte à analyser
            context: Contexte optionnel pour l'analyse
            
        Returns:
            IntentResult avec le type de commande et les métadonnées
        """
        if not text or not text.strip():
            return IntentResult(
                command_type="unknown",
                confidence=0.0,
                method_used="validation",
                parameters={},
                processing_time=0.0
            )
        
        start_time = time.time()
        normalized_text = text.lower().strip()
        
        # Simple pattern matching for common intents
        intent_patterns = self.intent_patterns
        
        best_match = None
        best_confidence = 0.0
        
        for intent_name, patterns in intent_patterns.items():
            # Check keywords
            keywords = patterns.get("keywords", [])
            keyword_matches = sum(1 for keyword in keywords if keyword in normalized_text)
            
            if keyword_matches > 0:
                confidence = min(0.8, keyword_matches * 0.3)
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = intent_name
        
        # Fallback to basic command mapping
        command_mapping = {
            "help": "help",
            "aide": "help",
            "status": "status",
            "statut": "status", 
            "quit": "quit",
            "quitte": "quit",
            "arrête": "quit",
            "stop": "quit",
            "time": "time",
            "heure": "time",
            "date": "date",
            "version": "version",
            "capabilities": "capabilities",
            "echo": "echo"
        }
        
        if not best_match:
            for word in normalized_text.split():
                if word in command_mapping:
                    best_match = command_mapping[word]
                    best_confidence = 0.7
                    break
        
        if not best_match:
            best_match = "unknown"
            best_confidence = 0.5
        
        processing_time = time.time() - start_time
        
        return IntentResult(
            command_type=best_match,
            confidence=best_confidence,
            method_used="pattern_matching",
            parameters={"full_text": text},
            processing_time=processing_time
        )

    def get_models_status(self) -> Dict[str, Any]:
        """
        Retourne le statut de tous les modèles NLP chargés.
        
        Returns:
            Dict contenant le statut de chaque modèle
        """
        status = {
            "spacy": {
                "loaded": hasattr(self, 'nlp') and self.nlp is not None,
                "model": "fr_core_news_sm" if hasattr(self, 'nlp') and self.nlp else None
            },
            "sentence_transformer": {
                "loaded": hasattr(self, 'sentence_transformer') and self.sentence_transformer is not None,
                "model": "sentence-transformers/all-MiniLM-L6-v2" if hasattr(self, 'sentence_transformer') and self.sentence_transformer else None
            },
            "intent_patterns": {
                "loaded": hasattr(self, 'intent_patterns') and bool(self.intent_patterns),
                "count": len(self.intent_patterns) if hasattr(self, 'intent_patterns') else 0
            }
        }
        return status
