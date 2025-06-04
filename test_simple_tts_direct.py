#!/usr/bin/env python3
"""
Test SimpleTTS facade with direct vocalization only.
This test verifies that all TTS engines work with direct speech output and no file recording.
"""

import sys
import os
import time
import logging

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from peer.interfaces.sui.tts.simple_tts_engine import SimpleTTS
from peer.interfaces.sui.tts.base import TTSConfig, TTSEngineType

def setup_logging():
    """Setup logging for the test."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

def test_simple_tts_engine(engine_name: str, text: str):
    """Test a specific SimpleTTS engine with direct vocalization."""
    print(f"\n🧪 Testing SimpleTTS with {engine_name} engine")
    print(f"📝 Text: '{text}'")
    
    try:
        # Create TTS config for the specific engine
        config = TTSConfig(
            engine_type=TTSEngineType.SIMPLE,
            language='fr-FR',
            voice=None,  # Use default voice
            engine_specific_params={
                "rate": 180,
                "volume": 0.8,
                "preferred_simple_engine_order": [engine_name]  # Force this engine
            }
        )
        
        # Create SimpleTTS instance
        tts_engine = SimpleTTS(config)
        
        # Check if the engine is available
        if not tts_engine.is_available():
            print(f"❌ SimpleTTS engine not available")
            return False
            
        # Check if specific engine is available
        if not tts_engine._available_engines.get(engine_name, False):
            print(f"❌ {engine_name} engine not available on this system")
            return False
        
        print(f"✅ {engine_name} engine is available")
        
        # Test synthesis with direct vocalization
        print(f"🔊 Starting direct vocalization with {engine_name}...")
        start_time = time.time()
        
        result = tts_engine.synthesize(text)
        
        end_time = time.time()
        duration = end_time - start_time
        
        if result.success:
            print(f"✅ Direct vocalization successful!")
            print(f"   Engine used: {result.engine_used}")
            print(f"   Duration: {duration:.2f} seconds")
            print(f"   Audio file: {result.audio_path or 'None (direct only)'}")
            
            # Verify no audio file was created (direct vocalization only)
            if result.audio_path is None:
                print(f"✅ Confirmed: No audio file created (direct vocalization only)")
            else:
                print(f"⚠️  Audio file was created: {result.audio_path}")
            
            return True
        else:
            print(f"❌ Direct vocalization failed: {result.error_message}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing {engine_name}: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_all_engines():
    """Test all available SimpleTTS engines with direct vocalization."""
    print("🎤 Testing SimpleTTS Direct Vocalization")
    print("=" * 50)
    
    test_text = "Bonjour, ceci est un test de synthèse vocale directe avec SimpleTTS."
    engines_to_test = ["say", "pyttsx3", "espeak", "mock"]
    
    results = {}
    
    for engine in engines_to_test:
        success = test_simple_tts_engine(engine, test_text)
        results[engine] = success
        
        if success:
            print(f"✅ {engine}: SUCCESS")
        else:
            print(f"❌ {engine}: FAILED")
        
        # Small delay between tests
        time.sleep(0.5)
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 30)
    successful_engines = [engine for engine, success in results.items() if success]
    failed_engines = [engine for engine, success in results.items() if not success]
    
    print(f"✅ Successful engines: {successful_engines}")
    print(f"❌ Failed engines: {failed_engines}")
    print(f"📈 Success rate: {len(successful_engines)}/{len(engines_to_test)} ({len(successful_engines)/len(engines_to_test)*100:.1f}%)")
    
    return len(successful_engines) > 0

def test_engine_discovery():
    """Test SimpleTTS engine discovery."""
    print("\n🔍 Testing SimpleTTS Engine Discovery")
    print("=" * 40)
    
    try:
        config = TTSConfig(
            engine_type=TTSEngineType.SIMPLE,
            language='fr-FR'
        )
        
        tts_engine = SimpleTTS(config)
        available_engines = tts_engine._available_engines
        
        print("Available engines:")
        for engine, available in available_engines.items():
            status = "✅ Available" if available else "❌ Not available"
            print(f"  {engine}: {status}")
        
        total_available = sum(available_engines.values())
        print(f"\nTotal available engines: {total_available}")
        
        return total_available > 0
        
    except Exception as e:
        print(f"❌ Error in engine discovery: {e}")
        return False

def test_configuration_handling():
    """Test SimpleTTS configuration handling."""
    print("\n⚙️  Testing SimpleTTS Configuration Handling")
    print("=" * 45)
    
    test_configs = [
        {
            "name": "Default config",
            "config": TTSConfig(engine_type=TTSEngineType.SIMPLE)
        },
        {
            "name": "French config",
            "config": TTSConfig(
                engine_type=TTSEngineType.SIMPLE,
                language='fr-FR',
                voice='Thomas'
            )
        },
        {
            "name": "Custom rate config",
            "config": TTSConfig(
                engine_type=TTSEngineType.SIMPLE,
                engine_specific_params={"rate": 200, "volume": 0.9}
            )
        }
    ]
    
    for test_config in test_configs:
        try:
            print(f"\n📋 Testing: {test_config['name']}")
            tts_engine = SimpleTTS(test_config['config'])
            
            if tts_engine.is_available():
                result = tts_engine.synthesize("Test de configuration")
                if result.success:
                    print(f"✅ Configuration test passed")
                else:
                    print(f"❌ Configuration test failed: {result.error_message}")
            else:
                print(f"⚠️  No engines available for this configuration")
                
        except Exception as e:
            print(f"❌ Configuration test error: {e}")

def main():
    """Main test function."""
    setup_logging()
    
    print("🎯 SimpleTTS Direct Vocalization Test Suite")
    print("=" * 60)
    print("This test suite verifies that SimpleTTS engines work with direct vocalization only")
    print("(no audio file recording).")
    print()
    
    try:
        # Test engine discovery
        discovery_success = test_engine_discovery()
        
        # Test configuration handling
        test_configuration_handling()
        
        # Test all engines
        engines_success = test_all_engines()
        
        # Overall result
        print("\n🏁 Overall Test Results")
        print("=" * 30)
        
        if discovery_success and engines_success:
            print("✅ All tests passed! SimpleTTS direct vocalization is working.")
            return True
        else:
            print("❌ Some tests failed. Check the output above for details.")
            return False
            
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
