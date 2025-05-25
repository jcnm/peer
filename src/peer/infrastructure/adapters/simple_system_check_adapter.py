"""
Module contenant l'adaptateur de vérification du système.
"""

import platform
import socket
import logging
from typing import Dict, Any

from peer.domain.entities.message_entities import SystemStatus
from peer.domain.ports.system_check_port import SystemCheckPort

logger = logging.getLogger(__name__)


class SimpleSystemCheckAdapter(SystemCheckPort):
    """
    Adaptateur simple pour la vérification de l'état du système.
    
    Cette implémentation vérifie l'état de base du système
    comme la connectivité réseau et les informations système.
    """
    
    def check_system_status(self) -> SystemStatus:
        """
        Vérifie l'état global du système.
        
        Returns:
            Un objet SystemStatus contenant l'état du système
        """
        components = {
            "network": self._check_network(),
            "system": self._check_system_info()
        }
        
        # Vérifier si tous les composants sont en ligne
        all_online = all(component.get("status", False) for component in components.values())
        
        message = "Tous les systèmes sont opérationnels." if all_online else "Certains systèmes ne sont pas opérationnels."
        
        return SystemStatus(
            is_online=all_online,
            components_status=components,
            message=message
        )
    
    def check_component(self, component_name: str) -> Dict[str, Any]:
        """
        Vérifie l'état d'un composant spécifique.
        
        Args:
            component_name: Nom du composant à vérifier
            
        Returns:
            Dictionnaire contenant les informations sur l'état du composant
        """
        if component_name == "network":
            return self._check_network()
        elif component_name == "system":
            return self._check_system_info()
        else:
            return {"status": False, "message": f"Composant inconnu: {component_name}"}
    
    def _check_network(self) -> Dict[str, Any]:
        """
        Vérifie la connectivité réseau.
        
        Returns:
            Dictionnaire contenant les informations sur l'état du réseau
        """
        try:
            # Tenter de résoudre google.com pour vérifier la connectivité
            socket.gethostbyname("google.com")
            return {
                "status": True,
                "message": "Connectivité réseau disponible"
            }
        except socket.error:
            return {
                "status": False,
                "message": "Pas de connectivité réseau"
            }
    
    def _check_system_info(self) -> Dict[str, Any]:
        """
        Récupère les informations système.
        
        Returns:
            Dictionnaire contenant les informations système
        """
        return {
            "status": True,
            "platform": platform.system(),
            "version": platform.version(),
            "processor": platform.processor(),
            "message": "Informations système disponibles"
        }
