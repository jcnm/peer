"""
Module contenant l'interface en ligne de commande (CLI).
"""

import argparse
import sys
import logging

from peer.domain.services.message_service import MessageService
from peer.domain.services.system_check_service import SystemCheckService
from peer.infrastructure.adapters.simple_tts_adapter import SimpleTTSAdapter
from peer.infrastructure.adapters.simple_system_check_adapter import SimpleSystemCheckAdapter

logger = logging.getLogger(__name__)


class CLI:
    """
    Interface en ligne de commande pour l'application Peer.
    
    Cette classe gère l'interface utilisateur en ligne de commande
    et expose les fonctionnalités principales de l'application.
    """
    
    def __init__(self):
        """Initialise l'interface CLI."""
        # Initialiser les adaptateurs
        self.tts_adapter = SimpleTTSAdapter()
        self.tts_adapter.initialize()
        
        self.system_check_adapter = SimpleSystemCheckAdapter()
        
        # Initialiser les services
        self.message_service = MessageService(self.tts_adapter)
        self.system_check_service = SystemCheckService(self.system_check_adapter)
    
    def run(self, args=None):
        """
        Exécute l'interface CLI avec les arguments fournis.
        
        Args:
            args: Arguments de ligne de commande (None pour utiliser sys.argv)
        """
        parser = self.create_parser()
        parsed_args = parser.parse_args(args)
        
        # Afficher le message de bienvenue par défaut
        if not any([parsed_args.check]):
            welcome_message = self.message_service.get_welcome_message()
            print(welcome_message.content)
            self.message_service.vocalize_message(welcome_message)
        
        # Exécuter les commandes
        if parsed_args.check:
            self.check_system()
    
    def create_parser(self):
        """
        Crée le parseur d'arguments pour l'interface CLI.
        
        Returns:
            Un parseur d'arguments configuré
        """
        parser = argparse.ArgumentParser(
            description="Peer - Assistant de développement",
            prog="peer"
        )
        
        parser.add_argument(
            "--check",
            action="store_true",
            help="Vérifie l'état du système"
        )
        
        return parser
    
    def check_system(self):
        """Vérifie et affiche l'état du système."""
        status = self.system_check_service.check_system()
        message = self.system_check_service.get_status_message()
        
        print(message)
        
        # Afficher les détails des composants
        print("\nDétails des composants:")
        for component, details in status.components_status.items():
            status_str = "✓" if details.get("status", False) else "✗"
            print(f"{status_str} {component}: {details.get('message', '')}")


def main():
    """Point d'entrée principal pour l'interface CLI."""
    try:
        cli = CLI()
        cli.run()
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de la CLI: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
