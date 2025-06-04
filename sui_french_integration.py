#!/usr/bin/env python3
"""
Script d'intégration SUI + TTS Français
=====================================
"""

import sys
import os
from pathlib import Path

# Ajout du chemin Peer
sys.path.insert(0, "/Users/smpceo/Desktop/peer/src")

try:
    from peer.interfaces.sui.tts.text_to_speech import TextToSpeech
    from peer.interfaces.sui.tts.base import TTSConfig, TTSEngineType
    
    print("🇫🇷 Test intégration SUI + TTS Français")
    print("="*40)
    
    # Configuration française optimisée
    config = TTSConfig(
        engine_type=TTSEngineType.SIMPLE,
        language="fr",
        voice="Audrey",
        engine_specific_params={
            "rate": 190,
            "volume": 0.8,
            "preferred_simple_engine_order": ["say", "pyttsx3"]
        }
    )
    
    # Initialisation TTS
    tts = TextToSpeech(config)
    
    # Test de synthèse
    test_phrases = [
        "Bonjour, je suis votre assistant vocal Peer.",
        "Le système de synthèse vocale française est maintenant opérationnel.",  
        "Merci d'avoir testé le système SUI avec la voix française."
    ]
    
    for i, phrase in enumerate(test_phrases, 1):
        print(f"🎤 [{i}/{len(test_phrases)}] Synthèse : {phrase[:50]}...")
        
        try:
            result = tts.synthesize(phrase)
            if result and result.success and os.path.exists(result.audio_path):
                print(f"✅ Synthèse réussie")
                # Lecture
                os.system(f"afplay '{result.audio_path}'")
                # Nettoyage optionnel (les fichiers temp sont auto-nettoyés)
            else:
                print(f"❌ Échec synthèse")
        except Exception as e:
            print(f"❌ Erreur : {e}")
    
    print("\n🎉 Test d'intégration terminé !")
    
except ImportError as e:
    print(f"❌ Erreur d'import : {e}")
except Exception as e:
    print(f"❌ Erreur générale : {e}")
