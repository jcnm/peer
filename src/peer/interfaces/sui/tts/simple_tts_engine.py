import os
import logging
import subprocess
import shutil

from .base import BaseTTS, TTSResult, TTSConfig, TTSEngineType

logger = logging.getLogger(__name__)

class SimpleTTS(BaseTTS):
    """TTS engine using system-based synthesis (say, espeak, pyttsx3) with direct vocalization only."""

    def __init__(self, config: TTSConfig):
        super().__init__(config)
        self._available_engines = self._discover_engines()

    def _discover_engines(self):
        """Discovers available system TTS engines."""
        engines = {
            "say": False,
            "espeak": False,
            "pyttsx3": False,
            "mock": True # Always available for testing
        }

        # Check for 'say' (macOS)
        if shutil.which("say"):
            engines["say"] = True
            logger.info("✅ System TTS 'say' command is available.")
        else:
            logger.info("ℹ️ System TTS 'say' command not found.")

        # Check for 'espeak'
        if shutil.which("espeak"):
            engines["espeak"] = True
            logger.info("✅ System TTS 'espeak' command is available.")
        else:
            logger.info("ℹ️ System TTS 'espeak' command not found.")
        
        # Check for 'pyttsx3'
        try:
            import pyttsx3
            # Try initializing to catch deeper errors
            try:
                engine = pyttsx3.init(debug=False)
                # Verify engine has necessary attributes
                if hasattr(engine, '_driver') and engine._driver:
                    driver_name = engine._driver.__class__.__name__
                    # In SimpleTTS, we only want pyttsx3 if it is NOT already handled by AdvancedTTS
                    # However, the logic here is for discovery. AdvancedTTS will make its own decision.
                    # We keep the original discovery logic for pyttsx3 here.
                    if driver_name == "NSSpeechDriver": # macOS
                        if not engines["say"]:
                            logger.info("✅ pyttsx3 (NSSpeechDriver) is available for SimpleTTS.")
                            engines["pyttsx3"] = True
                        else:
                            logger.info("ℹ️ pyttsx3 (NSSpeechDriver) found, but 'say' command is preferred on macOS for SimpleTTS.")
                    elif driver_name == "SAPI5Driver": # Windows
                        logger.info("✅ pyttsx3 (SAPI5Driver) is available for SimpleTTS.")
                        engines["pyttsx3"] = True
                    elif driver_name == "EspeakDriver": # Linux
                        # If espeak CLI is already available, prefer that over pyttsx3 with EspeakDriver for SimpleTTS
                        if not engines["espeak"]:
                            logger.info("✅ pyttsx3 (EspeakDriver) is available for SimpleTTS.")
                            engines["pyttsx3"] = True
                        else:
                            logger.info("ℹ️ pyttsx3 (EspeakDriver) found, but 'espeak' command is preferred for SimpleTTS.")
                    else: # Other or unknown driver
                        logger.info(f"✅ pyttsx3 ({driver_name}) is available for SimpleTTS.")
                        engines["pyttsx3"] = True
                else:
                    logger.warning("⚠️ pyttsx3 engine missing _driver attribute")
                    
                # Clean up properly
                try:
                    if hasattr(engine, 'stop'):
                        engine.stop()
                except:
                    pass
                    
            except Exception as e:
                logger.warning(f"⚠️ pyttsx3 found but failed to initialize for SimpleTTS: {e}")
        except ImportError:
            logger.info("ℹ️ pyttsx3 library not found for SimpleTTS.")
        except RuntimeError as e: # Catches "No system TTS speakers found" on some Linux
             logger.warning(f"⚠️ pyttsx3 runtime error during SimpleTTS initialization: {e}")

        logger.info(f"Discovered SimpleTTS engines: {engines}")
        return engines

    def synthesize(self, text: str) -> TTSResult:
        if not text:
            return TTSResult(success=False, error_message="Input text cannot be empty.", engine_used=self.__class__.__name__)

        preferred_engine_order = self.config.engine_specific_params.get("preferred_simple_engine_order", ["say", "pyttsx3", "espeak", "mock"])

        for engine_name in preferred_engine_order:
            if self._available_engines.get(engine_name):
                logger.info(f"Attempting synthesis with {engine_name}...")
                try:
                    if engine_name == "say":
                        result = self._synthesize_with_say(text)
                    elif engine_name == "pyttsx3":
                        result = self._synthesize_with_pyttsx3(text)
                    elif engine_name == "espeak":
                        result = self._synthesize_with_espeak(text)
                    elif engine_name == "mock":
                        result = self._synthesize_with_mock(text)
                    else:
                        continue # Should not happen

                    if result.success:
                        return result
                    else:
                        logger.warning(f"{engine_name} synthesis failed: {result.error_message}")
                except Exception as e:
                    logger.error(f"Unhandled exception during {engine_name} synthesis: {e}", exc_info=True)
        
        return TTSResult(success=False, error_message="All simple TTS engines failed or were unavailable.", engine_used=self.__class__.__name__)

    def _synthesize_with_say(self, text: str) -> TTSResult:
        try:
            # Always speak directly, no file recording
            cmd = ["say"]
            
            # Use engine-specific configuration if available
            say_config = self.config.engine_specific_params.get("engines", {}).get("say", {})
            
            # Priority: engine-specific voice > general config voice > French default
            voice = say_config.get("voice", self.config.voice)
            
            # Auto-select French voice if language is French and no voice specified
            if not voice and self.config.language and self.config.language.startswith("fr"):
                voice = "Audrey"  # Premium French voice by default
                logger.info(f"🇫🇷 Auto-selecting French voice: {voice}")
            
            if voice:
                cmd.extend(["-v", voice])
                logger.info(f"🔊 Using voice: {voice}")
            
            # Add rate parameter from engine-specific config or general config
            rate = say_config.get("rate") or self.config.engine_specific_params.get("rate")
            if rate:
                rate = int(rate)
                # 'say' rate is words per minute, generally 180-220 is normal for French
                # Optimize for French speech (slightly slower for better pronunciation)
                if voice and voice in ["Audrey", "Amelie", "Thomas", "Virginie"]:
                    rate = max(170, min(rate, 210))  # Optimal range for French voices
                cmd.extend(["-r", str(rate)])
                logger.info(f"🎯 Speech rate: {rate} WPM")
            
            cmd.append(text)
            
            logger.info(f"🎤 Executing 'say' command: {' '.join(cmd[:3])}... [text]")
            process = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if process.returncode != 0:
                logger.error(f"❌ 'say' command failed: {process.stderr}")
                return TTSResult(success=False, error_message=f"'say' command failed: {process.stderr}", engine_used="say")

            # Direct vocalization successful
            logger.info(f"✅ French TTS synthesis completed successfully with voice: {voice or 'system default'}")
            return TTSResult(success=True, engine_used="say")

        except Exception as e:
            logger.error(f"❌ Error during 'say' synthesis: {e}", exc_info=True)
            return TTSResult(success=False, error_message=str(e), engine_used="say")

    def _synthesize_with_espeak(self, text: str) -> TTSResult:
        try:
            # Use espeak to speak directly instead of saving to file
            cmd = ["espeak"]
            
            if self.config.language:
                # espeak uses language codes like "en", "fr", "es"
                lang_code = self.config.language.split('-')[0] 
                cmd.extend(["-v", lang_code])
            if self.config.voice: # espeak voices can be complex, e.g., "en+f3"
                cmd.extend(["-v", self.config.voice])
            
            # Add engine specific params like speed (rate), pitch, volume (amplitude)
            # espeak -s <words per minute>, -p <pitch adjustment 0-99>, -a <amplitude 0-200>
            if "rate" in self.config.engine_specific_params:
                 cmd.extend(["-s", str(self.config.engine_specific_params["rate"])])
            if "pitch" in self.config.engine_specific_params:
                 cmd.extend(["-p", str(self.config.engine_specific_params["pitch"])])
            if "amplitude" in self.config.engine_specific_params:
                 cmd.extend(["-a", str(self.config.engine_specific_params["amplitude"])])

            cmd.append(text)
            
            logger.info(f"Running 'espeak' command for direct vocalization: {' '.join(cmd)}")
            process = subprocess.run(cmd, capture_output=True, text=True, check=False)

            if process.returncode != 0:
                logger.error(f"'espeak' command failed: {process.stderr}")
                return TTSResult(success=False, error_message=f"'espeak' command failed: {process.stderr}", engine_used="espeak")

            logger.info(f"✅ Direct vocalization completed successfully with 'espeak'")
            return TTSResult(success=True, engine_used="espeak")

        except Exception as e:
            logger.error(f"Error during 'espeak' synthesis: {e}", exc_info=True)
            return TTSResult(success=False, error_message=str(e), engine_used="espeak")

    def _synthesize_with_pyttsx3(self, text: str) -> TTSResult:
        try:
            import pyttsx3

            logger.info("🔧 Initializing pyttsx3 engine for French TTS")
            engine = pyttsx3.init()
            
            # Debug: Log available voices
            voices = engine.getProperty('voices')
            voice_info = [f"{v.id} ({v.name})" for v in voices]
            logger.info(f"📋 Available pyttsx3 voices: {len(voices)} voices found")
            
            # Enhanced French voice selection
            pyttsx3_config = self.config.engine_specific_params.get("engines", {}).get("pyttsx3", {})
            target_voice = pyttsx3_config.get("voice", self.config.voice)
            
            # Auto-select French voice if language is French and no voice specified
            if not target_voice and self.config.language and self.config.language.startswith("fr"):
                # Prioritize French voices
                french_voices = ["Audrey", "Amelie", "Thomas", "Virginie"]
                for french_voice in french_voices:
                    for voice in voices:
                        if french_voice.lower() in voice.name.lower():
                            target_voice = voice.id
                            logger.info(f"🇫🇷 Auto-selected French voice: {voice.name}")
                            break
                    if target_voice:
                        break
            
            # Voice selection with enhanced matching
            if target_voice:
                found_voice = False
                for voice in voices:
                    if (target_voice.lower() in voice.name.lower() or 
                        target_voice == voice.id or
                        voice.name.lower() in target_voice.lower()):
                        engine.setProperty('voice', voice.id)
                        found_voice = True
                        logger.info(f"✅ Using voice: {voice.name} (ID: {voice.id})")
                        break
                if not found_voice:
                    logger.warning(f"⚠️ Voice '{target_voice}' not found. Using default.")
            elif self.config.language: # If no specific voice, try to match language
                lang_code = self.config.language.split('-')[0].lower()
                for voice in voices:
                    if hasattr(voice, 'languages') and voice.languages:
                        # Example: voice.languages = [b'en_US']
                        voice_langs = [lang.decode('utf-8').split('_')[0].lower() for lang in voice.languages if isinstance(lang, bytes)]
                        if lang_code in voice_langs:
                            engine.setProperty('voice', voice.id)
                            logger.info(f"🌍 Using voice for language '{lang_code}': {voice.name}")
                            break
                    elif lang_code in voice.name.lower(): # Fallback to name matching
                         engine.setProperty('voice', voice.id)
                         logger.info(f"🔍 Using voice (name match for '{lang_code}'): {voice.name}")
                         break

            # Apply optimized parameters for French
            rate = pyttsx3_config.get("rate", 200)  # Default to good French rate
            volume = pyttsx3_config.get("volume", 0.95)  # Slightly reduced for clarity
            
            # Optimize for French speech
            if self.config.language and self.config.language.startswith("fr"):
                rate = max(170, min(rate, 210))  # Optimal range for French
                logger.info(f"🎯 Optimized French speech rate: {rate}")
            
            logger.info(f"🔊 Setting pyttsx3 parameters - Rate: {rate}, Volume: {volume}")
            engine.setProperty('rate', rate)
            engine.setProperty('volume', volume)

            # Direct speak (this will block until speech is complete)
            logger.info(f"🎤 Speaking text directly with pyttsx3: '{text[:50]}...'")
            engine.say(text)
            engine.runAndWait()
            
            engine.stop() # Ensure engine is stopped and resources released

            logger.info(f"✅ French TTS synthesis completed successfully with pyttsx3")
            return TTSResult(success=True, engine_used="pyttsx3")

        except ImportError:
            return TTSResult(success=False, error_message="pyttsx3 library not installed.", engine_used="pyttsx3")
        except RuntimeError as e: # Catches "No system TTS سخنرانان found" or other init errors
            logger.error(f"RuntimeError during pyttsx3 synthesis: {e}", exc_info=True)
            return TTSResult(success=False, error_message=f"pyttsx3 runtime error: {e}", engine_used="pyttsx3")
        except Exception as e:
            logger.error(f"Error during pyttsx3 synthesis: {e}", exc_info=True)
            return TTSResult(success=False, error_message=str(e), engine_used="pyttsx3")

    def _synthesize_with_mock(self, text: str) -> TTSResult:
        logger.info(f"🗣️ [MOCK SimpleTTS] Direct vocalization (simulated): '{text}'")
        
        # No file output for mock - just direct "vocalization" simulation
        logger.info("Mock direct vocalization completed successfully")
        
        return TTSResult(success=True, engine_used="mock")

    def is_available(self) -> bool:
        """Checks if any of the simple TTS engines are available."""
        return any(self._available_engines.values())

    def stop(self):
        """Stops any ongoing speech."""
        # For direct vocalization, we don't need to manage processes or files
        logger.info("SimpleTTS stop requested - direct vocalization complete.")
