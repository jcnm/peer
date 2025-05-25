"""
Module contenant les services du domaine pour la gestion des messages.
"""

from typing import List, Optional

from peer.domain.entities.message_entities import Message, MessageType
from peer.domain.ports.tts_port import TTSPort


class MessageService:
    """
    Service du domaine pour la gestion des messages.
    
    Ce service centralise la logique de gestion des messages,
    y compris la génération du message de bienvenue et la vocalisation.
    """
    
    def __init__(self, tts_service: Optional[TTSPort] = None):
        """
        Initialise le service de messages.
        
        Args:
            tts_service: Service de synthèse vocale (optionnel)
        """
        self.tts_service = tts_service
        self.messages: List[Message] = []
    
    def get_welcome_message(self) -> Message:
        """
        Génère le message de bienvenue.
        
        Returns:
            Message de bienvenue
        """
        return Message(
            content="Bienvenue, copilot.",
            type=MessageType.WELCOME,
            should_vocalize=True,
            id="welcome_message"
        )
    
    def vocalize_message(self, message: Message) -> bool:
        """
        Vocalise un message si le service TTS est disponible.
        
        Args:
            message: Message à vocaliser
            
        Returns:
            True si la vocalisation a réussi, False sinon
        """
        if not message.should_vocalize or self.tts_service is None:
            return False
        
        return self.tts_service.speak(message.content)
    
    def add_message(self, message: Message) -> None:
        """
        Ajoute un message à l'historique et le vocalise si nécessaire.
        
        Args:
            message: Message à ajouter
        """
        self.messages.append(message)
        if message.should_vocalize:
            self.vocalize_message(message)
    
    def get_messages(self) -> List[Message]:
        """
        Récupère tous les messages de l'historique.
        
        Returns:
            Liste des messages
        """
        return self.messages
