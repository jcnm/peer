"""
Module NLU (Natural Language Understanding) pour l'interface SUI.

Ce module fournit des fonctionnalités de compréhension du langage naturel
pour l'interface vocale, avec une architecture modulaire et réutilisable.
"""

from peer.interfaces.sui.nlu.domain.nlp_engine import NLPEngine
from peer.interfaces.sui.nlu.domain.models import IntentResult, NLUMethod, NLUModelStatus, NLUPerformanceStats

__all__ = ['NLPEngine', 'IntentResult', 'NLUMethod', 'NLUModelStatus', 'NLUPerformanceStats']
