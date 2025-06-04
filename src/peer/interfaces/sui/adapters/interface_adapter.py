"""
Adaptateur d'interface pour SUI.

Ce module définit l'adaptateur qui fait le lien entre l'interface vocale (SUI)
et le Core, conformément à l'architecture hexagonale.
"""

import logging
from typing import Dict, Any, Optional
from enum import Enum

from peer.core import PeerDaemon, CoreRequest, CoreResponse, CommandType, ResponseType, InterfaceType
from peer.core.protocol import InterfaceAdapter

from peer.interfaces.sui.domain.models import InterfaceAction, SUIResponse


class SUIInterfaceAdapter(InterfaceAdapter):
    """
    Adaptateur pour l'interface vocale (SUI).
    
    Fait le lien entre l'interface SUI et le Core, en respectant
    l'indépendance du Core vis-à-vis des interfaces.
    """
    
    def __init__(self):
        """Initialise l'adaptateur d'interface SUI."""
        super().__init__(InterfaceType.SUI)
        self.logger = logging.getLogger("SUIInterfaceAdapter")
    
    def translate_to_core(self, interface_input) -> CoreRequest:
        """
        Traduit une entrée d'interface en requête Core.
        
        Args:
            interface_input: Entrée de l'interface (dict ou autre)
            
        Returns:
            Requête formatée pour le Core
        """
        if isinstance(interface_input, dict):
            command_type = interface_input.get('command_type')
            
            # Gestion spéciale pour les commandes de quit
            if command_type in ['DIRECT_QUIT', 'SOFT_QUIT', 'QUIT']:
                command_type = CommandType.QUIT
            
            # Si aucun type de commande n'est détecté ou si c'est une commande inconnue,
            # mapper vers PROMPT pour que le Core puisse traiter le texte libre
            if not command_type or command_type == 'UNKNOWN':
                command_type = CommandType.PROMPT
                self.logger.info(f"🔄 Commande inconnue mappée vers PROMPT: {interface_input.get('full_text', 'N/A')}")
            
            # Convertir en CommandType si c'est une chaîne
            if isinstance(command_type, str):
                try:
                    command_type = CommandType(command_type.lower())
                except ValueError:
                    # Si la conversion échoue, utiliser PROMPT comme fallback
                    self.logger.warning(f"⚠️ Type de commande invalide '{command_type}', utilisation de PROMPT")
                    command_type = CommandType.PROMPT
            
            return CoreRequest(
                command=command_type,
                interface_type=InterfaceType.SUI,
                parameters=interface_input.get('parameters', {}),
                **{k: v for k, v in interface_input.items() if k not in ['command_type', 'args', 'full_text']}
            )
        else:
            # Si l'entrée n'est pas un dictionnaire, on crée une requête simple
            return CoreRequest(
                command=CommandType.PROMPT,
                interface_type=InterfaceType.SUI,
                parameters={"full_text": str(interface_input)}
            )
    
    def translate_from_core(self, core_response: CoreResponse) -> SUIResponse:
        """
        Traduit une réponse Core en format spécifique à l'interface.
        
        Args:
            core_response: Réponse du Core
            
        Returns:
            Réponse formatée pour l'interface SUI
        """
        return self.process_core_response(core_response)
    
    def format_help(self, help_data) -> str:
        """
        Formate les informations d'aide pour cette interface.
        
        Args:
            help_data: Données d'aide du Core (peut être une chaîne ou un dictionnaire)
            
        Returns:
            str: Texte d'aide formaté pour cette interface
        """
        if isinstance(help_data, str):
            return help_data
        
        if isinstance(help_data, dict):
            commands = help_data.get('commands', {})
            help_text = "Commandes disponibles:\n\n"
            
            for cmd_name, cmd_info in commands.items():
                help_text += f"- {cmd_name}: {cmd_info.get('description', 'Pas de description')}\n"
            
            return help_text
        
        return "Aide non disponible."
    
    def format_error(self, error_response) -> str:
        """
        Formate une réponse d'erreur pour cette interface.
        
        Args:
            error_response: Réponse d'erreur du Core (CoreResponse ou chaîne)
            
        Returns:
            str: Message d'erreur formaté
        """
        if isinstance(error_response, str):
            return f"Erreur: {error_response}"
        
        if isinstance(error_response, CoreResponse):
            return f"Erreur: {error_response.message or 'Erreur inconnue'}"
        
        return "Une erreur est survenue."
    
    def process_core_response(self, core_response: CoreResponse) -> SUIResponse:
        """
        Traite la réponse du Core et la convertit en réponse SUI.
        
        Args:
            core_response: Réponse du Core
            
        Returns:
            Réponse formatée pour l'interface SUI
        """
        # Initialiser la réponse SUI
        response_data = SUIResponse(
            message=core_response.message or "",
            vocal_message=core_response.message or "",
            should_vocalize=True,
            interface_action=InterfaceAction.NONE,
            success=(core_response.type == ResponseType.SUCCESS)
        )
        
        # Définir le message d'erreur si nécessaire
        if core_response.type == ResponseType.ERROR:
            response_data.error_message = core_response.message or "Erreur inconnue"
            
        # Définir l'action d'interface en fonction de la réponse du Core
        if core_response.message:
            response_data.interface_action = InterfaceAction.INFORM
        
        # Gestion des actions spécifiques basées sur la réponse du démon
        if hasattr(core_response, 'data') and core_response.data:
            # Gestion des demandes de quitter
            if ('quit' in core_response.data and core_response.data['quit'] is True) or \
               ('farewell' in core_response.data and core_response.data['farewell'] is True):
                response_data.interface_action = InterfaceAction.QUIT
                self.logger.info("🎬 Action d'interface définie sur QUIT suite à la confirmation d'arrêt du démon.")
            
            # Gestion des demandes d'informations supplémentaires
            elif core_response.data.get("needs_user_clarification"):
                response_data.interface_action = InterfaceAction.ASK
                response_data.action_details = {
                    "clarification_prompt": core_response.data.get("clarification_prompt", "")
                }
                self.logger.info(f"🎬 Action d'interface définie sur ASK: {response_data.action_details}")
            
            # Gestion des informations de progression
            elif core_response.data.get("progress_info"):
                response_data.interface_action = InterfaceAction.PROGRESS
                response_data.action_details = {
                    "progress": core_response.data.get("progress_info", {})
                }
                self.logger.info(f"🎬 Action d'interface définie sur PROGRESS: {response_data.action_details}")

        # Pour les commandes spéciales, vérifier aussi le type de réponse et le statut
        if core_response.status == "quit_requested":
            response_data.interface_action = InterfaceAction.QUIT
            self.logger.info("🎬 Action d'interface définie sur QUIT en raison du statut 'quit_requested'.")

        return response_data
    
    def create_core_request(self, command_type: CommandType, args: list = None, 
                          full_text: str = "", **kwargs) -> CoreRequest:
        """
        Crée une requête pour le Core à partir des paramètres de l'interface.
        
        Args:
            command_type: Type de commande
            args: Arguments de la commande
            full_text: Texte complet de la commande
            **kwargs: Paramètres supplémentaires
            
        Returns:
            Requête formatée pour le Core
        """
        # Créer la requête de base
        request = CoreRequest(
            command=command_type,
            interface_type=InterfaceType.SUI,
            parameters={"args": args or []} if args else {}
        )
        
        # Ajouter les données supplémentaires
        if full_text:
            request.parameters["full_text"] = full_text
        
        # Ajouter les autres paramètres
        for key, value in kwargs.items():
            request.parameters[key] = value
        
        return request
