#!/usr/bin/env python3
"""
Test d'intégration spécialisé SUI + SimpleTTS
=============================================
Test optimisé pour le fonctionnement direct du SimpleTTS
"""

import os
import sys
import time
from pathlib import Path

def print_section(title, emoji="🎯"):
    print(f"\n{emoji} {title}")
    print("=" * (len(title) + 3))

def test_simple_tts_direct():
    """Test direct optimisé pour SimpleTTS"""
    print_section("TEST SIMPLETTS DIRECT", "🔊")
    
    try:
        sys.path.insert(0, str(Path("/Users/smpceo/Desktop/peer/src")))
        from peer.interfaces.sui.tts.simple_tts_engine import SimpleTTS
        from peer.interfaces.sui.tts.base import TTSConfig, TTSEngineType
        
        # Configuration française optimisée
        config = TTSConfig(
            engine_type=TTSEngineType.SIMPLE,
            language="fr",
            voice="Audrey",
            engine_specific_params={
                "rate": 190,
                "volume": 0.8,
                "preferred_simple_engine_order": ["say"]  # Forcer l'utilisation de 'say'
            }
        )
        
        engine = SimpleTTS(config)
        
        # Test de synthèse directe
        test_text = "Bonjour, test d'intégration du système vocal français."
        print(f"🎤 Test synthèse directe : '{test_text}'")
        
        result = engine.synthesize(test_text)
        
        if result.success:
            print(f"✅ Synthèse réussie avec engine: {result.engine_used}")
            print("🔊 Audio joué directement (vocalisation directe)")
            return True
        else:
            print(f"❌ Échec synthèse : {result.error_message}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur SimpleTTS direct : {e}")
        return False

def test_texttospeech_facade():
    """Test de la façade TextToSpeech"""
    print_section("TEST FACADE TEXTTOSPEECH", "🎭")
    
    try:
        sys.path.insert(0, str(Path("/Users/smpceo/Desktop/peer/src")))
        from peer.interfaces.sui.tts.text_to_speech import TextToSpeech
        from peer.interfaces.sui.tts.base import TTSConfig, TTSEngineType
        
        # Configuration française pour TextToSpeech
        config = TTSConfig(
            engine_type=TTSEngineType.SIMPLE,
            language="fr",
            voice="Audrey",
            engine_specific_params={
                "preferred_simple_engine_order": ["say"]
            }
        )
        
        tts = TextToSpeech(config)
        
        # Test de synthèse
        test_phrases = [
            "Test un : Système vocal français opérationnel.",
            "Test deux : Intégration SUI réussie.",
            "Test trois : Voix Audrey activée."
        ]
        
        success_count = 0
        
        for i, phrase in enumerate(test_phrases, 1):
            print(f"🎤 [{i}/{len(test_phrases)}] Test : {phrase[:30]}...")
            
            try:
                result = tts.synthesize(phrase)
                if result.success:
                    print(f"✅ Synthèse réussie")
                    success_count += 1
                    # Petite pause entre les synthèses
                    time.sleep(1)
                else:
                    print(f"❌ Échec : {result.error_message if result.error_message else 'Erreur inconnue'}")
            except Exception as e:
                print(f"❌ Erreur : {e}")
        
        print(f"\n📊 Résultats : {success_count}/{len(test_phrases)} réussi(s)")
        return success_count >= len(test_phrases) * 0.8  # 80% de réussite
        
    except Exception as e:
        print(f"❌ Erreur façade TextToSpeech : {e}")
        return False

def test_system_voices():
    """Test des voix système disponibles"""
    print_section("TEST VOIX SYSTÈME", "🎯")
    
    try:
        import subprocess
        
        # Test des voix system sur macOS
        result = subprocess.run(["say", "-v", "?"], capture_output=True, text=True)
        
        if result.returncode == 0:
            voices = result.stdout
            french_voices = [line for line in voices.split('\n') if 'fr_' in line or 'french' in line.lower()]
            
            print(f"🔍 Voix françaises détectées ({len(french_voices)}) :")
            for voice in french_voices[:5]:  # Limiter l'affichage
                print(f"  • {voice.split()[0]}")
            
            # Test rapide avec Audrey
            print("\n🎤 Test vocal avec Audrey...")
            test_result = subprocess.run(
                ["say", "-v", "Audrey", "-r", "190", "Test d'intégration système vocal français"],
                capture_output=True
            )
            
            if test_result.returncode == 0:
                print("✅ Test vocal Audrey réussi")
                return True
            else:
                print("❌ Test vocal Audrey échoué")
                return False
        else:
            print("❌ Commande 'say' non disponible")
            return False
            
    except Exception as e:
        print(f"❌ Erreur test voix système : {e}")
        return False

def main():
    """Test d'intégration spécialisé SimpleTTS"""
    print_section("TEST INTÉGRATION SPÉCIALISÉ SIMPLETTS", "🚀")
    
    tests = [
        ("Voix Système", test_system_voices),
        ("SimpleTTS Direct", test_simple_tts_direct),
        ("Façade TextToSpeech", test_texttospeech_facade),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔄 Exécution : {test_name}")
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
        print("🎉 INTÉGRATION SIMPLETTS COMPLÈTEMENT RÉUSSIE !")
        print("✅ Le système vocal français SimpleTTS est prêt")
    elif passed >= total * 0.66:
        print("⚠️ INTÉGRATION SIMPLETTS PARTIELLEMENT RÉUSSIE")
        print("🔧 Système fonctionnel avec ajustements mineurs")
    else:
        print("❌ INTÉGRATION SIMPLETTS ÉCHOUÉE")
        print("🔧 Des corrections majeures sont nécessaires")
    
    print("\n📋 UTILISATION RECOMMANDÉE :")
    print("  • SUI avec SimpleTTS : ./run_sui.sh")
    print("  • Configuration : models.yaml avec engine 'simple'")
    print("  • Voix française : Audrey (auto-sélectionnée)")
    print("  • Vocalisation : Directe (pas de fichier audio)")

if __name__ == "__main__":
    main()
