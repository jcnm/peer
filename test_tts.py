#!/usr/bin/env python3
"""
Test script for the TTS functionality of the Peer SUI.
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TTS-Test")

# Add the src directory to Python path
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
sys.path.insert(0, src_dir)

# Import TTS-related modules
from peer.interfaces.sui.tts.base import TTSConfig, TTSEngineType
from peer.interfaces.sui.tts.text_to_speech import TextToSpeech
from peer.interfaces.sui.config.config_loader import load_yaml_config, get_config_with_defaults

def test_tts():
    """Test TTS functionality with various text samples."""
    logger.info("🧪 Starting TTS test...")
    
    # Load configuration
    config_path = os.path.expanduser("~/.peer/config/sui.yaml")
    if os.path.exists(config_path):
        config = load_yaml_config(config_path)
        logger.info(f"✅ Loaded configuration from {config_path}")
    else:
        logger.warning(f"⚠️ Config file not found at {config_path}, using defaults")
        config = {}
    
    # Extract TTS settings
    tts_config_dict = config.get('tts_engine_settings', {})
    
    # Determine engine type
    engine_type_str = tts_config_dict.get('engine_type', 'pyttsx3').lower()
    if engine_type_str == 'pyttsx3' or engine_type_str == 'simple':
        engine_type = TTSEngineType.SIMPLE
    elif engine_type_str == 'piper' or engine_type_str == 'advanced':
        engine_type = TTSEngineType.ADVANCED
    elif engine_type_str == 'realistic':
        engine_type = TTSEngineType.REALISTIC
    else:
        engine_type = TTSEngineType.SIMPLE
    
    # Create TTSConfig
    tts_config = TTSConfig(
        engine_type=engine_type,
        language=tts_config_dict.get('language', 'fr-FR'),
        voice=tts_config_dict.get('voice', None),
        parameters=tts_config_dict
    )
    
    # Initialize TTS engine
    tts = TextToSpeech(tts_config)
    
    # Test if engine is available
    if not tts.is_engine_available():
        logger.error("❌ TTS engine is not available!")
        return
    
    logger.info(f"✅ TTS engine initialized: {engine_type.value}")
    
    # Test phrases to synthesize
    test_phrases = [
        "Bonjour, je suis Peer, votre assistant de programmation.",
        "La synthèse vocale fonctionne correctement.",
        "Commande exécutée avec succès.",
        "Enregistrement arrêté."
    ]
    
    # Synthesize and play each phrase
    for i, phrase in enumerate(test_phrases):
        logger.info(f"🔊 Test phrase {i+1}: '{phrase}'")
        result = tts.synthesize(phrase)
        
        if result.success:
            logger.info(f"✅ Synthesis successful, engine used: {result.engine_used}")
            if result.audio_path:
                logger.info(f"📁 Audio saved to: {result.audio_path}")
        else:
            logger.error(f"❌ Synthesis failed: {result.error_message}")
    
    # Cleanup
    tts.cleanup_temp_files()
    logger.info("🏁 TTS test completed")

if __name__ == "__main__":
    test_tts()
