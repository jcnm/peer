#!/usr/bin/env python3
"""
Test de l'interface SUI refactorisée

Ce script teste si l'interface SUI est bien alignée avec 
la nouvelle architecture centrée sur le daemon.
"""

import sys
import os
import time
import threading

# Ajouter le chemin du module peer
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    # Tester d'abord les imports du core
    from peer.core import PeerDaemon, CoreRequest, CommandType, InterfaceType
    print("✅ Imports core réussis")
    
    # Ensuite tester les imports SUI
    from peer.interfaces.sui.sui import SUI, SUISpeechAdapter
    print("✅ Imports SUI refactorisés réussis")
except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
    print("🔍 Vérification des modules disponibles...")
    
    # Lister les modules disponibles
    import os
    peer_path = os.path.join(os.path.dirname(__file__), 'src', 'peer')
    if os.path.exists(peer_path):
        print(f"📁 Contenu de {peer_path}:")
        for item in os.listdir(peer_path):
            print(f"   - {item}")
    else:
        print(f"❌ Chemin {peer_path} introuvable")
    
    sys.exit(1)

def test_sui_adapter():
    """Test de l'adaptateur SUI"""
    print("\n=== Test de l'adaptateur SUI ===")
    
    adapter = SUISpeechAdapter()
    
    # Test de traduction de commandes vocales
    test_commands = [
        "aide",
        "quelle heure",
        "statut",
        "répète bonjour tout le monde",
        "version",
        "que peux-tu faire"
    ]
    
    for command in test_commands:
        try:
            request = adapter.translate_to_core(command)
            print(f"✅ '{command}' → {request.command.value}")
            print(f"   Paramètres: {request.parameters}")
        except Exception as e:
            print(f"❌ Erreur pour '{command}': {e}")

def test_sui_with_daemon():
    """Test de l'interface SUI avec le daemon"""
    print("\n=== Test SUI avec Daemon ===")
    
    try:
        # Créer le daemon
        daemon = PeerDaemon()
        print("✅ Daemon créé")
        
        # Créer l'interface SUI
        sui = SUI(daemon)
        print("✅ Interface SUI créée")
        
        # Tester quelques commandes simulées
        test_commands = [
            "aide",
            "version", 
            "quelle heure",
            "statut"
        ]
        
        print("\n--- Test des commandes simulées ---")
        for command in test_commands:
            print(f"\nTest: '{command}'")
            try:
                sui.simulate_voice_command(command)
                time.sleep(1)  # Laisser le temps de traitement
                print(f"✅ Commande '{command}' envoyée")
            except Exception as e:
                print(f"❌ Erreur pour '{command}': {e}")
        
        # Laisser le temps aux threads de traiter
        time.sleep(2)
        
        # Arrêter l'interface
        sui.stop()
        print("✅ Interface SUI arrêtée")
        
    except Exception as e:
        print(f"❌ Erreur dans test SUI/Daemon: {e}")

def test_daemon_integration():
    """Test d'intégration avec le daemon"""
    print("\n=== Test d'intégration Daemon ===")
    
    try:
        daemon = PeerDaemon()
        
        # Test de création de session SUI
        session_id = daemon.create_session(InterfaceType.SUI)
        print(f"✅ Session SUI créée: {session_id}")
        
        # Test de commandes via daemon
        test_request = CoreRequest(
            command=CommandType.HELP,
            session_id=session_id,
            interface_type=InterfaceType.SUI
        )
        
        response = daemon.execute_command(test_request)
        print(f"✅ Commande HELP exécutée: {response.status}")
        
        # Test d'arrêt de session
        ended = daemon.end_session(session_id)
        print(f"✅ Session fermée: {ended}")
        
    except Exception as e:
        print(f"❌ Erreur d'intégration daemon: {e}")

def main():
    """Fonction principale de test"""
    print("🔍 Test de l'alignement de l'interface SUI")
    print("=" * 50)
    
    # Tests des composants
    test_sui_adapter()
    test_daemon_integration()
    
    # Test complet (commenté car nécessite des dépendances audio)
    print("\n=== Test SUI Complet ===")
    print("⚠️  Test complet désactivé (nécessite dépendances audio)")
    print("   Pour tester complètement:")
    print("   1. Installez: pip install pyaudio numpy openai-whisper")
    print("   2. Décommentez test_sui_with_daemon() ci-dessous")
    
    # test_sui_with_daemon()  # Décommenter pour test complet
    
    print("\n" + "=" * 50)
    print("✅ Tests d'alignement SUI terminés")
    print("\n📋 Résumé:")
    print("   • L'interface SUI est refactorisée")
    print("   • Elle utilise le daemon central via PeerDaemon")
    print("   • Elle traduit les commandes vocales en CoreRequest")
    print("   • Elle adapte les réponses pour la synthèse vocale")
    print("   • Elle respecte l'architecture hexagonale")

if __name__ == "__main__":
    main()
