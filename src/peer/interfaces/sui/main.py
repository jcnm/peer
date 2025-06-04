"""
Main module for the Speech User Interface (SUI).

This module implements the omniscient voice interface with advanced AI capabilities,
using hexagonal architecture and Domain-Driven Design (DDD) principles.
"""

import os
import sys
import time
import threading
import queue
import logging
import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Fix OMP warning: "Forking a process while a parallel region is active is potentially unsafe."
os.environ["OMP_NUM_THREADS"] = "1"

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.expanduser('~/.peer/sui.log'), mode='a')
    ]
)

# Import Peer modules
from peer.core import PeerDaemon, CoreRequest, CoreResponse, CommandType, ResponseType, InterfaceType
from peer.core.protocol import CoreProtocol

# Import SUI modules
from peer.interfaces.sui.config.config_loader import load_yaml_config, get_config_with_defaults
from peer.interfaces.sui.domain.models import SpeechRecognitionResult, VoiceActivityMetrics, ContextualInfo, SUIResponse, InterfaceAction
from peer.interfaces.sui.adapters.interface_adapter import SUIInterfaceAdapter
from peer.interfaces.sui.nlu.domain.nlp_engine import NLPEngine
from peer.interfaces.sui.stt.speech_recognizer import SpeechRecognizer
from peer.interfaces.sui.stt.audio_io import AudioCapture
from peer.interfaces.sui.tts.text_to_speech import TextToSpeech
from peer.interfaces.sui.voice_state_machine import VoiceStateMachine, VoiceInterfaceState


