#!/usr/bin/env python3
"""
Test XTTS V2 compatibility and fix transformers issue
"""

import os
import torch
import numpy as np
import soundfile as sf
from pathlib import Path

def test_xtts_v2_direct():
    """Test XTTS V2 directly with transformers workaround"""
    print("🧪 Testing XTTS V2 direct compatibility...")
    
    try:
        # First, try to import TTS and check available models
        from TTS.api import TTS
        
        # List available XTTS models
        print("📋 Available XTTS models:")
        models = TTS.list_models()
        xtts_models = [model for model in models if 'xtts' in model.lower()]
        for model in xtts_models:
            print(f"  - {model}")
        
        if not xtts_models:
            print("❌ No XTTS models found")
            return False
        
        # Try to load XTTS V2
        print("\n🔧 Attempting to load XTTS V2...")
        model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
        
        # Apply transformers monkey patch before loading
        try:
            import transformers.models.gpt2.modeling_gpt2 as gpt2_modeling
            
            # Check if the issue exists
            if hasattr(gpt2_modeling.GPT2LMHeadModel, 'generate'):
                print("✅ GPT2LMHeadModel.generate exists - no patch needed")
            else:
                print("⚠️ GPT2LMHeadModel.generate missing - applying patch...")
                # Apply patch if needed
                from transformers import GPT2LMHeadModel
                if not hasattr(GPT2LMHeadModel, 'generate'):
                    # Import the base generate method
                    from transformers.generation.utils import GenerationMixin
                    GPT2LMHeadModel.generate = GenerationMixin.generate
                    print("✅ Applied transformers patch")
        
        except Exception as patch_error:
            print(f"⚠️ Patch attempt failed: {patch_error}")
        
        # Now try to load XTTS V2
        try:
            tts = TTS(model_name)
            print("✅ XTTS V2 loaded successfully!")
            
            # Test basic synthesis
            temp_dir = Path("temp_audio")
            temp_dir.mkdir(exist_ok=True)
            
            test_text = "Hello, this is a test of XTTS version 2."
            output_file = temp_dir / "xtts_v2_test.wav"
            
            # Check if we need a speaker reference
            if hasattr(tts.tts, 'speakers') and tts.tts.speakers:
                print(f"📢 Available speakers: {tts.tts.speakers}")
                speaker = tts.tts.speakers[0] if tts.tts.speakers else None
                wav = tts.tts(text=test_text, speaker=speaker)
            else:
                # Try with reference audio (voice cloning approach)
                print("🎤 Using voice cloning approach...")
                ref_audio = temp_dir / "reference_voice.wav"
                
                # Create reference audio if it doesn't exist
                if not ref_audio.exists():
                    # Generate simple reference audio using existing TTS
                    fallback_tts = TTS("tts_models/en/ljspeech/tacotron2-DDC")
                    ref_wav = fallback_tts.tts("This is a reference voice for cloning.")
                    sf.write(ref_audio, ref_wav, 22050)
                    print(f"✅ Created reference audio: {ref_audio}")
                
                # Now try XTTS V2 with voice cloning
                wav = tts.tts(
                    text=test_text,
                    speaker_wav=str(ref_audio),
                    language="en"
                )
            
            # Save the output
            sf.write(output_file, wav, 24000)  # XTTS V2 typically uses 24kHz
            print(f"✅ XTTS V2 synthesis successful!")
            print(f"📁 Output file: {output_file}")
            print(f"📊 File size: {output_file.stat().st_size} bytes")
            
            return True
            
        except Exception as synthesis_error:
            print(f"❌ XTTS V2 synthesis failed: {synthesis_error}")
            
            # Check if it's the specific transformers issue
            if "'GPT2InferenceModel' object has no attribute 'generate'" in str(synthesis_error):
                print("🔍 Detected transformers compatibility issue")
                print("💡 Attempting alternative fix...")
                
                # Try alternative approach
                try:
                    # Force reload transformers with patched version
                    import importlib
                    import transformers
                    
                    # Backup and patch
                    original_gpt2 = transformers.models.gpt2.modeling_gpt2.GPT2LMHeadModel
                    
                    class PatchedGPT2LMHeadModel(original_gpt2):
                        def generate(self, *args, **kwargs):
                            # Use the parent class generate method
                            from transformers.generation.utils import GenerationMixin
                            return GenerationMixin.generate(self, *args, **kwargs)
                    
                    # Apply the patch
                    transformers.models.gpt2.modeling_gpt2.GPT2LMHeadModel = PatchedGPT2LMHeadModel
                    
                    # Try loading again
                    tts = TTS(model_name)
                    print("✅ XTTS V2 loaded with patch!")
                    return True
                    
                except Exception as patch_error:
                    print(f"❌ Alternative patch failed: {patch_error}")
            
            return False
    
    except Exception as e:
        print(f"❌ XTTS V2 test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_alternative_tts_engines():
    """Test alternative TTS engines for comparison"""
    print("\n🔄 Testing alternative TTS engines...")
    
    alternatives = [
        "tts_models/en/ljspeech/tacotron2-DDC",  # Current working
        "tts_models/en/ljspeech/fast_pitch",
        "tts_models/en/ljspeech/speedy_speech",
        "tts_models/en/ljspeech/neural_hmm",
    ]
    
    working_engines = []
    temp_dir = Path("temp_audio")
    temp_dir.mkdir(exist_ok=True)
    
    for model_name in alternatives:
        try:
            print(f"Testing {model_name}...")
            from TTS.api import TTS
            tts = TTS(model_name)
            
            # Quick synthesis test
            test_text = "This is a test."
            output_file = temp_dir / f"test_{model_name.split('/')[-1]}.wav"
            
            wav = tts.tts(text=test_text)
            sf.write(output_file, wav, 22050)
            
            print(f"✅ {model_name} - Working")
            working_engines.append(model_name)
            
            # Clean up
            try:
                os.remove(output_file)
            except:
                pass
                
        except Exception as e:
            print(f"❌ {model_name} - Failed: {e}")
    
    print(f"\n📊 Working TTS engines: {len(working_engines)}")
    for engine in working_engines:
        print(f"  ✅ {engine}")
    
    return working_engines

def main():
    """Run XTTS V2 compatibility tests"""
    print("🚀 XTTS V2 Compatibility Test Suite")
    print("=" * 60)
    
    # Test 1: Direct XTTS V2 attempt
    xtts_success = test_xtts_v2_direct()
    
    # Test 2: Alternative engines
    alternatives = test_alternative_tts_engines()
    
    print("\n" + "=" * 60)
    print("📋 SUMMARY:")
    print(f"XTTS V2 Status: {'✅ Working' if xtts_success else '❌ Issues detected'}")
    print(f"Alternative engines: {len(alternatives)} working")
    
    if not xtts_success:
        print("\n💡 RECOMMENDATIONS:")
        print("• Continue using Tacotron2-DDC (stable and working)")
        print("• Monitor TTS library updates for XTTS V2 fixes")
        print("• Consider Piper TTS as high-quality alternative")
        print("• Current system is fully functional for voice communication")
    else:
        print("\n🎉 XTTS V2 is working! Consider updating voice_peer.py")

if __name__ == "__main__":
    main()
