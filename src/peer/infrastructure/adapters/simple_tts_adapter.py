"""
Module contenant l'adaptateur de synthèse vocale simple avec fallback pyttsx3.
"""

import os
import platform
import subprocess
import logging
from typing import Optional

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

from peer.domain.ports.tts_port import TTSPort

logger = logging.getLogger(__name__)


class SimpleTTSAdapter(TTSPort):
    """
    Adaptateur simple pour la synthèse vocale avec fallback pyttsx3.
    """
    
    def __init__(self):
        """Initialise l'adaptateur TTS."""
        self.initialized = False
        self.platform = platform.system().lower()
        self.tts_command = self._get_tts_command()
        self.pyttsx3_engine = None
        self.use_pyttsx3 = True  # Forcer l'utilisation de pyttsx3

        # Initialiser avec configuration optimale
        if self._init_pyttsx3():
            print("Moteur pyttsx3 initialisé avec succès")
            # self.configure_natural_speech()
    
    def _test_say_command(self) -> bool:
        """Teste si la commande say fonctionne."""
        try:
            result = subprocess.run(
                ["say", "-v", "?"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                timeout=5,
                check=False
            )
            return result.returncode == 0
        except Exception as e:
            print(f"Test de la commande say échoué: {str(e)}")
            return False
        
    def _init_pyttsx3(self):
        """Initialise le moteur pyttsx3 avec la configuration optimale pour une voix naturelle."""
        if not PYTTSX3_AVAILABLE:
            print("pyttsx3 n'est pas installé")
            return False
        
        try:
            self.pyttsx3_engine = pyttsx3.init()
            
            # Configuration optimale pour une voix naturelle
            voices = self.pyttsx3_engine.getProperty('voices')
            selected_voice = None
            
            if voices:
                # Priorité de sélection des voix pour un rendu naturel
                voice_priorities = [
                    # Voix françaises premium (les plus naturelles)
                    ['thomas', 'audrey',  'shelley', 'grandma', 'eddy', 'clementine', 'celine', 'juliette'],
                    # Voix françaises standard
                    ['french', 'fr-fr', 'française'],
                    # Voix de qualité sur différentes plateformes
                    ['zira', 'hazel', 'karen', 'daniel', 'samantha', 'alex']
                ]
                
                # Chercher par ordre de priorité
                for priority_group in voice_priorities:
                    for voice in voices:
                        voice_name_lower = voice.name.lower() if voice.name else ""
                        voice_id_lower = voice.id.lower() if voice.id else ""
                        
                        for priority_name in priority_group:
                            if priority_name in voice_name_lower or priority_name in voice_id_lower:
                                selected_voice = voice
                                print(f"Voix sélectionnée: {voice.name} (priorité: {priority_name})")
                                break
                        if selected_voice:
                            break
                    if selected_voice:
                        break
                
                # Si aucune voix prioritaire trouvée, utiliser la première disponible
                if not selected_voice and voices:
                    selected_voice = voices[0]
                    print(f"Voix par défaut utilisée: {selected_voice.name}")
                
                if selected_voice:
                    self.pyttsx3_engine.setProperty('voice', selected_voice.id)
            
            # Configuration optimale pour une voix naturelle
            
            # 1. Vitesse de parole (mots par minute)
            # 150-180 = naturel et compréhensible
            # 120-140 = plus lent, style narration
            # 200+ = trop rapide, robotique
            self.pyttsx3_engine.setProperty('rate', 165)
            
            # 2. Volume (0.0 à 1.0)
            # 0.8-0.9 = optimal, évite la saturation
            self.pyttsx3_engine.setProperty('volume', 0.85)
            
            # 3. Propriétés avancées si supportées par le moteur
            try:
                # Pitch (hauteur de voix) - si supporté
                # Valeurs typiques: 0-100, 50 = neutre
                self.pyttsx3_engine.setProperty('pitch', 45)  # Légèrement plus grave
            except:
                pass  # Pas supporté sur tous les systèmes
            
            print("Moteur pyttsx3 configuré pour un rendu vocal naturel")
            return True
            
        except Exception as e:
            print(f"Erreur lors de l'initialisation de pyttsx3: {str(e)}")
            return False

    def configure_natural_speech(self):
        """Configuration avancée pour un rendu vocal plus naturel."""
        if not self.pyttsx3_engine:
            return False
        
        try:
            # Ajuster les paramètres selon le système d'exploitation
            system = platform.system().lower()
            
            if system == "windows":
                # Windows SAPI offre plus d'options
                # Essayer d'utiliser les voix Microsoft Speech Platform si disponibles
                voices = self.pyttsx3_engine.getProperty('voices')
                for voice in voices:
                    # Préférer les voix "Desktop" ou "Mobile" (plus naturelles)
                    if 'desktop' in voice.id.lower() or 'mobile' in voice.id.lower():
                        self.pyttsx3_engine.setProperty('voice', voice.id)
                        break
                
                # Configuration Windows optimale
                self.pyttsx3_engine.setProperty('rate', 170)
                self.pyttsx3_engine.setProperty('volume', 0.9)
                
            elif system == "darwin":  # macOS
                # macOS a d'excellentes voix système
                voices = self.pyttsx3_engine.getProperty('voices')
                premium_voices = ['alex', 'samantha', 'victoria', 'thomas']
                
                for voice in voices:
                    voice_name = voice.name.lower() if voice.name else ""
                    if any(pv in voice_name for pv in premium_voices):
                        self.pyttsx3_engine.setProperty('voice', voice.id)
                        break
                
                # Configuration macOS optimale
                self.pyttsx3_engine.setProperty('rate', 160)
                self.pyttsx3_engine.setProperty('volume', 0.8)
                
            elif system == "linux":
                # Linux avec espeak-ng ou festival
                # Configuration plus conservatrice
                self.pyttsx3_engine.setProperty('rate', 155)
                self.pyttsx3_engine.setProperty('volume', 0.85)
            
            return True
            
        except Exception as e:
            print(f"Erreur lors de la configuration avancée: {str(e)}")
            return False

    def list_available_voices(self):
        """Liste toutes les voix disponibles pour débogage."""
        if self.pyttsx3_engine:
            voices = self.pyttsx3_engine.getProperty('voices')
            print("\n=== Voix disponibles ===")
            for i, voice in enumerate(voices):
                print(f"{i}: {voice.name} - {voice.id}")
                print(f"   Languages: {getattr(voice, 'languages', 'N/A')}")
            print("========================\n")
    
    def set_voice_by_name(self, voice_name: str) -> bool:
        """Définit la voix par son nom."""
        if not self.pyttsx3_engine:
            return False
            
        voices = self.pyttsx3_engine.getProperty('voices')
        for voice in voices:
            if voice.name and voice_name.lower() in voice.name.lower():
                self.pyttsx3_engine.setProperty('voice', voice.id)
                print(f"Voix changée pour: {voice.name}")
                return True
        
        print(f"Voix '{voice_name}' non trouvée")
        return False
    
    def _get_tts_command(self) -> Optional[str]:
        """Détermine la commande TTS à utiliser selon la plateforme."""
        # On privilégie pyttsx3, donc cette méthode devient optionnelle
        if self.platform == "darwin":
            return "say"
        elif self.platform == "linux":
            if self._is_command_available("espeak"):
                return "espeak"
            elif self._is_command_available("festival"):
                return "echo %s | festival --tts"
        elif self.platform == "windows":
            return "powershell -Command \"Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('%s')\""
        
        return None
    
    def _is_command_available(self, command: str) -> bool:
        """Vérifie si une commande est disponible sur le système."""
        try:
            result = subprocess.run(
                ["which", command], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                check=False
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def initialize(self) -> bool:
        """Initialise le service de synthèse vocale."""
        self.initialized = self.pyttsx3_engine is not None
        logger.info(f"TTS initialisé: {self.initialized} (utilisant pyttsx3)")
        
        if self.initialized:
            self.list_available_voices()  # Afficher les voix pour débogage
        
        return self.initialized
    
    def speak(self, text: str) -> bool:
        """Convertit le texte en parole et le lit à haute voix."""
        if not self.initialized:
            logger.error("Le service TTS n'est pas initialisé")
            print(f"TTS: {text}")  # Fallback textuel
            return False
        
        try:
            logger.info(f"Vocalisation: '{text[:50]}{'...' if len(text) > 50 else ''}'")
            
            if self.use_pyttsx3 and self.pyttsx3_engine:
                # Utiliser pyttsx3
                self.pyttsx3_engine.say(text)
                self.pyttsx3_engine.runAndWait()
                logger.info("Vocalisation pyttsx3 terminée")
                return True
            
            elif self.platform == "darwin" and self.tts_command == "say":
                # Utiliser la commande say native
                result = subprocess.run(
                    ["say", text], 
                    check=True,
                    timeout=30
                )
                logger.info("Vocalisation 'say' terminée")
                return True
            
            else:
                # Autres plateformes
                if '%s' in self.tts_command:
                    command = self.tts_command % text
                    subprocess.run(command, shell=True, check=True, timeout=30)
                else:
                    subprocess.run([self.tts_command, text], check=True, timeout=30)
                return True
                
        except subprocess.TimeoutExpired:
            print("Timeout lors de la vocalisation")
            return False
        except Exception as e:
            logger.error(f"Erreur lors de la vocalisation: {str(e)}")
            print(f"TTS (erreur): {text}")  # Fallback textuel
            return False
        
    def is_available(self) -> bool:
        """Vérifie si le service de synthèse vocale est disponible."""
        return self.initialized
    
    def shutdown(self) -> bool:
        """Arrête proprement le service de synthèse vocale."""
        if self.pyttsx3_engine:
            try:
                self.pyttsx3_engine.stop()
            except:
                pass
        self.initialized = False
        return True