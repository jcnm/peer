"""
Module de reconnaissance vocale automatique (ASR).

Ce module gère :
- Reconnaissance vocale avec différents moteurs (Whisper, Vosk, Wav2Vec2)
- Système de fallback automatique
- Gestion des modèles et configurations
- Optimisation des performances
"""

import logging
import time
import tempfile
import wave
import os
import json
import numpy as np
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Imports conditionnels pour les moteurs STT
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    whisper = None

try:
    import vosk
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    vosk = None

try:
    from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
    import torch
    WAV2VEC2_AVAILABLE = True
except ImportError:
    WAV2VEC2_AVAILABLE = False

from ..domain.models import SpeechRecognitionResult

class ASREngine(Enum):
    """Types de moteurs de reconnaissance vocale supportés."""
    WHISPER = "whisper"
    VOSK = "vosk"
    WAV2VEC2 = "wav2vec2"
    MOCK = "mock"

@dataclass
class ASRConfig:
    """Configuration pour un moteur ASR."""
    enabled: bool = True
    model_name: str = ""
    model_path: str = ""
    language: str = "fr"
    parameters: Dict[str, Any] = None
    priority: int = 10
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}

class WhisperASR:
    """Moteur de reconnaissance Whisper (OpenAI)."""
    
    def __init__(self, config: ASRConfig):
        self.logger = logging.getLogger("WhisperASR")
        self.config = config
        self.model = None
        
        if not WHISPER_AVAILABLE:
            raise ImportError("Whisper non disponible")
        
        self._load_model()
    
    def _load_model(self):
        """Charge le modèle Whisper."""
        model_name = self.config.model_name or "base"
        
        try:
            self.logger.info(f"📥 Chargement Whisper {model_name}...")
            self.model = whisper.load_model(model_name)
            
            # Test du modèle
            test_audio = np.zeros(16000, dtype=np.float32)  # 1 seconde de silence
            result = self.model.transcribe(test_audio, language=self.config.language)
            
            self.logger.info(f"✅ Whisper {model_name} chargé et testé")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur chargement Whisper: {e}")
            raise
    
    def transcribe(self, audio_data: np.ndarray) -> Optional[SpeechRecognitionResult]:
        """
        Transcrit l'audio avec Whisper.
        
        Args:
            audio_data: Données audio (numpy array, float32, 16kHz)
            
        Returns:
            Résultat de la transcription ou None
        """
        if self.model is None:
            return None
        
        try:
            start_time = time.time()
            
            # Whisper peut traiter directement les numpy arrays
            result = self.model.transcribe(
                audio_data,
                language=self.config.language,
                task=self.config.parameters.get("task", "transcribe"),
                temperature=self.config.parameters.get("temperature", 0.0),
                beam_size=self.config.parameters.get("beam_size", 1),
                best_of=self.config.parameters.get("best_of", 1),
                fp16=self.config.parameters.get("fp16", False),
                verbose=False
            )
            
            processing_time = time.time() - start_time
            
            text = result.get("text", "").strip()
            if not text:
                return None
            
            # Calculer la confiance moyenne à partir des segments
            confidence = 0.8  # Valeur par défaut
            if "segments" in result and result["segments"]:
                segment_confidences = []
                for segment in result["segments"]:
                    if "confidence" in segment:
                        segment_confidences.append(segment["confidence"])
                if segment_confidences:
                    confidence = sum(segment_confidences) / len(segment_confidences)
            
            return SpeechRecognitionResult(
                text=text,
                confidence=confidence,
                language=result.get("language", self.config.language),
                processing_time=processing_time,
                engine_used="whisper"
            )
            
        except Exception as e:
            self.logger.error(f"❌ Erreur transcription Whisper: {e}")
            return None

