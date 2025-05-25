"""
Module contenant les ports pour les services de reconnaissance vocale (STT).
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List


class STTPort(ABC):
    """
    Interface pour les adaptateurs de reconnaissance vocale.
    
    Cette interface définit les méthodes que doivent implémenter
    les adaptateurs de reconnaissance vocale pour convertir la parole en texte.
    """
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialise le service de reconnaissance vocale.
        
        Returns:
            True si l'initialisation a réussi, False sinon
        """
        pass
    
    @abstractmethod
    def start_listening(self) -> bool:
        """
        Démarre l'écoute active.
        
        Returns:
            True si le démarrage a réussi, False sinon
        """
        pass
    
    @abstractmethod
    def stop_listening(self) -> bool:
        """
        Arrête l'écoute active.
        
        Returns:
            True si l'arrêt a réussi, False sinon
        """
        pass
    
    @abstractmethod
    def is_listening(self) -> bool:
        """
        Vérifie si le service est en train d'écouter.
        
        Returns:
            True si le service est en train d'écouter, False sinon
        """
        pass
    
    @abstractmethod
    def transcribe_audio(self, audio_data: bytes) -> str:
        """
        Transcrit des données audio en texte.
        
        Args:
            audio_data: Données audio à transcrire
            
        Returns:
            Texte transcrit
        """
        pass
    
    @abstractmethod
    def get_available_engines(self) -> Dict[str, bool]:
        """
        Récupère la liste des moteurs de reconnaissance vocale disponibles.
        
        Returns:
            Dictionnaire des moteurs disponibles avec leur état
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Vérifie si le service de reconnaissance vocale est disponible.
        
        Returns:
            True si le service est disponible, False sinon
        """
        pass
    
    @abstractmethod
    def shutdown(self) -> bool:
        """
        Arrête proprement le service de reconnaissance vocale.
        
        Returns:
            True si l'arrêt a réussi, False sinon
        """
        pass
