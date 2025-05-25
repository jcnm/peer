"""
Module contenant l'interface utilisateur textuelle (TUI).
"""

import curses
import logging
from typing import List, Tuple, Callable

from peer.domain.services.message_service import MessageService
from peer.domain.services.system_check_service import SystemCheckService
from peer.infrastructure.adapters.simple_tts_adapter import SimpleTTSAdapter
from peer.infrastructure.adapters.simple_system_check_adapter import SimpleSystemCheckAdapter

logger = logging.getLogger(__name__)


class TUI:
    """
    Interface utilisateur textuelle pour l'application Peer.
    
    Cette classe gère l'interface utilisateur textuelle basée sur curses
    et expose les fonctionnalités principales de l'application.
    """
    
    def __init__(self):
        """Initialise l'interface TUI."""
        # Initialiser les adaptateurs
        self.tts_adapter = SimpleTTSAdapter()
        self.tts_adapter.initialize()
        
        self.system_check_adapter = SimpleSystemCheckAdapter()
        
        # Initialiser les services
        self.message_service = MessageService(self.tts_adapter)
        self.system_check_service = SystemCheckService(self.system_check_adapter)
        
        # État de l'interface
        self.running = False
        self.current_menu = "main"
        self.current_selection = 0
        self.status_message = ""
        
        # Définir les menus
        self.menus = {
            "main": [
                ("Check", self.check_system),
                ("Quitter", self.quit)
            ]
        }
    
    def run(self):
        """Exécute l'interface TUI."""
        # Afficher et vocaliser le message de bienvenue
        welcome_message = self.message_service.get_welcome_message()
        self.message_service.vocalize_message(welcome_message)
        
        # Démarrer l'interface curses
        curses.wrapper(self._main_loop)
    
    def _main_loop(self, stdscr):
        """
        Boucle principale de l'interface TUI.
        
        Args:
            stdscr: Écran standard curses
        """
        # Configurer curses
        curses.curs_set(0)  # Masquer le curseur
        stdscr.timeout(100)  # Rafraîchissement toutes les 100ms
        
        # Initialiser les couleurs
        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Titre
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Sélection
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)    # Erreur
        curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Succès
        
        self.running = True
        while self.running:
            stdscr.clear()
            
            # Obtenir les dimensions de l'écran
            max_y, max_x = stdscr.getmaxyx()
            
            # Afficher le titre
            title = "Peer - Assistant de développement"
            stdscr.attron(curses.color_pair(1))
            stdscr.addstr(0, 0, " " * max_x)
            stdscr.addstr(0, (max_x - len(title)) // 2, title)
            stdscr.attroff(curses.color_pair(1))
            
            # Afficher le message de bienvenue
            welcome_message = self.message_service.get_welcome_message()
            stdscr.addstr(2, 2, welcome_message.content)
            
            # Afficher le menu actuel
            menu_items = self.menus[self.current_menu]
            for i, (item_text, _) in enumerate(menu_items):
                y = 4 + i
                if i == self.current_selection:
                    stdscr.attron(curses.color_pair(2))
                    stdscr.addstr(y, 2, f"> {item_text}")
                    stdscr.attroff(curses.color_pair(2))
                else:
                    stdscr.addstr(y, 2, f"  {item_text}")
            
            # Afficher le message de statut
            if self.status_message:
                status_y = 4 + len(menu_items) + 2
                stdscr.addstr(status_y, 2, self.status_message)
            
            # Rafraîchir l'écran
            stdscr.refresh()
            
            # Gérer les entrées utilisateur
            try:
                key = stdscr.getch()
                self._handle_key(key)
            except Exception as e:
                logger.error(f"Erreur lors de la gestion des touches: {str(e)}")
    
    def _handle_key(self, key):
        """
        Gère les touches pressées par l'utilisateur.
        
        Args:
            key: Code de la touche pressée
        """
        menu_items = self.menus[self.current_menu]
        
        if key == curses.KEY_UP:
            self.current_selection = (self.current_selection - 1) % len(menu_items)
        elif key == curses.KEY_DOWN:
            self.current_selection = (self.current_selection + 1) % len(menu_items)
        elif key == curses.KEY_ENTER or key == 10 or key == 13:
            # Exécuter l'action associée à l'élément sélectionné
            _, action = menu_items[self.current_selection]
            action()
    
    def check_system(self):
        """Vérifie et affiche l'état du système."""
        status = self.system_check_service.check_system()
        message = self.system_check_service.get_status_message()
        
        # Construire un message détaillé
        detailed_message = message + "\n\nDétails des composants:\n"
        for component, details in status.components_status.items():
            status_str = "✓" if details.get("status", False) else "✗"
            detailed_message += f"{status_str} {component}: {details.get('message', '')}\n"
        
        self.status_message = detailed_message
    
    def quit(self):
        """Quitte l'interface TUI."""
        self.running = False


def main():
    """Point d'entrée principal pour l'interface TUI."""
    try:
        tui = TUI()
        tui.run()
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de la TUI: {str(e)}")


if __name__ == "__main__":
    main()
