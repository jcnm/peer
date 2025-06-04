#!/usr/bin/env python3

import os
import sys
sys.path.append('/Users/smpceo/Desktop/peer/src')

from peer.interfaces.sui.tts.advanced_tts_engine import AdvancedTTS
from peer.interfaces.sui.tts.base import TTSConfig, TTSEngineType

def test_piper_tts():
    """Test Piper TTS functionality"""
    
    # Configuration pour Piper
    config = TTSConfig(
        engine_type=TTSEngineType.ADVANCED,
        voice="",
        engine_specific_params={
            "executable_path": "/Users/smpceo/Desktop/peer/piper/install/piper",
            "piper_model_path": "/Users/smpceo/Desktop/peer/piper/etc/test_voice.onnx"
        }
    )
    
    print("=== Test Piper TTS avec AdvancedTTS ===")
    print(f"Chemin Piper: {config.engine_specific_params['executable_path']}")
    print(f"Modèle Piper: {config.engine_specific_params['piper_model_path']}")
    
    # Vérifier si les fichiers existent
    piper_path = config.engine_specific_params['executable_path']
    model_path = config.engine_specific_params['piper_model_path']
    
    if not os.path.exists(piper_path):
        print(f"❌ Binaire Piper non trouvé: {piper_path}")
        return False
        
    if not os.path.exists(model_path):
        print(f"❌ Modèle Piper non trouvé: {model_path}")
        return False
        
    if not os.path.exists(model_path + ".json"):
        print(f"❌ Fichier de configuration du modèle non trouvé: {model_path}.json")
        return False
    
    print("✅ Fichiers Piper trouvés")
    
    # Tester l'initialisation
    try:
        tts = AdvancedTTS(config)
        print("✅ AdvancedTTS initialisé")
        
        if tts.is_available():
            print("✅ TTS disponible")
            
            # Test de synthèse
            print("🔊 Test de synthèse vocale...")
            result = tts.synthesize("Bonjour, ceci est un test de Piper TTS.")
            
            if result.success:
                print(f"✅ Synthèse réussie: {result.audio_path}")
                print(f"Moteur utilisé: {result.engine_used}")
                return True
            else:
                print(f"❌ Échec de la synthèse: {result.error_message}")
                return False
        else:
            print("❌ TTS non disponible")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation: {e}")
        return False

if __name__ == "__main__":
    success = test_piper_tts()
    sys.exit(0 if success else 1)
