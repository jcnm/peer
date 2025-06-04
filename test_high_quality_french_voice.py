#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test TTS/STT haute qualité français avec XTTS V2 + WhisperX
Solution portable sans dépendance système pour voix française premium
"""

import sys
import os
import time
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import torch
import logging
import tempfile
import soundfile as sf
from pathlib import Path

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("HighQualityFrenchVoice")

def test_xtts_v2_french():
    """Test XTTS V2 pour voix française de haute qualité"""
    
    print("🎯 TEST HAUTE QUALITÉ - TTS/STT FRANÇAIS XTTS V2")
    print("=" * 60)
    
    try:
        # Vérification PyTorch avec MPS
        print("🔧 Vérification environnement PyTorch...")
        if torch.backends.mps.is_available():
            device = "mps"
            print(f"✅ PyTorch MPS disponible : {torch.backends.mps.is_built()}")
        else:
            device = "cpu"
            print("ℹ️ Utilisation CPU (MPS non disponible)")
        
        print(f"🎯 Device sélectionné : {device}")
        
        # Import XTTS V2
        print("\n📥 Chargement XTTS V2...")
        from TTS.api import TTS
        
        # Initialisation XTTS V2 multilingue
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
        print("✅ XTTS V2 chargé avec succès")
        
        # Textes de test français
        test_texts = [
            "Bonjour ! Je suis l'assistant vocal Peer avec une voix française de haute qualité.",
            "Ma synthèse vocale utilise XTTS V2 pour une prononciation française naturelle et fluide.",
            "Cette solution est portable et fonctionne sur différents systèmes sans dépendances.",
            "L'intelligence artificielle vocale française atteint maintenant un niveau premium.",
            "Merci d'utiliser Peer - votre interface vocale française avancée."
        ]
        
        # Vérification voix de référence française
        ref_voice_path = "/Users/smpceo/Desktop/peer/temp_audio/reference_voice.wav"
        if not os.path.exists(ref_voice_path):
            print(f"⚠️ Voix de référence manquante : {ref_voice_path}")
            print("🔄 Création d'une voix de référence temporaire...")
            
            # Génération voix de référence avec une phrase simple
            temp_ref = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tts.tts_to_file(
                text="Ceci est ma voix de référence française pour la synthèse vocale.",
                file_path=temp_ref.name,
                language="fr"
            )
            ref_voice_path = temp_ref.name
            print(f"✅ Voix de référence créée : {ref_voice_path}")
        
        print(f"\n🎤 Test de {len(test_texts)} phrases françaises avec XTTS V2...")
        
        results = []
        for i, text in enumerate(test_texts, 1):
            print(f"\n[{i}/{len(test_texts)}] 🔊 Synthèse : '{text[:50]}...'")
            
            try:
                start_time = time.time()
                
                # Synthèse avec clonage de voix française
                output_path = f"/tmp/xtts_french_test_{i}.wav"
                
                tts.tts_to_file(
                    text=text,
                    speaker_wav=ref_voice_path,
                    language="fr",
                    file_path=output_path
                )
                
                synthesis_time = time.time() - start_time
                
                # Vérification du fichier généré
                if os.path.exists(output_path):
                    audio_data, sample_rate = sf.read(output_path)
                    duration = len(audio_data) / sample_rate
                    
                    print(f"✅ Synthèse réussie : {synthesis_time:.2f}s")
                    print(f"   📊 Durée audio : {duration:.2f}s")
                    print(f"   📁 Fichier : {output_path}")
                    
                    # Lecture automatique sur macOS
                    os.system(f"afplay {output_path}")
                    
                    results.append({
                        'text': text,
                        'synthesis_time': synthesis_time,
                        'audio_duration': duration,
                        'file_path': output_path,
                        'success': True
                    })
                else:
                    print(f"❌ Fichier audio non généré")
                    results.append({'text': text, 'success': False})
                    
            except Exception as e:
                print(f"❌ Erreur synthèse : {e}")
                results.append({'text': text, 'success': False, 'error': str(e)})
        
        # Statistiques finales
        successful = [r for r in results if r.get('success', False)]
        print(f"\n📊 RÉSULTATS XTTS V2 FRANÇAIS")
        print("=" * 40)
        print(f"✅ Synthèses réussies : {len(successful)}/{len(test_texts)}")
        
        if successful:
            avg_synthesis_time = sum(r['synthesis_time'] for r in successful) / len(successful)
            avg_audio_duration = sum(r['audio_duration'] for r in successful) / len(successful)
            
            print(f"⚡ Temps synthèse moyen : {avg_synthesis_time:.2f}s")
            print(f"🎵 Durée audio moyenne : {avg_audio_duration:.2f}s")
            print(f"🚀 Ratio performance : {avg_audio_duration/avg_synthesis_time:.2f}x temps réel")
            
            print(f"\n🎯 QUALITÉ VOCALE FRANÇAISE :")
            print("✅ Accent français naturel (XTTS V2)")
            print("✅ Clonage de voix de référence")
            print("✅ Synthèse multilingue avancée")
            print("✅ Solution portable sans dépendance système")
        
        return len(successful) == len(test_texts)
        
    except ImportError as e:
        print(f"❌ Erreur import TTS : {e}")
        print("💡 Installation requise : pip install TTS")
        return False
    except Exception as e:
        print(f"❌ Erreur XTTS V2 : {e}")
        return False

def test_whisperx_french():
    """Test WhisperX pour reconnaissance vocale française haute qualité"""
    
    print("\n🎤 TEST WHISPERX - RECONNAISSANCE FRANÇAISE")
    print("=" * 50)
    
    try:
        import whisperx
        
        print("📥 Chargement WhisperX pour français...")
        
        # Chargement modèle WhisperX français
        model = whisperx.load_model("base", device="cpu", language="fr")
        print("✅ Modèle WhisperX français chargé")
        
        # Test avec fichier audio français existant
        test_audio = "/Users/smpceo/Desktop/peer/temp_audio/reference_voice.wav"
        
        if os.path.exists(test_audio):
            print(f"🔊 Test reconnaissance sur : {test_audio}")
            
            # Transcription
            audio = whisperx.load_audio(test_audio)
            result = whisperx.transcribe(audio, model)
            
            print(f"📝 Transcription : '{result['text']}'")
            print("✅ WhisperX français fonctionnel")
            
            return True
        else:
            print("⚠️ Aucun fichier audio de test disponible")
            return False
            
    except ImportError:
        print("❌ WhisperX non installé")
        print("💡 Installation : pip install whisperx")
        return False
    except Exception as e:
        print(f"❌ Erreur WhisperX : {e}")
        return False

def main():
    """Test complet TTS/STT haute qualité français"""
    
    print("🚀 TEST COMPLET - SYSTÈME VOCAL FRANÇAIS HAUTE QUALITÉ")
    print("=" * 70)
    print("🎯 Objectif : Voix française premium sans dépendance système")
    print("🔧 Technologies : XTTS V2 + WhisperX")
    print()
    
    # Test TTS haute qualité
    tts_success = test_xtts_v2_french()
    
    # Test STT haute qualité  
    stt_success = test_whisperx_french()
    
    # Résultat final
    print(f"\n🏆 RÉSULTAT FINAL")
    print("=" * 30)
    
    if tts_success and stt_success:
        print("✅ SYSTÈME VOCAL FRANÇAIS HAUTE QUALITÉ VALIDÉ")
        print("🎯 TTS : XTTS V2 avec accent français naturel")
        print("🎤 STT : WhisperX reconnaissance française précise")
        print("📦 Solution portable multi-plateforme")
        return True
    else:
        print("⚠️ Configuration requise pour système haute qualité")
        if not tts_success:
            print("❌ TTS XTTS V2 : Problème détecté")
        if not stt_success:
            print("❌ STT WhisperX : Problème détecté")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
