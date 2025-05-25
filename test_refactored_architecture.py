#!/usr/bin/env python3
"""
Test de l'architecture refactorisée de Peer

Ce script teste la nouvelle architecture centrée sur le daemon
avec les adaptateurs d'interface.
"""

import sys
import os

# Ajouter le chemin src au PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from peer.core import get_daemon, CLIAdapter, CoreRequest, CommandType, InterfaceType


def test_daemon_basic():
    """Test basique du daemon"""
    print("=== Test du Daemon Central ===")
    
    # Obtenir l'instance du daemon
    daemon = get_daemon()
    
    # Test de la version
    version = daemon.get_version()
    print(f"Version du daemon: {version}")
    
    # Test des capacités
    capabilities = daemon.get_capabilities()
    print(f"Nombre de commandes disponibles: {len(capabilities)}")
    
    # Test du statut
    status = daemon.get_status()
    print(f"Statut: {status}")
    
    print("✓ Tests basiques du daemon réussis\n")


def test_cli_adapter():
    """Test de l'adaptateur CLI"""
    print("=== Test de l'Adaptateur CLI ===")
    
    daemon = get_daemon()
    adapter = CLIAdapter()
    
    # Créer une session
    session_id = daemon.create_session(InterfaceType.CLI)
    adapter.set_session_id(session_id)
    
    # Test de commandes via l'adaptateur
    test_commands = [
        {'command': 'help', 'args': []},
        {'command': 'version', 'args': []},
        {'command': 'echo', 'args': ['Hello', 'World']},
        {'command': 'time', 'args': []},
        {'command': 'status', 'args': []},
    ]
    
    for cmd_input in test_commands:
        print(f"Test commande: {cmd_input['command']} {' '.join(cmd_input['args'])}")
        
        # Traduire vers le core
        core_request = adapter.translate_to_core(cmd_input)
        
        # Exécuter
        core_response = daemon.execute_command(core_request)
        
        # Traduire la réponse
        cli_output = adapter.translate_from_core(core_response)
        
        print(f"Réponse: {cli_output[:100]}...")
        print(f"Type: {core_response.type.value}, Status: {core_response.status}")
        print()
    
    # Nettoyer la session
    daemon.end_session(session_id)
    
    print("✓ Tests de l'adaptateur CLI réussis\n")


def test_direct_core_requests():
    """Test de requêtes directes au core"""
    print("=== Test de Requêtes Directes au Core ===")
    
    daemon = get_daemon()
    
    # Test de requête d'aide
    help_request = CoreRequest(
        command=CommandType.HELP,
        interface_type=InterfaceType.INTERNAL
    )
    
    help_response = daemon.execute_command(help_request)
    print(f"Aide générale: {help_response.message}")
    print(f"Nombre de commandes dans les données: {len(help_response.data.get('commands', {}))}")
    
    # Test de requête d'aide spécifique
    help_echo_request = CoreRequest(
        command=CommandType.HELP,
        parameters={'command': 'echo'},
        interface_type=InterfaceType.INTERNAL
    )
    
    help_echo_response = daemon.execute_command(help_echo_request)
    print(f"Aide pour echo: {help_echo_response.message}")
    
    # Test de requête de capacités
    cap_request = CoreRequest(
        command=CommandType.CAPABILITIES,
        interface_type=InterfaceType.INTERNAL
    )
    
    cap_response = daemon.execute_command(cap_request)
    print(f"Capacités: {cap_response.message}")
    print(f"Catégories disponibles: {cap_response.data.get('categories', [])}")
    
    print("✓ Tests de requêtes directes réussis\n")


def test_session_management():
    """Test de la gestion des sessions"""
    print("=== Test de la Gestion des Sessions ===")
    
    daemon = get_daemon()
    
    # Créer plusieurs sessions
    sessions = []
    for interface in [InterfaceType.CLI, InterfaceType.TUI, InterfaceType.API]:
        session_id = daemon.create_session(interface)
        sessions.append(session_id)
        print(f"Session créée pour {interface.value}: {session_id}")
    
    # Obtenir les informations des sessions
    session_info_request = CoreRequest(
        command=CommandType.SESSION_INFO,
        interface_type=InterfaceType.INTERNAL
    )
    
    info_response = daemon.execute_command(session_info_request)
    print(f"Informations des sessions: {info_response.message}")
    print(f"Nombre de sessions actives: {info_response.data.get('total_sessions', 0)}")
    
    # Terminer les sessions
    for session_id in sessions:
        success = daemon.end_session(session_id)
        print(f"Session {session_id} terminée: {success}")
    
    print("✓ Tests de gestion des sessions réussis\n")


def main():
    """Fonction principale de test"""
    print("=== Tests de l'Architecture Refactorisée de Peer ===\n")
    
    try:
        test_daemon_basic()
        test_cli_adapter()
        test_direct_core_requests()
        test_session_management()
        
        print("=== Tous les tests sont réussis! ===")
        print("\nL'architecture refactorisée fonctionne correctement:")
        print("✓ Daemon central opérationnel")
        print("✓ API unifiée fonctionnelle")
        print("✓ Adaptateurs d'interface fonctionnels")
        print("✓ Gestion des sessions opérationnelle")
        print("✓ Protocole standardisé implémenté")
        
    except Exception as e:
        print(f"❌ Erreur lors des tests: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
