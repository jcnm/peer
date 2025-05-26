#!/usr/bin/env python3
"""
Test réaliste du flux complet du nouveau système de détection de sortie polie.

Ce test simule le flux complet: entrée utilisateur → NLP engine → réponse → SUI adapter
"""

import os
import sys
import logging
import warnings

# Ajouter le répertoire source au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Supprimer les warnings pour un output plus clean
warnings.filterwarnings("ignore")

from peer.interfaces.sui.nlp_engine import HybridNLPEngine
from peer.interfaces.sui.sui import IntelligentSUISpeechAdapter
from peer.core.api import CoreResponse, CoreRequest, CommandType

class RealisticQuitSystemTester:
    """Test du flux complet du système de détection de sortie polie."""
    
    def __init__(self):
        """Initialise le testeur."""
        self.logger = logging.getLogger("RealisticQuitTester")
        self.nlp_engine = HybridNLPEngine()
        self.sui_adapter = IntelligentSUISpeechAdapter()
        
    def test_basic_functionality(self):
        """Test des fonctionnalités de base."""
        print("🧪 === TEST DES FONCTIONNALITÉS DE BASE ===\n")
        
        test_cases = [
            {
                "input": "merci stop maintenant",
                "description": "Simple quit avec gratitude"
            },
            {
                "input": "analyse ce code et puis arrête-toi",
                "description": "Commande + quit en séquence"
            },
            {
                "input": "je pense qu'il faut arrêter cette session",
                "description": "SOFT_QUIT avec demande de confirmation"
            },
            {
                "input": "peux-tu m'aider à arrêter ce bug ?",
                "description": "Demande d'aide - ne doit PAS déclencher quit"
            }
        ]
        
        results = []
        for i, test_case in enumerate(test_cases, 1):
            print(f"Test {i}: {test_case['description']}")
            print(f"📝 Input: '{test_case['input']}'")
            
            # 1. Analyser avec le moteur NLP
            nlp_result = self.nlp_engine.extract_intent(test_case['input'])
            print(f"🧠 NLP Result: {nlp_result.command_type} (confidence: {nlp_result.confidence:.2f})")
            
            # 2. Créer une réponse simulée du daemon
            mock_core_response = self._create_mock_core_response(nlp_result)
            
            # 3. Traduire avec l'adaptateur SUI
            adapted_response = self.sui_adapter.translate_from_core(mock_core_response)
            
            # 4. Analyser le résultat final
            response_type = self._analyze_final_response(adapted_response)
            print(f"🎯 Response Type: {response_type}")
            
            if adapted_response.get("vocal_message"):
                print(f"💬 Message: {adapted_response['vocal_message'][:100]}...")
            
            print(f"✨ Special flags: {self._extract_special_flags(adapted_response)}")
            print()
            
            results.append({
                "test_case": test_case,
                "nlp_result": nlp_result,
                "adapted_response": adapted_response,
                "response_type": response_type
            })
        
        return results
    
    def _create_mock_core_response(self, nlp_result):
        """Crée une réponse simulée du daemon basée sur le résultat NLP."""
        # Simuler ce que ferait le daemon avec le résultat du NLP
        message = "Réponse simulée du daemon"
        
        # Créer la réponse avec les données appropriées
        response = CoreResponse(
            type=nlp_result.command_type,
            message=message,
            success=True,
            data=nlp_result.parameters if hasattr(nlp_result, 'parameters') else {}
        )
        
        return response
    
    def _analyze_final_response(self, adapted_response):
        """Analyse le type de réponse finale."""
        if adapted_response.get("immediate_quit"):
            return "immediate_quit"
        elif adapted_response.get("requires_confirmation"):
            return "requires_confirmation"
        elif adapted_response.get("is_command_sequence"):
            return "command_sequence"
        else:
            return "normal_command"
    
    def _extract_special_flags(self, adapted_response):
        """Extrait les flags spéciaux de la réponse."""
        flags = []
        if adapted_response.get("immediate_quit"):
            flags.append("immediate_quit")
        if adapted_response.get("requires_confirmation"):
            flags.append("requires_confirmation")
        if adapted_response.get("is_command_sequence"):
            flags.append("command_sequence")
        if adapted_response.get("confirmation_needed"):
            flags.append("confirmation_needed")
        return flags if flags else ["none"]

def main():
    """Fonction principale."""
    logging.basicConfig(level=logging.WARNING)
    
    tester = RealisticQuitSystemTester()
    
    try:
        print("🚀 Initialisation du test réaliste...\n")
        results = tester.test_basic_functionality()
        
        print("=" * 60)
        print("📊 RÉSUMÉ DES RÉSULTATS:")
        
        for i, result in enumerate(results, 1):
            test_case = result["test_case"]
            response_type = result["response_type"]
            nlp_command = result["nlp_result"].command_type
            
            print(f"Test {i}: {test_case['description']}")
            print(f"  NLP: {nlp_command} → SUI: {response_type}")
        
        print("\n🎉 Test réaliste terminé avec succès!")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
