"""
Module contenant le service de commandes centralisé pour le noyau de Peer.
Ce service reçoit et traite toutes les commandes des différentes interfaces.
"""

import logging
import datetime
import os
import sys
from typing import Dict, List, Optional, Any, Callable

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

class CommandService:
    """
    Service centralisé pour le traitement des commandes.
    Reçoit les commandes de toutes les interfaces et les traite de manière uniforme.
    """
    
    def __init__(self):
        """Initialise le service de commandes."""
        self.logger = logging.getLogger("CommandService")
        self.commands = self._register_commands()
        self.logger.info("Service de commandes initialisé")
    
    def _register_commands(self) -> Dict[str, Callable]:
        """
        Enregistre toutes les commandes disponibles.
        
        Returns:
            Dict[str, Callable]: Dictionnaire des commandes disponibles
        """
        return {
            "aide": self._cmd_help,
            "help": self._cmd_help,
            "heure": self._cmd_time,
            "date": self._cmd_date,
            "version": self._cmd_version,
            "echo": self._cmd_echo,
            "modifier_fichier": self._cmd_edit_file,
        }
    
    def execute_command(self, command: str, args: Optional[List[str]] = None) -> str:
        """
        Exécute une commande avec les arguments fournis.
        
        Args:
            command: La commande à exécuter
            args: Les arguments de la commande (optionnel)
            
        Returns:
            str: Le résultat de l'exécution de la commande
        """
        if args is None:
            args = []
            
        # Journalisation de la commande reçue
        self.logger.info(f"Commande reçue: {command} {' '.join(args)}")
        
        # Normalisation de la commande (minuscules, sans accents)
        normalized_command = self._normalize_command(command)
        
        # Recherche de la commande dans les commandes disponibles
        if normalized_command in self.commands:
            try:
                result = self.commands[normalized_command](args)
                self.logger.info(f"Commande exécutée avec succès: {command}")
                return result
            except Exception as e:
                error_msg = f"Erreur lors de l'exécution de la commande {command}: {str(e)}"
                self.logger.error(error_msg)
                return f"Erreur: {error_msg}"
        else:
            # Recherche de commandes similaires pour suggestion
            similar_commands = self._find_similar_commands(normalized_command)
            suggestion = ""
            if similar_commands:
                suggestion = f"\nCommandes similaires: {', '.join(similar_commands)}"
            
            self.logger.warning(f"Commande inconnue: {command}")
            return f"Commande inconnue: {command}{suggestion}\nUtilisez 'aide' pour voir les commandes disponibles."
    
    def _normalize_command(self, command: str) -> str:
        """
        Normalise une commande (minuscules, sans accents).
        
        Args:
            command: La commande à normaliser
            
        Returns:
            str: La commande normalisée
        """
        # Conversion en minuscules
        command = command.lower()
        
        # Mapping des commandes courantes
        command_mapping = {
            "quelle heure est-il": "heure",
            "quelle heure": "heure",
            "heure actuelle": "heure",
            "quelle date": "date",
            "date actuelle": "date",
            "date du jour": "date",
            "aide": "aide",
            "help": "aide",
            "aidez-moi": "aide",
            "version": "version",
            "echo": "echo",
            "répète": "echo",
            "modifier fichier": "modifier_fichier",
            "éditer fichier": "modifier_fichier",
        }
        
        # Retourne la commande mappée si elle existe, sinon la commande originale
        return command_mapping.get(command, command)
    
    def _find_similar_commands(self, command: str) -> List[str]:
        """
        Trouve des commandes similaires à la commande fournie.
        
        Args:
            command: La commande à comparer
            
        Returns:
            List[str]: Liste des commandes similaires
        """
        similar_commands = []
        for cmd in self.commands.keys():
            # Calcul simple de similarité (préfixe commun)
            if cmd.startswith(command[:2]) or command.startswith(cmd[:2]):
                similar_commands.append(cmd)
        return similar_commands
    
    # Implémentation des commandes
    
    def _cmd_help(self, args: List[str]) -> str:
        """
        Affiche l'aide des commandes disponibles.
        
        Args:
            args: Arguments de la commande (non utilisés)
            
        Returns:
            str: Message d'aide
        """
        help_text = "Commandes disponibles:\n"
        help_text += "  aide - Affiche cette aide\n"
        help_text += "  heure - Affiche l'heure actuelle\n"
        help_text += "  date - Affiche la date actuelle\n"
        help_text += "  version - Affiche la version de Peer\n"
        help_text += "  echo [texte] - Répète le texte fourni\n"
        help_text += "  modifier_fichier [fichier] - Modifie un fichier (non implémenté)\n"
        return help_text
    
    def _cmd_time(self, args: List[str]) -> str:
        """
        Affiche l'heure actuelle.
        
        Args:
            args: Arguments de la commande (non utilisés)
            
        Returns:
            str: Heure actuelle
        """
        now = datetime.datetime.now()
        return f"Il est {now.strftime('%H:%M:%S')}"
    
    def _cmd_date(self, args: List[str]) -> str:
        """
        Affiche la date actuelle.
        
        Args:
            args: Arguments de la commande (non utilisés)
            
        Returns:
            str: Date actuelle
        """
        now = datetime.datetime.now()
        return f"Nous sommes le {now.strftime('%d/%m/%Y')}"
    
    def _cmd_version(self, args: List[str]) -> str:
        """
        Affiche la version de Peer.
        
        Args:
            args: Arguments de la commande (non utilisés)
            
        Returns:
            str: Version de Peer
        """
        return "Peer version 0.2.0"
    
    def _cmd_echo(self, args: List[str]) -> str:
        """
        Répète le texte fourni.
        
        Args:
            args: Texte à répéter
            
        Returns:
            str: Texte répété
        """
        if not args:
            return "Erreur: Aucun texte fourni pour la commande echo"
        return " ".join(args)
    
    def _cmd_edit_file(self, args: List[str]) -> str:
        """
        Modifie un fichier (non implémenté).
        
        Args:
            args: Arguments de la commande
            
        Returns:
            str: Message d'erreur
        """
        return "Not Implemented: La modification de fichiers sera disponible dans une version future"
