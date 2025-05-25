"""
Module contenant l'interface TUI de Peer.
"""

import sys
import logging
import threading
import time
from typing import List, Optional, Dict, Any

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Importation des dépendances
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.text import Text
    from rich.prompt import Prompt
except ImportError as e:
    print(f"Erreur lors du chargement des dépendances: {e}")
    print("Veuillez installer les dépendances requises:")
    print("  pip install rich")
    sys.exit(1)

# Importation des services
from peer.domain.services.message_service import MessageService
from peer.domain.services.system_check_service import SystemCheckService
from peer.domain.services.command_service import CommandService
from peer.infrastructure.adapters.simple_system_check_adapter import SimpleSystemCheckAdapter

class TUI:
    """
    Interface utilisateur textuelle (Text User Interface) pour Peer.
    """
    
    def __init__(self):
        """Initialise l'interface TUI."""
        self.logger = logging.getLogger("TUI")
        self.console = Console()
        
        # Initialisation des services
        self.message_service = MessageService()
        self.system_check_service = SystemCheckService(SimpleSystemCheckAdapter())
        self.command_service = CommandService()  # Service centralisé de commandes
        
        # Initialisation des variables d'état
        self.running = False
        self.layout = None
        self.messages = []
    
    def _setup_layout(self):
        """Configure la disposition de l'interface."""
        self.layout = Layout()
        
        # Diviser l'écran en sections
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        # Configurer l'en-tête
        self.layout["header"].update(
            Panel(
                Text("Peer - Interface Textuelle", style="bold blue"),
                style="blue"
            )
        )
        
        # Configurer le pied de page
        self.layout["footer"].update(
            Panel(
                Text("Tapez 'aide' pour afficher l'aide, 'quitter' pour quitter", style="italic"),
                style="blue"
            )
        )
        
        # Configurer la section principale
        self.layout["main"].update(
            Panel(
                Text("Bienvenue dans l'interface textuelle de Peer.\nComment puis-je vous aider?"),
                title="Conversation",
                style="green"
            )
        )
    
    def _update_main_panel(self):
        """Met à jour le panneau principal avec les messages."""
        content = ""
        for msg in self.messages[-10:]:  # Afficher les 10 derniers messages
            if msg["type"] == "user":
                content += f"[bold blue]Vous:[/bold blue] {msg['text']}\n"
            else:
                content += f"[bold green]Peer:[/bold green] {msg['text']}\n"
        
        self.layout["main"].update(
            Panel(
                Text.from_markup(content),
                title="Conversation",
                style="green"
            )
        )
    
    def _add_message(self, text: str, msg_type: str = "system"):
        """
        Ajoute un message à l'historique.
        
        Args:
            text: Texte du message
            msg_type: Type de message ('user', 'system')
        """
        self.messages.append({
            "text": text,
            "type": msg_type,
            "timestamp": time.time()
        })
        self._update_main_panel()
    
    def start(self):
        """Démarre l'interface TUI."""
        if self.running:
            self.logger.warning("L'interface TUI est déjà en cours d'exécution")
            return
        
        self.running = True
        self.logger.info("Démarrage de l'interface TUI...")
        
        # Configurer la disposition
        self._setup_layout()
        
        # Afficher la disposition initiale
        self.console.clear()
        self.console.print(self.layout)
        
        # Message de bienvenue
        self._add_message("Bienvenue dans l'interface textuelle de Peer. Comment puis-je vous aider?")
        
        # Boucle principale
        try:
            while self.running:
                # Afficher la disposition
                self.console.print(self.layout)
                
                # Demander une commande
                command = Prompt.ask("Entrez une commande")
                
                # Traiter la commande
                self._process_command(command)
        except KeyboardInterrupt:
            self.logger.info("Interruption clavier détectée")
            self.stop()
        except Exception as e:
            self.logger.error(f"Erreur dans la boucle principale: {e}")
            self.stop()
    
    def stop(self):
        """Arrête l'interface TUI."""
        if not self.running:
            return
        
        self.logger.info("Arrêt de l'interface TUI...")
        self.running = False
        
        # Afficher un message d'au revoir
        self.console.clear()
        self.console.print(Panel(Text("Merci d'avoir utilisé Peer. À bientôt!", style="bold green")))
    
    def _process_command(self, command: str):
        """
        Traite une commande textuelle.
        
        Args:
            command: Commande à traiter
        """
        if not command:
            return
        
        self.logger.info(f"Traitement de la commande: {command}")
        
        # Ajouter la commande à l'historique
        self._add_message(command, "user")
        
        # Commandes spéciales
        if command.lower() in ["quitter", "exit", "stop", "arrêter"]:
            self._add_message("Au revoir!")
            self.stop()
            return
        
        # Déléguer la commande au service de commandes centralisé
        try:
            # Extraire les arguments de la commande
            parts = command.split()
            cmd = parts[0] if parts else ""
            args = parts[1:] if len(parts) > 1 else []
            
            # Exécuter la commande via le service centralisé
            result = self.command_service.execute_command(command, args)
            
            # Afficher le résultat
            self._add_message(result)
        except Exception as e:
            error_msg = f"Erreur lors du traitement de la commande: {e}"
            self.logger.error(error_msg)
            self._add_message(f"Je n'ai pas compris cette commande.")

def main():
    """Point d'entrée principal de l'interface TUI."""
    tui = TUI()
    try:
        tui.start()
    except KeyboardInterrupt:
        tui.stop()
    except Exception as e:
        print(f"Erreur: {e}")
        tui.stop()

if __name__ == "__main__":
    main()
