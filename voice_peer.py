#!/usr/bin/env python3
"""
Système de communication vocale peer-to-peer avec XTTS V2 et WhisperX
Optimisé pour macOS avec support MPS (Metal Performance Shaders)
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

class VoicePeerSystem:
    def __init__(self):
        self.device = self._get_optimal_device()
        self.sample_rate = 16000
        self.chunk_duration = 3  # secondes
        self.is_running = False
        
        # Queues pour la communication entre threads
        self.audio_queue = queue.Queue()
        self.text_queue = queue.Queue()
        self.response_queue = queue.Queue()
        
        # Initialisation des modèles
        self._setup_whisperx()
        self._setup_xtts()
        
        # Configuration des dossiers
        self.temp_dir = Path("temp_audio")
        self.temp_dir.mkdir(exist_ok=True)
        
        print(f"✅ Système initialisé avec device: {self.device}")
        
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
                device=self.device if self.device != "mps" else "cpu",  # WhisperX n'est pas toujours compatible MPS
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
    
    def _setup_xtts(self):
        """Initialiser le système TTS (Tacotron2 pour stabilité)"""
        print("🔊 Initialisation du système TTS...")
        
        # Pour le moment, utilisons Tacotron2 qui est stable et fiable
        # XTTS V2 sera réactivé quand les incompatibilités seront résolues
        try:
            print("📍 Utilisation du modèle Tacotron2-DDC (stable et fiable)")
            self.tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")
            self.is_xtts_v2 = False
            
            if self.device == "mps":
                self.tts.to(self.device)
            elif self.device == "cuda":
                self.tts.to(self.device)
            
            print("✅ Tacotron2-DDC initialisé avec succès")
            
        except Exception as e:
            print(f"❌ Erreur lors de l'initialisation TTS: {e}")
            # Fallback sur CPU
            try:
                self.tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")
                self.is_xtts_v2 = False
                print("✅ Tacotron2-DDC initialisé en mode CPU")
            except Exception as e2:
                print(f"❌ Erreur fatale TTS: {e2}")
                raise e2
    
    def speech_to_text(self, audio_file_path):
        """Convertir la parole en texte avec WhisperX"""
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
    
    def text_to_speech(self, text, output_file, speaker_voice="female"):
        """Convertir le texte en parole avec Tacotron2"""
        try:
            print(f"🔊 Génération vocale avec Tacotron2")
            
            # Utiliser Tacotron2 (single speaker, stable)
            wav = self.tts.tts(text=text)
            
            # Ajuster le sample rate si nécessaire
            if hasattr(self.tts, 'synthesizer') and hasattr(self.tts.synthesizer, 'output_sample_rate'):
                output_sample_rate = self.tts.synthesizer.output_sample_rate
            else:
                output_sample_rate = 22050  # Sample rate par défaut pour Tacotron2
            
            sf.write(output_file, wav, output_sample_rate)
            return True
            
        except Exception as e:
            print(f"❌ Erreur text_to_speech: {e}")
            return False
    
    def record_audio(self, duration=None):
        """Enregistrer l'audio depuis le microphone avec optimisations"""
        duration = duration or self.chunk_duration
        
        try:
            print(f"🎤 Enregistrement audio ({duration}s)...")
            
            # Enregistrement avec paramètres optimisés
            audio_data = sd.rec(
                int(duration * self.sample_rate), 
                samplerate=self.sample_rate, 
                channels=1,
                dtype='float32',
                blocking=True  # Attendre automatiquement
            )
            
            # Normaliser l'audio pour améliorer la détection
            audio_data = audio_data.flatten()
            
            # Vérification de base du niveau audio
            max_amplitude = np.max(np.abs(audio_data))
            if max_amplitude < 0.01:  # Très faible signal
                print("⚠️ Signal audio très faible, vérifiez votre microphone")
            
            # Sauvegarder le fichier temporaire
            temp_file = self.temp_dir / f"recorded_{time.time()}.wav"
            sf.write(temp_file, audio_data, self.sample_rate)
            
            return str(temp_file)
            
        except Exception as e:
            print(f"❌ Erreur enregistrement audio: {e}")
            return None
    
    def play_audio(self, audio_file):
        """Lire un fichier audio"""
        try:
            audio_data, sample_rate = sf.read(audio_file)
            sd.play(audio_data, sample_rate)
            sd.wait()
            return True
        except Exception as e:
            print(f"❌ Erreur lecture audio: {e}")
            return False
    
    def process_voice_input(self):
        """Thread pour traiter l'entrée vocale en continu"""
        while self.is_running:
            try:
                # Enregistrer l'audio
                audio_file = self.record_audio()
                if audio_file:
                    # Convertir en texte
                    text = self.speech_to_text(audio_file)
                    if text:
                        print(f"👤 Vous avez dit: {text}")
                        self.text_queue.put(text)
                    
                    # Nettoyer le fichier temporaire
                    try:
                        os.remove(audio_file)
                    except:
                        pass
                        
                time.sleep(0.1)  # Petit délai
                
            except Exception as e:
                print(f"❌ Erreur process_voice_input: {e}")
                time.sleep(1)
    
    def process_text_response(self):
        """Thread pour traiter les réponses textuelles et les convertir en audio"""
        while self.is_running:
            try:
                if not self.response_queue.empty():
                    response_text = self.response_queue.get()
                    
                    # Convertir en audio
                    output_file = self.temp_dir / f"response_{time.time()}.wav"
                    if self.text_to_speech(response_text, str(output_file)):
                        print(f"🤖 Réponse: {response_text}")
                        
                        # Jouer l'audio
                        self.play_audio(str(output_file))
                        
                        # Nettoyer
                        try:
                            os.remove(output_file)
                        except:
                            pass
                
                time.sleep(0.1)
                
            except Exception as e:
                print(f"❌ Erreur process_text_response: {e}")
                time.sleep(1)
    
    def simple_ai_response(self, user_text):
        """Génère une réponse simple (à remplacer par votre logique IA)"""
        responses = {
            "hello": "Hello! How can I help you today?",
            "hi": "Hi there! Nice to meet you!",
            "how are you": "I'm doing great, thank you for asking!",
            "goodbye": "Goodbye! Have a wonderful day!",
            "bye": "See you later!",
            "what time": f"The current time is {time.strftime('%H:%M:%S')}",
            "date": f"Today is {time.strftime('%Y-%m-%d')}",
            "test": "This is a test response. The voice system is working correctly!",
        }
        
        user_lower = user_text.lower()
        for key, response in responses.items():
            if key in user_lower:
                return response
        
        return f"I heard you say: '{user_text}'. This is an echo response."
    
    def start_conversation(self):
        """Démarrer le système de conversation vocale"""
        print("\n🎙️ Démarrage du système de communication vocale peer-to-peer")
        print("=" * 60)
        print("📋 Instructions:")
        print("• Parlez clairement dans le microphone")
        print("• Le système vous répondra vocalement")
        print("• Tapez 'quit' pour quitter")
        print("=" * 60)
        
        self.is_running = True
        
        # Démarrer les threads
        voice_thread = threading.Thread(target=self.process_voice_input, daemon=True)
        response_thread = threading.Thread(target=self.process_text_response, daemon=True)
        
        voice_thread.start()
        response_thread.start()
        
        try:
            while True:
                # Vérifier les nouveaux messages texte
                if not self.text_queue.empty():
                    user_text = self.text_queue.get()
                    
                    # Générer une réponse
                    response = self.simple_ai_response(user_text)
                    self.response_queue.put(response)
                
                # Vérifier si l'utilisateur veut quitter
                try:
                    user_input = input("Tapez 'quit' pour quitter ou 'test' pour un test audio: ").strip()
                    if user_input.lower() == 'quit':
                        break
                    elif user_input.lower() == 'test':
                        self.response_queue.put("This is a test of the text to speech system. Can you hear me clearly?")
                except KeyboardInterrupt:
                    break
                
        except KeyboardInterrupt:
            print("\n👋 Arrêt du système...")
        finally:
            self.is_running = False
            time.sleep(1)  # Laisser les threads se terminer
    
    def test_system(self):
        """Tester les composants du système"""
        print("\n🧪 Test du système de communication vocale")
        print("=" * 50)
        
        # Test 1: Text-to-Speech
        print("1️⃣ Test de la synthèse vocale...")
        test_text = "Hello! This is a test of the voice synthesis system using XTTS version 2."
        test_file = self.temp_dir / "test_tts.wav"
        
        if self.text_to_speech(test_text, str(test_file)):
            print("✅ Synthèse vocale: OK")
            print(f"🔊 Lecture du test audio...")
            self.play_audio(str(test_file))
            
            # Nettoyer
            try:
                os.remove(test_file)
            except:
                pass
        else:
            print("❌ Synthèse vocale: ERREUR")
        
        # Test 2: Speech-to-Text
        print("\n2️⃣ Test de reconnaissance vocale...")
        print("🎤 Enregistrement de 5 secondes. Parlez maintenant!")
        
        audio_file = self.record_audio(5)
        if audio_file:
            text = self.speech_to_text(audio_file)
            if text:
                print(f"✅ Reconnaissance vocale: OK")
                print(f"📝 Texte détecté: '{text}'")
                
                # Echo test
                print("🔊 Echo du texte détecté...")
                echo_file = self.temp_dir / "echo_test.wav"
                if self.text_to_speech(f"I heard you say: {text}", str(echo_file)):
                    self.play_audio(str(echo_file))
                    try:
                        os.remove(echo_file)
                    except:
                        pass
            else:
                print("❌ Reconnaissance vocale: Aucun texte détecté")
            
            # Nettoyer
            try:
                os.remove(audio_file)
            except:
                pass
        else:
            print("❌ Enregistrement audio: ERREUR")
        
        print("\n✅ Tests terminés!")

