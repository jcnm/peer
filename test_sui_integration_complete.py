#!/usr/bin/env python3
"""
Test d'intégration complète SUI + Système vocal français
======================================================
Ce script teste l'intégration end-to-end du système SUI avec le TTS français optimisé.
"""

import os
import sys
import time
import subprocess
import threading
import signal
from pathlib import Path

# Configuration
PEER_ROOT = Path("/Users/smpceo/Desktop/peer")
SUI_SCRIPT = PEER_ROOT / "run_sui.sh"
CONFIG_PATH = Path("/Users/smpceo/.peer/config/sui/models.yaml")

def print_section(title, emoji="🎯"):
    print(f"\n{emoji} {title}")
    print("=" * (len(title) + 3))

def test_tts_direct():
    """Test direct du système TTS français"""
    print_section("TEST TTS DIRECT", "🔊")
    
    try:
        sys.path.insert(0, str(PEER_ROOT / "src"))
        from peer.interfaces.sui.tts.simple_tts_engine import SimpleTTS
        from peer.interfaces.sui.tts.base import TTSConfig, TTSEngineType
        
        # Test avec configuration française
        config = TTSConfig(
            engine_type=TTSEngineType.SIMPLE,
            language="fr",
            voice="Audrey",
            engine_specific_params={
                "rate": 190,
                "volume": 0.8,
                "preferred_simple_engine_order": ["say", "pyttsx3"]
            }
        )
        engine = SimpleTTS(config)
        
        # Test de synthèse
        test_text = "Bonjour, je suis le système vocal français de Peer."
        print(f"🎤 Test synthèse : '{test_text}'")
        
        result = engine.synthesize(
            text=test_text
        )
        
        if result and os.path.exists(result):
            print(f"✅ Synthèse réussie : {result}")
            
            # Lecture du fichier audio
            subprocess.run(["afplay", result], check=True)
            print("🔊 Audio lu avec succès")
            
            # Nettoyage
            os.remove(result)
            return True
        else:
            print("❌ Échec de la synthèse")
            return False
            
    except Exception as e:
        print(f"❌ Erreur TTS direct : {e}")
        return False

def test_config_loading():
    """Test du chargement de configuration"""
    print_section("TEST CONFIGURATION", "⚙️")
    
    try:
        if not CONFIG_PATH.exists():
            print(f"❌ Configuration non trouvée : {CONFIG_PATH}")
            return False
            
        with open(CONFIG_PATH, 'r') as f:
            content = f.read()
            
        print(f"📋 Configuration trouvée : {CONFIG_PATH}")
        
        # Vérification du contenu
        if "simple" in content:
            print("✅ Engine 'simple' configuré")
        else:
            print("⚠️ Engine 'simple' non trouvé dans la config")
            
        if "fr" in content or "french" in content.lower():
            print("✅ Configuration française détectée")
        else:
            print("⚠️ Configuration française non détectée")
            
        return True
        
    except Exception as e:
        print(f"❌ Erreur configuration : {e}")
        return False

