#!/usr/bin/env python3
"""
Test d'intégration pour la fonctionnalité d'arrêt poli de l'interface SUI.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from peer.core.api import CommandType
from peer.interfaces.sui.sui import IntelligentSUISpeechAdapter

def test_polite_quit_detection():
    """Test la détection des intentions d'arrêt polies."""
    print("🧪 Test de détection des intentions d'arrêt polies")
    print("=" * 60)
    
    adapter = IntelligentSUISpeechAdapter()
    
    # Messages d'arrêt polis à tester
    polite_quit_messages = [
        "Merci pour ton aide, tu peux t'arrêter",
        "C'est bon merci",
        "Merci beaucoup, c'est parfait",
        "Super, merci pour tout",
        "Très bien, tu peux arrêter",
        "Parfait, merci de ton aide",
        "Excellent travail, arrête-toi maintenant",
        "Merci, c'est exactement ce qu'il me fallait",
        "Formidable, tu peux te reposer",
        "Génial, merci pour cette assistance"
    ]
    
    # Messages normaux qui ne doivent PAS déclencher l'arrêt
    normal_messages = [
        "Merci de m'expliquer comment ça marche",
        "Peux-tu analyser ce code s'il te plaît",
        "Aide-moi avec ce problème",
        "Explique-moi la fonction",
        "Quelle heure est-il",
        "Comment optimiser ce script"
    ]
    
    print("\n📋 Test des messages d'arrêt polis (doivent retourner QUIT):")
    success_count = 0
    
    for i, message in enumerate(polite_quit_messages, 1):
        normalized = adapter._normalize_speech_input(message)
        command, params = adapter._parse_intelligent_speech_command(normalized, {})
        
        status = "✅ PASS" if command == CommandType.QUIT else "❌ FAIL"
        if command == CommandType.QUIT:
            success_count += 1
            
        print(f"{i:2d}. {status} | '{message}' → {command.value}")
        if command == CommandType.QUIT and "intent" in params:
            print(f"     └─ Intent: {params['intent']}")
    
    print(f"\n📊 Résultats messages d'arrêt: {success_count}/{len(polite_quit_messages)} détectés correctement")
    
    print("\n📋 Test des messages normaux (ne doivent PAS retourner QUIT):")
    normal_success_count = 0
    
    for i, message in enumerate(normal_messages, 1):
        normalized = adapter._normalize_speech_input(message)
        command, params = adapter._parse_intelligent_speech_command(normalized, {})
        
        status = "✅ PASS" if command != CommandType.QUIT else "❌ FAIL"
        if command != CommandType.QUIT:
            normal_success_count += 1
            
        print(f"{i:2d}. {status} | '{message}' → {command.value}")
    
    print(f"\n📊 Résultats messages normaux: {normal_success_count}/{len(normal_messages)} non-arrêt détectés correctement")
    
    # Résumé final
    total_success = success_count + normal_success_count
    total_tests = len(polite_quit_messages) + len(normal_messages)
    success_rate = (total_success / total_tests) * 100
    
    print("\n" + "=" * 60)
    print(f"🎯 RÉSUMÉ FINAL:")
    print(f"   Tests réussis: {total_success}/{total_tests}")
    print(f"   Taux de réussite: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("🎉 Excellent! La fonctionnalité fonctionne très bien.")
    elif success_rate >= 75:
        print("👍 Bien! Quelques ajustements peuvent être nécessaires.")
    else:
        print("⚠️  Des améliorations sont nécessaires.")
    
    return success_rate >= 75

def test_direct_quit_commands():
    """Test les commandes d'arrêt directes."""
    print("\n🧪 Test des commandes d'arrêt directes")
    print("=" * 60)
    
    adapter = IntelligentSUISpeechAdapter()
    
    direct_quit_commands = [
        "arrête",
        "stop",
        "quitter",
        "au revoir",
        "merci",
        "bye",
        "quit"
    ]
    
    success_count = 0
    
    for i, command in enumerate(direct_quit_commands, 1):
        normalized = adapter._normalize_speech_input(command)
        detected_command, params = adapter._parse_intelligent_speech_command(normalized, {})
        
        status = "✅ PASS" if detected_command == CommandType.QUIT else "❌ FAIL"
        if detected_command == CommandType.QUIT:
            success_count += 1
            
        print(f"{i:2d}. {status} | '{command}' → {detected_command.value}")
    
    success_rate = (success_count / len(direct_quit_commands)) * 100
    print(f"\n📊 Commandes directes: {success_count}/{len(direct_quit_commands)} détectées ({success_rate:.1f}%)")
    
    return success_rate >= 90

def test_priority_order():
    """Test que les intentions d'arrêt polies ont bien la priorité."""
    print("\n🧪 Test de l'ordre de priorité")
    print("=" * 60)
    
    adapter = IntelligentSUISpeechAdapter()
    
    # Messages qui contiennent à la fois des mots d'arrêt polis ET d'autres commandes
    mixed_messages = [
        "Aide-moi s'il te plaît, et merci pour ton aide tu peux t'arrêter",
        "Analyse ce code, c'est bon merci",
        "Explique-moi ça, et merci beaucoup c'est parfait",
        "Quelle heure est-il ? Bon, merci pour tout"
    ]
    
    success_count = 0
    
    print("Messages mixtes (l'arrêt poli doit avoir la priorité):")
    for i, message in enumerate(mixed_messages, 1):
        normalized = adapter._normalize_speech_input(message)
        command, params = adapter._parse_intelligent_speech_command(normalized, {})
        
        status = "✅ PASS" if command == CommandType.QUIT else "❌ FAIL"
        if command == CommandType.QUIT:
            success_count += 1
            
        print(f"{i:2d}. {status} | '{message}'")
        print(f"     └─ Commande détectée: {command.value}")
        if "intent" in params:
            print(f"     └─ Intent: {params.get('intent', 'N/A')}")
    
    success_rate = (success_count / len(mixed_messages)) * 100
    print(f"\n📊 Priorité d'arrêt: {success_count}/{len(mixed_messages)} correctes ({success_rate:.1f}%)")
    
    return success_rate >= 75

if __name__ == "__main__":
    print("🚀 Test d'intégration de la fonctionnalité d'arrêt poli SUI")
    print("=" * 80)
    
    # Exécuter tous les tests
    test1_ok = test_polite_quit_detection()
    test2_ok = test_direct_quit_commands()
    test3_ok = test_priority_order()
    
    # Résumé final
    all_tests_passed = test1_ok and test2_ok and test3_ok
    
    print("\n" + "=" * 80)
    print("🎯 RÉSUMÉ DES TESTS:")
    print(f"   ✅ Détection intentions polies: {'PASS' if test1_ok else 'FAIL'}")
    print(f"   ✅ Commandes directes: {'PASS' if test2_ok else 'FAIL'}")
    print(f"   ✅ Ordre de priorité: {'PASS' if test3_ok else 'FAIL'}")
    print(f"\n🏆 RÉSULTAT GLOBAL: {'SUCCESS' if all_tests_passed else 'NEEDS IMPROVEMENT'}")
    
    sys.exit(0 if all_tests_passed else 1)
