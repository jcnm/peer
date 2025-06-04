from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any

class TTSEngineType(Enum):
    """Specifies the type of TTS engine to use (Simple, Advanced, or Realistic)."""
    SIMPLE = "simple"
    ADVANCED = "advanced"
    REALISTIC = "realistic"

@dataclass
class TTSConfig:
    """Configuration for the Text-to-Speech system."""
    engine_type: TTSEngineType = TTSEngineType.SIMPLE
    language: str = "fr-FR"
    voice: Optional[str] = None
    output_path: Optional[str] = None  # Optional path to save the audio file
    engine_specific_params: Dict[str, Any] = field(default_factory=dict)
    # Example: For Piper in AdvancedTTS, could include model path, speaker_id, etc.
    # Example: For SimpleTTS, could specify preferred sub-engine (say, espeak)
    
    def __post_init__(self):
        """Initialize default values if not provided."""
        if not self.engine_specific_params:
            self.engine_specific_params = {}
        
        # Set default parameters for SimpleTTS if not provided
        if self.engine_type == TTSEngineType.SIMPLE and "preferred_simple_engine_order" not in self.engine_specific_params:
            self.engine_specific_params["preferred_simple_engine_order"] = ["say", "pyttsx3", "espeak", "mock"]

@dataclass
class TTSResult:
    """Result of a Text-to-Speech synthesis operation."""
    success: bool
    audio_path: Optional[str] = None  # Path to the generated audio file, if saved
    audio_content: Optional[bytes] = None # Raw audio bytes, if not saved to file
    error_message: Optional[str] = None
    engine_used: Optional[str] = None # To know which low-level engine was actually used

class BaseTTS(ABC):
    """Abstract Base Class for TTS engines."""

    def __init__(self, config: TTSConfig):
        self.config = config

    @abstractmethod
    def synthesize(self, text: str) -> TTSResult:
        """
        Synthesizes speech from the given text.

        Args:
            text: The text to synthesize.

        Returns:
            A TTSResult object containing the outcome of the synthesis.
        """
        pass

    def is_available(self) -> bool:
        """
        Checks if the TTS engine and its dependencies are available.
        Default implementation, can be overridden by subclasses.
        """
        return True # Subclasses should implement specific checks
    
    def cleanup_temp_files(self):
        """
        Cleans up temporary files created by the TTS engine.
        Default implementation does nothing. Subclasses should override if needed.
        """
        pass
