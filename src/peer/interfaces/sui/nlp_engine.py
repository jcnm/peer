"""
Module d'intelligence NLP amélioré pour l'extraction d'intentions vocales.

Ce module implémente une approche hybride robuste combinant plusieurs modèles NLP
pour assurer une extraction d'intentions fiable même en cas de problèmes de compatibilité
avec certains modèles (ex: problèmes PyTorch/BERT).

Architecture:
1. Modèles légers rapides (spaCy + patterns)
2. Sentence Transformers pour la similarité sémantique
3. BERT comme option avancée (avec fallback robuste)
4. Classification par mots-clés intelligents
5. Analyse contextuelle adaptive
"""

import os
import sys
import json
import time
import logging
import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Union
from dataclasses import dataclass
from collections import defaultdict, deque
import numpy as np

# Configuration des variables d'environnement pour éviter les warnings
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Patch de compatibilité PyTorch AVANT toute importation
try:
    import torch
    # Patch pour PyTorch 2.2.2 - ajouter get_default_device manquant
    if not hasattr(torch, 'get_default_device'):
        def get_default_device():
            return 'cpu'
        torch.get_default_device = get_default_device
        logging.info("✅ Patch PyTorch get_default_device appliqué")
except ImportError:
    logging.warning("PyTorch non disponible")

# Importations avec gestion d'erreurs
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logging.warning("spaCy non disponible - fallback vers méthodes alternatives")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning("sentence-transformers non disponible - utilisation d'alternatives")
except Exception as e:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning(f"sentence-transformers non compatible: {e}")

try:
    from transformers import AutoTokenizer, AutoModel, pipeline
    import torch.nn.functional as F
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logging.warning("transformers non disponibles - utilisation de méthodes alternatives")
except Exception as e:
    TRANSFORMERS_AVAILABLE = False
    logging.warning(f"transformers non compatibles: {e}")

from peer.core import CommandType


@dataclass
class IntentResult:
    """Résultat de l'analyse d'intention."""
    command_type: CommandType
    confidence: float
    method_used: str
    parameters: Dict[str, Any]
    processing_time: float = 0.0
    fallback_used: bool = False


