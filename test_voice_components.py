#!/usr/bin/env python3
"""
Test script for voice communication system components
"""

import os
import sys
import time
from pathlib import Path

# Add the current directory to path
sys.path.append('/Users/smpceo/Desktop/peer')

def test_imports():
    """Test if all required modules can be imported"""
    print("🧪 Testing imports...")
    
    try:
        import torch
        print(f"✅ PyTorch {torch.__version__}")
        print(f"  MPS available: {torch.backends.mps.is_available()}")
        print(f"  MPS built: {torch.backends.mps.is_built()}")
    except Exception as e:
        print(f"❌ PyTorch import failed: {e}")
        return False
    
    try:
        import whisperx
        print(f"✅ WhisperX imported successfully")
    except Exception as e:
        print(f"❌ WhisperX import failed: {e}")
        return False
    
    try:
        from TTS.api import TTS
        print(f"✅ Coqui TTS imported successfully")
    except Exception as e:
        print(f"❌ TTS import failed: {e}")
        return False
    
    try:
        import sounddevice as sd
        import soundfile as sf
        import numpy as np
        print(f"✅ Audio libraries imported successfully")
    except Exception as e:
        print(f"❌ Audio libraries import failed: {e}")
        return False
    
    return True

def test_voice_system_initialization():
    """Test voice system initialization"""
    print("\n🔧 Testing voice system initialization...")
    
    try:
        from voice_peer import VoicePeerSystem
        
        # Initialize the system
        voice_system = VoicePeerSystem()
        print(f"✅ Voice system initialized successfully")
        print(f"  Device: {voice_system.device}")
        print(f"  Sample rate: {voice_system.sample_rate}")
        print(f"  TTS model type: {'XTTS V2' if getattr(voice_system, 'is_xtts_v2', False) else 'Tacotron2-DDC'}")
        
        return voice_system
        
    except Exception as e:
        print(f"❌ Voice system initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_tts_basic(voice_system):
    """Test basic text-to-speech functionality"""
    print("\n🔊 Testing TTS functionality...")
    
    try:
        temp_dir = Path("temp_audio")
        temp_dir.mkdir(exist_ok=True)
        
        test_text = "Hello! This is a test of the text to speech system."
        output_file = temp_dir / "test_tts_basic.wav"
        
        success = voice_system.text_to_speech(test_text, str(output_file))
        
        if success and output_file.exists():
            file_size = output_file.stat().st_size
            print(f"✅ TTS test successful")
            print(f"  Generated file: {output_file}")
            print(f"  File size: {file_size} bytes")
            
            # Try to play the audio
            try:
                print("🔊 Playing generated audio...")
                voice_system.play_audio(str(output_file))
                print("✅ Audio playback successful")
            except Exception as e:
                print(f"⚠️ Audio playback failed: {e}")
            
            # Clean up
            try:
                os.remove(output_file)
            except:
                pass
                
            return True
        else:
            print(f"❌ TTS test failed - no output file generated")
            return False
            
    except Exception as e:
        print(f"❌ TTS test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_audio_devices():
    """Test audio device detection"""
    print("\n🎵 Testing audio devices...")
    
    try:
        import sounddevice as sd
        
        devices = sd.query_devices()
        print(f"✅ Found {len(devices)} audio devices:")
        
        for i, device in enumerate(devices):
            marker = " (default)" if i == sd.default.device[0] or i == sd.default.device[1] else ""
            print(f"  {i}: {device['name']}{marker}")
            print(f"      Max input channels: {device['max_input_channels']}")
            print(f"      Max output channels: {device['max_output_channels']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Audio device test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Voice Communication System Component Test")
    print("=" * 60)
    
    # Test 1: Imports
    if not test_imports():
        print("❌ Import tests failed - cannot continue")
        return
    
    # Test 2: Audio devices
    test_audio_devices()
    
    # Test 3: Voice system initialization
    voice_system = test_voice_system_initialization()
    if not voice_system:
        print("❌ Voice system initialization failed - cannot continue")
        return
    
    # Test 4: Basic TTS
    test_tts_basic(voice_system)
    
    print("\n" + "=" * 60)
    print("✅ Component tests completed!")
    print("\nNext steps:")
    print("• Run 'python voice_peer.py' to start the full system")
    print("• Choose option 1 to run built-in system tests")
    print("• Choose option 2 to start voice conversation")

if __name__ == "__main__":
    main()
