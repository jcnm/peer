#!/usr/bin/env python3
"""
Enhanced voice peer system with improved XTTS V2 support and fallback mechanism
"""

import os
import time
import threading
import queue
import torch
import whisperx
import numpy as np
import soundfile as sf
import sounddevice as sd
from TTS.api import TTS
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

class EnhancedVoicePeerSystem:
    def __init__(self):
        self.device = self._get_optimal_device()
        self.sample_rate = 16000
        self.chunk_duration = 3  # secondes
        self.is_running = False
        
        # TTS Engine selection
        self.primary_tts_engine = "tacotron2"  # or "xtts_v2"
        self.fallback_tts_engine = "tacotron2"
        
        # Queues pour la communication entre threads
        self.audio_queue = queue.Queue()
        self.text_queue = queue.Queue()
        self.response_queue = queue.Queue()
        
        # Initialisation des modèles
        self._setup_whisperx()
        self._setup_tts_engines()
        
        # Configuration des dossiers
        self.temp_dir = Path("temp_audio")
        self.temp_dir.mkdir(exist_ok=True)
        
        print(f"✅ Système initialisé avec device: {self.device}")
        print(f"🔊 TTS Engine: {self.primary_tts_engine}")
        
    def _get_optimal_device(self):
        """Déterminer le meilleur device disponible pour macOS"""
        if torch.backends.mps.is_available() and torch.backends.mps.is_built():
            print("🚀 Utilisation de MPS (Metal Performance Shaders) pour macOS")
            return "mps"
        elif torch.cuda.is_available():
            print("🚀 Utilisation de CUDA")
            return "cuda"
        else:
            print("💻 Utilisation du CPU")
            return "cpu"
    
    def _setup_whisperx(self):
        """Initialiser WhisperX pour la reconnaissance vocale"""
        print("🎤 Initialisation de WhisperX...")
        try:
            # Configuration optimale pour MPS/macOS
            compute_type = "int8" if self.device == "mps" else "float16"
            
            # Charger le modèle Whisper optimisé
            self.whisper_model = whisperx.load_model(
                "base", 
                device=self.device if self.device != "mps" else "cpu",
                compute_type=compute_type
            )
            
            # Charger le modèle d'alignement pour une meilleure précision
            self.align_model, self.align_metadata = whisperx.load_align_model(
                language_code="en", 
                device=self.device if self.device != "mps" else "cpu"
            )
            
            print("✅ WhisperX initialisé avec succès")
        except Exception as e:
            print(f"❌ Erreur lors de l'initialisation WhisperX: {e}")
            # Fallback sur CPU si nécessaire
            self.whisper_model = whisperx.load_model("base", device="cpu", compute_type="int8")
            self.align_model, self.align_metadata = whisperx.load_align_model(language_code="en", device="cpu")
    
    def _apply_transformers_patch(self):
        """Apply patch for transformers compatibility with XTTS V2"""
        try:
            import transformers.models.gpt2.modeling_gpt2 as gpt2_modeling
            from transformers.generation.utils import GenerationMixin
            
            # Check if patch is needed
            original_class = gpt2_modeling.GPT2LMHeadModel
            if not hasattr(original_class, 'generate'):
                print("🔧 Applying transformers compatibility patch...")
                
                # Create patched class
                class PatchedGPT2LMHeadModel(original_class):
                    def generate(self, *args, **kwargs):
                        return GenerationMixin.generate(self, *args, **kwargs)
                
                # Apply patch
                gpt2_modeling.GPT2LMHeadModel = PatchedGPT2LMHeadModel
                print("✅ Transformers patch applied successfully")
                return True
            else:
                print("✅ Transformers patch not needed")
                return True
                
        except Exception as e:
            print(f"⚠️ Transformers patch failed: {e}")
            return False
    
    def _setup_tts_engines(self):
        """Initialiser les moteurs TTS avec fallback"""
        print("🔊 Initialisation des moteurs TTS...")
        
        self.tts_engines = {}
        
        # Try XTTS V2 first if enabled
        if self.primary_tts_engine == "xtts_v2":
            try:
                print("🧪 Tentative d'initialisation XTTS V2...")
                
                # Apply transformers patch
                if self._apply_transformers_patch():
                    # Try to load XTTS V2
                    xtts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
                    
                    if self.device == "mps":
                        xtts_model.to(self.device)
                    elif self.device == "cuda":
                        xtts_model.to(self.device)
                    
                    self.tts_engines["xtts_v2"] = xtts_model
                    print("✅ XTTS V2 initialisé avec succès!")
                    
                    # Create reference voice for cloning
                    self._setup_reference_voice()
                    
                else:
                    raise Exception("Transformers patch failed")
                    
            except Exception as e:
                print(f"⚠️ XTTS V2 failed: {e}")
                print("🔄 Basculement vers Tacotron2...")
                self.primary_tts_engine = "tacotron2"
        
        # Initialize Tacotron2 (stable fallback)
        try:
            print("📍 Initialisation Tacotron2-DDC...")
            tacotron_model = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")
            
            if self.device == "mps":
                tacotron_model.to(self.device)
            elif self.device == "cuda":
                tacotron_model.to(self.device)
            
            self.tts_engines["tacotron2"] = tacotron_model
            print("✅ Tacotron2-DDC initialisé avec succès")
            
        except Exception as e:
            print(f"❌ Erreur fatale TTS: {e}")
            raise e
    
    def _setup_reference_voice(self):
        """Setup reference voice for XTTS V2 voice cloning"""
        try:
            ref_voice_path = self.temp_dir / "reference_voice.wav"
            
            if not ref_voice_path.exists():
                print("🎤 Création de la voix de référence...")
                
                # Use Tacotron2 to create reference voice
                if "tacotron2" in self.tts_engines:
                    reference_text = "This is a reference voice for cloning. It will be used to generate natural speech in the target voice."
                    ref_wav = self.tts_engines["tacotron2"].tts(text=reference_text)
                    sf.write(ref_voice_path, ref_wav, 22050)
                    print(f"✅ Voix de référence créée: {ref_voice_path}")
                else:
                    # Fallback: create simple reference audio
                    sample_rate = 22050
                    duration = 3  # seconds
                    t = np.linspace(0, duration, int(sample_rate * duration))
                    # Create a simple tone pattern
                    frequency = 440  # A4 note
                    audio = 0.1 * np.sin(2 * np.pi * frequency * t)
                    sf.write(ref_voice_path, audio, sample_rate)
                    print(f"✅ Voix de référence simple créée: {ref_voice_path}")
            
            self.reference_voice_path = str(ref_voice_path)
            
        except Exception as e:
            print(f"⚠️ Erreur création voix de référence: {e}")
            self.reference_voice_path = None
    
    def text_to_speech(self, text, output_file, speaker_voice="female", language="en"):
        """Convertir le texte en parole avec gestion des multiples moteurs"""
        try:
            # Try primary engine first
            if self.primary_tts_engine in self.tts_engines:
                success = self._synthesize_with_engine(
                    self.primary_tts_engine, text, output_file, speaker_voice, language
                )
                if success:
                    return True
            
            # Try fallback engine
            if self.fallback_tts_engine in self.tts_engines and self.fallback_tts_engine != self.primary_tts_engine:
                print(f"🔄 Basculement vers {self.fallback_tts_engine}...")
                success = self._synthesize_with_engine(
                    self.fallback_tts_engine, text, output_file, speaker_voice, language
                )
                if success:
                    return True
            
            print("❌ Tous les moteurs TTS ont échoué")
            return False
            
        except Exception as e:
            print(f"❌ Erreur text_to_speech: {e}")
            return False
    
    def _synthesize_with_engine(self, engine_name, text, output_file, speaker_voice, language):
        """Synthesize with specific engine"""
        try:
            engine = self.tts_engines[engine_name]
            
            if engine_name == "xtts_v2":
                # XTTS V2 synthesis with voice cloning
                if self.reference_voice_path:
                    wav = engine.tts(
                        text=text,
                        speaker_wav=self.reference_voice_path,
                        language=language
                    )
                    sf.write(output_file, wav, 24000)  # XTTS V2 sample rate
                else:
                    print("⚠️ Pas de voix de référence pour XTTS V2")
                    return False
                    
            elif engine_name == "tacotron2":
                # Tacotron2 synthesis
                wav = engine.tts(text=text)
                output_sample_rate = getattr(engine.synthesizer, 'output_sample_rate', 22050)
                sf.write(output_file, wav, output_sample_rate)
            
            print(f"✅ Synthèse réussie avec {engine_name}")
            return True
            
        except Exception as e:
            print(f"❌ Échec synthèse {engine_name}: {e}")
            return False
    
    def speech_to_text(self, audio_file_path):
        """Convertir la parole en texte avec WhisperX - inchangé"""
        try:
            # Charger l'audio
            audio = whisperx.load_audio(audio_file_path)
            
            # Transcription avec paramètres optimisés pour de courts clips
            result = self.whisper_model.transcribe(
                audio, 
                batch_size=16,
                language=None,  # Auto-détection
                task="transcribe"
            )
            
            # Vérifier s'il y a des segments
            if not result.get("segments"):
                return ""
            
            # Alignement pour une meilleure précision (seulement si nécessaire)
            try:
                result = whisperx.align(
                    result["segments"], 
                    self.align_model, 
                    self.align_metadata, 
                    audio, 
                    self.device if self.device != "mps" else "cpu"
                )
            except Exception as align_error:
                print(f"⚠️ Warning: Alignment failed: {align_error}")
                # Continuer sans alignement
            
            # Extraire le texte
            if result.get("segments"):
                text = " ".join([segment["text"] for segment in result["segments"]])
                return text.strip()
            else:
                return ""
            
        except Exception as e:
            print(f"❌ Erreur speech_to_text: {e}")
            return ""
    
    def record_audio(self, duration=None):
        """Enregistrer l'audio depuis le microphone - inchangé"""
        duration = duration or self.chunk_duration
        
        try:
            print(f"🎤 Enregistrement audio ({duration}s)...")
            
            # Enregistrement avec paramètres optimisés
            audio_data = sd.rec(
                int(duration * self.sample_rate), 
                samplerate=self.sample_rate, 
                channels=1,
                dtype='float32',
                blocking=True
            )
            
            # Normaliser l'audio pour améliorer la détection
            audio_data = audio_data.flatten()
            
            # Vérification de base du niveau audio
            max_amplitude = np.max(np.abs(audio_data))
            if max_amplitude < 0.01:
                print("⚠️ Signal audio très faible, vérifiez votre microphone")
            
            # Sauvegarder le fichier temporaire
            temp_file = self.temp_dir / f"recorded_{time.time()}.wav"
            sf.write(temp_file, audio_data, self.sample_rate)
            
            return str(temp_file)
            
        except Exception as e:
            print(f"❌ Erreur enregistrement audio: {e}")
            return None
    
    def play_audio(self, audio_file):
        """Lire un fichier audio - inchangé"""
        try:
            audio_data, sample_rate = sf.read(audio_file)
            sd.play(audio_data, sample_rate)
            sd.wait()
            return True
        except Exception as e:
            print(f"❌ Erreur lecture audio: {e}")
            return False
    
    def get_system_status(self):
        """Get comprehensive system status"""
        status = {
            "device": self.device,
            "primary_tts": self.primary_tts_engine,
            "available_engines": list(self.tts_engines.keys()),
            "whisperx_ready": hasattr(self, 'whisper_model'),
            "reference_voice": hasattr(self, 'reference_voice_path') and self.reference_voice_path
        }
        return status
    
    def simple_ai_response(self, user_text):
        """Génère une réponse simple - inchangé"""
        responses = {
            "hello": "Hello! How can I help you today?",
            "hi": "Hi there! Nice to meet you!",
            "how are you": "I'm doing great, thank you for asking!",
            "goodbye": "Goodbye! Have a wonderful day!",
            "bye": "See you later!",
            "what time": f"The current time is {time.strftime('%H:%M:%S')}",
            "date": f"Today is {time.strftime('%Y-%m-%d')}",
            "test": "This is a test response. The voice system is working correctly!",
            "status": f"System status: Using {self.primary_tts_engine} TTS engine on {self.device} device.",
        }
        
        user_lower = user_text.lower()
        for key, response in responses.items():
            if key in user_lower:
                return response
        
        return f"I heard you say: '{user_text}'. This is an echo response."