class SpeechUserInterface:
    """Voice user interface with AI."""
    
    def __init__(self):
        """Initialize the SUI voice interface."""
        self.logger = logging.getLogger("SUI")
        self.logger.info("🎤 Initializing SUI voice interface...")
        
        # Load configuration
        self.config = self._load_configuration()
        
        # Initialize adapters
        self.interface_adapter = SUIInterfaceAdapter()
        
        # Initialize TTS engine
        self.tts_engine = self._init_tts_engine()
        
        # Initialize audio I/O system
        self.audio_capture = self._init_audio_capture()
        
        # Initialize NLP engine
        self.nlp_engine = self._init_nlp_engine()
        
        # Initialize speech recognizer
        self.speech_recognizer = self._init_speech_recognizer(self.config.get('stt_engine_settings', {}))
        
        # Initialize context
        self.context = self._init_context()
        
        # Connect to Peer daemon
        self.peer_daemon = PeerDaemon()
        
        # Initialize voice state machine
        self.voice_state_machine = self._init_voice_state_machine()
        
        # Interface state
        self.is_running = False
        self.is_listening = False
        
        self.logger.info("✅ SUI voice interface initialized successfully")
    
    def _load_configuration(self) -> Dict[str, Any]:
        """Load SUI configuration from YAML files."""
        # Default SUI configuration
        default_config = {
            'global_settings': {
                'default_stt_engine': 'whisperx', # Default if models.yaml is missing
                'default_tts_engine': 'xtts_v2',  # Default if models.yaml is missing
                'models_base_dir': os.path.expanduser('~/.peer/models'),
                'vosk_model_path': os.path.expanduser('~/.peer/models/stt/vosk/vosk-model-small-fr-0.22'), # Example default
                'piper_voices_path': os.path.expanduser('~/.peer/models/tts/piper_voices'), # Example default
            },
            'stt_engines': {
                'whisperx': {
                    'enabled': False, # Fallback: disabled if models.yaml is missing
                    'notes': "WhisperX STT Engine - requires ffmpeg",
                    'settings': {
                        'model': "base",
                        'device': "cpu",
                        'language': "fr",
                        'compute_type': "int8",
                        'batch_size': 16,
                        'threads': 4,
                        'hf_token': None,
                        'diarize': False,
                        'min_speakers': None,
                        'max_speakers': None
                    },
                    'user_data_dir': os.path.expanduser('~/.cache/whisperx')
                }
                # Add other minimal STT engine defaults if necessary, e.g., a mock engine
            },
            'tts_engines': {
                'xtts_v2': {
                    'enabled': False, # Fallback: disabled if models.yaml is missing
                    'notes': "Coqui XTTS_v2 Engine",
                    'settings': {
                        'model_name': "tts_models/multilingual/multi-dataset/xtts_v2",
                        'language': "fr",
                        'speaker_wav': None, # Or a default path
                        'device': "cpu"
                    },
                    'user_data_dir': os.path.expanduser('~/.local/share/tts/tts_models--multilingual--multi-dataset--xtts_v2')
                }
                # Add other minimal TTS engine defaults if necessary
            },
            'audio': { # Preserved from original default_config
                'sample_rate': 16000,
                'channels': 1,
                'chunk_size': 1024
            },
            'nlp': { # Preserved from original default_config
                'confidence_threshold': 0.7,
                'models': {
                    'spacy': 'fr_core_news_sm',
                    'sentence_transformer': 'sentence-transformers/all-MiniLM-L6-v2'
                }
            }
        }
        
        try:
            # Configuration file path - CHANGED
            config_path = os.path.expanduser("~/.peer/config/sui/models.yaml")
            
            # Load config with defaults
            config = get_config_with_defaults(config_path, default_config)
            self.logger.info(f"✅ Configuration loaded from {config_path}")
            return config
            
        except Exception as e:
            self.logger.error(f"❌ Error loading configuration: {e}")
            self.logger.info("Using default configuration")
            return default_config
    
    def _init_tts_engine(self) -> Optional[TextToSpeech]:
        """Initialize the Text-to-Speech engine."""
        try:
            from peer.interfaces.sui.config.config_loader import create_tts_config_from_sui_config
            
            # Use the proper config loader to create TTS config
            tts_config = create_tts_config_from_sui_config(self.config, "test")
            
            self.logger.info(f"Creating TTS engine with config: {tts_config.engine_type.value}, language: {tts_config.language}, voice: {tts_config.voice}")
            
            # Initialize TTS engine with proper config object
            tts_engine = TextToSpeech(tts_config)
            
            if tts_engine.is_engine_available():
                self.logger.info(f"✅ TTS engine initialized successfully using {tts_config.engine_type.value}")
                # Test to see if TTS is working
                test_result = tts_engine.synthesize("Test de synthèse vocale")
                if test_result.success:
                    self.logger.info(f"✅ TTS test successful: engine={test_result.engine_used}")
                else:
                    self.logger.warning(f"⚠️ TTS test failed: {test_result.error_message}")
            else:
                self.logger.warning(f"⚠️ TTS engine initialized but reported as unavailable")
                
            return tts_engine
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize TTS engine: {e}", exc_info=True)
            return None
    
    def _init_audio_capture(self) -> Optional[AudioCapture]:
        """Initialize the audio capture system."""
        try:
            audio_config = self.config.get('audio_handler_settings', self.config.get('audio', {}))
            audio_capture = AudioCapture(audio_config)
            self.logger.info("✅ Audio capture initialized successfully")
            return audio_capture
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize audio capture: {e}")
            return None
    
    def _init_nlp_engine(self) -> Optional[NLPEngine]:
        """Initialize the NLP engine."""
        try:
            nlp_config = self.config.get('nlp_engine_settings', self.config.get('nlp', {}))
            nlp_engine = NLPEngine(nlp_config)
            self.logger.info("✅ NLP engine initialized successfully")
            return nlp_engine
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize NLP engine: {e}")
            return None
    
    def _init_speech_recognizer(self, stt_config: Dict[str, Any]) -> Optional[SpeechRecognizer]:
        """Initialise le moteur de reconnaissance vocale."""
        # Check if STT is explicitly disabled, otherwise assume it's enabled if stt_engine_settings exists
        if stt_config.get("enabled", True) is False:
            self.logger.info("🎙️ STT disabled by configuration.")
            return None

        # The SpeechRecognizer class itself now handles the internal selection and fallback of engines
        # based on the 'stt_engine_settings' part of the global SUI configuration.
        # We pass the entire SUI config to it, as it parses 'stt_engine_settings' internally.
        try:
            self.logger.info(f"🎙️ Initializing SpeechRecognizer with main config...")
            # SpeechRecognizer expects the global SUI configuration dictionary
            recognizer = SpeechRecognizer(config=self.config)
            
            # Log available and primary engines from the recognizer
            engine_info = recognizer.get_engine_info()
            self.logger.info(f"SpeechRecognizer initialized. Available: {engine_info['available_engines']}, Primary: {engine_info['primary_engine']}")
            
            # Check if the primary engine (or any engine) is available
            if not engine_info['primary_engine'] and not engine_info['available_engines']:
                self.logger.error("❌ No STT engines could be initialized by SpeechRecognizer.")
                return None
            
            self.logger.info(f"✅ Speech Recognizer initialized successfully. Primary engine: {engine_info['primary_engine'] or 'None'}")
            return recognizer
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize SpeechRecognizer: {e}", exc_info=True)
            return None

    def _init_fallback_recognizer(self) -> Optional[SpeechRecognizer]:
        """Initialise un reconnaisseur de secours (mock)."""
        self.logger.info("↪️ Initializing fallback STT recognizer (mock)...")
        try:
            # Create a minimal config for the mock recognizer
            # SpeechRecognizer expects the global SUI config, so we provide a minimal one
            # that enables only the mock engine.
            mock_sui_config = {
                "stt_settings": {
                    "enabled": True,
                    "engines": {
                        "mock": {"enabled": True, "priority": 1},
                        "whisper": {"enabled": False}, # Ensure others are disabled
                        "vosk": {"enabled": False},
                        "wav2vec2": {"enabled": False}
                    }
                }
                # Add other minimal required config keys if SpeechRecognizer depends on them
            }
            fallback_recognizer = SpeechRecognizer(mock_sui_config)
            engine_info = fallback_recognizer.get_engine_info()

            if not engine_info['available_engines'] or engine_info['primary_engine'] != 'mock':
                 self.logger.error("❌ Failed to initialize mock STT engine for fallback.")
                 return None
            
            self.logger.info("✅ Fallback STT recognizer (mock) initialized.")
            return fallback_recognizer
        except Exception as e:
            self.logger.error(f"❌ Failed to create fallback STT recognizer: {e}", exc_info=True)
            return None
    
    def _init_context(self) -> ContextualInfo:
        """Initialize the interface context."""
        return ContextualInfo(
            current_time=datetime.datetime.now(),
            session_duration=0.0,
            commands_count=0,
            working_directory=os.getcwd()
        )

    def _init_voice_state_machine(self) -> Optional[VoiceStateMachine]:
        """Initialize the voice state machine."""
        try:
            if not all([self.audio_capture, self.speech_recognizer, self.nlp_engine, self.tts_engine]):
                self.logger.warning("⚠️ Some components missing for voice state machine initialization")
                return None
            
            # Create voice state machine
            voice_state_machine = VoiceStateMachine(
                audio_capture=self.audio_capture,
                speech_recognizer=self.speech_recognizer,
                nlp_engine=self.nlp_engine,
                tts_engine=self.tts_engine,
                peer_daemon=self.peer_daemon
            )
            
            # Set the command handler after initialization
            voice_state_machine.command_handler = self._handle_voice_command
            
            self.logger.info("✅ Voice state machine initialized successfully")
            return voice_state_machine
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize voice state machine: {e}", exc_info=True)
            return None

    def _normalize_speech_input(self, speech_input: str) -> str:
        """Normalise l'entrée vocale."""
        # Simple conversion en minuscules et suppression des espaces excessifs
        return speech_input.lower().strip()

    def _handle_voice_command(self, intent_result, recognition_text: str) -> Optional[str]:
        """
        Handle voice command processing for the state machine.
        
        Args:
            intent_result: NLP intent extraction result
            recognition_text: Original recognized text
            
        Returns:
            Response message for TTS, or None if no response needed
        """
        try:
            self.logger.info(f"🧠 Processing intent: {intent_result.command_type} (confidence: {intent_result.confidence:.2f})")
            
            # Announce what we're about to do
            action_announcement = self._generate_action_announcement(intent_result, recognition_text)
            if action_announcement:
                self.logger.info(f"🔊 Announcing action: {action_announcement}")
                # Use direct TTS for immediate feedback
                try:
                    import platform
                    if platform.system() == 'Darwin':  # macOS
                        import subprocess
                        subprocess.run(['say', '-v', 'Audrey', action_announcement], check=False)
                except Exception as e:
                    self.logger.warning(f"Direct TTS failed: {e}")
            
            # Command type mapping from NLP engine strings to CommandType enum
            command_type_mapping = {
                "help": CommandType.HELP,
                "quit": CommandType.QUIT,
                "status": CommandType.STATUS,
                "time": CommandType.TIME,
                "date": CommandType.DATE,
                "version": CommandType.VERSION,
                "capabilities": CommandType.CAPABILITIES,
                "echo": CommandType.ECHO,
                # Map unsupported commands to working alternatives
                "analyze": CommandType.STATUS,
                "analysis": CommandType.STATUS,
                "file_operation": CommandType.CAPABILITIES,
                "suggest": CommandType.HELP,
                "explain": CommandType.HELP,
                "prompt": CommandType.HELP,
                "unknown": CommandType.HELP
            }
            
            # Map command type
            command_type = command_type_mapping.get(intent_result.command_type, CommandType.HELP)
            self.logger.info(f"🎯 Mapped command type: {command_type}")
            
            # Execute command through daemon
            response = self._execute_command(command_type, intent_result, recognition_text)
            
            # Update context
            self._update_context(intent_result)
            
            # Generate detailed result announcement
            result_message = self._generate_result_announcement(response, command_type, recognition_text)
            
            # Return response message for TTS
            if response:
                if response.type == ResponseType.QUIT:
                    self.is_running = False
                    return result_message or "Au revoir !"
                elif response.type == ResponseType.ERROR:
                    return result_message or f"Erreur : {response.message}"
                else:
                    return result_message or "Commande exécutée avec succès"
            
            return result_message or "Commande traitée"
            
        except Exception as e:
            self.logger.error(f"❌ Error handling voice command: {e}")
            return f"Erreur lors du traitement de la commande : {str(e)}"
    
    def _generate_action_announcement(self, intent_result, recognition_text: str) -> str:
        """Generate an announcement of what action is about to be performed."""
        command_type = intent_result.command_type.lower()
        
        announcements = {
            "help": "Je vais vous donner les informations d'aide disponibles.",
            "status": "Je vérifie le statut du système pour vous.",
            "time": "Je regarde l'heure actuelle.",
            "date": "Je consulte la date d'aujourd'hui.",
            "version": "Je vérifie la version du système.",
            "capabilities": "Je vais vous expliquer mes capacités.",
            "echo": f"Je vais répéter ce que vous avez dit : {recognition_text}",
            "quit": "Je vais arrêter le système comme demandé.",
            "analyze": "Je vais analyser les informations disponibles.",
            "analysis": "Je commence l'analyse des données.",
        }
        
        return announcements.get(command_type, f"Je traite votre demande : {recognition_text}")
    
    def _generate_result_announcement(self, response, command_type, original_text: str) -> str:
        """Generate a detailed announcement of what was accomplished."""
        if not response:
            return "La commande a été traitée mais aucun résultat n'est disponible."
        
        base_message = response.message or ""
        
        # Add context-specific completion messages
        completion_messages = {
            CommandType.HELP: "Voici les informations d'aide demandées.",
            CommandType.STATUS: "Le statut du système a été vérifié avec succès.",
            CommandType.TIME: "Voici l'heure actuelle.",
            CommandType.DATE: "Voici la date d'aujourd'hui.",
            CommandType.VERSION: "Voici les informations de version.",
            CommandType.CAPABILITIES: "Voici un résumé de mes capacités.",
            CommandType.ECHO: "J'ai répété votre message comme demandé.",
            CommandType.QUIT: "Le système va s'arrêter maintenant. Au revoir !",
        }
        
        prefix = completion_messages.get(command_type, "Voici le résultat de votre demande :")
        
        if response.type == ResponseType.SUCCESS:
            if base_message:
                return f"{prefix} {base_message}"
            else:
                return f"{prefix} La commande a été exécutée avec succès."
        elif response.type == ResponseType.ERROR:
            return f"Désolé, une erreur s'est produite : {base_message}"
        elif response.type == ResponseType.PROGRESS:
            return f"En cours de traitement : {base_message}"
        else:
            return f"{prefix} {base_message}" if base_message else prefix

    def start_voice_processing(self):
        """Start the voice processing pipeline using the state machine."""
        if not self.voice_state_machine:
            self.logger.error("❌ Cannot start voice processing: voice state machine not initialized")
            return
        
        self.is_running = True
        self.logger.info("🎤 Starting intelligent voice processing pipeline...")
        
        try:
            # Start the voice state machine
            self.voice_state_machine.start()
            
            # Keep the main thread alive while the voice interface is running
            while self.is_running:
                try:
                    time.sleep(0.5)
                    
                    # Check if state machine is still running
                    if not self.voice_state_machine.is_running:
                        self.logger.info("🛑 Voice state machine stopped, shutting down")
                        break
                        
                except KeyboardInterrupt:
                    self.logger.info("⏹️ Voice processing interrupted by user")
                    break
                    
        except Exception as e:
            self.logger.error(f"❌ Error in voice processing: {e}")
        finally:
            self.stop()
    
    def _execute_command(self, command_type: CommandType, intent_result, original_text: str) -> Optional[CoreResponse]:
        """Execute a command through the Peer daemon."""
        try:
            # Create request
            request = CoreProtocol.create_request(
                command=command_type,
                interface_type=InterfaceType.SUI,
                parameters=intent_result.parameters,
                context={"original_text": original_text}
            )
            
            self.logger.info(f"📤 Sending command to daemon: {command_type}")
            
            # Execute through daemon
            response = self.peer_daemon.execute_command(request)
            
            if response and response.type == ResponseType.SUCCESS:
                self.logger.info(f"✅ Command executed successfully: {response.message}")
            else:
                error_msg = response.message if response else "No response from daemon"
                self.logger.warning(f"⚠️ Command execution failed: {error_msg}")
            
            return response
            
        except Exception as e:
            self.logger.error(f"❌ Error executing command: {e}")
            return None
    
    def _provide_voice_feedback(self, response: CoreResponse):
        """Provide voice feedback for the command response."""
        try:
            if not self.tts_engine:
                self.logger.warning("⚠️ Cannot provide voice feedback: TTS engine not available")
                return
            
            # Handle different response types
            if response.type == ResponseType.QUIT:
                # Special handling for quit command
                if response.message:
                    result = self.tts_engine.synthesize(response.message)
                    self._log_tts_result(result, response.message)
                    # Give it a moment to complete playback before quitting
                    time.sleep(1.0)
                # Signal that we should quit
                self.is_running = False
                return
            elif response.type == ResponseType.SUCCESS:
                # Success responses get voice feedback
                feedback = response.message or "Command executed successfully"
            elif response.type == ResponseType.ERROR:
                # Error responses get voice feedback with error indication
                feedback = f"Error: {response.message}"
            elif response.type == ResponseType.PROGRESS:
                # Progress updates get brief voice feedback
                feedback = response.message or "Processing..."
            else:
                # Other response types get generic feedback
                feedback = response.message or "Command processed"
            
            self.logger.info(f"🔊 Providing voice feedback: {feedback}")
            
            # Direct vocalization using system TTS ('say' command on macOS)
            # This is a backup in case the regular TTS engine isn't working
            try:
                import platform
                if platform.system() == 'Darwin':  # macOS
                    import subprocess
                    self.logger.info("Using direct 'say' command as backup TTS")
                    subprocess.run(['say', feedback], check=False)
            except Exception as e:
                self.logger.warning(f"Backup TTS failed: {e}")
                
            # Use regular TTS engine
            result = self.tts_engine.synthesize(feedback)
            self._log_tts_result(result, feedback)
            
        except Exception as e:
            self.logger.error(f"❌ Error providing voice feedback: {e}", exc_info=True)
            
    def _log_tts_result(self, result, text):
        """Log the result of a TTS synthesis operation."""
        if result.success:
            self.logger.info(f"✅ Voice feedback synthesized successfully for: '{text[:30]}...'")
            self.logger.debug(f"TTS engine used: {result.engine_used}, Audio file: {result.audio_file_path}")
        else:
            self.logger.warning(f"⚠️ Voice feedback synthesis failed: {result.error_message}")
            self.logger.debug(f"Failed text: '{text}'")
    
    def _update_context(self, intent_result):
        """Update the interface context."""
        try:
            self.context.commands_count += 1
            self.context.current_time = datetime.datetime.now()
            # Could add more context updates here based on intent_result
        except Exception as e:
            self.logger.error(f"❌ Error updating context: {e}")
    
    def stop(self):
        """Stop the voice interface."""
        self.logger.info("⏹️ Stopping SUI voice interface...")
        self.is_running = False
        self.is_listening = False
        
        # Stop voice state machine
        if self.voice_state_machine:
            try:
                self.voice_state_machine.stop()
            except Exception as e:
                self.logger.error(f"❌ Error stopping voice state machine: {e}")
        
        # Cleanup resources
        if self.audio_capture:
            try:
                self.audio_capture.stop()
            except Exception as e:
                self.logger.error(f"❌ Error stopping audio capture: {e}")
        
        if self.tts_engine:
            try:
                self.tts_engine.cleanup_temp_files()
            except Exception as e:
                self.logger.error(f"❌ Error cleaning up TTS engine: {e}")
        
        self.logger.info("✅ SUI voice interface stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the voice interface."""
        status = {
            "is_running": self.is_running,
            "is_listening": self.is_listening,
            "components": {
                "audio_capture": self.audio_capture is not None,
                "speech_recognizer": self.speech_recognizer is not None,
                "nlp_engine": self.nlp_engine is not None,
                "tts_engine": self.tts_engine is not None,
                "voice_state_machine": self.voice_state_machine is not None
            },
            "context": {
                "commands_count": self.context.commands_count,
                "session_duration": self.context.session_duration,
                "working_directory": self.context.working_directory
            } if self.context else {}
        }
        
        # Add voice state machine status if available
        if self.voice_state_machine:
            status["voice_state_machine"] = {
                "current_state": self.voice_state_machine.current_state.value,
                "is_running": self.voice_state_machine.is_running,
                "commands_processed": self.voice_state_machine.commands_processed,
                "audio_buffer_size": len(self.voice_state_machine.audio_buffer)
            }
        
        return status


def main():
    """Main entry point for the SUI voice interface."""
    try:
        # Create and start the voice interface
        sui = SpeechUserInterface()
        
        # Start voice processing
        sui.start_voice_processing()
        
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
