#!/usr/bin/env python3
"""
Test complet du nouveau système de détection de sortie polie intelligent.

Ce test valide le nouveau système de détection multi-commandes avec:
1. Analyse libre des modèles NLP sans exclusions strictes
2. Méthodes de fallback intelligentes
3. Détection de plusieurs commandes dans une seule phrase
4. Demandes de confirmation intelligentes
5. Distinction entre DIRECT_QUIT et SOFT_QUIT
6. Génération de phrases de confirmation contextuelles
7. Gestion des séquences de commandes
"""

import os
import sys
import logging
import time
from typing import Dict, Any, List

# Ajouter le répertoire source au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from peer.core.api import CoreRequest, CoreResponse, CommandType
from peer.interfaces.sui.nlp_engine import HybridNLPEngine

class PoliteQuitSystemTester:
    """Testeur complet du nouveau système de détection de sortie polie."""
    
    def __init__(self):
        """Initialise le testeur."""
        self.logger = logging.getLogger("PoliteQuitTester")
        self.engine = HybridNLPEngine()
        self.test_cases = self._prepare_test_cases()
        self.results = []
        
    def _prepare_test_cases(self) -> List[Dict[str, Any]]:
        """Prépare les cas de test pour le nouveau système."""
        return [
            # Tests DIRECT_QUIT (à la fin de phrase)
            {
                "input": "Merci beaucoup pour ton aide, maintenant stop",
                "expected_type": "immediate_quit",
                "expected_quit_type": "DIRECT_QUIT",
                "description": "DIRECT_QUIT à la fin avec gratitude"
            },
            {
                "input": "C'est parfait, je vais m'arrêter là",
                "expected_type": "immediate_quit", 
                "expected_quit_type": "DIRECT_QUIT",
                "description": "DIRECT_QUIT naturel en fin de phrase"
            },
            {
                "input": "Analyse ce code et puis arrête-toi",
                "expected_type": "command_sequence",
                "expected_commands": ["PROMPT", "DIRECT_QUIT"],
                "description": "Commande + DIRECT_QUIT en séquence"
            },
            
            # Tests SOFT_QUIT (milieu de phrase ou ambigu)
            {
                "input": "Je pense qu'il faut arrêter cette analyse maintenant",
                "expected_type": "requires_confirmation",
                "expected_quit_type": "SOFT_QUIT",
                "description": "SOFT_QUIT au milieu - demande confirmation"
            },
            {
                "input": "Stop l'analyse et montre-moi les résultats",
                "expected_type": "requires_confirmation",
                "expected_quit_type": "DIRECT_QUIT",  # DIRECT_QUIT au milieu
                "description": "DIRECT_QUIT au milieu - demande précision"
            },
            
            # Tests de séquences multiples
            {
                "input": "Vérifie le status, puis montre la version et arrête",
                "expected_type": "command_sequence",
                "expected_commands": ["STATUS", "VERSION", "DIRECT_QUIT"],
                "description": "Séquence de 3 commandes avec quit final"
            },
            {
                "input": "Help avec les fonctions puis stop maintenant",
                "expected_type": "command_sequence", 
                "expected_commands": ["HELP", "DIRECT_QUIT"],
                "description": "Help + quit immédiat"
            },
            
            # Tests de confirmation contextuelle
            {
                "input": "Merci infiniment pour cette aide précieuse, je pense que ça suffit",
                "expected_type": "requires_confirmation",
                "expected_quit_type": "SOFT_QUIT",
                "expected_context": ["gratitude", "politeness"],
                "description": "SOFT_QUIT avec forte politesse - confirmation intelligente"
            },
            {
                "input": "URGENT: stop tout maintenant !!!",
                "expected_type": "immediate_quit",
                "expected_quit_type": "DIRECT_QUIT", 
                "expected_context": ["urgency"],
                "description": "DIRECT_QUIT urgent - exécution immédiate"
            },
            
            # Tests de non-détection (phrases qui ne doivent PAS déclencher quit)
            {
                "input": "Peux-tu m'aider à arrêter cette fonction qui bug ?",
                "expected_type": "normal_command",
                "expected_command": "PROMPT",
                "description": "Demande d'aide - ne doit pas déclencher quit"
            },
            {
                "input": "Comment faire pour stopper proprement un processus ?",
                "expected_type": "normal_command",
                "expected_command": "PROMPT", 
                "description": "Question technique - ne doit pas déclencher quit"
            }
        ]
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Exécute tous les tests du nouveau système."""
        print("🧪 === TEST DU NOUVEAU SYSTÈME DE DÉTECTION DE SORTIE POLIE ===")
        print(f"📋 Exécution de {len(self.test_cases)} cas de test...\n")
        
        passed = 0
        failed = 0
        
        for i, test_case in enumerate(self.test_cases, 1):
            print(f"Test {i}/{len(self.test_cases)}: {test_case['description']}")
            print(f"📝 Input: '{test_case['input']}'")
            
            try:
                result = self._run_single_test(test_case)
                if result['success']:
                    print(f"✅ RÉUSSI")
                    passed += 1
                else:
                    print(f"❌ ÉCHEC: {result['error']}")
                    failed += 1
                    
                self.results.append(result)
                print()
                
            except Exception as e:
                print(f"💥 ERREUR CRITIQUE: {e}")
                failed += 1
                print()
        
        # Résumé final
        print("=" * 60)
        print(f"📊 RÉSULTATS FINAUX:")
        print(f"✅ Tests réussis: {passed}/{len(self.test_cases)}")
        print(f"❌ Tests échoués: {failed}/{len(self.test_cases)}")
        print(f"📈 Taux de réussite: {(passed/len(self.test_cases)*100):.1f}%")
        
        return {
            "total_tests": len(self.test_cases),
            "passed": passed,
            "failed": failed,
            "success_rate": passed/len(self.test_cases) if self.test_cases else 0,
            "details": self.results
        }
    
    def _run_single_test(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Exécute un test individuel."""
        input_text = test_case['input']
        
        # Analyser avec le nouveau moteur
        start_time = time.time()
        result = self.engine.extract_intent(input_text)
        processing_time = time.time() - start_time
        
        print(f"⚙️ Résultat: {result}")
        print(f"⏱️ Temps: {processing_time:.3f}s")
        
        # Analyser le type de réponse basé sur le résultat
        response_type = self._analyze_response_type(result)
        print(f"🎯 Type détecté: {response_type}")
        
        # Valider selon les attentes
        success, error = self._validate_result(test_case, result, response_type)
        
        return {
            "test_case": test_case,
            "result": result,
            "response_type": response_type,
            "processing_time": processing_time,
            "success": success,
            "error": error
        }
    
    def _analyze_response_type(self, result) -> str:
        """Analyse le type de réponse basé sur le résultat du moteur."""
        if not result or not hasattr(result, 'parameters'):
            return "normal_command"
            
        params = result.parameters
        
        if params.get("immediate_quit"):
            return "immediate_quit"
        elif params.get("confirmation_needed") or params.get("requires_confirmation"):
            return "requires_confirmation"
        elif params.get("is_command_sequence"):
            return "command_sequence"
        else:
            return "normal_command"
    
    def _validate_result(self, test_case: Dict[str, Any], result, response_type: str) -> tuple:
        """Valide le résultat par rapport aux attentes."""
        expected_type = test_case['expected_type']
        
        # Vérification du type de réponse
        if response_type != expected_type:
            return False, f"Type attendu: {expected_type}, obtenu: {response_type}"
        
        # Validations spécifiques selon le type
        if expected_type == "immediate_quit":
            return self._validate_immediate_quit(test_case, result)
        elif expected_type == "requires_confirmation":
            return self._validate_confirmation_request(test_case, result)
        elif expected_type == "command_sequence":
            return self._validate_command_sequence(test_case, result)
        elif expected_type == "normal_command":
            return self._validate_normal_command(test_case, result)
        
        return True, None
    
    def _validate_immediate_quit(self, test_case: Dict[str, Any], result) -> tuple:
        """Valide un quit immédiat."""
        if not hasattr(result, 'response_data'):
            return False, "Pas de response_data"
            
        response_data = result.response_data
        expected_quit_type = test_case.get('expected_quit_type')
        
        if expected_quit_type:
            actual_quit_type = response_data.get('quit_type')
            if actual_quit_type != expected_quit_type:
                return False, f"Type quit attendu: {expected_quit_type}, obtenu: {actual_quit_type}"
        
        return True, None
    
    def _validate_confirmation_request(self, test_case: Dict[str, Any], result) -> tuple:
        """Valide une demande de confirmation."""
        if not hasattr(result, 'response_data'):
            return False, "Pas de response_data"
            
        response_data = result.response_data
        
        # Vérifier la présence d'un message de confirmation
        if not response_data.get('vocal_message'):
            return False, "Pas de message de confirmation"
        
        # Vérifier le type de quit si spécifié
        expected_quit_type = test_case.get('expected_quit_type')
        if expected_quit_type:
            actual_quit_type = response_data.get('quit_type')
            if actual_quit_type != expected_quit_type:
                return False, f"Type quit attendu: {expected_quit_type}, obtenu: {actual_quit_type}"
        
        return True, None
    
    def _validate_command_sequence(self, test_case: Dict[str, Any], result) -> tuple:
        """Valide une séquence de commandes."""
        if not hasattr(result, 'response_data'):
            return False, "Pas de response_data"
            
        response_data = result.response_data
        command_sequence = response_data.get('command_sequence', [])
        
        expected_commands = test_case.get('expected_commands', [])
        if expected_commands:
            actual_commands = [cmd.get('command') for cmd in command_sequence]
            if actual_commands != expected_commands:
                return False, f"Commandes attendues: {expected_commands}, obtenues: {actual_commands}"
        
        return True, None
    
    def _validate_normal_command(self, test_case: Dict[str, Any], result) -> tuple:
        """Valide une commande normale."""
        expected_command = test_case.get('expected_command')
        if expected_command:
            actual_command = result.command_type if result else None
            if str(actual_command) != expected_command:
                return False, f"Commande attendue: {expected_command}, obtenue: {actual_command}"
        
        return True, None

def main():
    """Fonction principale de test."""
    # Suppress BERT warnings for cleaner output
    import warnings
    warnings.filterwarnings("ignore")
    
    logging.basicConfig(
        level=logging.WARNING,  # Only show warnings and errors
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    tester = PoliteQuitSystemTester()
    results = tester.run_all_tests()
    
    # Retourner un code d'erreur approprié
    if results['success_rate'] < 0.8:  # Moins de 80% de réussite
        print("⚠️ Taux de réussite insuffisant!")
        sys.exit(1)
    else:
        print("🎉 Tests du nouveau système réussis!")
        sys.exit(0)

if __name__ == "__main__":
    main()
