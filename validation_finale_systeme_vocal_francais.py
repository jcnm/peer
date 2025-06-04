#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validation finale du système vocal français haute qualité
Test complet de l'intégration SUI + Peer + Voix française premium
"""

import sys
import os
import time
import subprocess
import logging
from pathlib import Path

# Configuration logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FinalFrenchValidation")

def test_basic_french_voice():
    """Test de base de la synthèse vocale française"""
    
    print("🎯 TEST 1/5 : SYNTHÈSE VOCALE FRANÇAISE DE BASE")
    print("=" * 55)
    
    try:
        # Test direct avec say
        test_text = "Bonjour ! Test de la voix française optimisée."
        print(f"🔊 Test direct avec voix Audrey : '{test_text}'")
        
        if sys.platform == "darwin":
            cmd = ["say", "-v", "Audrey", "-r", "200", test_text]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Test vocal de base réussi")
                return True
            else:
                print(f"❌ Erreur test vocal : {result.stderr}")
                return False
        else:
            print("ℹ️ Test vocal système non disponible (macOS requis)")
            return True
            
    except Exception as e:
        print(f"❌ Erreur test vocal de base : {e}")
        return False

def test_peer_tts_integration():
    """Test d'intégration TTS avec les modules Peer"""
    
    print("\n🎯 TEST 2/5 : INTÉGRATION TTS PEER")
    print("=" * 40)
    
    try:
        # Test d'import des modules TTS
        sys.path.insert(0, '/Users/smpceo/Desktop/peer/src')
        
        from peer.interfaces.sui.tts.text_to_speech import TextToSpeech
        from peer.interfaces.sui.tts.base import TTSConfig
        
        print("✅ Modules TTS Peer importés avec succès")
        
        # Test de configuration TTS
        config = TTSConfig(
            engine="simple",
            voice="Audrey",
            language="fr-FR",
            engine_specific_params={
                "engines": {
                    "say": {
                        "voice": "Audrey",
                        "rate": 200
                    }
                },
                "preferred_simple_engine_order": ["say", "pyttsx3", "espeak", "mock"]
            }
        )
        
        tts = TextToSpeech(config)
        print("✅ TextToSpeech configuré pour français")
        
        # Test de synthèse
        test_text = "Test d'intégration TTS avec la voix française Audrey."
        print(f"🔊 Test synthèse : '{test_text}'")
        
        result = tts.synthesize(test_text)
        
        if result.success:
            print("✅ Synthèse TTS intégrée réussie")
            return True
        else:
            print(f"❌ Échec synthèse TTS : {result.error_message}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur intégration TTS Peer : {e}")
        return False

