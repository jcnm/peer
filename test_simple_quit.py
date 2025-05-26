#!/usr/bin/env python3
"""Test simple d'intégration d'arrêt poli."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from peer.core.api import CommandType
    from peer.interfaces.sui.sui import IntelligentSUISpeechAdapter
    
    print("🧪 Test simple d'intégration d'arrêt poli")
    print("=" * 50)
    
    # Test basique
    adapter = IntelligentSUISpeechAdapter()
    
    test_message = "Merci pour ton aide, tu peux t'arrêter"
    print(f"Message testé: '{test_message}'")
    
    # Test de traduction
    core_request = adapter.translate_to_core(test_message)
    
    print(f"Commande détectée: {core_request.command.value}")
    print(f"Paramètres: {core_request.parameters}")
    
    if core_request.command == CommandType.QUIT:
        print("✅ SUCCESS: L'arrêt poli fonctionne !")
    else:
        print("❌ FAIL: L'arrêt poli ne fonctionne pas")
        
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
