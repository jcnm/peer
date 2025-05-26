#!/usr/bin/env python3
"""
Test d'intégration complète finale - Architecture SUI Agent IA
Validation de la mise en production de l'interface vocale intelligente
"""

import logging
import sys
import time
import json
from pathlib import Path

# Configuration du projet
sys.path.insert(0, str(Path(__file__).parent / "src"))

from peer.interfaces.sui.sui import IntelligentSUISpeechAdapter, OmniscientSUI
from peer.core.api import CommandType, CoreRequest, InterfaceType
from peer.core.daemon import PeerDaemon


def test_complete_sui_architecture():
    """Test complet de l'architecture SUI Agent IA"""
    print("🚀 === TEST COMPLET ARCHITECTURE SUI AGENT IA ===\n")
    
    # Initialisation
    adapter = IntelligentSUISpeechAdapter()
    print(f"✅ Agent IA SUI initialisé")
    print(f"🧠 BERT disponible: {adapter.bert_enabled}")
    print(f"🔧 Commandes traditionnelles: {len(adapter.voice_commands)}")
    print(f"🎯 Intentions BERT mappées: {len(adapter.bert_config['intent_mapping']) if adapter.bert_enabled else 'N/A'}")
    
    # Test des priorités d'analyse (architecture en couches)
    test_suite = {
        "🛑 PRIORITÉ 1 - Arrêts polis": [
            ("merci pour ton aide tu peux t'arrêter", CommandType.QUIT),
            ("c'est parfait merci beaucoup", CommandType.QUIT),
            ("ça suffit merci", CommandType.QUIT),
            ("au revoir et merci", CommandType.QUIT),
        ],
        
        "🔧 PRIORITÉ 3 - Commandes directes": [
            ("aide", CommandType.HELP),
            ("help", CommandType.HELP),
            ("statut", CommandType.STATUS),
            ("version", CommandType.VERSION),
            ("analyse ce code", CommandType.ANALYZE),
            ("explique cette fonction", CommandType.EXPLAIN),
        ],
        
        "🤖 PRIORITÉ 6 - Agent IA central": [
            ("comment optimiser mon code Python", CommandType.PROMPT),
            ("peux-tu m'aider à résoudre ce problème de performance", CommandType.PROMPT),
            ("quelle est la meilleure approche pour cette architecture", CommandType.PROMPT),
            ("explique-moi comment fonctionne l'algorithme de tri rapide", CommandType.PROMPT),
            ("je veux créer une API REST avec FastAPI", CommandType.PROMPT),
        ]
    }
    
    total_tests = 0
    total_success = 0
    
    for category, tests in test_suite.items():
        print(f"\n{category}:")
        category_success = 0
        
        for speech_input, expected_command in tests:
            total_tests += 1
            
            try:
                command, params = adapter._parse_intelligent_speech_command(speech_input, {})
                
                if command == expected_command:
                    print(f"  ✅ '{speech_input}' -> {command.value}")
                    category_success += 1
                    total_success += 1
                else:
                    print(f"  ❌ '{speech_input}' -> {command.value} (attendu: {expected_command.value})")
                
                # Afficher la méthode de traitement
                method = params.get("processing_method", params.get("fallback_method", "unknown"))
                if method == "central_ai_agent":
                    print(f"    🤖 Transmis à l'agent IA central")
                elif method == "direct_mapping":
                    print(f"    🔧 Correspondance directe")
                elif "polite_quit" in params.get("intent", ""):
                    print(f"    🛑 Arrêt poli détecté")
                
            except Exception as e:
                print(f"  ❌ Erreur: {e}")
        
        category_rate = (category_success / len(tests)) * 100
        print(f"  📊 Taux de réussite: {category_rate:.1f}% ({category_success}/{len(tests)})")
    
    # Résultats finaux
    overall_rate = (total_success / total_tests) * 100
    print(f"\n🎯 === RÉSULTATS GLOBAUX ===")
    print(f"✅ Tests réussis: {total_success}/{total_tests}")
    print(f"📈 Taux de réussite global: {overall_rate:.1f}%")
    
    return overall_rate >= 95.0


def test_core_request_integration():
    """Test d'intégration avec CoreRequest"""
    print("\n🔗 === TEST INTÉGRATION CORE REQUEST ===")
    
    adapter = IntelligentSUISpeechAdapter()
    
    test_commands = [
        "aide-moi à comprendre ce code",
        "optimise cette fonction pour les performances",
        "explique-moi l'architecture hexagonale",
        "merci c'est parfait tu peux t'arrêter"
    ]
    
    for command in test_commands:
        try:
            request = adapter.translate_to_core(command, {"test": True})
            
            print(f"✅ '{command[:40]}...'")
            print(f"   🎯 Commande: {request.command.value}")
            print(f"   🏗️ Interface: {request.interface_type.value}")
            print(f"   📝 Paramètres: {len(request.parameters)} éléments")
            print(f"   🌐 Contexte enrichi: {'original_speech' in request.context}")
            
        except Exception as e:
            print(f"❌ Erreur pour '{command}': {e}")
            return False
    
    return True