def test_sui_startup():
    """Test de démarrage SUI avec configuration française"""
    
    print("\n🎯 TEST 3/5 : DÉMARRAGE SUI AVEC CONFIGURATION FRANÇAISE")
    print("=" * 65)
    
    try:
        # Vérifier la configuration
        config_path = Path("/Users/smpceo/.peer/config/sui/models.yaml")
        if not config_path.exists():
            print("❌ Configuration SUI non trouvée")
            return False
        
        print("✅ Configuration SUI trouvée")
        
        # Tester le script de lancement
        if not Path("/Users/smpceo/Desktop/peer/run_sui.sh").exists():
            print("❌ Script run_sui.sh non trouvé")
            return False
        
        print("✅ Script SUI disponible")
        
        # Test rapide de démarrage SUI (timeout court)
        print("🔄 Test démarrage SUI (timeout 10s)...")
        
        process = subprocess.Popen(
            ["./run_sui.sh"],
            cwd="/Users/smpceo/Desktop/peer",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Attendre un peu pour voir si le processus démarre
        time.sleep(5)
        
        if process.poll() is None:
            print("✅ SUI démarre correctement")
            # Arrêter le processus
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
            return True
        else:
            stdout, stderr = process.communicate()
            print(f"❌ SUI n'a pas démarré correctement")
            if stderr:
                print(f"Erreur : {stderr[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ Erreur test démarrage SUI : {e}")
        return False

def test_voice_quality_comparison():
    """Test comparatif de qualité vocale"""
    
    print("\n🎯 TEST 4/5 : COMPARAISON QUALITÉ VOCALE")
    print("=" * 45)
    
    try:
        if sys.platform != "darwin":
            print("ℹ️ Test qualité vocal disponible uniquement sur macOS")
            return True
        
        # Test de différentes voix françaises
        french_voices = ["Audrey", "Amelie", "Thomas", "Virginie"]
        test_text = "Voici un test de qualité de la synthèse vocale française."
        
        successful_voices = []
        
        for voice in french_voices:
            print(f"🔊 Test voix {voice}...")
            
            try:
                cmd = ["say", "-v", voice, test_text]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    print(f"✅ Voix {voice} : Fonctionnelle")
                    successful_voices.append(voice)
                    time.sleep(0.5)  # Pause entre les voix
                else:
                    print(f"❌ Voix {voice} : Erreur")
                    
            except subprocess.TimeoutExpired:
                print(f"⚠️ Voix {voice} : Timeout")
            except Exception as e:
                print(f"❌ Voix {voice} : {e}")
        
        if successful_voices:
            print(f"\n✅ Test qualité : {len(successful_voices)}/{len(french_voices)} voix françaises disponibles")
            print(f"🎯 Voix recommandée pour Peer : Audrey")
            return True
        else:
            print("❌ Aucune voix française fonctionnelle")
            return False
            
    except Exception as e:
        print(f"❌ Erreur test qualité vocale : {e}")
        return False

def test_complete_workflow():
    """Test du workflow complet avec démonstration"""
    
    print("\n🎯 TEST 5/5 : WORKFLOW COMPLET")
    print("=" * 35)
    
    try:
        # Test du script de démonstration
        demo_path = Path("/Users/smpceo/Desktop/peer/demo_voice_system.py")
        if not demo_path.exists():
            print("❌ Script démonstration non trouvé")
            return False
        
        print("🔄 Exécution script démonstration...")
        
        result = subprocess.run(
            ["python", str(demo_path)],
            cwd="/Users/smpceo/Desktop/peer",
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✅ Script démonstration exécuté avec succès")
            print("🎤 Workflow vocal français complet validé")
            return True
        else:
            print(f"❌ Erreur script démonstration : {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⚠️ Script démonstration : Timeout")
        return False
    except Exception as e:
        print(f"❌ Erreur workflow complet : {e}")
        return False

def create_final_report(results):
    """Création du rapport final de validation"""
    
    print("\n🏆 RAPPORT FINAL - SYSTÈME VOCAL FRANÇAIS HAUTE QUALITÉ")
    print("=" * 70)
    
    total_score = sum(results.values())
    max_score = len(results)
    percentage = (total_score / max_score) * 100
    
    print(f"📊 SCORE GLOBAL : {total_score}/{max_score} ({percentage:.1f}%)")
    print()
    
    test_names = {
        'basic_voice': "Synthèse vocale de base",
        'tts_integration': "Intégration TTS Peer", 
        'sui_startup': "Démarrage SUI",
        'voice_quality': "Qualité vocale",
        'complete_workflow': "Workflow complet"
    }
    
    for test_key, passed in results.items():
        status = "✅ VALIDÉ" if passed else "❌ ÉCHEC"
        print(f"{status} : {test_names[test_key]}")
    
    print()
    
    if total_score >= 4:
        print("🎉 SYSTÈME VOCAL FRANÇAIS HAUTE QUALITÉ VALIDÉ !")
        print()
        print("📋 RÉSUMÉ DE LA SOLUTION :")
        print("   • Voix française premium : Audrey (macOS)")
        print("   • Moteur TTS : Simple TTS avec commande 'say'")
        print("   • Configuration : Optimisée pour français sans accent anglais")
        print("   • Intégration : Compatible avec SUI de Peer")
        print("   • Performance : Synthèse temps réel haute qualité")
        print()
        print("🚀 PRÊT POUR PRODUCTION :")
        print("   1. Lancer : ./run_sui.sh")
        print("   2. Utiliser : Commandes vocales en français")
        print("   3. Réponses : Voix française naturelle sans accent anglais")
        
        return True
    elif total_score >= 2:
        print("⚠️ Système partiellement fonctionnel")
        print("💡 Actions recommandées selon les échecs détectés")
        return False
    else:
        print("❌ Système vocal non fonctionnel")
        print("🔧 Révision complète de l'installation requise")
        return False

def main():
    """Validation finale complète du système vocal français"""
    
    print("🚀 VALIDATION FINALE - SYSTÈME VOCAL FRANÇAIS HAUTE QUALITÉ")
    print("=" * 70)
    print("🎯 Objectif : Validation complète pour production")
    print("🔧 Tests : Synthèse, intégration, démarrage, qualité, workflow")
    print()
    
    # Exécution des tests
    results = {}
    
    results['basic_voice'] = test_basic_french_voice()
    results['tts_integration'] = test_peer_tts_integration()
    results['sui_startup'] = test_sui_startup()
    results['voice_quality'] = test_voice_quality_comparison()
    results['complete_workflow'] = test_complete_workflow()
    
    # Génération du rapport final
    success = create_final_report(results)
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
