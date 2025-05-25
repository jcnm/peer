"""
Module contenant l'interface CLI de Peer.
"""

import sys
import argparse
import logging
from typing import List, Optional

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Importation des services
from peer.domain.services.message_service import MessageService
from peer.domain.services.system_check_service import SystemCheckService
from peer.domain.services.command_service import CommandService
from peer.infrastructure.adapters.simple_system_check_adapter import SimpleSystemCheckAdapter

class CLI:
    """
    Interface en ligne de commande pour Peer.
    """
    
    def __init__(self):
        """Initialise l'interface CLI."""
        self.logger = logging.getLogger("CLI")
        self.message_service = MessageService()
        self.system_check_service = SystemCheckService(SimpleSystemCheckAdapter())
        self.command_service = CommandService()  # Service centralisé de commandes
    
    def parse_args(self, args: List[str]) -> argparse.Namespace:
        """
        Parse les arguments de la ligne de commande.
        
        Args:
            args: Arguments de la ligne de commande
            
        Returns:
            argparse.Namespace: Arguments parsés
        """
        parser = argparse.ArgumentParser(description="Peer CLI - Interface en ligne de commande pour Peer")
        
        # Commandes principales
        parser.add_argument('command', nargs='?', default='help',
                            help='Commande à exécuter (help, version, etc.)')
        
        # Arguments supplémentaires
        parser.add_argument('args', nargs='*',
                            help='Arguments pour la commande')
        
        # Options
        parser.add_argument('-v', '--verbose', action='store_true',
                            help='Mode verbeux')
        
        return parser.parse_args(args)
    
    def run(self, args: Optional[List[str]] = None):
        """
        Exécute l'interface CLI avec les arguments fournis.
        
        Args:
            args: Arguments de la ligne de commande (utilise sys.argv si None)
        """
        if args is None:
            args = sys.argv[1:]
        
        parsed_args = self.parse_args(args)
        
        # Configurer le niveau de log
        if parsed_args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
            self.logger.debug("Mode verbeux activé")
        
        # Exécuter la commande via le service centralisé
        try:
            result = self.command_service.execute_command(parsed_args.command, parsed_args.args)
            print(result)
        except Exception as e:
            self.logger.error(f"Erreur lors de l'exécution de la commande: {e}")
            print(f"Erreur: {e}")
            return 1
        
        return 0

def main():
    """Point d'entrée principal de l'interface CLI."""
    cli = CLI()
    sys.exit(cli.run())

if __name__ == "__main__":
    main()