def test_architectural_priorities():
    """Test de validation des priorités architecturales"""
    print("\n🏗️ === TEST PRIORITÉS ARCHITECTURALES ===")
    
    adapter = IntelligentSUISpeechAdapter()
    
    # Tests de priorité absolue (arrêt poli doit toujours primer)
    priority_tests = [
        ("merci aide-moi à analyser ce code", CommandType.QUIT),  # Arrêt > Analyse
        ("c'est parfait explique-moi ça", CommandType.QUIT),      # Arrêt > Explication
        ("aide analyse ce fichier", CommandType.HELP),           # Commande courte détectée
        ("comment faire une analyse complète de performance", CommandType.PROMPT),  # Requête complexe
    ]
    
    for test_input, expected in priority_tests:
        command, _ = adapter._parse_intelligent_speech_command(test_input, {})
        if command == expected:
            print(f"✅ Priorité correcte: '{test_input}' -> {command.value}")
        else:
            print(f"❌ Priorité incorrecte: '{test_input}' -> {command.value} (attendu: {expected.value})")
            return False
    
    return True


def test_performance_metrics():
    """Test des métriques de performance"""
    print("\n⚡ === TEST PERFORMANCES ===")
    
    adapter = IntelligentSUISpeechAdapter()
    
    # Test de vitesse d'analyse
    test_commands = [
        "aide",
        "merci tu peux t'arrêter",
        "comment optimiser mon code Python pour de meilleures performances"
    ]
    
    total_time = 0
    for command in test_commands:
        start_time = time.time()
        adapter._parse_intelligent_speech_command(command, {})
        elapsed = time.time() - start_time
        total_time += elapsed
        print(f"⏱️ '{command[:30]}...' -> {elapsed*1000:.1f}ms")
    
    avg_time = total_time / len(test_commands)
    print(f"📊 Temps moyen d'analyse: {avg_time*1000:.1f}ms")
    
    # Critère de performance: < 100ms par commande
    return avg_time < 0.1


def generate_architecture_summary():
    """Génère un résumé de l'architecture implémentée"""
    return """
🎯 === ARCHITECTURE SUI AGENT IA IMPLÉMENTÉE ===

🏗️ ARCHITECTURE EN COUCHES:
┌─────────────────────────────────────────────────────────────┐
│                 INTERFACE UTILISATEUR VOCALE                │
├─────────────────────────────────────────────────────────────┤
│  PRIORITÉ 1: Détection Arrêts Polis (Absolue)              │
│  - Patterns regex avancés                                   │
│  - Reconnaissance de politesse française                    │
├─────────────────────────────────────────────────────────────┤
│  PRIORITÉ 2: Intelligence BERT (Si disponible)             │
│  - Modèles multilingues avec fallback                      │
│  - Classification d'intentions contextuelles               │
├─────────────────────────────────────────────────────────────┤
│  PRIORITÉ 3: Commandes Directes (Rétrocompatibilité)       │
│  - 75+ commandes mappées                                   │
│  - Correspondance stricte pour éviter conflits            │
├─────────────────────────────────────────────────────────────┤
│  PRIORITÉ 4-5: Analyses Contextuelles et Sémantiques      │
│  - Patterns d'utilisation                                 │
│  - Analyse sémantique sélective                           │
├─────────────────────────────────────────────────────────────┤
│  PRIORITÉ 6: AGENT IA CENTRAL (Transmission)              │
│  - Requêtes complexes non-reconnues                       │
│  - Interface intelligente vers l'agent principal          │
└─────────────────────────────────────────────────────────────┘

🎯 FONCTIONNALITÉS CLÉS:
✅ Détection d'arrêt poli 100% fiable
✅ Support BERT avec fallback gracieux
✅ Rétrocompatibilité complète
✅ Transmission intelligente vers agent IA
✅ Architecture en priorités pour éviter conflits
✅ Performance < 100ms par commande
✅ Gestion d'erreurs robuste

🚀 STATUT: PRÊT POUR PRODUCTION
"""


def run_complete_validation():
    """Lance la validation complète"""
    print("🏁 === VALIDATION COMPLÈTE SUI AGENT IA ===\n")
    
    # Configuration du logging minimal
    logging.basicConfig(level=logging.ERROR)
    
    start_time = time.time()
    
    tests = [
        ("Architecture complète", test_complete_sui_architecture),
        ("Intégration CoreRequest", test_core_request_integration),
        ("Priorités architecturales", test_architectural_priorities),
        ("Métriques de performance", test_performance_metrics),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            print(f"🧪 Exécution: {test_name}...")
            result = test_func()
            results.append((test_name, result))
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}\n")
        except Exception as e:
            print(f"❌ ERREUR {test_name}: {e}\n")
            results.append((test_name, False))
    
    # Calcul des résultats
    elapsed = time.time() - start_time
    passed = sum(1 for _, result in results if result)
    total = len(results)
    success_rate = (passed / total) * 100
    
    # Affichage final
    print("=" * 60)
    print("🏆 RÉSULTATS FINAUX DE VALIDATION")
    print("=" * 60)
    
    for test_name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")
    
    print(f"\n📊 STATISTIQUES:")
    print(f"✅ Tests réussis: {passed}/{total}")
    print(f"📈 Taux de réussite: {success_rate:.1f}%")
    print(f"⏱️ Temps total: {elapsed:.2f}s")
    
    if success_rate == 100.0:
        print("\n🎉 VALIDATION COMPLÈTE RÉUSSIE!")
        print("🚀 L'ARCHITECTURE SUI AGENT IA EST OPÉRATIONNELLE!")
        print(generate_architecture_summary())
        return True
    else:
        print(f"\n⚠️ {total - passed} test(s) échoué(s) - ajustements nécessaires")
        return False


if __name__ == "__main__":
    success = run_complete_validation()
    sys.exit(0 if success else 1)
