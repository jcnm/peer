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
    
    def _test_tts_availability(self):
        """Teste la disponibilité du TTS."""
        try:
            import pyttsx3
            self.logger.info("Module pyttsx3 disponible")
            self.tts_available = True
        except ImportError as e:
            self.logger.error(f"Module pyttsx3 non disponible: {e}")
            self.tts_available = False
    
    def speak(self, text: str):
        """
        Vocalise un texte en utilisant un processus séparé pour éviter les conflits.
        
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
                    self.logger.info(f"Texte vocalisé: {text[:50]}...")
                except subprocess.SubprocessError as e:
                    self.logger.error(f"Erreur lors de l'exécution du processus TTS: {e}")
                    print(f"TTS (erreur): {text}")
                finally:
                    # Supprimer le fichier temporaire
                    try:
                        os.unlink(script_path)
                    except Exception as e:
                        self.logger.warning(f"Impossible de supprimer le fichier temporaire: {e}")
            
            except Exception as e:
                self.logger.error(f"Erreur lors de la vocalisation: {e}")
                print(f"TTS (erreur): {text}")
            finally:
                self.speaking = False
