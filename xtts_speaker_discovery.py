#!/usr/bin/env python3
"""
Utilitaire pour découvrir les speakers disponibles dans XTTS V2
"""

import torch
from TTS.api import TTS
import warnings
warnings.filterwarnings("ignore")

def discover_xtts_speakers():
    """Découvrir les speakers disponibles dans XTTS V2"""
    print("🔍 Découverte des speakers XTTS V2...")
    
    try:
        # Configuration temporaire pour contourner le problème weights_only
        old_load = torch.load
        def safe_load(*args, **kwargs):
            kwargs['weights_only'] = False
            return old_load(*args, **kwargs)
        torch.load = safe_load
        
        # Charger XTTS V2
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
        
        # Restaurer la fonction load originale
        torch.load = old_load
        
        print("✅ XTTS V2 chargé avec succès")
        
        # Essayer différentes méthodes pour obtenir les speakers
        speakers_found = False
        
        # Méthode 1: tts.speakers
        if hasattr(tts, 'speakers') and tts.speakers:
            print(f"📋 Speakers via tts.speakers: {tts.speakers}")
            speakers_found = True
        
        # Méthode 2: tts.tts.speakers  
        if hasattr(tts, 'tts') and hasattr(tts.tts, 'speakers') and tts.tts.speakers:
            print(f"📋 Speakers via tts.tts.speakers: {tts.tts.speakers}")
            speakers_found = True
            
        # Méthode 3: tts.synthesizer
        if hasattr(tts, 'synthesizer'):
            synth = tts.synthesizer
            if hasattr(synth, 'tts_speakers') and synth.tts_speakers:
                print(f"📋 Speakers via synthesizer.tts_speakers: {synth.tts_speakers}")
                speakers_found = True
            if hasattr(synth, 'speaker_manager') and synth.speaker_manager:
                sm = synth.speaker_manager
                if hasattr(sm, 'speaker_names') and sm.speaker_names:
                    print(f"📋 Speakers via speaker_manager.speaker_names: {sm.speaker_names}")
                    speakers_found = True
                if hasattr(sm, 'speakers') and sm.speakers:
                    print(f"📋 Speakers via speaker_manager.speakers: {list(sm.speakers.keys())}")
                    speakers_found = True
        
        # Méthode 4: Inspection directe des attributs
        print("\n🔍 Inspection des attributs XTTS:")
        attrs = [attr for attr in dir(tts) if 'speaker' in attr.lower()]
        for attr in attrs:
            try:
                value = getattr(tts, attr)
                print(f"  - {attr}: {value}")
            except:
                print(f"  - {attr}: <non accessible>")
        
        if hasattr(tts, 'tts'):
            print("\n🔍 Inspection des attributs tts.tts:")
            attrs = [attr for attr in dir(tts.tts) if 'speaker' in attr.lower()]
            for attr in attrs:
                try:
                    value = getattr(tts.tts, attr)
                    print(f"  - tts.{attr}: {value}")
                except:
                    print(f"  - tts.{attr}: <non accessible>")
        
        if not speakers_found:
            print("⚠️ Aucun speaker trouvé via les méthodes standards")
            print("💡 XTTS V2 utilise peut-être des embeddings de référence vocale")
        
        # Test avec une approche de clonage vocal
        print("\n🧪 Test avec approche de clonage vocal...")
        try:
            # Essayer de générer sans speaker mais avec un fichier de référence
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                tts.tts_to_file(
                    text="Hello, this is a test.", 
                    file_path=tmp.name,
                    language="en"
                )
                print("✅ Génération réussie sans speaker explicite !")
                return True
        except Exception as e:
            print(f"❌ Erreur lors de la génération: {e}")
            
            # Essayer avec un fichier de référence vocal
            print("🎤 Essai avec fichier de référence vocal...")
            try:
                # Créer un fichier audio de référence simple
                import numpy as np
                import soundfile as sf
                
                # Générer un signal audio simple (440Hz pendant 1 seconde)
                sample_rate = 22050
                duration = 1
                t = np.linspace(0, duration, int(sample_rate * duration))
                signal = 0.1 * np.sin(2 * np.pi * 440 * t)
                
                ref_file = "temp_reference.wav"
                sf.write(ref_file, signal, sample_rate)
                
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                    tts.tts_to_file(
                        text="Hello, this is a test with voice cloning.", 
                        file_path=tmp.name,
                        speaker_wav=ref_file,
                        language="en"
                    )
                    print("✅ Génération réussie avec fichier de référence !")
                    return True
                    
            except Exception as e2:
                print(f"❌ Erreur avec fichier de référence: {e2}")
        
        return False
        
    except Exception as e:
        print(f"❌ Erreur lors du chargement XTTS V2: {e}")
        return False

if __name__ == "__main__":
    discover_xtts_speakers()
