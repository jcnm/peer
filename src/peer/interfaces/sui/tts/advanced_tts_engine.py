import os
import tempfile
import logging
import subprocess
import shutil
import sys
from .base import BaseTTS, TTSResult, TTSConfig, TTSEngineType

logger = logging.getLogger(__name__)

class AdvancedTTS(BaseTTS):
    """TTS engine using advanced, model-based synthesis (e.g., Piper) and pyttsx3 as a fallback."""
    
    def __init__(self, config: TTSConfig):
        super().__init__(config)
        self.temp_files = []
        self.piper_path = None
        self.piper_model_path = None
        self.pyttsx3_available = False
        self.audio_players = []
        self._initialize_engines()
        self._initialize_audio_players()

    def _initialize_engines(self):
        """Initializes Piper and pyttsx3 TTS engines if available."""
        # Initialize Piper
        # Check for configured executable path first, then fall back to PATH
        configured_piper_path = self.config.engine_specific_params.get("executable_path")
        if configured_piper_path and os.path.isfile(configured_piper_path) and os.access(configured_piper_path, os.X_OK):
            self.piper_path = configured_piper_path
            logger.info(f"✅ Using configured Piper executable at: {self.piper_path}")
        else:
            self.piper_path = shutil.which("piper")
            if self.piper_path:
                logger.info(f"✅ Piper command-line tool found in PATH at: {self.piper_path}")
            else:
                logger.info("ℹ️ Piper command-line tool not found in PATH or configured path.")
        
        if self.piper_path:
            model_path_config = self.config.engine_specific_params.get("piper_model_path")
            if not model_path_config:
                logger.warning("⚠️ Piper is available, but 'piper_model_path' not specified in engine_specific_params.")
                self.piper_path = None  # Mark as unavailable for synthesis
            elif not os.path.exists(model_path_config):
                logger.warning(f"⚠️ Piper model path '{model_path_config}' does not exist.")
                self.piper_path = None  # Mark as unavailable for synthesis
            elif os.path.exists(model_path_config + ".json"):
                # Model path points to .onnx, .json exists, likely OK
                self.piper_model_path = model_path_config
                logger.info(f"✅ Using Piper model at: {self.piper_model_path}")
            elif model_path_config.endswith(".json") and os.path.exists(model_path_config):
                # Model path points to .json file
                self.piper_model_path = model_path_config[:-5]  # Remove .json suffix for onnx path
                if os.path.exists(self.piper_model_path):
                    logger.info(f"✅ Using Piper model at: {self.piper_model_path}")
                else:
                    logger.warning(f"⚠️ Piper .onnx model file not found at: {self.piper_model_path}")
                    self.piper_path = None
            else:
                logger.warning(f"⚠️ Piper model structure not recognized at: {model_path_config}")
                self.piper_path = None

        # Initialize pyttsx3 as fallback
        try:
            import pyttsx3
            # Test if pyttsx3 works by creating an engine
            engine = pyttsx3.init()
            if engine:
                self.pyttsx3_available = True
                engine.stop()  # Clean up test engine
                logger.info("✅ pyttsx3 TTS engine available as fallback")
            else:
                logger.warning("⚠️ pyttsx3 import successful but engine initialization failed")
        except Exception as e:
            logger.warning(f"⚠️ pyttsx3 TTS engine not available: {e}")

    def _initialize_audio_players(self):
        """Initialize available audio playback systems."""
        self.audio_players = []
        
        # Test system commands for audio playback
        if sys.platform == "darwin":  # macOS
            try:
                subprocess.run(["which", "afplay"], check=True, capture_output=True)
                self.audio_players.append("afplay")
                logger.info("✅ afplay available (macOS)")
            except subprocess.CalledProcessError:
                pass
        elif sys.platform == "linux":  # Linux
            for player in ["aplay", "paplay", "play"]:
                try:
                    subprocess.run(["which", player], check=True, capture_output=True)
                    self.audio_players.append(player)
                    logger.info(f"✅ {player} available (Linux)")
                    break
                except subprocess.CalledProcessError:
                    continue
        
        # Test Python libraries for audio playback
        try:
            import sounddevice as sd
            import soundfile as sf
            self.audio_players.append("python_sounddevice")
            logger.info("✅ sounddevice + soundfile available")
        except ImportError:
            pass
        
        try:
            import pygame
            self.audio_players.append("pygame")
            logger.info("✅ pygame available")
        except ImportError:
            pass
        
        if not self.audio_players:
            logger.warning("⚠️ No audio playback system detected")
        else:
            logger.info(f"🔊 Available audio systems: {', '.join(self.audio_players)}")

    def _play_audio_file(self, audio_file_path: str) -> bool:
        """Play an audio file with the best available system."""
        if not self.audio_players:
            logger.error("❌ No audio playback system available")
            return False
        
        # Try different playback systems in order of preference
        for player in self.audio_players:
            try:
                if player == "afplay":  # macOS
                    subprocess.run(["afplay", audio_file_path], check=True, timeout=30)
                    logger.debug(f"🔊 Audio played with afplay: {audio_file_path}")
                    return True
                    
                elif player in ["aplay", "paplay", "play"]:  # Linux
                    subprocess.run([player, audio_file_path], check=True, timeout=30)
                    logger.debug(f"🔊 Audio played with {player}: {audio_file_path}")
                    return True
                    
                elif player == "python_sounddevice":
                    import sounddevice as sd
                    import soundfile as sf
                    data, samplerate = sf.read(audio_file_path)
                    sd.play(data, samplerate)
                    sd.wait()  # Wait for playback to finish
                    logger.debug(f"🔊 Audio played with sounddevice: {audio_file_path}")
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
                    logger.debug(f"🔊 Audio played with pygame: {audio_file_path}")
                    return True
                    
            except Exception as e:
                logger.debug(f"Failed to play with {player}: {e}")
                continue
                
        logger.error(f"❌ Failed to play audio file with any available system: {audio_file_path}")
        return False

    def synthesize(self, text: str) -> TTSResult:
        """
        Synthesizes speech from text using Piper (primary) or pyttsx3 (fallback).
        Automatically plays the generated audio if playback systems are available.
        """
        if not text.strip():
            return TTSResult(success=False, error_message="Empty text provided")

        # Try Piper first
        if self.piper_path and self.piper_model_path:
            result = self._synthesize_with_piper(text)
            if result.success:
                # Automatically play the generated audio
                if result.audio_path and os.path.exists(result.audio_path):
                    logger.info(f"🔊 Playing generated audio: {result.audio_path}")
                    self._play_audio_file(result.audio_path)
                return result

        # Fallback to pyttsx3
        if self.pyttsx3_available:
            result = self._synthesize_with_pyttsx3(text)
            if result.success:
                # Automatically play the generated audio
                if result.audio_path and os.path.exists(result.audio_path):
                    logger.info(f"🔊 Playing generated audio: {result.audio_path}")
                    self._play_audio_file(result.audio_path)
                return result

        return TTSResult(success=False, error_message="No TTS engines available")

    def _synthesize_with_piper(self, text: str) -> TTSResult:
        """Synthesizes speech using Piper TTS."""
        try:
            # Create temporary file for output
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                output_path = temp_file.name
                self.temp_files.append(output_path)

            # Prepare Piper command
            cmd = [
                self.piper_path,
                "--model", self.piper_model_path,
                "--output_file", output_path
            ]

            # Add speaker if specified
            speaker_id = self.config.engine_specific_params.get("speaker_id")
            if speaker_id is not None:
                cmd.extend(["--speaker", str(speaker_id)])

            # Run Piper with text as input
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(input=text)
            
            if process.returncode == 0 and os.path.exists(output_path):
                logger.info(f"✅ Piper synthesis successful: {output_path}")
                return TTSResult(
                    success=True,
                    audio_path=output_path,
                    engine_used="piper"
                )
            else:
                error_msg = f"Piper failed (exit code {process.returncode}): {stderr}"
                logger.error(error_msg)
                if os.path.exists(output_path):
                    os.unlink(output_path)
                    if output_path in self.temp_files:
                        self.temp_files.remove(output_path)
                return TTSResult(success=False, error_message=error_msg)

        except Exception as e:
            error_msg = f"Piper synthesis error: {str(e)}"
            logger.error(error_msg)
            return TTSResult(success=False, error_message=error_msg)

    def _synthesize_with_pyttsx3(self, text: str) -> TTSResult:
        """Synthesizes speech using pyttsx3 and saves to file."""
        try:
            import pyttsx3
            import threading
            import time
            
            # Create temporary file for output
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                output_path = temp_file.name
                self.temp_files.append(output_path)

            # Handle macOS threading issues with pyttsx3
            synthesis_result = {"success": False, "error": None}
            
            def synthesis_worker():
                try:
                    # Initialize pyttsx3 engine in separate thread to avoid run loop conflicts
                    engine = pyttsx3.init()
                    
                    # Configure voice settings
                    if self.config.voice:
                        voices = engine.getProperty('voices')
                        for voice in voices:
                            if self.config.voice.lower() in voice.name.lower():
                                engine.setProperty('voice', voice.id)
                                break

                    # Configure speech rate and volume
                    if hasattr(self.config, 'pyttsx3_rate'):
                        engine.setProperty('rate', self.config.pyttsx3_rate)
                    if hasattr(self.config, 'pyttsx3_volume'):
                        engine.setProperty('volume', self.config.pyttsx3_volume)
                    
                    # Save to file
                    engine.save_to_file(text, output_path)
                    engine.runAndWait()
                    engine.stop()
                    
                    synthesis_result["success"] = True
                    
                except Exception as e:
                    synthesis_result["error"] = str(e)
            
            # Run synthesis in separate thread to avoid macOS run loop issues
            thread = threading.Thread(target=synthesis_worker)
            thread.daemon = True
            thread.start()
            thread.join(timeout=10)  # 10 second timeout
            
            if thread.is_alive():
                synthesis_result["error"] = "pyttsx3 synthesis timed out"
            
            if synthesis_result["success"] and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"✅ pyttsx3 synthesis successful: {output_path}")
                return TTSResult(
                    success=True,
                    audio_path=output_path,
                    engine_used="pyttsx3"
                )
            else:
                error_msg = synthesis_result.get("error", "pyttsx3 failed to generate audio file")
                logger.error(error_msg)
                # Clean up failed file
                if os.path.exists(output_path):
                    os.unlink(output_path)
                    if output_path in self.temp_files:
                        self.temp_files.remove(output_path)
                return TTSResult(success=False, error_message=error_msg)

        except Exception as e:
            error_msg = f"pyttsx3 synthesis error: {str(e)}"
            logger.error(error_msg)
            return TTSResult(success=False, error_message=error_msg)

    def is_available(self) -> bool:
        """Check if any TTS engine is available."""
        return (self.piper_path and self.piper_model_path) or self.pyttsx3_available

    def _create_temp_file(self, suffix: str = ".wav") -> str:
        """Create a temporary file and track it for cleanup."""
        temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        temp_path = temp_file.name
        temp_file.close()
        self.temp_files.append(temp_path)
        return temp_path

    def cleanup(self):
        """Clean up temporary files."""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                    logger.debug(f"Cleaned up temporary file: {temp_file}")
            except Exception as e:
                logger.warning(f"Failed to clean up {temp_file}: {e}")
        self.temp_files.clear()

    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()