def main():
    """Fonction principale pour tester le système amélioré"""
    print("🚀 Système de Communication Vocale Amélioré")
    print("=" * 60)
    
    try:
        # Créer le système amélioré
        voice_system = EnhancedVoicePeerSystem()
        
        # Afficher le statut
        status = voice_system.get_system_status()
        print(f"\n📊 STATUT DU SYSTÈME:")
        print(f"Device: {status['device']}")
        print(f"TTS Principal: {status['primary_tts']}")
        print(f"Moteurs disponibles: {', '.join(status['available_engines'])}")
        print(f"WhisperX: {'✅' if status['whisperx_ready'] else '❌'}")
        print(f"Voix de référence: {'✅' if status['reference_voice'] else '❌'}")
        
        # Test simple
        print(f"\n🧪 Test de synthèse...")
        test_text = "Hello! This is a test of the enhanced voice system with automatic engine fallback."
        test_file = voice_system.temp_dir / "enhanced_test.wav"
        
        if voice_system.text_to_speech(test_text, str(test_file)):
            print("✅ Test de synthèse réussi!")
            
            # Jouer l'audio
            print("🔊 Lecture du test...")
            voice_system.play_audio(str(test_file))
            
            # Nettoyer
            try:
                os.remove(test_file)
            except:
                pass
        else:
            print("❌ Test de synthèse échoué")
        
        print(f"\n✅ Système amélioré prêt à l'utilisation!")
        print(f"Vous pouvez maintenant utiliser ce système pour des conversations vocales complètes.")
        
    except Exception as e:
        print(f"❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
