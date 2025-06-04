"""
Exposes the main Text-to-Speech interface and related components.
"""

from .base import TTSConfig, TTSResult, TTSEngineType, BaseTTS
from .text_to_speech import TextToSpeech
from .simple_tts_engine import SimpleTTS
from .advanced_tts_engine import AdvancedTTS
from .realistic_tts_engine import RealisticTTS

__all__ = [
    "TextToSpeech",
    "BaseTTS",
    "SimpleTTS",
    "AdvancedTTS",
    "RealisticTTS",
    "TTSConfig",
    "TTSResult",
    "TTSEngineType",
]