class HybridNLPEngine:
    """
    Moteur NLP hybride robuste pour l'extraction d'intentions vocales.
    
    Combine plusieurs approches pour assurer une fiabilité maximale:
    - Modèles légers rapides (spaCy)
    - Sentence Transformers pour similarité sémantique
    - BERT avec fallback robuste
    - Classification par règles intelligentes
    """
    
    def __init__(self):
        self.logger = logging.getLogger("HybridNLPEngine")
        self.logger.info("🧠 Initialisation du moteur NLP hybride...")
        
        # Métriques et cache
        self.processing_times = deque(maxlen=100)
        self.success_rates = defaultdict(list)
        self.embedding_cache = {}
        self.pattern_cache = {}
        
        # Configuration
        self.config = {
            "confidence_threshold": 0.7,
            "semantic_threshold": 0.75,
            "max_cache_size": 500,
            "enable_learning": True,
            "fallback_enabled": True
        }
        
        # Initialiser les modèles par ordre de priorité
        self._init_lightweight_models()
        self._init_sentence_transformers()
        self._init_bert_model()
        self._build_intent_patterns()
        
        self.logger.info("✅ Moteur NLP hybride initialisé avec succès")
    
    def _init_lightweight_models(self):
        """Initialise les modèles légers (spaCy)."""
        self.spacy_model = None
        self.spacy_enabled = False
        
        if SPACY_AVAILABLE:
            try:
                # Tenter de charger le modèle français
                try:
                    self.spacy_model = spacy.load("fr_core_news_sm")
                    self.logger.info("✅ Modèle spaCy français chargé")
                except OSError:
                    # Fallback vers le modèle anglais
                    try:
                        self.spacy_model = spacy.load("en_core_web_sm")
                        self.logger.info("✅ Modèle spaCy anglais chargé (fallback)")
                    except OSError:
                        self.logger.warning("⚠️ Aucun modèle spaCy disponible")
                
                if self.spacy_model:
                    self.spacy_enabled = True
                    
            except Exception as e:
                self.logger.warning(f"⚠️ Erreur lors du chargement spaCy: {e}")
    
    def _init_sentence_transformers(self):
        """Initialise Sentence Transformers pour la similarité sémantique."""
        self.sentence_model = None
        self.sentence_transformers_enabled = False
        
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                # Modèles par ordre de préférence (du plus léger au plus lourd)
                models_to_try = [
                    "all-MiniLM-L6-v2",           # Très léger et rapide
                    "distiluse-base-multilingual-cased-v2",  # Multilingue
                    "paraphrase-multilingual-MiniLM-L12-v2"  # Fallback
                ]
                
                for model_name in models_to_try:
                    try:
                        self.logger.info(f"📥 Tentative de chargement Sentence Transformer: {model_name}")
                        
                        # Configuration compatible avec PyTorch 2.2.2
                        import os
                        os.environ["SENTENCE_TRANSFORMERS_HOME"] = str(Path.home() / '.cache' / 'sentence_transformers')
                        
                        # Patch temporaire pour compatibilité PyTorch 2.2.2
                        if not hasattr(torch, 'get_default_device'):
                            def get_default_device():
                                return 'cpu'
                            torch.get_default_device = get_default_device
                        
                        self.sentence_model = SentenceTransformer(
                            model_name,
                            device='cpu',  # Forcer CPU pour éviter les problèmes de compatibilité
                            cache_folder=os.environ["SENTENCE_TRANSFORMERS_HOME"]
                        )
                        self.sentence_transformers_enabled = True
                        self.logger.info(f"✅ Sentence Transformer chargé: {model_name}")
                        break
                    except Exception as e:
                        self.logger.warning(f"⚠️ Échec {model_name}: {e}")
                        continue
                        
            except Exception as e:
                self.logger.warning(f"⚠️ Erreur Sentence Transformers: {e}")
    
    def _init_bert_model(self):
        """Initialise BERT avec fallback robuste."""
        self.bert_model = None
        self.bert_tokenizer = None
        self.bert_enabled = False
        
        if TRANSFORMERS_AVAILABLE:
            try:
                # Modèles BERT par ordre de préférence
                models_to_try = [
                    "distilbert-base-multilingual-cased",  # Plus léger que BERT complet
                    "bert-base-multilingual-cased",
                    "distilbert-base-uncased"  # Fallback anglais
                ]
                
                for model_name in models_to_try:
                    try:
                        self.logger.info(f"📥 Tentative BERT: {model_name}")
                        
                        # Patch temporaire pour compatibilité PyTorch 2.2.2
                        if not hasattr(torch, 'get_default_device'):
                            def get_default_device():
                                return 'cpu'
                            torch.get_default_device = get_default_device
                        
                        # Chargement avec gestion d'erreurs robuste
                        self.bert_tokenizer = AutoTokenizer.from_pretrained(
                            model_name,
                            use_fast=True,  # Utiliser les tokenizers rapides
                            clean_up_tokenization_spaces=True
                        )
                        
                        self.bert_model = AutoModel.from_pretrained(
                            model_name,
                            output_hidden_states=True,
                            output_attentions=False,
                            return_dict=True
                        )
                        
                        # Configuration pour l'inférence
                        self.bert_model.eval()
                        
                        # Test rapide pour vérifier la compatibilité (CPU seulement)
                        test_input = self.bert_tokenizer("test", return_tensors="pt", padding=True)
                        with torch.no_grad():
                            _ = self.bert_model(**test_input)
                        
                        self.bert_enabled = True
                        self.logger.info(f"✅ BERT chargé avec succès: {model_name}")
                        break
                        
                    except Exception as e:
                        self.logger.warning(f"⚠️ Échec BERT {model_name}: {e}")
                        continue
                        
            except Exception as e:
                self.logger.warning(f"⚠️ BERT non disponible: {e}")
        
        if not self.bert_enabled:
            self.logger.info("🔄 Fonctionnement sans BERT - modèles alternatifs activés")
    
    def _build_intent_patterns(self):
        """Construit les patterns d'intention optimisés."""
        self.intent_patterns = {
            CommandType.HELP: {
                "keywords": ["aide", "help", "assistance", "support", "comment faire", "tutorial"],
                "patterns": [
                    r"(?:aide|help)(?:-moi|me)?",
                    r"j'ai besoin d'aide",
                    r"comment (?:faire|je fais|utiliser)",
                    r"peux-tu m'aider",
                    r"tutorial",
                    r"guide"
                ],
                "semantic_examples": [
                    "aide-moi s'il te plaît",
                    "j'ai besoin d'assistance",
                    "comment utiliser cette fonction",
                    "peux-tu m'expliquer",
                    "guide d'utilisation"
                ]
            },
            
            CommandType.STATUS: {
                "keywords": ["statut", "status", "état", "santé", "ça va", "marche", "fonctionne"],
                "patterns": [
                    r"(?:statut|status|état)(?:\s+(?:du\s+)?système)?",
                    r"(?:ça\s+va|tout\s+va\s+bien)",
                    r"(?:ça\s+)?(?:marche|fonctionne)",
                    r"système\s+(?:ok|opérationnel)",
                    r"health\s+check"
                ],
                "semantic_examples": [
                    "comment ça va",
                    "état du système",
                    "tout fonctionne bien",
                    "santé du système",
                    "système opérationnel"
                ]
            },
            
            CommandType.ANALYZE: {
                "keywords": ["analyse", "analyze", "vérifie", "examine", "contrôle", "inspecte"],
                "patterns": [
                    r"(?:analyse|analyze|vérifie|examine|contrôle)\s+(?:ce|ça|ceci|this)",
                    r"regarde\s+(?:ce|ça|this)",
                    r"inspection\s+(?:de|of)",
                    r"évaluation\s+(?:de|of)",
                    r"check\s+this"
                ],
                "semantic_examples": [
                    "analyse ce code",
                    "vérifie cette fonction",
                    "regarde ça",
                    "examine ce fichier",
                    "contrôle qualité"
                ]
            },
            
            CommandType.SUGGEST: {
                "keywords": ["optimise", "améliore", "suggère", "recommande", "conseille"],
                "patterns": [
                    r"(?:optimise|améliore|optimize|improve)",
                    r"(?:suggère|recommande|conseille|propose)",
                    r"comment\s+(?:améliorer|optimiser)",
                    r"suggestions?\s+(?:pour|d'amélioration)",
                    r"recommendations?"
                ],
                "semantic_examples": [
                    "optimise ce code",
                    "améliore les performances",
                    "suggère des améliorations",
                    "recommandations pour optimiser",
                    "comment améliorer ça"
                ]
            },
            
            CommandType.EXPLAIN: {
                "keywords": ["explique", "explain", "qu'est-ce", "comment", "pourquoi", "clarification"],
                "patterns": [
                    r"(?:explique|explain)(?:-moi)?",
                    r"qu'est-ce\s+que",
                    r"comment\s+(?:ça\s+)?(?:marche|fonctionne)",
                    r"pourquoi",
                    r"clarification",
                    r"describe"
                ],
                "semantic_examples": [
                    "explique-moi comment ça marche",
                    "qu'est-ce que cette fonction fait",
                    "comment ça fonctionne",
                    "pourquoi ça ne marche pas",
                    "clarification sur ce point"
                ]
            },
            
            CommandType.TIME: {
                "keywords": ["heure", "time", "quelle heure", "what time"],
                "patterns": [
                    r"(?:quelle\s+)?heure(?:\s+est-il)?",
                    r"what\s+time",
                    r"il\s+est\s+quelle\s+heure",
                    r"heure\s+actuelle",
                    r"current\s+time"
                ],
                "semantic_examples": [
                    "quelle heure est-il",
                    "donne-moi l'heure",
                    "il est quelle heure",
                    "heure actuelle",
                    "what time is it"
                ]
            },
            
            CommandType.DATE: {
                "keywords": ["date", "jour", "quelle date", "what date", "calendrier"],
                "patterns": [
                    r"(?:quelle\s+)?date(?:\s+(?:est-ce|d'aujourd'hui))?",
                    r"what\s+date",
                    r"quel\s+jour",
                    r"calendrier",
                    r"today's\s+date"
                ],
                "semantic_examples": [
                    "quelle date sommes-nous",
                    "date d'aujourd'hui",
                    "quel jour on est",
                    "what date is it",
                    "current date"
                ]
            },
            
            CommandType.QUIT: {
                "keywords": ["merci", "arrête", "stop", "quitte", "au revoir", "bye", "fini"],
                "patterns": [
                    r"merci.*(?:tu peux|vous pouvez).*(?:arrêt|stop|quitt)",
                    r"(?:c'est bon|parfait|excellent).*merci",
                    r"merci.*(?:pour (?:ton )?aide|d'assistance)",
                    r"(?:au revoir|bye|goodbye)",
                    r"(?:arrête|stop|quitte).*(?:maintenant|stp|s'il te plaît)",
                    r"(?:bonne journée|bonne soirée)",
                    r"tu peux.*(?:t'arrêter|partir|te reposer)"
                ],
                "semantic_examples": [
                    "merci pour ton aide tu peux t'arrêter",
                    "c'est parfait merci",
                    "au revoir et merci",
                    "arrête-toi maintenant",
                    "bonne journée"
                ]
            },
            
            # Nouvelles catégories d'arrêt
            CommandType.DIRECT_QUIT: {
                "keywords": ["arrête", "stop", "quitte", "ferme", "exit", "quit", "arrête-toi", "arrêtes-toi"],
                "patterns": [
                    # Commandes d'arrêt directes en début de phrase
                    r"^(?:arrête|stop|quitte|ferme|exit|quit)(?:\s+(?:maintenant|stp|tout|ça))?$",
                    # Commandes d'arrêt directes en fin de phrase (après contexte)
                    r"(?:arrête|stop|quitte|ferme|exit|quit)(?:[-\s]toi)?(?:\s+maintenant)?$",
                    # Impératifs directs d'arrêt (patterns plus larges)
                    r"(?:arrête|stop)[-\s](?:toi|vous)(?:\s+maintenant)?",
                    # Commandes avec "maintenant" qui indiquent une urgence
                    r"(?:arrête|stop|quitte|ferme)(?:[-\s]toi)?\s+maintenant",
                    # Au revoir et formules de politesse directes
                    r"^(?:au revoir|bye|goodbye)$",
                    r"^(?:bonne journée|bonne soirée|à bientôt)$",
                    # Patterns pour détecter les commandes d'arrêt explicites même dans un contexte
                    r"\b(?:arrête[-\s]toi|arrêtes[-\s]toi|stop)\s+(?:maintenant|stp|tout de suite)",
                    r"(?:tu peux|vous pouvez)\s+(?:arrêter|t'arrêter|vous arrêter)(?:\s+maintenant)?",
                ],
                "semantic_examples": [
                    "arrête",
                    "stop",
                    "quit",
                    "arrête-toi maintenant",
                    "stop maintenant", 
                    "au revoir",
                    "bye",
                    "arrête-toi",
                    "tu peux t'arrêter maintenant"
                ]
            },
            
            CommandType.SOFT_QUIT: {
                "keywords": ["merci", "parfait", "excellent", "super", "génial", "très bien"],
                "patterns": [
                    r"merci.*(?:beaucoup|bien|pour.*(?:aide|tout|assistance))",
                    r"(?:c'est\s+)?(?:parfait|excellent|super|génial|très\s+bien).*merci",
                    r"merci.*(?:tu\s+peux|vous\s+pouvez).*(?:arrêter|partir|te\s+reposer)",
                    r"(?:ça\s+suffit|c'est\s+tout|j'ai\s+fini).*merci"
                ],
                "semantic_examples": [
                    "merci beaucoup pour ton aide",
                    "c'est parfait merci",
                    "super merci pour tout",
                    "très bien merci tu peux t'arrêter",
                    "génial merci pour cette assistance"
                ]
            }
        }
    
    def extract_intent(self, text: str, context: Dict[str, Any] = None) -> IntentResult:
        """
        Extrait l'intention du texte en utilisant l'approche hybride intelligente.
        
        Nouvelle approche:
        1. Laisse les modèles NLP décider librement (pas d'exclusions strictes)
        2. Détecte plusieurs commandes dans une phrase
        3. Utilise la méthode de base uniquement en cas d'indisponibilité/indécision
        4. Distingue DIRECT_QUIT vs SOFT_QUIT
        """
        start_time = time.time()
        context = context or {}
        
        normalized_text = self._normalize_text(text)
        
        # Analyser avec tous les modèles disponibles pour détecter plusieurs intentions
        all_detections = []
        
        # MÉTHODE 1: Sentence Transformers (priorité pour la précision sémantique)
        if self.sentence_transformers_enabled:
            st_results = self._analyze_with_sentence_transformers_multi(normalized_text, context)
            if st_results:
                all_detections.extend(st_results)
        
        # MÉTHODE 2: spaCy NLP (bon pour la structure grammaticale)
        if self.spacy_enabled:
            spacy_results = self._analyze_with_spacy_multi(normalized_text, context)
            if spacy_results:
                all_detections.extend(spacy_results)
        
        # MÉTHODE 3: BERT (si disponible, excellente compréhension contextuelle)
        if self.bert_enabled:
            bert_results = self._analyze_with_bert_multi(normalized_text, context)
            if bert_results:
                all_detections.extend(bert_results)
        
        # MÉTHODE 4: Patterns regex (fallback mais toujours utile)
        pattern_results = self._analyze_with_patterns_multi(normalized_text, context)
        if pattern_results:
            all_detections.extend(pattern_results)
        
        # MÉTHODE 5: Classification par mots-clés (dernier recours)
        if not all_detections:
            keyword_results = self._analyze_with_keywords_multi(normalized_text, context)
            if keyword_results:
                all_detections.extend(keyword_results)
        
        # Analyser et consolider les détections multiples
        final_result = self._consolidate_multi_detections(all_detections, normalized_text, context)
        
        if final_result:
            method_used = "multi_model_analysis"
            if len(all_detections) > 1:
                method_used = "multi_command_detected"
            return self._create_result(final_result, method_used, start_time)
        
        # Fallback final vers l'agent IA central
        return self._create_result(
            (CommandType.PROMPT, 0.5, {"full_text": text, "unrecognized": True}),
            "fallback_to_ai", start_time
        )
    
    def _normalize_text(self, text: str) -> str:
        """Normalise le texte pour l'analyse."""
        # Conversion basique
        normalized = text.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Corrections phonétiques
        phonetic_corrections = {
            "pire": "peer", "père": "peer", "pair": "peer", "per": "peer",
            "c l i": "cli", "t u i": "tui", "s u i": "sui", "a p i": "api"
        }
        
        for incorrect, correct in phonetic_corrections.items():
            normalized = normalized.replace(incorrect, correct)
        
        return normalized
    
    def _consolidate_multi_detections(self, all_detections: List[Tuple[CommandType, float, Dict[str, Any]]], 
                                     text: str, context: Dict[str, Any]) -> Optional[Tuple[CommandType, float, Dict[str, Any]]]:
        """
        Consolide les multiples détections en une décision finale intelligente.
        
        RÈGLES MODIFIÉES POUR PRIVILÉGIER LES COMMANDES D'ARRÊT EXPLICITES:
        1. DIRECT_QUIT détecté = TOUJOURS DIRECT_QUIT (sans délai ni confirmation)
        2. SOFT_QUIT seulement = demander confirmation
        3. Position et contexte influencent seulement pour les cas ambigus
        """
        if not all_detections:
            return None
        
        # Grouper par type de commande
        command_groups = defaultdict(list)
        for cmd_type, confidence, params in all_detections:
            command_groups[cmd_type].append((confidence, params))
        
        # Rechercher les commandes d'arrêt
        direct_quit = command_groups.get(CommandType.DIRECT_QUIT)
        soft_quit = command_groups.get(CommandType.SOFT_QUIT)
        other_commands = {k: v for k, v in command_groups.items() 
                         if k not in [CommandType.DIRECT_QUIT, CommandType.SOFT_QUIT, CommandType.QUIT]}
        
        # Analyser la position des commandes d'arrêt dans le texte
        quit_position = self._analyze_quit_position(text, direct_quit, soft_quit)
        
        # RÈGLE 1 PRIORITAIRE: DIRECT_QUIT détecté -> TOUJOURS EXÉCUTION IMMÉDIATE
        # Cette règle a la priorité absolue car les commandes explicites doivent toujours être respectées
        if direct_quit:
            best_confidence, best_params = max(direct_quit, key=lambda x: x[0])
            return CommandType.DIRECT_QUIT, best_confidence, {
                **best_params,
                "immediate_quit": True,
                "confirmation_needed": False,
                "reason": "explicit_quit_command_always_respected",
                "user_intent_clear": True,
                "position": quit_position,
                "has_other_commands": bool(other_commands)
            }
        
        # RÈGLE 2: SOFT_QUIT détecté -> DEMANDER CONFIRMATION
        if soft_quit:
            best_confidence, best_params = max(soft_quit, key=lambda x: x[0])
            confirmation_msg = self._generate_intelligent_confirmation(
                text, "soft_quit_detected", soft_quit, other_commands, context
            )
            return CommandType.SOFT_QUIT, best_confidence, {
                **best_params,
                "confirmation_needed": True,
                "precision_needed": True,
                "confirmation_message": confirmation_msg,
                "reason": "soft_quit_inherently_uncertain",
                "phrase_part_questioned": self._extract_questioned_part(text, quit_position)
            }
        
        # RÈGLE 3: Plusieurs commandes sans quit -> séquence normale
        if len(other_commands) > 0:
            return self._create_command_sequence(text, None, other_commands, context)
        
        return None
    
    def _analyze_quit_position(self, text: str, direct_quit: List, soft_quit: List) -> str:
        """Analyse la position des commandes d'arrêt dans le texte."""
        if not (direct_quit or soft_quit):
            return "none"
        
        words = text.lower().split()
        total_words = len(words)
        
        # Mots-clés d'arrêt à rechercher
        quit_keywords = ["arrête", "stop", "quitte", "ferme", "exit", "quit", "bye", "au revoir"]
        
        # Trouver la position du dernier mot-clé d'arrêt
        last_quit_position = -1
        for i, word in enumerate(words):
            if any(keyword in word for keyword in quit_keywords):
                last_quit_position = i
        
        if last_quit_position == -1:
            return "none"
        
        # Considérer comme "fin" si dans les 20% derniers mots
        if last_quit_position >= total_words * 0.8:
            return "end"
        else:
            return "middle"

    def _extract_questioned_part(self, text: str, quit_position: str) -> str:
        """
        Extrait la partie de la phrase qui pose question selon la position du quit.
        
        Utile pour clarifier ce que l'utilisateur entend par cette partie ambiguë.
        """
        words = text.split()
        quit_keywords = ["arrête", "stop", "quitte", "ferme", "exit", "quit", "bye", "au revoir", "merci"]
        
        # Trouver la position du mot d'arrêt
        quit_word_index = -1
        quit_word = ""
        for i, word in enumerate(words):
            if any(keyword in word.lower() for keyword in quit_keywords):
                quit_word_index = i
                quit_word = word
                break
        
        if quit_word_index == -1:
            return text  # Pas de mot d'arrêt trouvé, retourner tout le texte
        
        if quit_position == "middle":
            # Si quit au milieu, la partie questionnée inclut le contexte autour
            start_context = max(0, quit_word_index - 2)
            end_context = min(len(words), quit_word_index + 3)
            questioned_part = " ".join(words[start_context:end_context])
            return f"...{questioned_part}..."
        
        elif quit_position == "end":
            # Si quit à la fin, la partie questionnée est principalement le mot d'arrêt
            return quit_word
        
        else:
            return text

    def _build_command_sequence(self, direct_quit: List, other_commands: Dict) -> List[Dict]:
        """Construit une séquence de commandes à partir des détections multiples."""
        sequence = []
        
        # Ajouter les autres commandes triées par confiance
        for cmd_type, detections in other_commands.items():
            best_conf, best_params = max(detections, key=lambda x: x[0])
            sequence.append({
                "command": cmd_type,
                "confidence": best_conf,
                "params": best_params,
                "context_from_original": True
            })
        
        # Ajouter DIRECT_QUIT à la fin
        if direct_quit:
            best_conf, best_params = max(direct_quit, key=lambda x: x[0])
            sequence.append({
                "command": CommandType.DIRECT_QUIT,
                "confidence": best_conf,
                "params": best_params,
                "context_from_original": True
            })
        
        return sequence

    def _generate_intelligent_confirmation(self, original_text: str, scenario: str, 
                                         quit_commands: List, other_commands: Dict, 
                                         context: Dict[str, Any]) -> str:
        """Génère une demande de confirmation intelligente basée sur le contexte."""
        
        # Extraire des éléments contextuels du texte original
        context_elements = self._extract_context_elements(original_text)
        
        # Identifier la partie de phrase remise en question
        quit_position = self._analyze_quit_position(original_text, quit_commands, [])
        questioned_part = self._extract_questioned_part(original_text, quit_position)
        
        if scenario == "direct_quit_middle":
            return f"J'ai entendu '{original_text}'. Je détecte une demande d'arrêt au milieu de votre phrase. " \
                   f"Que voulez-vous dire exactement par '{questioned_part}' ? " \
                   f"Souhaitez-vous que je m'arrête maintenant ou vouliez-vous dire autre chose ?"
        
        elif scenario == "soft_quit_detected":
            if "merci" in original_text.lower():
                return f"Vous avez dit '{original_text}'. Je perçois de la gratitude avec '{questioned_part}'. " \
                       f"Souhaitez-vous que je continue à vous assister ou préférez-vous que je m'arrête ?"
            else:
                return f"D'après '{original_text}', que voulez-vous dire par '{questioned_part}' ? " \
                       f"Dois-je comprendre que vous souhaitez que je m'arrête ?"
        
        elif scenario == "multiple_with_direct_quit":
            cmd_names = [cmd.value for cmd in other_commands.keys()]
            return f"Dans '{original_text}', je détecte plusieurs intentions : {', '.join(cmd_names)} " \
                   f"et aussi '{questioned_part}'. " \
                   f"Voulez-vous que j'exécute ces commandes puis que je m'arrête, ou avez-vous une autre intention ?"
        
        else:
            return f"Pouvez-vous clarifier ce que vous entendez par '{questioned_part}' dans : '{original_text}' ?"
    
    def _extract_context_elements(self, text: str) -> Dict[str, Any]:
        """Extrait des éléments de contexte du texte original."""
        elements = {
            "has_gratitude": any(word in text.lower() for word in ["merci", "thank", "thanks"]),
            "has_politeness": any(word in text.lower() for word in ["s'il vous plaît", "please", "stp"]),
            "has_urgency": any(word in text.lower() for word in ["maintenant", "now", "immédiatement"]),
            "has_uncertainty": any(word in text.lower() for word in ["peut-être", "maybe", "je pense"]),
            "word_count": len(text.split()),
            "has_question": "?" in text
        }
        return elements
    
    def _create_command_sequence(self, text: str, soft_quit: List, other_commands: Dict, 
                               context: Dict[str, Any]) -> Tuple[CommandType, float, Dict[str, Any]]:
        """Crée une séquence de commandes avec contexte approprié."""
        
        # Trier les commandes par confiance
        sorted_commands = []
        for cmd_type, detections in other_commands.items():
            best_conf, best_params = max(detections, key=lambda x: x[0])
            sorted_commands.append((cmd_type, best_conf, best_params))
        
        sorted_commands.sort(key=lambda x: x[1], reverse=True)
        
        # Commande principale = celle avec la plus haute confiance
        main_cmd_type, main_confidence, main_params = sorted_commands[0]
        
        # Construire la séquence
        command_sequence = [
            {
                "command": cmd_type,
                "confidence": confidence,
                "params": params,
                "context_from_original": text
            }
            for cmd_type, confidence, params in sorted_commands
        ]
        
        # Ajouter SOFT_QUIT à la fin si présent
        if soft_quit:
            best_soft_conf, best_soft_params = max(soft_quit, key=lambda x: x[0])
            command_sequence.append({
                "command": CommandType.SOFT_QUIT,
                "confidence": best_soft_conf,
                "params": best_soft_params,
                "context_from_original": text
            })
        
        # Message contextuel pour la séquence
        sequence_description = f"Séquence détectée dans '{text}': " + \
                             " → ".join([f"{cmd['command'].value}" for cmd in command_sequence])
        
        # Si SOFT_QUIT est présent avec d'autres commandes -> demander confirmation
        if soft_quit:
            confirmation_msg = self._generate_intelligent_confirmation(
                text, "multiple_with_soft_quit", soft_quit, other_commands, context
            )
            return main_cmd_type, main_confidence, {
                **main_params,
                "is_command_sequence": True,
                "command_sequence": command_sequence,
                "sequence_description": sequence_description,
                "original_context": text,
                "confirmation_needed": True,
                "confirmation_message": confirmation_msg,
                "reason": "multiple_commands_with_soft_quit"
            }
        
        # Séquence sans SOFT_QUIT -> exécution automatique
        return main_cmd_type, main_confidence, {
            **main_params,
            "is_command_sequence": True,
            "command_sequence": command_sequence,
            "sequence_description": sequence_description,
            "original_context": text,
            "confirmation_needed": False,
            "reason": "multiple_commands_detected_as_sequence"
        }

    def _analyze_with_sentence_transformers_multi(self, text: str, context: Dict[str, Any]) -> List[Tuple[CommandType, float, Dict[str, Any]]]:
        """Analyse avec Sentence Transformers pour détecter plusieurs intentions."""
        try:
            if not self.sentence_model:
                return []
            
            # Générer l'embedding du texte
            text_embedding = self.sentence_model.encode([text])[0]
            
            detections = []
            
            # Comparer avec les exemples sémantiques de TOUS les types de commandes
            for command_type, patterns in self.intent_patterns.items():
                examples = patterns.get("semantic_examples", [])
                
                if examples:
                    # Générer les embeddings des exemples (avec cache)
                    example_embeddings = []
                    for example in examples:
                        if example in self.embedding_cache:
                            example_embeddings.append(self.embedding_cache[example])
                        else:
                            emb = self.sentence_model.encode([example])[0]
                            if len(self.embedding_cache) < self.config["max_cache_size"]:
                                self.embedding_cache[example] = emb
                            example_embeddings.append(emb)
                    
                    # Calculer la similarité maximale
                    similarities = [
                        self._cosine_similarity(text_embedding, example_emb)
                        for example_emb in example_embeddings
                    ]
                    
                    max_similarity = max(similarities) if similarities else 0
                    
                    # Seuil adaptatif selon le type de commande
                    threshold = 0.6  # Seuil de base plus permissif
                    if command_type in [CommandType.DIRECT_QUIT, CommandType.SOFT_QUIT]:
                        threshold = 0.55  # Plus sensible pour les arrêts
                    elif command_type in [CommandType.HELP, CommandType.ANALYZE]:
                        threshold = 0.65  # Plus strict pour les commandes importantes
                    
                    if max_similarity >= threshold:
                        best_example = examples[similarities.index(max_similarity)]
                        detections.append((command_type, max_similarity, {
                            "best_example": best_example,
                            "semantic_score": max_similarity,
                            "method": "sentence_transformers"
                        }))
            
            return detections
            
        except Exception as e:
            self.logger.warning(f"⚠️ Erreur Sentence Transformers: {e}")
            return []
    
    def _analyze_with_spacy_multi(self, text: str, context: Dict[str, Any]) -> List[Tuple[CommandType, float, Dict[str, Any]]]:
        """Analyse avec spaCy pour détecter plusieurs intentions."""
        try:
            if not self.spacy_model:
                return []
            
            doc = self.spacy_model(text)
            detections = []
            
            # Analyse des entités nommées et POS tags
            entities = [(ent.text, ent.label_) for ent in doc.ents]
            pos_tags = [(token.text, token.pos_) for token in doc]
            
            # Analyse des mots-clés pour chaque type de commande
            for command_type, patterns in self.intent_patterns.items():
                keywords = patterns.get("keywords", [])
                confidence = 0.0
                found_keywords = []
                
                # Compter les mots-clés trouvés
                for keyword in keywords:
                    if keyword in text.lower():
                        found_keywords.append(keyword)
                        confidence += 0.3
                
                # Analyser la structure grammaticale
                verb_count = sum(1 for _, pos in pos_tags if pos == "VERB")
                noun_count = sum(1 for _, pos in pos_tags if pos == "NOUN")
                
                # Bonus basé sur le type de commande et la structure
                if command_type == CommandType.DIRECT_QUIT and any(token.pos_ == "VERB" for token in doc):
                    confidence += 0.2
                elif command_type == CommandType.SOFT_QUIT and any(token.text.lower() in ["merci", "parfait"] for token in doc):
                    confidence += 0.3
                elif command_type == CommandType.HELP and "?" in text:
                    confidence += 0.2
                elif command_type == CommandType.ANALYZE and noun_count > 0:
                    confidence += 0.2
                
                # Normaliser la confiance
                confidence = min(confidence, 1.0)
                
                if confidence >= 0.5 and found_keywords:
                    detections.append((command_type, confidence, {
                        "found_keywords": found_keywords,
                        "entities": entities,
                        "pos_structure": {"verbs": verb_count, "nouns": noun_count},
                        "method": "spacy_nlp"
                    }))
            
            return detections
            
        except Exception as e:
            self.logger.warning(f"⚠️ Erreur spaCy: {e}")
            return []
    
    def _analyze_with_bert_multi(self, text: str, context: Dict[str, Any]) -> List[Tuple[CommandType, float, Dict[str, Any]]]:
        """Analyse avec BERT pour détecter plusieurs intentions."""
        try:
            if not self.bert_enabled or not hasattr(self, 'bert_model'):
                return []
            
            detections = []
            
            # Pour chaque type de commande, calculer la probabilité avec BERT
            for command_type in CommandType:
                # Créer un prompt de classification pour BERT
                prompt = f"L'intention de '{text}' est-elle '{command_type.value}'?"
                
                # Utiliser BERT pour la classification (implémentation simplifiée)
                # Dans une vraie implémentation, on utiliserait un modèle fine-tuné
                inputs = self.bert_tokenizer(prompt, return_tensors="pt", max_length=512, truncation=True)
                outputs = self.bert_model(**inputs)
                
                # Extraire une probabilité (méthode simplifiée)
                # En réalité, il faudrait un modèle de classification fine-tuné
                logits = outputs.last_hidden_state.mean(dim=1).mean(dim=1)  # Moyenne sur toutes les dimensions
                confidence = torch.sigmoid(logits).item()
                
                if confidence >= 0.6:
                    detections.append((command_type, confidence, {
                        "bert_confidence": confidence,
                        "method": "bert_classification"
                    }))
            
            return detections
            
        except Exception as e:
            self.logger.warning(f"⚠️ Erreur BERT: {e}")
            return []
    
    def _analyze_with_patterns_multi(self, text: str, context: Dict[str, Any]) -> List[Tuple[CommandType, float, Dict[str, Any]]]:
        """Analyse avec patterns regex pour détecter plusieurs intentions."""
        detections = []
        
        for command_type, patterns_config in self.intent_patterns.items():
            patterns = patterns_config.get("patterns", [])
            
            for pattern in patterns:
                try:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        # Calculer la confiance basée sur la qualité du match
                        match_length = len(match.group(0))
                        text_length = len(text.strip())
                        coverage = match_length / text_length if text_length > 0 else 0
                        
                        # Confiance basée sur la couverture et le type de pattern
                        confidence = 0.7 + (coverage * 0.3)
                        confidence = min(confidence, 0.95)  # Cap à 95%
                        
                        detections.append((command_type, confidence, {
                            "matched_pattern": pattern,
                            "matched_text": match.group(0),
                            "coverage": coverage,
                            "method": "regex_pattern"
                        }))
                        break  # Un seul match par type de commande
                        
                except re.error as e:
                    self.logger.warning(f"⚠️ Erreur pattern regex '{pattern}': {e}")
        
        return detections
    
    def _analyze_with_keywords_multi(self, text: str, context: Dict[str, Any]) -> List[Tuple[CommandType, float, Dict[str, Any]]]:
        """Analyse basée sur les mots-clés pour détecter plusieurs intentions (fallback)."""
        detections = []
        words = text.lower().split()
        
        for command_type, patterns_config in self.intent_patterns.items():
            keywords = patterns_config.get("keywords", [])
            
            found_keywords = []
            total_score = 0
            
            for keyword in keywords:
                if keyword in text.lower():
                    found_keywords.append(keyword)
                    # Bonus si le mot-clé est en début ou fin de phrase
                    if text.lower().startswith(keyword) or text.lower().endswith(keyword):
                        total_score += 0.4
                    else:
                        total_score += 0.3
            
            if found_keywords:
                # Calculer la confiance basée sur le nombre et la qualité des matches
                confidence = min(total_score, 0.8)  # Cap à 80% pour les mots-clés
                
                detections.append((command_type, confidence, {
                    "found_keywords": found_keywords,
                    "keyword_score": total_score,
                    "method": "keyword_matching"
                }))
        
        return detections

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calcule la similarité cosinus entre deux vecteurs."""
        try:
            # Normaliser les vecteurs
            norm_vec1 = vec1 / np.linalg.norm(vec1)
            norm_vec2 = vec2 / np.linalg.norm(vec2)
            
            # Calculer la similarité cosinus
            similarity = np.dot(norm_vec1, norm_vec2)
            return float(similarity)
        except:
            return 0.0

    def _create_result(self, detection_result: Any, method_used: str, start_time: float) -> 'IntentResult':
        """Crée un objet IntentResult à partir du résultat de détection."""
        processing_time = time.time() - start_time
        
        if detection_result is None:
            return IntentResult(
                command_type=CommandType.PROMPT,
                confidence=0.0,
                method_used="fallback",
                parameters={},
                processing_time=processing_time,
                fallback_used=True
            )
        
        # Si c'est déjà un IntentResult, le retourner directement
        if hasattr(detection_result, 'command_type'):
            return detection_result
        
        # Si c'est un tuple (command, confidence, metadata)
        if isinstance(detection_result, tuple) and len(detection_result) >= 2:
            command_type, confidence = detection_result[:2]
            metadata = detection_result[2] if len(detection_result) > 2 else {}
            
            return IntentResult(
                command_type=command_type,
                confidence=confidence,
                method_used=method_used,
                parameters=metadata,
                processing_time=processing_time,
                fallback_used=False
            )
        
        # Cas de fallback
        return IntentResult(
            command_type=CommandType.PROMPT,
            confidence=0.0,
            method_used="fallback",
            parameters={},
            processing_time=processing_time,
            fallback_used=True
        )

    def get_performance_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de performance."""
        if not self.processing_times:
            return {"status": "no_data"}
        
        avg_time = sum(self.processing_times) / len(self.processing_times)
        max_time = max(self.processing_times)
        min_time = min(self.processing_times)
        
        method_stats = {}
        for method, confidences in self.success_rates.items():
            if confidences:
                method_stats[method] = {
                    "avg_confidence": sum(confidences) / len(confidences),
                    "calls": len(confidences)
                }
        
        return {
            "avg_processing_time": avg_time,
            "max_processing_time": max_time,
            "min_processing_time": min_time,
            "total_processed": len(self.processing_times),
            "method_statistics": method_stats,
            "models_available": {
                "spacy": self.spacy_enabled,
                "sentence_transformers": self.sentence_transformers_enabled,
                "bert": self.bert_enabled
            }
        }
    
    def update_config(self, new_config: Dict[str, Any]):
        """Met à jour la configuration."""
        self.config.update(new_config)
