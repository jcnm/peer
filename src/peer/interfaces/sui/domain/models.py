"""
Modèles de domaine pour l'interface SUI.

Ce module définit les entités et value objects du domaine SUI,
conformément aux principes du Domain-Driven Design (DDD).
"""

import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
from enum import Enum, auto


class InterfaceAction(Enum):
    """Actions génériques que l'interface peut effectuer."""
    QUIT = auto()      # Terminer la session et s'arrêter
    INFORM = auto()    # Informer l'utilisateur d'un résultat
    ASK = auto()       # Demander plus d'informations à l'utilisateur
    PROGRESS = auto()  # Informer l'utilisateur de la progression
    WAIT = auto()      # Attendre une action externe
    RETRY = auto()     # Réessayer une opération
    NONE = auto()      # Aucune action spécifique


@dataclass
class SpeechRecognitionResult:
    """Value Object: Résultat enrichi de reconnaissance vocale."""
    text: str
    confidence: float = 0.0
    language: str = "fr"
    processing_time: float = 0.0
    audio_quality: float = 0.0
    is_command: bool = False
    intent_confidence: float = 0.0
    engine_used: str = "unknown"


@dataclass 
class VoiceActivityMetrics:
    """Value Object: Métriques d'activité vocale pour analyse intelligente."""
    speech_detected: bool = False
    energy_level: float = 0.0
    zero_crossing_rate: float = 0.0
    spectral_centroid: float = 0.0
    background_noise_level: float = 0.0
    speech_probability: float = 0.0


@dataclass
class ContextualInfo:
    """Value Object: Informations contextuelles pour l'assistance intelligente."""
    current_time: datetime.datetime = field(default_factory=datetime.datetime.now)
    session_duration: float = 0.0
    commands_count: int = 0
    last_commands: List[str] = field(default_factory=list)
    user_response_pattern: Dict[str, Any] = field(default_factory=dict)
    system_performance: Dict[str, float] = field(default_factory=dict)
    recent_errors: List[str] = field(default_factory=list)
    working_directory: str = ""
    active_files: List[str] = field(default_factory=list)


@dataclass
class SUIResponse:
    """Value Object: Réponse formatée de l'interface SUI."""
    message: str = ""
    vocal_message: str = ""
    should_vocalize: bool = False
    interface_action: InterfaceAction = InterfaceAction.NONE
    action_details: Dict[str, Any] = field(default_factory=dict)
    context_update: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: str = ""