def main():
    """Fonction principale"""
    print("🚀 Initialisation du système de communication vocale peer-to-peer")
    print("Utilisant XTTS V2 et WhisperX avec optimisation macOS MPS")
    
    try:
        # Créer le système
        voice_system = VoicePeerSystem()
        
        # Menu principal
        while True:
            print("\n" + "=" * 60)
            print("🎙️ SYSTÈME DE COMMUNICATION VOCALE PEER-TO-PEER")
            print("=" * 60)
            print("1. 🧪 Tester le système")
            print("2. 💬 Démarrer une conversation")
            print("3. 🔧 Informations système")
            print("4. 🚪 Quitter")
            print("=" * 60)
            
            choice = input("Choisissez une option (1-4): ").strip()
            
            if choice == "1":
                voice_system.test_system()
            elif choice == "2":
                voice_system.start_conversation()
            elif choice == "3":
                print(f"\n📊 Informations système:")
                print(f"Device: {voice_system.device}")
                print(f"Sample Rate: {voice_system.sample_rate}")
                print(f"Chunk Duration: {voice_system.chunk_duration}s")
                print(f"PyTorch version: {torch.__version__}")
                print(f"MPS disponible: {torch.backends.mps.is_available()}")
                print(f"XTTS V2 actif: {getattr(voice_system, 'is_xtts_v2', False)}")
            elif choice == "4":
                print("👋 Au revoir!")
                break
            else:
                print("❌ Option invalide. Veuillez choisir 1-4.")
                
    except Exception as e:
        print(f"❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
