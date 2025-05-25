"""
Module contenant les entités du domaine pour les messages et notifications.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


class MessageType(Enum):
    """Types de messages supportés par le système."""
    WELCOME = auto()
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    STATUS = auto()


@dataclass
class Message:
    """
    Représente un message dans le système.
    
    Attributes:
        content: Contenu textuel du message
        type: Type de message
        should_vocalize: Indique si le message doit être vocalisé
        id: Identifiant optionnel du message
    """
    content: str
    # sender: str = "System"
    # receiver: str = "User"
    type: MessageType
    should_vocalize: bool = False
    id: Optional[str] = None


@dataclass
class SystemStatus:
    """
    Représente l'état du système.
    
    Attributes:
        is_online: Indique si le système est en ligne
        components_status: Dictionnaire des statuts des composants
        message: Message décrivant l'état global
    """
    is_online: bool
    components_status: dict
    message: str
