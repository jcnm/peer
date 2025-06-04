"""
Modèles de domaine pour le module NLU (Natural Language Understanding).

Ce module définit les entités et value objects du domaine NLU,
conformément aux principes du Domain-Driven Design (DDD).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum


@dataclass
class IntentResult:
    """Value Object: Résultat de l'analyse d'intention."""
    command_type: str  # Utilise une chaîne pour éviter la dépendance directe à CommandType
    confidence: float
    method_used: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    processing_time: float = 0.0
    fallback_used: bool = False


class NLUMethod(Enum):
    """Méthodes d'analyse utilisées par le moteur NLU."""
    SPACY = "spacy"
    SENTENCE_TRANSFORMER = "sentence_transformer"
    BERT = "bert"
    KEYWORD = "keyword"
    PATTERN = "pattern"
    CONTEXTUAL = "contextual"
    FALLBACK = "fallback"
    MULTI_MODEL = "multi_model"


@dataclass
class NLUModelStatus:
    """Value Object: État des modèles NLU."""
    name: str
    available: bool
    loaded: bool
    version: Optional[str] = None
    error: Optional[str] = None


@dataclass
class NLUPerformanceStats:
    """Value Object: Statistiques de performance du moteur NLU."""
    models_available: Dict[str, bool] = field(default_factory=dict)
    average_processing_time: float = 0.0
    success_rate: float = 0.0
    fallback_rate: float = 0.0
    method_usage_counts: Dict[str, int] = field(default_factory=dict)
    cache_hit_rate: float = 0.0


@dataclass
class IntentPattern:
    """Value Object: Pattern d'intention pour la reconnaissance."""
    keywords: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
    semantic_examples: List[str] = field(default_factory=list)


@dataclass
class NLUContext:
    """Value Object: Contexte pour l'analyse NLU."""
    recent_commands: List[str] = field(default_factory=list)
    session_data: Dict[str, Any] = field(default_factory=dict)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    environment_info: Dict[str, Any] = field(default_factory=dict)
