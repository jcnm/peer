#!/usr/bin/env python3
"""
Test simple du système de communication vocale
"""

import torch
import sys
import os

def test_imports():
    """Tester les imports des librairies principales"""
    print("🧪 Test des imports...")
    
    try:
        import TTS
        print(f"✅ TTS (XTTS V2) version: {TTS.__version__}")
    except ImportError as e:
        print(f"❌ Erreur import TTS: {e}")
        return False
    
    try:
        import whisperx
        print("✅ WhisperX importé avec succès")
    except ImportError as e:
        print(f"❌ Erreur import WhisperX: {e}")
        return False
    
    try:
        import sounddevice as sd
        print("✅ SoundDevice importé avec succès")
    except ImportError as e:
        print(f"❌ Erreur import SoundDevice: {e}")
        return False
    
    try:
        import soundfile as sf
        print("✅ SoundFile importé avec succès")
    except ImportError as e:
        print(f"❌ Erreur import SoundFile: {e}")
        return False
    
    return True

def test_device_setup():
    """Tester la configuration des devices"""
    print("\n🔧 Test de configuration des devices...")
    
    print(f"PyTorch version: {torch.__version__}")
    print(f"MPS disponible: {torch.backends.mps.is_available()}")
    print(f"MPS compilé: {torch.backends.mps.is_built()}")
    
    if torch.backends.mps.is_available():
        device = "mps"
        print("🚀 Utilisation de MPS (Metal Performance Shaders)")
    elif torch.cuda.is_available():
        device = "cuda"
        print("🚀 Utilisation de CUDA")
    else:
        device = "cpu"
        print("💻 Utilisation du CPU")
    
    return device

def test_audio_devices():
    """Tester les périphériques audio"""
    print("\n🎧 Test des périphériques audio...")
    
    try:
        import sounddevice as sd
        
        # Lister les devices
        devices = sd.query_devices()
        print(f"Nombre de périphériques audio: {len(devices)}")
        
        # Device par défaut
        default_input = sd.default.device[0]
        default_output = sd.default.device[1]
        
        print(f"Entrée par défaut: {devices[default_input]['name']}")
        print(f"Sortie par défaut: {devices[default_output]['name']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur test audio: {e}")
        return False

def test_basic_tts():
    """Test basique de text-to-speech"""
    print("\n🔊 Test basique de Text-to-Speech...")
    
    try:
        from TTS.api import TTS
        import tempfile
        import os
        
        # Charger un modèle simple pour le test
        print("Chargement du modèle TTS...")
        tts = TTS("tts_models/en/ljspeech/tacotron2-DDC")
        
        # Générer un test audio
        test_text = "Hello, this is a test of the text to speech system."
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_filename = temp_file.name
        
        print("Génération audio...")
        tts.tts_to_file(text=test_text, file_path=temp_filename)
        
        # Vérifier que le fichier existe
        if os.path.exists(temp_filename):
            file_size = os.path.getsize(temp_filename)
            print(f"✅ Audio généré: {temp_filename} ({file_size} bytes)")
            
            # Nettoyer
            os.remove(temp_filename)
            return True
        else:
            print("❌ Fichier audio non généré")
            return False
            
    except Exception as e:
        print(f"❌ Erreur TTS: {e}")
        return False

def test_basic_whisper():
    """Test basique de WhisperX"""
    print("\n🎤 Test basique de WhisperX...")
    
    try:
        import whisperx
        
        print("Chargement du modèle WhisperX...")
        # Utiliser CPU pour éviter les conflits MPS avec WhisperX
        model = whisperx.load_model("base", device="cpu", compute_type="float32")
        
        print("✅ Modèle WhisperX chargé avec succès")
        
        # Note: Un test complet nécessiterait un fichier audio
        return True
        
    except Exception as e:
        print(f"❌ Erreur WhisperX: {e}")
        return False

def main():
    print("🚀 TEST DU SYSTÈME DE COMMUNICATION VOCALE")
    print("=" * 50)
    
    # Tests des composants
    tests = [
        ("Imports des librairies", test_imports),
        ("Configuration des devices", test_device_setup),
        ("Périphériques audio", test_audio_devices),
        ("Text-to-Speech basique", test_basic_tts),
        ("WhisperX basique", test_basic_whisper),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ Erreur inattendue: {e}")
            results[test_name] = False
    
    # Résumé des résultats
    print(f"\n{'='*50}")
    print("📊 RÉSUMÉ DES TESTS")
    print(f"{'='*50}")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSÉ" if result else "❌ ÉCHEC"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nRésultat: {passed}/{total} tests réussis")
    
    if passed == total:
        print("\n🎉 Tous les tests sont passés! Le système est prêt.")
        print("\n📋 Prochaines étapes:")
        print("1. Exécutez: python voice_peer.py")
        print("2. Choisissez l'option '1' pour tester le système complet")
        print("3. Choisissez l'option '2' pour démarrer une conversation")
    else:
        print(f"\n⚠️ {total - passed} test(s) ont échoué. Vérifiez les erreurs ci-dessus.")
        
        if not results.get("Imports des librairies", False):
            print("💡 Suggestion: Réinstallez les dépendances avec:")
            print("   pip install TTS whisperx sounddevice soundfile")

if __name__ == "__main__":
    main()
