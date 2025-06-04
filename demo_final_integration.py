#!/usr/bin/env python3
"""
DÉMONSTRATION FINALE - Système Vocal Français Peer SUI
=====================================================
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path("/Users/smpceo/Desktop/peer/src")))

try:
    from peer.interfaces.sui.tts.text_to_speech import TextToSpeech
    from peer.interfaces.sui.tts.base import TTSConfig, TTSEngineType
    
    print("🇫🇷 DÉMONSTRATION SYSTÈME VOCAL FRANÇAIS PEER")
    print("=" * 50)
    
    # Configuration française optimisée
    config = TTSConfig(
        engine_type=TTSEngineType.SIMPLE,
        language="fr",
        voice="Audrey",
        engine_specific_params={
            "preferred_simple_engine_order": ["say"]
        }
    )
    
    tts = TextToSpeech(config)
    
    # Messages de démonstration
    messages = [
        ("Bienvenue", "Bienvenue dans le système vocal français de Peer."),
        ("Présentation", "Je suis votre assistant vocal intelligent, utilisant la voix française Audrey."),
        ("Fonctionnalités", "Je peux comprendre et répondre en français avec une voix naturelle."),
        ("SUI", "Le système SUI est maintenant opérationnel avec support vocal français complet."),
        ("Conclusion", "L\'intégration du système vocal français dans Peer est maintenant terminée.")
    ]
    
    print("\n🎤 Démonstration vocale :")
    print("-" * 30)
    
    for i, (titre, message) in enumerate(messages, 1):
        print(f"[{i}/{len(messages)}] {titre}...")
        
        try:
            result = tts.synthesize(message)
            if result.success:
                print(f"    ✅ Synthèse réussie")
                time.sleep(1.5)  # Pause entre messages
            else:
                print(f"    ❌ Erreur : {result.error_message}")
        except Exception as e:
            print(f"    ❌ Exception : {e}")
    
    print("\n🎉 DÉMONSTRATION TERMINÉE !")
    print("✅ Système vocal français Peer SUI opérationnel")
    print("\n📋 UTILISATION :")
    print("  • Lancer SUI : ./run_sui.sh")
    print("  • Voix utilisée : Audrey (français)")
    print("  • Engine : SimpleTTS (vocalisation directe)")
    print("  • Configuration : /Users/smpceo/.peer/config/sui/models.yaml")
    
except ImportError as e:
    print(f"❌ Erreur import : {e}")
except Exception as e:
    print(f"❌ Erreur générale : {e}")
