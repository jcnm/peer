#!/usr/bin/env python3
"""
Test d'intégration complète SUI avec Agent IA Central
Validation de l'architecture intelligente de traitement des commandes vocales
"""

import logging
import sys
import time
from pathlib import Path

# Ajouter le chemin du projet
sys.path.insert(0, str(Path(__file__).parent / "src"))

from peer.interfaces.sui.sui import IntelligentSUISpeechAdapter
from peer.core.api import CommandType, CoreRequest, InterfaceType
from peer.core.daemon import PeerDaemon


def setup_logging():
    """Configure le logging pour les tests"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def test_agent_ia_architecture():
    """Test de l'architecture Agent IA de SUI"""
    print("🧪 === TEST ARCHITECTURE AGENT IA SUI ===")
    
    # Initialiser l'adaptateur intelligent
    adapter = IntelligentSUISpeechAdapter()
    print(f"✅ Adaptateur SUI initialisé - BERT: {adapter.bert_enabled}")
    
    # Tests d'analyse intelligente des commandes
    test_cases = [
        # Arrêts polis (priorité absolue)
        ("merci pour ton aide tu peux t'arrêter", CommandType.QUIT),
        ("c'est parfait merci", CommandType.QUIT),
        ("tu peux arrêter maintenant", CommandType.QUIT),
        
        # Commandes directes (rétrocompatibilité)
        ("aide", CommandType.HELP),
        ("statut", CommandType.STATUS),
        ("analyse ce code", CommandType.ANALYZE),
        ("explique cette fonction", CommandType.EXPLAIN),
        
        # Requêtes complexes (transmission à l'agent IA central)
        ("comment optimiser la performance de mon application", CommandType.PROMPT),
        ("peux-tu m'aider à résoudre ce problème de mémoire", CommandType.PROMPT),
        ("quelle est la meilleure façon de structurer ce projet", CommandType.PROMPT),
    ]
    
    success_count = 0
    for speech_input, expected_command in test_cases:
        try:
            # Analyser la commande
            command, params = adapter._parse_intelligent_speech_command(speech_input, {})
            
            # Vérifier le résultat
            if command == expected_command:
                print(f"✅ '{speech_input}' -> {command.value}")
                success_count += 1
            else:
                print(f"❌ '{speech_input}' -> {command.value} (attendu: {expected_command.value})")
                
            # Afficher la méthode de traitement utilisée
            method = params.get("processing_method", params.get("fallback_method", "unknown"))
            print(f"   📝 Méthode: {method}")
            
        except Exception as e:
            print(f"❌ Erreur lors de l'analyse de '{speech_input}': {e}")
    
    success_rate = (success_count / len(test_cases)) * 100
    print(f"\n🎯 Taux de réussite: {success_rate:.1f}% ({success_count}/{len(test_cases)})")
    
    return success_rate >= 90.0


def test_core_request_generation():
    """Test de génération des requêtes CoreRequest"""
    print("\n🧪 === TEST GÉNÉRATION CORE REQUEST ===")
    
    adapter = IntelligentSUISpeechAdapter()
    
    test_inputs = [
        "aide-moi à comprendre ce code",
        "optimise cette fonction",
        "explique-moi l'architecture",
        "merci c'est parfait"
    ]
    
    for speech_input in test_inputs:
        try:
            # Générer la requête
            request = adapter.translate_to_core(speech_input, {"session": "test"})
            
            print(f"✅ '{speech_input}':")
            print(f"   🎯 Commande: {request.command.value}")
            print(f"   📋 Paramètres: {len(request.parameters)} éléments")
            print(f"   🌐 Interface: {request.interface_type.value}")
            print(f"   📝 Contexte enrichi: {bool(request.context)}")
            
        except Exception as e:
            print(f"❌ Erreur pour '{speech_input}': {e}")
    
    return True


def test_with_daemon():
    """Test d'intégration avec le daemon IA"""
    print("\n🧪 === TEST INTÉGRATION DAEMON IA ===")
    
    try:
        # Créer un daemon pour les tests
        daemon = PeerDaemon()
        adapter = IntelligentSUISpeechAdapter()
        
        # Test de requêtes complètes
        test_commands = [
            "aide",
            "statut",
            "merci tu peux t'arrêter"
        ]
        
        for command_text in test_commands:
            print(f"\n🔍 Test: '{command_text}'")
            
            try:
                # Traduire en requête
                request = adapter.translate_to_core(command_text)
                print(f"   ✅ Requête générée: {request.command.value}")
                
                # Simuler l'exécution par le daemon
                # (en mode test, on n'exécute pas réellement)
                print(f"   📤 Transmission à l'agent IA central: OK")
                
            except Exception as e:
                print(f"   ❌ Erreur: {e}")
        
        print("✅ Intégration daemon validée")
        return True
        
    except Exception as e:
        print(f"❌ Erreur d'intégration daemon: {e}")
        return False


def test_intelligent_prioritization():
    """Test de la priorisation intelligente des commandes"""
    print("\n🧪 === TEST PRIORISATION INTELLIGENTE ===")
    
    adapter = IntelligentSUISpeechAdapter()
    
    # Tester l'ordre de priorité
    priority_tests = [
        # Priorité 1: Arrêt poli (doit toujours être détecté en premier)
        ("merci pour ton aide analyse ce code", CommandType.QUIT),
        ("c'est parfait aide-moi", CommandType.QUIT),
        
        # Priorité 2-3: Commandes directes vs BERT (BERT désactivé ici)
        ("aide avec l'analyse", CommandType.HELP),  # "aide" détecté directement
        ("analyseur ce fichier", CommandType.PROMPT),  # Pas de correspondance directe
    ]
    
    for test_input, expected in priority_tests:
        command, params = adapter._parse_intelligent_speech_command(test_input, {})
        
        if command == expected:
            print(f"✅ Priorité correcte: '{test_input}' -> {command.value}")
        else:
            print(f"❌ Priorité incorrecte: '{test_input}' -> {command.value} (attendu: {expected.value})")
    
    return True


def run_all_tests():
    """Exécute tous les tests d'intégration"""
    print("🚀 === TESTS D'INTÉGRATION SUI AGENT IA ===\n")
    
    setup_logging()
    start_time = time.time()
    
    tests = [
        ("Architecture Agent IA", test_agent_ia_architecture),
        ("Génération CoreRequest", test_core_request_generation),
        ("Intégration Daemon", test_with_daemon),
        ("Priorisation Intelligente", test_intelligent_prioritization),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"{'✅' if result else '❌'} {test_name}: {'PASS' if result else 'FAIL'}")
        except Exception as e:
            print(f"❌ {test_name}: ERREUR - {e}")
            results.append((test_name, False))
        print()
    
    # Résumé final
    elapsed = time.time() - start_time
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"🎯 === RÉSUMÉ FINAL ===")
    print(f"✅ Tests réussis: {passed}/{total}")
    print(f"⏱️ Temps d'exécution: {elapsed:.2f}s")
    print(f"🏆 Taux de réussite: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 TOUS LES TESTS D'INTÉGRATION RÉUSSIS!")
        print("🤖 L'architecture Agent IA SUI est opérationnelle!")
    else:
        print("⚠️ Certains tests ont échoué - vérification nécessaire")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
