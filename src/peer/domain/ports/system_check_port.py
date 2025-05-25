"""
Module contenant les ports pour les services de vérification du système.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

from peer.domain.entities.message_entities import SystemStatus


class SystemCheckPort(ABC):
    """
    Interface pour les adaptateurs de vérification du système.
    
    Cette interface définit les méthodes que doivent implémenter
    les adaptateurs de vérification pour contrôler l'état du système.
    """
    
    @abstractmethod
    def check_system_status(self) -> SystemStatus:
        """
        Vérifie l'état global du système.
        
        Returns:
            Un objet SystemStatus contenant l'état du système
        """
        pass
    
    @abstractmethod
    def check_component(self, component_name: str) -> Dict[str, Any]:
        """
        Vérifie l'état d'un composant spécifique.
        
        Args:
            component_name: Nom du composant à vérifier
            
        Returns:
            Dictionnaire contenant les informations sur l'état du composant
        """
        pass
