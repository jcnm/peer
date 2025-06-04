"""
Module d'initialisation de l'interface SUI.

Ce module expose les classes et fonctions principales de l'interface SUI.
"""

from .main import SpeechUserInterface
from .domain.models import SUIResponse, InterfaceAction
from .adapters.interface_adapter import SUIInterfaceAdapter

__all__ = ['SpeechUserInterface', 'SUIResponse', 'InterfaceAction', 'SUIInterfaceAdapter']
