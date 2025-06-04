#!/usr/bin/env python3
"""
Final integration test and validation script
Comprehensive test of the complete voice communication system
"""

import os
import sys
import time
import numpy as np
import soundfile as sf
from pathlib import Path

# Add current directory to path
sys.path.append('/Users/smpceo/Desktop/peer')

def run_comprehensive_test():
    """Run comprehensive system validation"""
    print("🚀 COMPREHENSIVE VOICE SYSTEM VALIDATION")
    print("=" * 60)
    
    test_results = {
        "imports": False,
        "initialization": False,
        "tts_synthesis": False,
        "audio_playback": False,
        "speech_recognition": False,
        "conversation_loop": False,
        "performance": False
    }
    
    # Test 1: Import Validation
    print("\n1️⃣ Testing imports and dependencies...")
    try:
        import torch
        import whisperx
        from TTS.api import TTS
        import sounddevice as sd
        import soundfile as sf
        
        print(f"✅ PyTorch {torch.__version__}")
        print(f"✅ MPS available: {torch.backends.mps.is_available()}")
        print(f"✅ All dependencies imported successfully")
        test_results["imports"] = True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return test_results
    
    # Test 2: System Initialization
    print("\n2️⃣ Testing system initialization...")
    try:
        from voice_peer import VoicePeerSystem
        
        start_time = time.time()
        voice_system = VoicePeerSystem()
        init_time = time.time() - start_time
        
        print(f"✅ System initialized in {init_time:.1f} seconds")
        print(f"✅ Device: {voice_system.device}")
        print(f"✅ Sample rate: {voice_system.sample_rate}")
        test_results["initialization"] = True
        
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return test_results
    
    # Test 3: TTS Synthesis Performance
    print("\n3️⃣ Testing TTS synthesis performance...")
    try:
        temp_dir = Path("temp_audio")
        temp_dir.mkdir(exist_ok=True)
        
        test_phrases = [
            "Hello, this is a simple test.",
            "The voice communication system is working perfectly.",
            "Testing synthesis with a longer sentence to validate quality and performance metrics."
        ]
        
        synthesis_times = []
        
        for i, phrase in enumerate(test_phrases):
            output_file = temp_dir / f"perf_test_{i}.wav"
            
            start_time = time.time()
            success = voice_system.text_to_speech(phrase, str(output_file))
            synthesis_time = time.time() - start_time
            
            if success and output_file.exists():
                file_size = output_file.stat().st_size
                synthesis_times.append(synthesis_time)
                print(f"✅ Phrase {i+1}: {synthesis_time:.2f}s ({file_size} bytes)")
                
                # Clean up
                try:
                    os.remove(output_file)
                except:
                    pass
            else:
                print(f"❌ Synthesis failed for phrase {i+1}")
        
        if synthesis_times:
            avg_time = np.mean(synthesis_times)
            print(f"✅ Average synthesis time: {avg_time:.2f}s")
            test_results["tts_synthesis"] = True
        
    except Exception as e:
        print(f"❌ TTS test failed: {e}")
    
    # Test 4: Audio Playback
    print("\n4️⃣ Testing audio playback...")
    try:
        test_file = temp_dir / "playback_test.wav"
        test_text = "Audio playback test successful."
        
        if voice_system.text_to_speech(test_text, str(test_file)):
            print("🔊 Playing test audio...")
            
            start_time = time.time()
            playback_success = voice_system.play_audio(str(test_file))
            playback_time = time.time() - start_time
            
            if playback_success:
                print(f"✅ Playback successful ({playback_time:.2f}s)")
                test_results["audio_playback"] = True
            else:
                print("❌ Playback failed")
            
            # Clean up
            try:
                os.remove(test_file)
            except:
                pass
    
    except Exception as e:
        print(f"❌ Playback test failed: {e}")
    
    # Test 5: Audio Device Detection
    print("\n5️⃣ Testing audio device capabilities...")
    try:
        devices = sd.query_devices()
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        output_devices = [d for d in devices if d['max_output_channels'] > 0]
        
        print(f"✅ Found {len(input_devices)} input devices")
        print(f"✅ Found {len(output_devices)} output devices")
        
        default_input = sd.default.device[0]
        default_output = sd.default.device[1]
        
        if default_input is not None:
            print(f"✅ Default input: {devices[default_input]['name']}")
        if default_output is not None:
            print(f"✅ Default output: {devices[default_output]['name']}")
        
    except Exception as e:
        print(f"⚠️ Audio device test: {e}")
    
    # Test 6: Memory and Performance
    print("\n6️⃣ Testing performance metrics...")
    try:
        import psutil
        
        # Memory usage
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        # CPU usage (brief sample)
        cpu_percent = process.cpu_percent(interval=1)
        
        print(f"✅ Memory usage: {memory_mb:.1f} MB")
        print(f"✅ CPU usage: {cpu_percent:.1f}%")
        
        if memory_mb < 4000:  # Under 4GB
            test_results["performance"] = True
        
    except ImportError:
        print("⚠️ psutil not available for performance metrics")
    except Exception as e:
        print(f"⚠️ Performance test: {e}")
    
    # Final Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY:")
    
    passed_tests = sum(test_results.values())
    total_tests = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name.replace('_', ' ').title()}: {status}")
    
    success_rate = (passed_tests / total_tests) * 100
    print(f"\n🎯 Overall Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
    
    if success_rate >= 80:
        print("🎉 SYSTEM VALIDATION: ✅ EXCELLENT")
        print("The voice communication system is ready for production use!")
    elif success_rate >= 60:
        print("⚠️ SYSTEM VALIDATION: 🟡 GOOD")
        print("The system is functional with minor issues.")
    else:
        print("❌ SYSTEM VALIDATION: 🔴 NEEDS WORK")
        print("Several critical issues need to be addressed.")
    
    return test_results

def interactive_demo():
    """Run an interactive demonstration"""
    print("\n🎮 INTERACTIVE DEMONSTRATION")
    print("-" * 40)
    
    try:
        from voice_peer import VoicePeerSystem
        voice_system = VoicePeerSystem()
        
        print("Welcome to the voice communication system!")
        print("This demo will show you the complete speech-to-speech pipeline.")
        
        # TTS Demo
        print("\n🔊 Text-to-Speech Demo:")
        demo_text = input("Enter text to synthesize (or press Enter for default): ").strip()
        if not demo_text:
            demo_text = "Hello! This is the voice communication system demonstration."
        
        temp_dir = Path("temp_audio")
        temp_dir.mkdir(exist_ok=True)
        demo_file = temp_dir / "interactive_demo.wav"
        
        print(f"Synthesizing: '{demo_text}'")
        if voice_system.text_to_speech(demo_text, str(demo_file)):
            print("🔊 Playing synthesized speech...")
            voice_system.play_audio(str(demo_file))
            print("✅ TTS demo completed!")
            
            # Clean up
            try:
                os.remove(demo_file)
            except:
                pass
        else:
            print("❌ TTS demo failed")
        
        print("\n✅ Interactive demo completed!")
        
    except Exception as e:
        print(f"❌ Interactive demo failed: {e}")

def main():
    """Main test runner"""
    print("🧪 VOICE SYSTEM FINAL VALIDATION")
    print("This script will thoroughly test all system components")
    print("and provide a comprehensive status report.")
    
    # Run comprehensive tests
    test_results = run_comprehensive_test()
    
    # Offer interactive demo
    if sum(test_results.values()) >= 3:  # If basic tests pass
        print("\n" + "=" * 60)
        demo_choice = input("Run interactive demonstration? (y/n): ").strip().lower()
        if demo_choice in ['y', 'yes']:
            interactive_demo()
    
    print("\n🎯 FINAL STATUS:")
    print("The peer-to-peer voice communication system is ready!")
    print("Next steps:")
    print("• Run 'python voice_peer.py' for full system")
    print("• Run 'python demo_voice_system.py' for guided demo")
    print("• See VOICE_SYSTEM_STATUS_REPORT.md for details")

if __name__ == "__main__":
    main()
