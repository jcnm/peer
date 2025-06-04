#!/usr/bin/env python3
"""
Script de configuration et d'optimisation pour le système de communication vocale
"""

import os
import sys
import subprocess
import torch
import platform

def check_system_requirements():
    """Vérifier la configuration système"""
    print("🔍 Vérification de la configuration système...")
    
    # Informations système
    print(f"Système: {platform.system()} {platform.release()}")
    print(f"Architecture: {platform.machine()}")
    print(f"Python: {sys.version}")
    
    # PyTorch et MPS
    print(f"PyTorch: {torch.__version__}")
    print(f"MPS disponible: {torch.backends.mps.is_available()}")
    print(f"MPS compilé: {torch.backends.mps.is_built()}")
    
    if torch.backends.mps.is_available():
        print("✅ Metal Performance Shaders (MPS) activé")
    else:
        print("⚠️ MPS non disponible, utilisation du CPU")
    
    # CUDA (si applicable)
    if torch.cuda.is_available():
        print(f"CUDA disponible: {torch.cuda.device_count()} device(s)")
    
    return True

def check_audio_devices():
    """Vérifier les périphériques audio"""
    print("\n🎧 Vérification des périphériques audio...")
    
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        
        print("Périphériques audio disponibles:")
        for i, device in enumerate(devices):
            device_type = []
            if device['max_input_channels'] > 0:
                device_type.append("INPUT")
            if device['max_output_channels'] > 0:
                device_type.append("OUTPUT")
            
            print(f"  {i}: {device['name']} [{', '.join(device_type)}]")
        
        # Périphérique par défaut
        default_device = sd.default.device
        print(f"\nPériphérique par défaut: {default_device}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur vérification audio: {e}")
        return False

def optimize_for_macos():
    """Optimisations spécifiques à macOS"""
    print("\n🍎 Optimisations macOS...")
    
    # Variables d'environnement pour MPS
    os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
    os.environ['PYTORCH_MPS_HIGH_WATERMARK_RATIO'] = '0.0'
    
    print("✅ Variables d'environnement MPS configurées")
    
    # Recommandations système
    print("\n📋 Recommandations système:")
    print("• Fermez les autres applications audio intensives")
    print("• Vérifiez que le microphone est autorisé dans Préférences Système")
    print("• Utilisez des écouteurs pour éviter l'écho")
    
    return True

def test_models():
    """Tester le chargement des modèles"""
    print("\n🧪 Test de chargement des modèles...")
    
    # Test TTS
    try:
        print("Chargement de XTTS V2...")
        from TTS.api import TTS
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
        print("✅ XTTS V2 chargé avec succès")
        del tts  # Libérer la mémoire
    except Exception as e:
        print(f"❌ Erreur XTTS V2: {e}")
    
    # Test WhisperX
    try:
        print("Chargement de WhisperX...")
        import whisperx
        model = whisperx.load_model("base", device="cpu", compute_type="float32")
        print("✅ WhisperX chargé avec succès")
        del model  # Libérer la mémoire
    except Exception as e:
        print(f"❌ Erreur WhisperX: {e}")
    
    return True

def create_startup_script():
    """Créer un script de démarrage simplifié"""
    startup_script = """#!/bin/bash
# Script de démarrage pour le système de communication vocale

echo "🚀 Démarrage du système de communication vocale peer-to-peer"
echo "==============================================="

# Activer l'environnement virtuel
source vepeer/bin/activate

# Vérifier que nous sommes dans le bon répertoire
if [ ! -f "voice_peer.py" ]; then
    echo "❌ Erreur: voice_peer.py non trouvé"
    echo "Veuillez exécuter ce script depuis le répertoire /Users/smpceo/Desktop/peer"
    exit 1
fi

# Configuration des variables d'environnement pour macOS MPS
export PYTORCH_ENABLE_MPS_FALLBACK=1
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0

# Lancer le système
python voice_peer.py

echo "👋 Système arrêté"
"""
    
    with open("/Users/smpceo/Desktop/peer/start_voice_system.sh", "w") as f:
        f.write(startup_script)
    
    # Rendre le script exécutable
    os.chmod("/Users/smpceo/Desktop/peer/start_voice_system.sh", 0o755)
    
    print("✅ Script de démarrage créé: start_voice_system.sh")
    return True

def main():
    print("🔧 CONFIGURATION DU SYSTÈME DE COMMUNICATION VOCALE")
    print("=" * 55)
    
    try:
        # Vérifications système
        check_system_requirements()
        check_audio_devices()
        optimize_for_macos()
        test_models()
        create_startup_script()
        
        print("\n" + "=" * 55)
        print("✅ CONFIGURATION TERMINÉE AVEC SUCCÈS!")
        print("=" * 55)
        print("\n📋 Instructions d'utilisation:")
        print("1. Pour démarrer le système: ./start_voice_system.sh")
        print("2. Ou directement: python voice_peer.py")
        print("3. Assurez-vous que votre microphone est autorisé")
        print("4. Utilisez des écouteurs pour une meilleure expérience")
        
        print("\n🎯 Fonctionnalités disponibles:")
        print("• Reconnaissance vocale en temps réel (WhisperX)")
        print("• Synthèse vocale haute qualité (XTTS V2)")
        print("• Optimisation macOS MPS pour de meilleures performances")
        print("• Communication bidirectionnelle voix-à-voix")
        
    except Exception as e:
        print(f"\n❌ Erreur durant la configuration: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    main()
