#!/usr/bin/env python3
"""
Test simple pour vérifier le fonctionnement de base du nouveau système.
"""

import os
import sys

# Ajouter le répertoire source au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    print("🔄 Import du moteur NLP...")
    from peer.interfaces.sui.nlp_engine import HybridNLPEngine
    print("✅ Import réussi!")
    
    print("🔄 Initialisation du moteur...")
    engine = HybridNLPEngine()
    print("✅ Initialisation réussie!")
    
    print("🔄 Test simple...")
    result = engine.extract_intent("Merci pour ton aide, maintenant stop")
    print(f"✅ Résultat: {result}")
    
    if result:
        print(f"📊 Type de commande: {result.command_type}")
        print(f"📊 Confiance: {result.confidence}")
        print(f"📊 Méthode: {result.method_used}")
        if hasattr(result, 'response_data'):
            print(f"📊 Données de réponse: {result.response_data}")
    
    print("🎉 Test simple réussi!")
    
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
