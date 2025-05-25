"""
Module contenant l'interface CLI de Peer.

Refactorisé pour utiliser le daemon central et l'adaptateur CLI.
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

# Importation du core centralisé
from peer.core import get_daemon, CLIAdapter, CoreRequest, CoreResponse, InterfaceType

class CLI:
    """
    Interface en ligne de commande pour Peer.
    
    Refactorisée pour utiliser le daemon central via l'adaptateur CLI.
    """
    
    def __init__(self):
        """Initialise l'interface CLI."""
        self.logger = logging.getLogger("CLI")
        
        # Obtenir l'instance du daemon central
        self.daemon = get_daemon()
        
        # Créer l'adaptateur CLI pour la traduction des commandes
        self.adapter = CLIAdapter()
        
        # Créer une session pour cette interface CLI
        self.session_id = self.daemon.create_session(InterfaceType.CLI)
        self.adapter.set_session_id(self.session_id)
        
        self.logger.info(f"CLI initialized with session {self.session_id}")
    
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
        
        try:
            parsed_args = self.parse_args(args)
            
            # Configurer le niveau de log
            if parsed_args.verbose:
                logging.getLogger().setLevel(logging.DEBUG)
                self.logger.debug("Mode verbeux activé")
            
            # Traduire les arguments CLI en requête core via l'adaptateur
            interface_input = {
                'command': parsed_args.command,
                'args': parsed_args.args
            }
            
            core_request = self.adapter.translate_to_core(interface_input)
            
            # Exécuter la commande via le daemon
            core_response = self.daemon.execute_command(core_request)
            
            # Traduire la réponse core en format CLI
            cli_output = self.adapter.translate_from_core(core_response)
            
            # Afficher le résultat
            print(cli_output)
            
            # Retourner le code de sortie approprié
            return 0 if core_response.type.value in ['success', 'info'] else 1
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'exécution de la commande: {e}")
            print(f"Erreur: {e}")
            return 1
        finally:
            # Nettoyer la session si nécessaire
            if hasattr(self, 'session_id') and self.session_id:
                self.daemon.end_session(self.session_id)

def main():
    """Point d'entrée principal de l'interface CLI."""
    cli = CLI()
    sys.exit(cli.run())

if __name__ == "__main__":
    main()