class VoskASR:
    """Moteur de reconnaissance Vosk."""
    
    def __init__(self, config: ASRConfig):
        self.logger = logging.getLogger("VoskASR")
        self.config = config
        self.model = None
        self.recognizer = None
        
        if not VOSK_AVAILABLE:
            raise ImportError("Vosk non disponible")
        
        self._load_model()
    
    def _load_model(self):
        """Charge le modèle Vosk."""
        model_path = self.config.model_path
        if not model_path or not os.path.exists(model_path):
            raise FileNotFoundError(f"Modèle Vosk non trouvé: {model_path}")
        
        try:
            self.logger.info(f"📥 Chargement Vosk: {model_path}")
            self.model = vosk.Model(model_path)
            self.recognizer = vosk.KaldiRecognizer(self.model, 16000)  # 16kHz fixe pour Vosk
            
            self.logger.info(f"✅ Vosk chargé: {os.path.basename(model_path)}")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur chargement Vosk: {e}")
            raise
    
    def transcribe(self, audio_data: np.ndarray) -> Optional[SpeechRecognitionResult]:
        """
        Transcrit l'audio avec Vosk.
        
        Args:
            audio_data: Données audio (numpy array, float32, 16kHz)
            
        Returns:
            Résultat de la transcription ou None
        """
        if self.recognizer is None:
            return None
        
        try:
            start_time = time.time()
            
            # Convertir en int16 pour Vosk
            audio_int16 = (audio_data * 32767).astype(np.int16)
            audio_bytes = audio_int16.tobytes()
            
            # Reset du recognizer
            self.recognizer.Reset()
            
            # Traitement par chunks
            chunk_size = 4000  # Chunk size pour Vosk
            final_result = None
            
            for i in range(0, len(audio_bytes), chunk_size):
                chunk = audio_bytes[i:i + chunk_size]
                if self.recognizer.AcceptWaveform(chunk):
                    result = json.loads(self.recognizer.Result())
                    if result.get("text"):
                        final_result = result
            
            # Récupérer le résultat final
            if not final_result:
                final_result = json.loads(self.recognizer.FinalResult())
            
            processing_time = time.time() - start_time
            
            text = final_result.get("text", "").strip()
            if not text:
                return None
            
            # Vosk peut fournir une confiance
            confidence = final_result.get("confidence", 0.7)
            
            return SpeechRecognitionResult(
                text=text,
                confidence=confidence,
                language=self.config.language,
                processing_time=processing_time,
                engine_used="vosk"
            )
            
        except Exception as e:
            self.logger.error(f"❌ Erreur transcription Vosk: {e}")
            return None

class Wav2Vec2ASR:
    """Moteur de reconnaissance Wav2Vec2 (Facebook/Meta)."""
    
    def __init__(self, config: ASRConfig):
        self.logger = logging.getLogger("Wav2Vec2ASR")
        self.config = config
        self.processor = None
        self.model = None
        
        if not WAV2VEC2_AVAILABLE:
            raise ImportError("Wav2Vec2 non disponible")
        
        self._load_model()
    
    def _load_model(self):
        """Charge le modèle Wav2Vec2."""
        model_name = self.config.model_name or "facebook/wav2vec2-base-960h"
        
        try:
            self.logger.info(f"📥 Chargement Wav2Vec2: {model_name}")
            
            self.processor = Wav2Vec2Processor.from_pretrained(model_name)
            self.model = Wav2Vec2ForCTC.from_pretrained(model_name)
            
            self.logger.info(f"✅ Wav2Vec2 chargé: {model_name}")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur chargement Wav2Vec2: {e}")
            raise
    
    def transcribe(self, audio_data: np.ndarray) -> Optional[SpeechRecognitionResult]:
        """
        Transcrit l'audio avec Wav2Vec2.
        
        Args:
            audio_data: Données audio (numpy array, float32, 16kHz)
            
        Returns:
            Résultat de la transcription ou None
        """
        if self.processor is None or self.model is None:
            return None
        
        try:
            start_time = time.time()
            
            # Preprocessing
            input_values = self.processor(
                audio_data, 
                sampling_rate=16000, 
                return_tensors="pt", 
                padding=True
            ).input_values
            
            # Inference
            with torch.no_grad():
                logits = self.model(input_values).logits
            
            # Décodage
            predicted_ids = torch.argmax(logits, dim=-1)
            text = self.processor.batch_decode(predicted_ids)[0]
            
            processing_time = time.time() - start_time
            
            text = text.strip()
            if not text:
                return None
            
            # Wav2Vec2 ne fournit pas directement de score de confiance
            # On peut l'estimer à partir des logits
            confidence = 0.6  # Valeur conservative
            
            return SpeechRecognitionResult(
                text=text,
                confidence=confidence,
                language=self.config.language,
                processing_time=processing_time,
                engine_used="wav2vec2"
            )
            
        except Exception as e:
            self.logger.error(f"❌ Erreur transcription Wav2Vec2: {e}")
            return None

