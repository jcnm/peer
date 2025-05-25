"""
Module contenant le service de vérification du système.
"""

from peer.domain.entities.message_entities import SystemStatus
from peer.domain.ports.system_check_port import SystemCheckPort


class SystemCheckService:
    """
    Service du domaine pour la vérification de l'état du système.
    
    Ce service centralise la logique de vérification de l'état du système
    et de ses composants.
    """
    
    def __init__(self, system_check_adapter: SystemCheckPort):
        """
        Initialise le service de vérification du système.
        
        Args:
            system_check_adapter: Adaptateur pour la vérification du système
        """
        self.system_check_adapter = system_check_adapter
    
    def check_system(self) -> SystemStatus:
        """
        Vérifie l'état global du système.
        
        Returns:
            Un objet SystemStatus contenant l'état du système
        """
        return self.system_check_adapter.check_system_status()
    
    def get_status_message(self) -> str:
        """
        Génère un message décrivant l'état du système.
        
        Returns:
            Message décrivant l'état du système
        """
        status = self.check_system()
        
        if status.is_online:
            return "Tout va bien, tous les systèmes sont opérationnels."
        else:
            return f"Attention, certains systèmes ne sont pas opérationnels: {status.message}"
