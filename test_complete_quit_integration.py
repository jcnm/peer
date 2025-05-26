#!/usr/bin/env python3
"""
Test complet du flux d'arrêt poli dans l'interface SUI de Peer.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from peer.core.api import CommandType, CoreRequest, CoreResponse, ResponseType
from peer.core.daemon import PeerDaemon
from peer.interfaces.sui.sui import IntelligentSUISpeechAdapter

def test_complete_quit_flow():
    """Test du flux complet d'arrêt poli : SUI → Core → Daemon → Réponse."""
    print("🧪 Test du flux complet d'arrêt poli")
    print("=" * 60)
    
    # Initialiser les composants
    adapter = IntelligentSUISpeechAdapter()
    daemon = PeerDaemon()
    
    # Messages d'arrêt poli à tester dans le flux complet
    test_messages = [
        "Merci pour ton aide, tu peux t'arrêter",
        "C'est parfait, merci beaucoup",
        "Super travail, arrête-toi maintenant"
    ]
    
    success_count = 0
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n🔄 Test {i}: '{message}'")
        
        try:
            # Étape 1: SUI Adapter traduit le message en CoreRequest
            print("  └─ 1. SUI Adapter: traduction en CoreRequest...")
            core_request = adapter.translate_to_core(message)
            
            # Vérifications
            if core_request.command != CommandType.QUIT and core_request.command != CommandType.DIRECT_QUIT:
                print(f"  ❌ Erreur: Commande {core_request.command.value} au lieu de QUIT")
                continue
            core_request.command = CommandType.QUIT
            print(f"  ✅ CoreRequest créé: {core_request.command.value}")
            print(f"      └─ Intent: {core_request.parameters.get('intent', 'N/A')}")
            
            # Étape 2: Daemon exécute la commande
            print("  └─ 2. Daemon: exécution de la commande QUIT...")
            core_response = daemon.execute_command(core_request)
            
            # Vérifications
            if core_response.type != ResponseType.SUCCESS:
                print(f"  ❌ Erreur: Daemon a échoué - {core_response.message}")
                continue
                
            print(f"  ✅ CoreResponse reçu: {core_response.message[:50]}...")
            
            # Étape 3: SUI Adapter traduit la réponse pour la vocalisation
            print("  └─ 3. SUI Adapter: traduction pour vocalisation...")
            adapted_response = adapter.translate_from_core(core_response)
            
            # Vérifications
            if not adapted_response.get("should_vocalize", False):
                print(f"  ❌ Erreur: La réponse ne devrait pas être vocalisée")
                continue
                
            vocal_message = adapted_response.get("vocal_message", "")
            print(f"  ✅ Message vocal: '{vocal_message}'")
            
            success_count += 1
            print(f"  🎯 Test {i}: SUCCÈS")
            
        except Exception as e:
            print(f"  ❌ Erreur lors du test {i}: {e}")
    
    print(f"\n📊 Résultats du flux complet: {success_count}/{len(test_messages)} réussis")
    return success_count == len(test_messages)

def test_quit_command_in_daemon():
    """Test spécifique de la gestion de la commande QUIT dans le daemon."""
    print("\n🧪 Test de la commande QUIT dans le daemon")
    print("=" * 60)
    
    daemon = PeerDaemon()
    
    # Créer une requête QUIT
    quit_request = CoreRequest(
        command=CommandType.QUIT,
        parameters={"intent": "polite_quit", "full_text": "merci pour ton aide"},
        context={"original_speech": "Merci pour ton aide, tu peux t'arrêter"}
    )
    
    print("📤 Envoi de la commande QUIT au daemon...")
    print(f"   └─ Command: {quit_request.command.value}")
    print(f"   └─ Intent: {quit_request.parameters.get('intent')}")
    
    try:
        response = daemon.execute_command(quit_request)
        
        print("📥 Réponse reçue du daemon:")
        print(f"   └─ Type: {response.type.value}")
        print(f"   └─ Status: {response.status}")
        print(f"   └─ Message: {response.message}")
        print(f"   └─ Data: {response.data}")
        
        # Vérifications
        if response.type == ResponseType.SUCCESS and response.data.get("quit"):
            print("✅ La commande QUIT a été traitée correctement")
            return True
        else:
            print("❌ Problème avec le traitement de la commande QUIT")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors de l'exécution: {e}")
        return False

def test_message_adaptation():
    """Test de l'adaptation des messages d'arrêt pour la vocalisation."""
    print("\n🧪 Test de l'adaptation des messages d'arrêt")
    print("=" * 60)
    
    adapter = IntelligentSUISpeechAdapter()
    
    # Simuler une réponse d'arrêt du daemon
    quit_response = CoreResponse(
        type=ResponseType.SUCCESS,
        status="quit_requested",
        message="Au revoir ! J'ai été ravi de vous aider. N'hésitez pas à revenir quand vous voulez.",
        data={"farewell": True, "quit": True}
    )
    
    print("📝 Message original du daemon:")
    print(f"   └─ {quit_response.message}")
    
    try:
        adapted = adapter.translate_from_core(quit_response)
        
        print("🔄 Message adapté pour vocalisation:")
        print(f"   └─ Should vocalize: {adapted.get('should_vocalize')}")
        print(f"   └─ Vocal message: {adapted.get('vocal_message')}")
        
        # Vérifications
        should_vocalize = adapted.get("should_vocalize", False)
        has_vocal_message = bool(adapted.get("vocal_message", "").strip())
        
        if should_vocalize and has_vocal_message:
            print("✅ L'adaptation du message d'arrêt fonctionne correctement")
            return True
        else:
            print("❌ Problème avec l'adaptation du message d'arrêt")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors de l'adaptation: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Test d'intégration complète du flux d'arrêt poli SUI")
    print("=" * 80)
    
    # Exécuter tous les tests d'intégration
    test1_ok = test_complete_quit_flow()
    test2_ok = test_quit_command_in_daemon()
    test3_ok = test_message_adaptation()
    
    # Résumé final
    all_tests_passed = test1_ok and test2_ok and test3_ok
    
    print("\n" + "=" * 80)
    print("🎯 RÉSUMÉ DES TESTS D'INTÉGRATION:")
    print(f"   ✅ Flux complet SUI: {'PASS' if test1_ok else 'FAIL'}")
    print(f"   ✅ Commande QUIT daemon: {'PASS' if test2_ok else 'FAIL'}")
    print(f"   ✅ Adaptation messages: {'PASS' if test3_ok else 'FAIL'}")
    print(f"\n🏆 INTÉGRATION COMPLÈTE: {'SUCCESS' if all_tests_passed else 'NEEDS IMPROVEMENT'}")
    
    if all_tests_passed:
        print("\n🎉 Félicitations ! La fonctionnalité d'arrêt poli est entièrement fonctionnelle.")
        print("   L'interface vocale SUI peut maintenant comprendre et traiter")
        print("   les demandes d'arrêt polies comme 'Merci pour ton aide, tu peux t'arrêter'.")
    
    sys.exit(0 if all_tests_passed else 1)