class MockASR:
    """Moteur de reconnaissance simulé pour les tests."""
    
    def __init__(self, config: ASRConfig):
        self.logger = logging.getLogger("MockASR")
        self.config = config
        self.responses = [
            "bonjour peer",
            "aide moi s'il te plaît",
            "quelle heure est-il",
            "quel est le statut du système", 
            "je voudrais des informations",
            "comment ça marche",
            "merci beaucoup",
            "au revoir",
            "arrête toi",
            "mode texte",
            "mode vocal"
        ]
        self.counter = 0
    
    def transcribe(self, audio_data: np.ndarray) -> SpeechRecognitionResult:
        """Retourne une transcription simulée."""
        response = self.responses[self.counter % len(self.responses)]
        self.counter += 1
        
        # Simuler un délai de traitement
        time.sleep(0.1)
        
        return SpeechRecognitionResult(
            text=response,
            confidence=0.9,
            language=self.config.language,
            processing_time=0.1,
            engine_used="mock"
        )

class SpeechRecognizer:
    """
    Gestionnaire principal de reconnaissance vocale avec fallbacks.
    
    Gère plusieurs moteurs ASR avec basculement automatique en cas d'échec.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger("SpeechRecognizer")
        self.config = config
        
        # Configuration des moteurs
        self.engine_configs = self._parse_engine_configs()
        self.engines = {}
        self.fallback_order = []
        
        self.logger.info("🎤 Initialisation du reconnaisseur vocal...")
        self._initialize_engines()
        self._setup_fallback_order()
        
        if not self.engines:
            raise RuntimeError("Aucun moteur ASR disponible")
        
        self.logger.info(f"✅ Reconnaisseur vocal initialisé avec {len(self.engines)} moteurs")
    
    def _parse_engine_configs(self) -> Dict[ASREngine, ASRConfig]:
        """Parse la configuration des moteurs."""
        configs = {}
        stt_config = self.config.get('stt_settings', {})
        engines_config = stt_config.get('engines', {})
        
        # Configuration par défaut
        default_configs = {
            ASREngine.WHISPER: ASRConfig(
                enabled=True,
                model_name="base",
                language="fr",
                priority=1,
                parameters={"temperature": 0.0, "beam_size": 1}
            ),
            ASREngine.VOSK: ASRConfig(
                enabled=True,
                model_path="vepeer/models/vosk/vosk-model-fr-0.22",
                language="fr",
                priority=2
            ),
            ASREngine.WAV2VEC2: ASRConfig(
                enabled=True,
                model_name="facebook/wav2vec2-base-960h",
                language="en",  # Modèle anglais par défaut
                priority=3
            ),
            ASREngine.MOCK: ASRConfig(
                enabled=True,
                language="fr",
                priority=99
            )
        }
        
        # Fusionner avec la configuration utilisateur
        for engine in ASREngine:
            engine_config = engines_config.get(engine.value, {})
            default_config = default_configs.get(engine, ASRConfig())
            
            # Mettre à jour avec la config utilisateur
            config = ASRConfig(
                enabled=engine_config.get('enabled', default_config.enabled),
                model_name=engine_config.get('model_name', default_config.model_name),
                model_path=engine_config.get('model_path', default_config.model_path),
                language=engine_config.get('language', default_config.language),
                priority=engine_config.get('priority', default_config.priority),
                parameters={**default_config.parameters, **engine_config.get('parameters', {})}
            )
            
            configs[engine] = config
        
        return configs
    
    def _initialize_engines(self):
        """Initialise tous les moteurs ASR disponibles."""
        for engine_type, config in self.engine_configs.items():
            if not config.enabled:
                continue
            
            try:
                engine = self._create_engine(engine_type, config)
                if engine:
                    self.engines[engine_type] = engine
                    self.logger.info(f"✅ Moteur {engine_type.value} initialisé")
                
            except Exception as e:
                self.logger.warning(f"⚠️ Échec initialisation {engine_type.value}: {e}")
    
    def _create_engine(self, engine_type: ASREngine, config: ASRConfig):
        """Crée une instance de moteur ASR."""
        if engine_type == ASREngine.WHISPER:
            return WhisperASR(config)
        elif engine_type == ASREngine.VOSK:
            return VoskASR(config)
        elif engine_type == ASREngine.WAV2VEC2:
            return Wav2Vec2ASR(config)
        elif engine_type == ASREngine.MOCK:
            return MockASR(config)
        else:
            raise ValueError(f"Moteur inconnu: {engine_type}")
    
    def _setup_fallback_order(self):
        """Configure l'ordre de fallback basé sur les priorités."""
        available_engines = list(self.engines.keys())
        
        # Trier par priorité
        self.fallback_order = sorted(
            available_engines,
            key=lambda e: self.engine_configs[e].priority
        )
        
        if self.fallback_order:
            primary = self.fallback_order[0]
            fallbacks = self.fallback_order[1:]
            
            self.logger.info(f"🎯 Moteur principal: {primary.value}")
            if fallbacks:
                fallback_names = [e.value for e in fallbacks]
                self.logger.info(f"🔄 Fallbacks: {', '.join(fallback_names)}")
    
    def transcribe(self, audio_data: np.ndarray) -> Optional[SpeechRecognitionResult]:
        """
        Transcrit l'audio en utilisant le système de fallback.
        
        Args:
            audio_data: Données audio (numpy array, float32, 16kHz)
            
        Returns:
            Résultat de transcription ou None si tous les moteurs échouent
        """
        if not audio_data.size or not self.fallback_order:
            return None
        
        last_error = None
        
        for engine_type in self.fallback_order:
            engine = self.engines.get(engine_type)
            if not engine:
                continue
            
            try:
                self.logger.debug(f"🔄 Tentative avec {engine_type.value}")
                result = engine.transcribe(audio_data)
                
                if result and result.text.strip():
                    self.logger.info(f"✅ Succès avec {engine_type.value}: '{result.text}'")
                    return result
                
            except Exception as e:
                last_error = e
                self.logger.warning(f"⚠️ Échec {engine_type.value}: {e}")
                continue
        
        self.logger.error(f"❌ Tous les moteurs ont échoué. Dernière erreur: {last_error}")
        return None
    
    def get_available_engines(self) -> List[str]:
        """Retourne la liste des moteurs disponibles."""
        return [engine.value for engine in self.engines.keys()]
    
    def get_primary_engine(self) -> Optional[str]:
        """Retourne le moteur principal."""
        return self.fallback_order[0].value if self.fallback_order else None
    
    def get_engine_info(self) -> Dict[str, Any]:
        """Retourne les informations sur les moteurs."""
        return {
            'available_engines': self.get_available_engines(),
            'primary_engine': self.get_primary_engine(),
            'fallback_order': [e.value for e in self.fallback_order],
            'total_engines': len(self.engines)
        }
