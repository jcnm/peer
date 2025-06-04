import logging
from typing import Optional

from .base import TTSConfig, TTSResult, TTSEngineType, BaseTTS
from .simple_tts_engine import SimpleTTS
from .advanced_tts_engine import AdvancedTTS
from .realistic_tts_engine import RealisticTTS

# Configuration du logging
logger = logging.getLogger(__name__)

# Façade pour l'interface TextToSpeech complète
class TextToSpeech:
    """
    Main facade for the Text-to-Speech system.
    It initializes and manages a specific TTS engine (Simple, Advanced, or Realistic)
    based on the provided configuration.
    """

    def __init__(self, config: TTSConfig):
        """
        Initializes the TextToSpeech system with a specific engine strategy.

        Args:
            config: TTSConfiguration object specifying which engine to use
                    and its parameters.
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self._engine: Optional[BaseTTS] = None
        self._initialize_engine()

    def _initialize_engine(self):
        """
        Initializes the appropriate TTS engine based on the configuration.
        """
        engine_type = self.config.engine_type
        self.logger.info(f"Initializing TTS system with engine type: {engine_type.value}")
        self.logger.info(f"TTS Config: language={self.config.language}, voice={self.config.voice}, params={self.config.engine_specific_params}")

        if engine_type == TTSEngineType.SIMPLE:
            self._engine = SimpleTTS(self.config)
        elif engine_type == TTSEngineType.ADVANCED:
            self._engine = AdvancedTTS(self.config)
        elif engine_type == TTSEngineType.REALISTIC:
            self._engine = RealisticTTS(self.config)
        else:
            self.logger.error(f"Unsupported TTS engine type: {engine_type}. Defaulting to SimpleTTS if available, otherwise no engine.")
            # Fallback strategy: try SimpleTTS, or leave _engine as None
            default_config = TTSConfig(engine_type=TTSEngineType.SIMPLE, 
                                       language=self.config.language, 
                                       voice=self.config.voice, 
                                       engine_specific_params=self.config.engine_specific_params)
            self._engine = SimpleTTS(default_config)
            if not self._engine.is_available():
                 self.logger.warning("Fallback SimpleTTS engine is also not available. TTS will not function.")
                 self._engine = None # Explicitly set to None

        if self._engine:
            if self._engine.is_available():
                self.logger.info(f"{self._engine.__class__.__name__} initialized and available.")
            else:
                self.logger.warning(f"{self._engine.__class__.__name__} initialized but is not available. TTS might not function correctly.")
        else:
            self.logger.error("No TTS engine could be initialized. TextToSpeech will not be functional.")


    def synthesize(self, text: str) -> TTSResult:
        """
        Synthesizes speech from the given text using the configured engine.

        Args:
            text: The text to synthesize.

        Returns:
            A TTSResult object containing the outcome of the synthesis.
        """
        if not self._engine:
            self.logger.error("No TTS engine is initialized. Cannot synthesize.")
            return TTSResult(success=False, error_message="TTS engine not initialized.")

        if not self._engine.is_available():
            self.logger.warning(f"TTS engine {self._engine.__class__.__name__} is not available. Synthesis may fail.")
            # Still attempt, as is_available might be a soft check or state might have changed.
            # The engine itself should handle its unavailability gracefully.

        self.logger.info(f"Synthesizing text using {self._engine.__class__.__name__}: \'{text[:50]}...\'")
        try:
            result = self._engine.synthesize(text)
            if result.success:
                self.logger.info(f"Synthesis successful with {result.engine_used}. Audio path: {result.audio_path}")
            else:
                self.logger.warning(f"Synthesis failed with {result.engine_used or self._engine.__class__.__name__}. Error: {result.error_message}")
            return result
        except Exception as e:
            self.logger.error(f"Unhandled exception during synthesis with {self._engine.__class__.__name__}: {e}", exc_info=True)
            return TTSResult(success=False, error_message=f"Unhandled exception: {str(e)}", engine_used=self._engine.__class__.__name__)

    def is_engine_available(self) -> bool:
        """Checks if the configured TTS engine is available."""
        if not self._engine:
            return False
        return self._engine.is_available()

    def cleanup_temp_files(self):
        """Cleans up temporary files created by the TTS engine, if any."""
        if self._engine:
            self.logger.info(f"Cleaning up temporary files for {self._engine.__class__.__name__}.")
            self._engine.cleanup_temp_files()

    def __del__(self):
        # Ensure cleanup is called when the TextToSpeech object is destroyed
        self.cleanup_temp_files()

# Example Usage (for testing purposes, can be removed or placed in a test file)
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # --- Test SimpleTTS ---
    logger.info("\n--- Testing SimpleTTS ---")
    simple_config = TTSConfig(
        engine_type=TTSEngineType.SIMPLE,
        language="en-US",
        voice="default",
        parameters={
            "preferred_simple_engine_order": ["say", "pyttsx3", "espeak", "mock"]
        }
    )
    tts_simple = TextToSpeech(config=simple_config)
    if tts_simple.is_engine_available():
        result_simple = tts_simple.synthesize("Hello from the simple Text to Speech system. This is a test.")
        logger.info(f"SimpleTTS Result: Success={result_simple.success}, Path={result_simple.audio_file_path}, Engine={result_simple.engine_used}, Error={result_simple.error_message}")
    else:
        logger.warning("SimpleTTS engine not available for testing.")
    tts_simple.cleanup_temp_files()

    # --- Test AdvancedTTS (Piper) ---
    logger.info("\n--- Testing AdvancedTTS (Piper) ---")
    piper_model_path = "/path/to/your/piper/model/en_US-lessac-medium.onnx"  # CHANGE THIS
    
    advanced_config = TTSConfig(
        engine_type=TTSEngineType.ADVANCED,
        language="en-US",
        parameters={
            "model_path": piper_model_path
        }
    )
    tts_advanced = TextToSpeech(config=advanced_config)
    if tts_advanced.is_engine_available():
        result_advanced = tts_advanced.synthesize("Hello from the advanced Piper Text to Speech system. This is a test.")
        logger.info(f"AdvancedTTS Result: Success={result_advanced.success}, Path={result_advanced.audio_file_path}, Engine={result_advanced.engine_used}, Error={result_advanced.error_message}")
    else:
        logger.warning(f"AdvancedTTS (Piper) engine not available for testing. Check Piper installation and model path: '{piper_model_path}'")
    tts_advanced.cleanup_temp_files()

    # --- Test RealisticTTS (Placeholder) ---
    logger.info("\n--- Testing RealisticTTS (Placeholder) ---")
    realistic_config = TTSConfig(engine_type=TTSEngineType.REALISTIC)
    tts_realistic = TextToSpeech(config=realistic_config)
    if tts_realistic.is_engine_available():
        result_realistic = tts_realistic.synthesize("This should not produce any audio.")
        logger.info(f"RealisticTTS Result: Success={result_realistic.success}, Error={result_realistic.error_message}")
    else:
        logger.warning("RealisticTTS engine is (correctly) not available as it's a placeholder.")
    tts_realistic.cleanup_temp_files()

    logger.info("\n--- TTS Testing Complete ---")