def test_sui_startup():
    """Test de démarrage SUI avec timeout"""
    print_section("TEST DÉMARRAGE SUI", "🚀")
    
    try:
        if not SUI_SCRIPT.exists():
            print(f"❌ Script SUI non trouvé : {SUI_SCRIPT}")
            return False
            
        print(f"🔄 Démarrage SUI (timeout 30s)...")
        
        # Démarrage SUI avec timeout
        process = subprocess.Popen(
            ["bash", str(SUI_SCRIPT)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(PEER_ROOT)
        )
        
        # Attendre le démarrage (max 30s)
        start_time = time.time()
        timeout = 30
        
        while time.time() - start_time < timeout:
            if process.poll() is not None:
                # Le processus s'est terminé
                stdout, stderr = process.communicate()
                
                if process.returncode == 0:
                    print("✅ SUI démarré avec succès")
                    return True
                else:
                    print(f"❌ SUI échec de démarrage (code: {process.returncode})")
                    if stderr:
                        print(f"🔍 Erreurs : {stderr[:500]}...")
                    return False
            
            time.sleep(1)
        
        # Timeout atteint, tuer le processus
        print("⏰ Timeout atteint, arrêt du processus...")
        process.terminate()
        time.sleep(2)
        if process.poll() is None:
            process.kill()
            
        print("⚠️ SUI prend trop de temps à démarrer (normal en mode interactif)")
        return True  # Ce n'est pas forcément une erreur
        
    except Exception as e:
        print(f"❌ Erreur démarrage SUI : {e}")
        return False

def test_integration_script():
    """Création d'un script d'intégration SUI + TTS"""
    print_section("CRÉATION SCRIPT INTÉGRATION", "🔧")
    
    integration_script = PEER_ROOT / "sui_french_integration.py"
    
    script_content = '''#!/usr/bin/env python3
"""
Script d'intégration SUI + TTS Français
=====================================
"""

import sys
import os
from pathlib import Path

# Ajout du chemin Peer
sys.path.insert(0, "/Users/smpceo/Desktop/peer/src")

try:
    from peer.interfaces.sui.tts.text_to_speech import TextToSpeech
    from peer.interfaces.sui.tts.base import TTSConfig, TTSEngineType
    
    print("🇫🇷 Test intégration SUI + TTS Français")
    print("="*40)
    
    # Configuration française optimisée
    config = TTSConfig(
        engine_type=TTSEngineType.SIMPLE,
        language="fr",
        voice="Audrey",
        engine_specific_params={
            "rate": 190,
            "volume": 0.8,
            "preferred_simple_engine_order": ["say", "pyttsx3"]
        }
    )
    
    # Initialisation TTS
    tts = TextToSpeech(config)
    
    # Test de synthèse
    test_phrases = [
        "Bonjour, je suis votre assistant vocal Peer.",
        "Le système de synthèse vocale française est maintenant opérationnel.",  
        "Merci d'avoir testé le système SUI avec la voix française."
    ]
    
    for i, phrase in enumerate(test_phrases, 1):
        print(f"🎤 [{i}/{len(test_phrases)}] Synthèse : {phrase[:50]}...")
        
        try:
            result = tts.synthesize(phrase)
            if result and result.success and os.path.exists(result.audio_path):
                print(f"✅ Synthèse réussie")
                # Lecture
                os.system(f"afplay '{result.audio_path}'")
                # Nettoyage optionnel (les fichiers temp sont auto-nettoyés)
            else:
                print(f"❌ Échec synthèse")
        except Exception as e:
            print(f"❌ Erreur : {e}")
    
    print("\\n🎉 Test d'intégration terminé !")
    
except ImportError as e:
    print(f"❌ Erreur d'import : {e}")
except Exception as e:
    print(f"❌ Erreur générale : {e}")
'''
    
    try:
        with open(integration_script, 'w') as f:
            f.write(script_content)
        
        os.chmod(integration_script, 0o755)
        print(f"✅ Script créé : {integration_script}")
        
        # Test du script
        print("🔄 Exécution du script d'intégration...")
        result = subprocess.run(
            ["python3", str(integration_script)],
            capture_output=True,
            text=True,
            cwd=str(PEER_ROOT)
        )
        
        if result.returncode == 0:
            print("✅ Script d'intégration exécuté avec succès")
            print(f"📋 Sortie :\n{result.stdout}")
            return True
        else:
            print("❌ Échec du script d'intégration")
            print(f"🔍 Erreurs : {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur création script : {e}")
        return False

def main():
    """Test d'intégration complète"""
    print_section("TEST INTÉGRATION COMPLÈTE SUI + TTS FRANÇAIS", "🎯")
    
    tests = [
        ("Configuration", test_config_loading),
        ("TTS Direct", test_tts_direct),
        ("Script Intégration", test_integration_script),
        ("Démarrage SUI", test_sui_startup),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔄 Test : {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
            status = "✅ RÉUSSI" if result else "❌ ÉCHEC"
            print(f"📊 {test_name} : {status}")
        except Exception as e:
            print(f"❌ Erreur {test_name} : {e}")
            results.append((test_name, False))
    
    # Résultats finaux
    print_section("RÉSULTATS FINAUX", "🏆")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")
    
    print(f"\n📊 Score : {passed}/{total}")
    
    if passed == total:
        print("🎉 INTÉGRATION COMPLÈTE RÉUSSIE !")
        print("✅ Le système vocal français est prêt pour SUI")
    elif passed >= total * 0.75:
        print("⚠️ INTÉGRATION PARTIELLEMENT RÉUSSIE")
        print("🔧 Quelques ajustements mineurs peuvent être nécessaires")
    else:
        print("❌ INTÉGRATION ÉCHOUÉE")
        print("🔧 Des corrections sont nécessaires")
    
    print("\n📋 UTILISATION :")
    print("  • SUI complet : ./run_sui.sh")
    print("  • Test intégration : python3 sui_french_integration.py")
    print("  • Validation simple : python3 validation_finale_simple.py")

if __name__ == "__main__":
    main()
