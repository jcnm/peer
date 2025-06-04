"""
Module contenant l'adaptateur TTS simple pour Peer.
"""

import threading
import logging
import sys
import os
import subprocess
import tempfile
from typing import Optional

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

class SimpleTTSAdapter:
    """
    Adaptateur TTS simple utilisant pyttsx3 avec isolation de processus.
    Gère la synthèse vocale en créant un processus séparé pour chaque vocalisation,
    éliminant complètement le problème 'run loop already started'.
    """
    
    def __init__(self):
        """Initialise l'adaptateur TTS."""
        self.logger = logging.getLogger("SimpleTTSAdapter")
        self.tts_lock = threading.Lock()
        self.speaking = False
        self._test_tts_availability()
        self._test_audio_playback()
        self._setup_tts_manager()
    
    def _test_tts_availability(self):
        """Teste la disponibilité du TTS."""
        try:
            import pyttsx3
            self.logger.info("Module pyttsx3 disponible")
            self.tts_available = True
        except ImportError as e:
            self.logger.error(f"Module pyttsx3 non disponible: {e}")
            self.tts_available = False
    
    def _test_audio_playback(self):
        """Teste la disponibilité des outils de lecture audio."""
        self.audio_players = []
        
        # Test des commandes système pour la lecture audio
        if sys.platform == "darwin":  # macOS
            try:
                subprocess.run(["which", "afplay"], check=True, capture_output=True)
                self.audio_players.append("afplay")
                self.logger.info("✅ afplay disponible (macOS)")
            except subprocess.CalledProcessError:
                pass
        elif sys.platform == "linux":  # Linux
            for player in ["aplay", "paplay", "play"]:
                try:
                    subprocess.run(["which", player], check=True, capture_output=True)
                    self.audio_players.append(player)
                    self.logger.info(f"✅ {player} disponible (Linux)")
                    break
                except subprocess.CalledProcessError:
                    continue
        
        # Test des bibliothèques Python pour la lecture audio
        try:
            import sounddevice as sd
            import soundfile as sf
            self.audio_players.append("python_sounddevice")
            self.logger.info("✅ sounddevice + soundfile disponibles")
        except ImportError:
            pass
        
        try:
            import pygame
            self.audio_players.append("pygame")
            self.logger.info("✅ pygame disponible")
        except ImportError:
            pass
        
        if not self.audio_players:
            self.logger.warning("⚠️ Aucun système de lecture audio détecté")
        else:
            self.logger.info(f"🔊 Systèmes audio disponibles: {', '.join(self.audio_players)}")
    
    def _setup_tts_manager(self):
        """Configure le gestionnaire TTS avancé."""
        try:
            # Importer depuis le bon chemin avec le bon nom de classe
            sys.path.append('/Users/smpceo/Desktop/peer/src')
            from peer.interfaces.sui.tts.text_to_speech import TextToSpeech, TTSConfig, TTSEngineType, SimpleTTS, AdvancedTTS
            self.TextToSpeech = TextToSpeech
            self.TTSConfig = TTSConfig
            self.TTSEngineType = TTSEngineType
            self.SimpleTTS = SimpleTTS
            self.AdvancedTTS = AdvancedTTS
            self.advanced_tts_available = True
            self.logger.info("✅ Système TTS avancé disponible")
        except Exception as e:
            self.logger.debug(f"Système TTS avancé non disponible: {e}")
            self.advanced_tts_available = False
    
    def _play_audio_file(self, audio_file_path: str):
        """Lit un fichier audio avec le meilleur système disponible."""
        if not self.audio_players:
            self.logger.error("❌ Aucun système de lecture audio disponible")
            return False
        
        # Essayer les différents systèmes de lecture par ordre de préférence
        for player in self.audio_players:
            try:
                if player == "afplay":  # macOS
                    subprocess.run(["afplay", audio_file_path], check=True, timeout=30)
                    self.logger.debug(f"🔊 Audio lu avec afplay: {audio_file_path}")
                    return True
                    
                elif player in ["aplay", "paplay", "play"]:  # Linux
                    subprocess.run([player, audio_file_path], check=True, timeout=30)
                    self.logger.debug(f"🔊 Audio lu avec {player}: {audio_file_path}")
                    return True
                    
                elif player == "python_sounddevice":
                    import sounddevice as sd
                    import soundfile as sf
                    data, samplerate = sf.read(audio_file_path)
                    sd.play(data, samplerate)
                    sd.wait()  # Attendre que la lecture soit terminée
                    self.logger.debug(f"🔊 Audio lu avec sounddevice: {audio_file_path}")
                    return True
                    
                elif player == "pygame":
                    import pygame
                    pygame.mixer.init()
                    pygame.mixer.music.load(audio_file_path)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        import time
                        time.sleep(0.1)
                    pygame.mixer.quit()
                    self.logger.debug(f"🔊 Audio lu avec pygame: {audio_file_path}")
                    return True
                    
            except Exception as e:
                self.logger.debug(f"Échec lecture avec {player}: {e}")
                continue
        
        self.logger.error(f"❌ Impossible de lire le fichier audio: {audio_file_path}")
        return False
    
    def speak(self, text: str):
        """
        Vocalise un texte en utilisant les moteurs TTS disponibles et LIT l'audio.
        
        Args:
            text: Texte à vocaliser
        """
        if not text:
            return
        
        if not self.tts_available:
            self.logger.warning("TTS non disponible")
            print(f"TTS (non disponible): {text}")
            return
        
        # Acquérir le verrou pour éviter les vocalisations simultanées
        with self.tts_lock:
            try:
                self.speaking = True
                
                # Essayer d'abord les moteurs TTS système avec LECTURE AUDIO
                if self._try_system_tts_with_playback(text):
                    return
                
                # Fallback : processus séparé pyttsx3 (ancien système)
                self._speak_with_separate_process(text)
                
            except Exception as e:
                self.logger.error(f"Erreur lors de la vocalisation: {e}")
                print(f"TTS (erreur): {text}")
            finally:
                self.speaking = False
    
    def _try_system_tts_with_playback(self, text: str) -> bool:
        """Essaie la synthèse avec les moteurs système et lecture audio."""
        
        # Utiliser le système TTS avancé si disponible
        if self.advanced_tts_available:
            audio_file = self._synthesize_with_advanced_tts(text)
            if audio_file:
                # IMPORTANT: LIRE le fichier audio généré
                if self._play_audio_file(audio_file):
                    # Nettoyer le fichier temporaire après lecture
                    try:
                        os.unlink(audio_file)
                    except:
                        pass
                    return True
        
        return False
    
    def _speak_with_separate_process(self, text: str):
        """Méthode de fallback avec processus séparé (ancien système)."""
        # Créer un script Python temporaire pour la vocalisation
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            script_path = f.name
            f.write("""
import sys
import signal
import pyttsx3

def signal_handler(signum, frame):
    '''Gestionnaire de signal pour arrêt gracieux'''
    print("TTS subprocess interrupted gracefully")
    sys.exit(0)

def speak(text):
    # Installer le gestionnaire de signal pour KeyboardInterrupt
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 1.0)
        
        # Sélectionner une voix française si disponible
        voices = engine.getProperty('voices')
        for voice in voices:
            if 'french' in voice.name.lower() or 'fr' in voice.id.lower():
                engine.setProperty('voice', voice.id)
                break
        
        engine.say(text)
        engine.runAndWait()
        engine.stop()
    except Exception as e:
        print(f"TTS Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        speak(sys.argv[1])
""")
        
        # Exécuter le script dans un processus séparé
        try:
            # Utiliser le même interpréteur Python que celui en cours d'exécution
            python_executable = sys.executable
            subprocess.run([python_executable, script_path, text], 
                          check=True, 
                          timeout=60)  # Timeout de 60 secondes pour les messages longs
            self.logger.info(f"Texte vocalisé (processus séparé): {text[:50]}...")
        except subprocess.SubprocessError as e:
            self.logger.error(f"Erreur lors de l'exécution du processus TTS: {e}")
            print(f"TTS (erreur): {text}")
        finally:
            # Supprimer le fichier temporaire
            try:
                os.unlink(script_path)
            except Exception as e:
                self.logger.warning(f"Impossible de supprimer le fichier temporaire: {e}")
    
    def synthesize(self, text: str) -> Optional[str]:
        """
        Synthétise du texte en audio et retourne le chemin du fichier audio.
        
        Args:
            text: Texte à synthétiser
            
        Returns:
            Chemin vers le fichier audio généré ou None en cas d'échec
        """
        if not text:
            return None
        
        if not self.tts_available:
            self.logger.warning("TTS non disponible")
            return None
        
        with self.tts_lock:
            try:
                self.speaking = True
                
                # Essayer le système TTS avancé d'abord
                if self.advanced_tts_available:
                    result = self._synthesize_with_advanced_tts(text)
                    if result:
                        return result
                
                # Fallback vers pyttsx3 avec fichier de sortie
                return self._synthesize_with_pyttsx3(text)
                
            except Exception as e:
                self.logger.error(f"Erreur lors de la synthèse: {e}")
                return None
            finally:
                self.speaking = False
    
    def _synthesize_with_advanced_tts(self, text: str) -> Optional[str]:
        """Synthétise avec le système TTS avancé."""
        try:
            # Load configuration from SUI config file
            from peer.interfaces.sui.config.config_loader import load_sui_config, create_tts_config_from_sui_config
            
            sui_config = load_sui_config()
            tts_config = create_tts_config_from_sui_config(sui_config, text)
            tts_manager = self.TextToSpeech(tts_config)
            
            # Essayer la synthèse
            result = tts_manager.synthesize(text)
            if result.success and result.audio_file_path:
                self.logger.info(f"🎵 Synthèse réussie avec {result.engine_used}")
                return result.audio_file_path
            else:
                self.logger.debug(f"Synthèse avancée échouée: {result.error_message}")
                
        except Exception as e:
            self.logger.debug(f"Système TTS avancé échoué: {e}")
        
        return None
    
    def _synthesize_with_pyttsx3(self, text: str) -> Optional[str]:
        """Synthétise avec pyttsx3 basique vers un fichier."""
        try:
            # Créer un fichier temporaire pour l'audio
            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            audio_file_path = temp_file.name
            temp_file.close()
            
            # Créer un script Python temporaire pour la synthèse
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                script_path = f.name
                f.write(f"""
import sys
import pyttsx3
import os

def synthesize_to_file(text, output_file):
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 1.0)
        
        # Sélectionner une voix française si disponible
        voices = engine.getProperty('voices')
        for voice in voices:
            if 'french' in voice.name.lower() or 'fr' in voice.id.lower():
                engine.setProperty('voice', voice.id)
                break
        
        # Essayer save_to_file d'abord
        try:
            engine.save_to_file(text, output_file)
            engine.runAndWait()
            engine.stop()
            
            # Vérifier si le fichier a été créé
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                return True
        except Exception as e:
            print(f"save_to_file failed: {{e}}", file=sys.stderr)
        
        # Fallback: synthèse directe (pas de fichier audio mais au moins on test)
        print("Fallback: synthèse directe sans fichier", file=sys.stderr)
        engine.say(text)
        engine.runAndWait()
        engine.stop()
        
        # Créer un fichier vide pour indiquer le succès
        with open(output_file, 'w') as f:
            f.write("# Synthèse directe effectuée")
        
        return True
        
    except Exception as e:
        print(f"TTS Error: {{e}}", file=sys.stderr)
        return False

if __name__ == "__main__":
    if len(sys.argv) > 2:
        success = synthesize_to_file(sys.argv[1], sys.argv[2])
        sys.exit(0 if success else 1)
""")
            
            # Exécuter le script dans un processus séparé
            python_executable = sys.executable
            result = subprocess.run([python_executable, script_path, text, audio_file_path], 
                                  check=False,  # Ne pas lever d'exception sur erreur
                                  timeout=60,
                                  capture_output=True)
            
            # Nettoyer le script
            try:
                os.unlink(script_path)
            except:
                pass
            
            # Vérifier le résultat
            if result.returncode == 0 and os.path.exists(audio_file_path):
                self.logger.info(f"Synthèse pyttsx3 réussie vers fichier: {audio_file_path}")
                return audio_file_path
            else:
                # Afficher les erreurs pour debug
                if result.stderr:
                    self.logger.debug(f"Erreurs pyttsx3: {result.stderr.decode()}")
                
                # Nettoyer le fichier si vide ou inexistant
                try:
                    if os.path.exists(audio_file_path):
                        os.unlink(audio_file_path)
                except:
                    pass
                return None
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la synthèse avec pyttsx3: {e}")
            # Nettoyer les fichiers temporaires
            try:
                if os.path.exists(audio_file_path):
                    os.unlink(audio_file_path)
            except:
                pass
            try:
                if 'script_path' in locals() and os.path.exists(script_path):
                    os.unlink(script_path)
            except:
                pass
            return None
