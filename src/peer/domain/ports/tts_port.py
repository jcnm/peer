"""
Module contenant les ports pour les services de synthèse vocale (TTS).
"""

from abc import ABC, abstractmethod
from typing import Optional


class TTSPort(ABC):
    """
    Interface pour les adaptateurs de synthèse vocale.
    
    Cette interface définit les méthodes que doivent implémenter
    les adaptateurs de synthèse vocale pour convertir du texte en parole.
    """
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialise le service de synthèse vocale.
        
        Returns:
            True si l'initialisation a réussi, False sinon
        """
        pass
    
    @abstractmethod
    def speak(self, text: str) -> bool:
        """
        Convertit le texte en parole et le lit à haute voix.
        
        Args:
            text: Texte à convertir en parole
            
        Returns:
            True si la conversion et la lecture ont réussi, False sinon
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Vérifie si le service de synthèse vocale est disponible.
        
        Returns:
            True si le service est disponible, False sinon
        """
        pass
    
    @abstractmethod
    def shutdown(self) -> bool:
        """
        Arrête proprement le service de synthèse vocale.
        
        Returns:
            True si l'arrêt a réussi, False sinon
        """
        pass
