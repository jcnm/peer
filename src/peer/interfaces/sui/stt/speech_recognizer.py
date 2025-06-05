"""
Module de reconnaissance vocale automatique (ASR).

Ce module gère :
- Reconnaissance vocale avec différents moteurs (WhisperX, Vosk)
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
    import whisperx
    WHISPERX_AVAILABLE = True
except ImportError:
    WHISPERX_AVAILABLE = False
    whisperx = None

try:
    import vosk
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    vosk = None

from ..domain.models import SpeechRecognitionResult

class ASREngine(Enum):
    """Types de moteurs de reconnaissance vocale supportés."""
    WHISPERX = "whisperx"
    VOSK = "vosk"
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

class WhisperXASR:
    """Moteur de reconnaissance WhisperX (version améliorée)."""
    
    def __init__(self, config: ASRConfig):
        self.logger = logging.getLogger("WhisperXASR")
        self.config = config
        self.model = None
        self.align_model = None
        self.align_metadata = None
        
        if not WHISPERX_AVAILABLE:
            raise ImportError("WhisperX non disponible")
        
        self._load_model()
    
    def _load_model(self):
        """Charge le modèle WhisperX."""
        model_name = self.config.model_name or "base"
        
        try:
            self.logger.info(f"📥 Chargement WhisperX {model_name}...")
            
            # Déterminer le device optimal
            device = "cpu"
            compute_type = "int8"
            
            # Essayer d'utiliser GPU si disponible
            try:
                import torch
                if torch.cuda.is_available():
                    device = "cuda"
                    compute_type = "float16"
                elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    # MPS sur macOS - utiliser CPU pour WhisperX pour éviter les problèmes
                    device = "cpu"
                    compute_type = "int8"
            except ImportError:
                pass
            
            # Charger le modèle principal
            self.model = whisperx.load_model(
                model_name, 
                device=device,
                compute_type=compute_type
            )
            
            # Charger le modèle d'alignement pour la langue configurée
            try:
                language_code = self.config.language if self.config.language in ["en", "fr", "de", "es", "it", "ja", "zh", "nl", "uk", "pt"] else "en"
                self.align_model, self.align_metadata = whisperx.load_align_model(
                    language_code=language_code, 
                    device=device
                )
                self.logger.info(f"✅ Modèle d'alignement chargé pour {language_code}")
            except Exception as e:
                self.logger.warning(f"⚠️ Impossible de charger le modèle d'alignement: {e}")
                self.align_model = None
                self.align_metadata = None
            
            self.logger.info(f"✅ WhisperX {model_name} chargé et configuré sur {device}")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur chargement WhisperX: {e}")
            raise
    
    def transcribe(self, audio_data: np.ndarray) -> Optional[SpeechRecognitionResult]:
        """
        Transcrit l'audio avec WhisperX.
        
        Args:
            audio_data: Données audio (numpy array, float32, 16kHz)
            
        Returns:
            Résultat de la transcription ou None
        """
        if self.model is None:
            return None
        
        try:
            start_time = time.time()
            
            # WhisperX transcription avec paramètres optimisés
            result = self.model.transcribe(
                audio_data,
                batch_size=self.config.parameters.get("batch_size", 16),
                language=self.config.language if self.config.language != "auto" else None,
                task=self.config.parameters.get("task", "transcribe")
            )
            
            # Vérifier s'il y a des segments
            if not result.get("segments"):
                return None
            
            # Appliquer l'alignement si disponible pour une meilleure précision
            if self.align_model and self.align_metadata:
                try:
                    result = whisperx.align(
                        result["segments"], 
                        self.align_model, 
                        self.align_metadata, 
                        audio_data, 
                        device="cpu"  # Utiliser CPU pour l'alignement pour éviter les problèmes
                    )
                except Exception as align_error:
                    self.logger.warning(f"⚠️ Échec alignement: {align_error}")
                    # Continuer sans alignement
            
            processing_time = time.time() - start_time
            
            # Extraire le texte des segments
            text_parts = []
            total_confidence = 0
            segment_count = 0
            
            for segment in result.get("segments", []):
                if "text" in segment and segment["text"].strip():
                    text_parts.append(segment["text"].strip())
                    
                    # Calculer la confiance
                    if "score" in segment:
                        total_confidence += segment["score"]
                        segment_count += 1
                    elif "confidence" in segment:
                        total_confidence += segment["confidence"]
                        segment_count += 1
            
            if not text_parts:
                return None
            
            text = " ".join(text_parts)
            confidence = total_confidence / segment_count if segment_count > 0 else 0.8
            
            # Détecter la langue si pas spécifiée
            detected_language = result.get("language", self.config.language)
            
            return SpeechRecognitionResult(
                text=text,
                confidence=confidence,
                language=detected_language,
                processing_time=processing_time,
                engine_used="whisperx"
            )
            
        except Exception as e:
            self.logger.error(f"❌ Erreur transcription WhisperX: {e}")
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
            ASREngine.WHISPERX: ASRConfig(
                enabled=True,
                model_name="base",
                language="fr",
                priority=1,
                parameters={"batch_size": 16, "task": "transcribe"}
            ),
            ASREngine.VOSK: ASRConfig(
                enabled=True,
                model_path="vepeer/models/vosk/vosk-model-fr-0.22",
                language="fr",
                priority=2
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
        if engine_type == ASREngine.WHISPERX:
            return WhisperXASR(config)
        elif engine_type == ASREngine.VOSK:
            return VoskASR(config)
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
    
    def transcribe_audio(self, audio_data: np.ndarray, use_alignment: bool = False) -> Optional[SpeechRecognitionResult]:
        """
        Transcrit les données audio avec options avancées.
        
        Args:
            audio_data: Données audio (numpy array, float32, 16kHz)
            use_alignment: Utiliser l'alignement pour une meilleure précision
            
        Returns:
            Résultat de la transcription ou None
        """
        # Utiliser la méthode standard pour la transcription
        result = self.transcribe(audio_data)
        
        # Si alignement demandé et WhisperX disponible, améliorer la précision
        if use_alignment and result and ASREngine.WHISPERX in self.engines:
            try:
                whisperx_engine = self.engines[ASREngine.WHISPERX]
                if hasattr(whisperx_engine, 'align_model') and whisperx_engine.align_model:
                    # Re-faire la transcription avec alignement forcé
                    aligned_result = whisperx_engine.transcribe(audio_data)
                    if aligned_result and aligned_result.confidence > result.confidence:
                        result = aligned_result
                        self.logger.debug("🎯 Alignement appliqué pour améliorer la précision")
            except Exception as e:
                self.logger.warning(f"⚠️ Échec de l'alignement: {e}")
        
        return result
    
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
