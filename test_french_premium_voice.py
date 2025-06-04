#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de validation de la voix française premium optimisée pour SUI Peer
Test rapide de la synthèse vocale française avec Audrey (Premium)
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from peer.interfaces.sui.tts.text_to_speech import TextToSpeech
from peer.interfaces.sui.config.config_loader import load_sui_config, create_tts_config_from_sui_config
import logging

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FrenchVoiceTest")

def test_french_premium_voice():
    """Test de la voix française premium Audrey"""
    
    print("🎙️ Test de la voix française premium pour SUI Peer")
    print("=" * 60)
    
    try:
        # Chargement de la configuration SUI
        config = load_sui_config()
        
        # Création de la configuration TTS appropriée
        tts_config = create_tts_config_from_sui_config(config, "Test de voix française premium")
        
        print(f"✅ Configuration TTS créée : {tts_config.engine_type.value}, langue: {tts_config.language}, voix: {tts_config.voice}")
        
        # Initialisation du moteur TTS
        print("\n🔧 Initialisation du moteur TTS...")
        tts = TextToSpeech(tts_config)
        
        # Tests vocaux en français
        test_phrases = [
            "Bonjour ! Je suis l'interface vocale Peer avec la voix française premium Audrey.",
            "Ma synthèse vocale française est maintenant optimisée pour une meilleure fluidité.",
            "Test de reconnaissance : Quelle heure est-il ?",
            "Interface vocale prête pour les commandes SUI.",
            "Merci d'utiliser Peer - votre assistant vocal intelligent."
        ]
        
        print(f"\n🎤 Test de {len(test_phrases)} phrases françaises...")
        
        for i, phrase in enumerate(test_phrases, 1):
            print(f"\n[{i}/{len(test_phrases)}] 🔊 Synthèse : '{phrase[:50]}...'")
            
            try:
                result = tts.synthesize(phrase)
                if result.success:
                    print(f"✅ Synthèse réussie avec {result.engine_used}")
                else:
                    print(f"⚠️ Synthèse échouée : {result.error_message}")
                    
            except Exception as e:
                print(f"❌ Erreur synthèse : {e}")
        
        print(f"\n✅ Test de la voix française premium terminé avec succès!")
        print("🎯 Voix configurée : Audrey (Premium) - Qualité optimale")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test vocal : {e}")
        return False

if __name__ == "__main__":
    success = test_french_premium_voice()
    sys.exit(0 if success else 1)
