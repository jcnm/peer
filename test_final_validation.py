#!/usr/bin/env python3
"""
Final validation test for WhisperX migration
Tests that all documentation and system is fully migrated from Whisper to WhisperX
"""

import os
import re
import subprocess
import sys
from pathlib import Path

def test_documentation_migration():
    """Test that all documentation references are updated to WhisperX"""
    print("🔍 Testing documentation migration...")
    
    readme_path = Path("README.md")
    
    if not readme_path.exists():
        print("❌ README.md not found")
        return False
    
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for old Whisper references (should be 0)
    whisper_matches = re.findall(r'\bWhisper\b(?!\s*X)', content, re.IGNORECASE)
    whisper_only_matches = [match for match in whisper_matches if match.lower() != 'whisperx']
    
    # Check for new WhisperX references (should be multiple)
    whisperx_matches = re.findall(r'\bWhisperX\b', content)
    
    print(f"📊 Found {len(whisper_only_matches)} old Whisper references")
    print(f"📊 Found {len(whisperx_matches)} WhisperX references")
    
    if whisper_only_matches:
        print("❌ Found old Whisper references that should be WhisperX:")
        for match in whisper_only_matches[:5]:  # Show first 5
            print(f"   - {match}")
        return False
    
    if len(whisperx_matches) < 5:
        print("❌ Expected multiple WhisperX references in documentation")
        return False
    
    print("✅ Documentation properly migrated to WhisperX")
    return True

def test_system_imports():
    """Test that system properly imports WhisperX"""
    print("🔍 Testing system imports...")
    
    try:
        # Test WhisperX import
        result = subprocess.run([
            sys.executable, "-c", 
            "import whisperx; print('WhisperX version:', whisperx.__version__ if hasattr(whisperx, '__version__') else 'installed')"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"❌ WhisperX import failed: {result.stderr}")
            return False
        
        print(f"✅ WhisperX import successful: {result.stdout.strip()}")
        return True
        
    except Exception as e:
        print(f"❌ WhisperX import test failed: {e}")
        return False

def test_asr_engine_enum():
    """Test that ASR engine enum is properly updated"""
    print("🔍 Testing ASR engine enum...")
    
    try:
        sys.path.insert(0, 'src')
        from peer.interfaces.sui.stt.speech_recognizer import ASREngine
        
        # Check that WHISPERX exists
        if not hasattr(ASREngine, 'WHISPERX'):
            print("❌ ASREngine.WHISPERX not found")
            return False
        
        # Check that old WHISPER is removed
        if hasattr(ASREngine, 'WHISPER'):
            print("❌ Old ASREngine.WHISPER still exists")
            return False
        
        # Check available engines
        available_engines = [attr for attr in dir(ASREngine) if not attr.startswith('_')]
        print(f"📊 Available engines: {available_engines}")
        
        expected_engines = ['WHISPERX', 'VOSK', 'MOCK']
        for engine in expected_engines:
            if engine not in available_engines:
                print(f"❌ Expected engine {engine} not found")
                return False
        
        print("✅ ASR engine enum properly updated")
        return True
        
    except Exception as e:
        print(f"❌ ASR engine enum test failed: {e}")
        return False

def test_whisperx_asr_class():
    """Test that WhisperXASR class exists and is functional"""
    print("🔍 Testing WhisperXASR class...")
    
    try:
        sys.path.insert(0, 'src')
        from peer.interfaces.sui.stt.speech_recognizer import WhisperXASR, ASRConfig
        
        # Test class instantiation with proper config
        config = ASRConfig(
            enabled=True,
            model_name="base",
            model_path=""
        )
        asr = WhisperXASR(config)
        
        # Check key methods exist
        required_methods = ['transcribe', '_load_model']
        for method in required_methods:
            if not hasattr(asr, method):
                print(f"❌ WhisperXASR missing method: {method}")
                return False
        
        # Check key attributes exist
        required_attributes = ['model', 'config', 'logger']
        for attr in required_attributes:
            if not hasattr(asr, attr):
                print(f"❌ WhisperXASR missing attribute: {attr}")
                return False
        
        print("✅ WhisperXASR class properly implemented")
        return True
        
    except Exception as e:
        print(f"❌ WhisperXASR class test failed: {e}")
        return False

def test_no_wav2vec2_references():
    """Test that no wav2vec2 references remain"""
    print("🔍 Testing wav2vec2 removal...")
    
    # Search for wav2vec2 references in Python files
    try:
        result = subprocess.run([
            'grep', '-r', '-i', 'wav2vec2', 'src/', '--include=*.py'
        ], capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout.strip():
            print("❌ Found wav2vec2 references:")
            print(result.stdout)
            return False
        
        print("✅ No wav2vec2 references found")
        return True
        
    except Exception as e:
        print(f"❌ wav2vec2 search failed: {e}")
        return False

def main():
    """Run all validation tests"""
    print("🚀 Starting final validation tests for WhisperX migration...")
    print("=" * 60)
    
    tests = [
        ("Documentation Migration", test_documentation_migration),
        ("System Imports", test_system_imports),
        ("ASR Engine Enum", test_asr_engine_enum),
        ("WhisperXASR Class", test_whisperx_asr_class),
        ("WAV2VEC2 Removal", test_no_wav2vec2_references)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name}...")
        result = test_func()
        results.append((test_name, result))
        print("-" * 40)
    
    print("\n" + "=" * 60)
    print("📊 FINAL VALIDATION RESULTS:")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print("=" * 60)
    print(f"📈 Summary: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! WhisperX migration is complete and validated!")
        return True
    else:
        print(f"⚠️  {total - passed} tests failed. Migration needs attention.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
