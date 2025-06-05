"""
Module de gestion de la parole continue avec batching intelligent.

Ce module gère :
- Détection intelligente des pauses dans la parole
- Regroupement des segments de parole en batches cohérents
- Transcription en temps réel avec WhisperX
- Affichage progressif de la transcription
"""

import time
import threading
import queue
import logging
import numpy as np
from typing import Optional, List, Callable, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

from ..domain.models import SpeechRecognitionResult
from .speech_recognizer import SpeechRecognizer, ASREngine


class SpeechSegmentState(Enum):
    """États d'un segment de parole."""
    ACTIVE = "active"           # Parole en cours
    PAUSED = "paused"           # Pause courte détectée
    COMPLETED = "completed"     # Segment terminé
    TRANSCRIBING = "transcribing"  # En cours de transcription


@dataclass
class SpeechSegment:
    """Segment de parole avec métadonnées."""
    audio_data: np.ndarray
    start_time: float
    end_time: float
    state: SpeechSegmentState = SpeechSegmentState.ACTIVE
    transcription: Optional[str] = None
    confidence: float = 0.0
    partial_transcription: Optional[str] = None
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


@dataclass
class SpeechBatch:
    """Batch de segments de parole à transcrire ensemble."""
    segments: List[SpeechSegment] = field(default_factory=list)
    start_time: float = 0.0
    last_activity_time: float = 0.0
    state: SpeechSegmentState = SpeechSegmentState.ACTIVE
    accumulated_audio: Optional[np.ndarray] = None
    final_transcription: Optional[str] = None
    
    def add_segment(self, segment: SpeechSegment):
        """Ajoute un segment au batch."""
        self.segments.append(segment)
        self.last_activity_time = segment.end_time
        
        # Concaténer l'audio
        if self.accumulated_audio is None:
            self.accumulated_audio = segment.audio_data.copy()
        else:
            self.accumulated_audio = np.concatenate([self.accumulated_audio, segment.audio_data])
    
    @property
    def total_duration(self) -> float:
        if not self.segments:
            return 0.0
        return self.segments[-1].end_time - self.segments[0].start_time
    
    @property
    def pause_duration(self) -> float:
        """Durée depuis la dernière activité."""
        return time.time() - self.last_activity_time


class ContinuousSpeechManager:
    """Gestionnaire de parole continue avec batching intelligent."""
    
    def __init__(self, 
                 speech_recognizer: SpeechRecognizer,
                 pause_threshold: float = 1.5,      # Seuil de pause pour finaliser un batch (secondes)
                 min_segment_duration: float = 0.3,  # Durée minimale d'un segment (secondes)
                 max_batch_duration: float = 10.0,   # Durée maximale d'un batch (secondes)
                 transcription_callback: Optional[Callable[[str, bool], None]] = None):
        """
        Initialize le gestionnaire de parole continue.
        
        Args:
            speech_recognizer: Instance du recognizer vocal
            pause_threshold: Seuil de pause pour finaliser un batch
            min_segment_duration: Durée minimale d'un segment
            max_batch_duration: Durée maximale d'un batch
            transcription_callback: Callback pour les transcriptions (texte, is_final)
        """
        self.logger = logging.getLogger("ContinuousSpeechManager")
        self.speech_recognizer = speech_recognizer
        
        # Configuration des seuils
        self.pause_threshold = pause_threshold
        self.min_segment_duration = min_segment_duration
        self.max_batch_duration = max_batch_duration
        
        # Callbacks
        self.transcription_callback = transcription_callback
        
        # État de la parole
        self.current_batch: Optional[SpeechBatch] = None
        self.completed_batches: deque = deque(maxlen=10)  # Historique des batches
        
        # Threading
        self.processing_queue = queue.Queue()
        self.running = False
        self.processing_thread: Optional[threading.Thread] = None
        
        # Métriques
        self.stats = {
            'segments_processed': 0,
            'batches_completed': 0,
            'total_audio_duration': 0.0,
            'avg_transcription_time': 0.0
        }
        
        self.logger.info(f"✅ ContinuousSpeechManager initialisé")
        self.logger.info(f"   Seuil de pause: {pause_threshold}s")
        self.logger.info(f"   Durée min segment: {min_segment_duration}s")
        self.logger.info(f"   Durée max batch: {max_batch_duration}s")
    
    def start(self):
        """Démarre le gestionnaire de parole continue."""
        if self.running:
            self.logger.warning("Gestionnaire déjà en cours")
            return
        
        self.running = True
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()
        
        self.logger.info("🎙️ Gestionnaire de parole continue démarré")
    
    def stop(self):
        """Arrête le gestionnaire de parole continue."""
        if not self.running:
            return
        
        self.running = False
        
        # Finaliser le batch en cours
        if self.current_batch:
            try:
                self._finalize_current_batch()
            except Exception as e:
                self.logger.error(f"❌ Erreur lors de la finalisation du dernier batch: {e}")
        
        # Vider la file d'attente
        try:
            while not self.processing_queue.empty():
                self.processing_queue.get_nowait()
                self.processing_queue.task_done()
        except:
            pass
            
        # Attendre l'arrêt du thread
        if self.processing_thread and self.processing_thread.is_alive():
            try:
                # Ne pas utiliser join() ici pour éviter le blocage
                self.processing_thread.join(timeout=1.0)
            except Exception as e:
                self.logger.error(f"❌ Erreur lors de l'arrêt du thread: {e}")
        
        self.logger.info("🛑 Gestionnaire de parole continue arrêté")
    
    def add_audio_segment(self, audio_data: np.ndarray, has_speech: bool = True):
        """
        Ajoute un segment audio à traiter.
        
        Args:
            audio_data: Données audio (16kHz, mono, float32)
            has_speech: Indique si le segment contient de la parole
        """
        if not self.running:
            return
        
        self.logger.debug(f"📥 Segment reçu: {len(audio_data)} échantillons, parole={has_speech}")
        
        current_time = time.time()
        
        # Vérifier si le batch actuel existe et si une pause a été détectée
        if self.current_batch and not has_speech:
            pause_duration = current_time - self.current_batch.last_activity_time
            
            # Si une pause de plus de 1 seconde est détectée et qu'il y a suffisamment de contenu,
            # finaliser immédiatement pour réduire le délai
            if pause_duration >= 1.0 and len(self.current_batch.segments) >= 2 and self.current_batch.total_duration >= 0.5:
                self.logger.info(f"🔇 Pause naturelle de {pause_duration:.1f}s détectée, finalisation immédiate")
                self._finalize_current_batch()
        
        if has_speech and len(audio_data) > 0:
            # Créer un nouveau segment de parole
            segment_duration = len(audio_data) / 16000
            segment = SpeechSegment(
                audio_data=audio_data,
                start_time=current_time - segment_duration,  # Estimer le temps de début
                end_time=current_time,
                state=SpeechSegmentState.ACTIVE
            )
            
            # Accepter tous les segments avec parole, presque sans seuil minimum
            min_duration = max(0.02, self.min_segment_duration * 0.1)  # Seuil encore plus bas pour capter toute parole
            
            # Log plus détaillé
            self.logger.debug(f"📥 Nouveau segment: durée={segment.duration:.3f}s, échantillons={len(audio_data)}")
            
            # Presque toujours accepter les segments qui contiennent de la parole
            if segment.duration >= min_duration:
                self.logger.debug(f"✅ Segment valide: {segment.duration:.3f}s")
                self._process_speech_segment(segment)
            else:
                self.logger.debug(f"⏭️ Segment très court: {segment.duration:.3f}s < {min_duration:.3f}s")
                # Ajouter quand même presque tous les segments courts
                if len(audio_data) > 0:
                    self.logger.debug("🔄 Ajout forcé du segment court")
                    self._process_speech_segment(segment)
        else:
            # Pas de parole - gérer la pause mais de manière moins agressive
            if self.current_batch is not None:
                self._handle_pause()
            else:
                self.logger.debug("🔇 Silence détecté (pas de batch actif)")
    
    def _process_speech_segment(self, segment: SpeechSegment):
        """Traite un segment de parole."""
        current_time = time.time()
        
        # Créer un nouveau batch si nécessaire
        if self.current_batch is None:
            self.current_batch = SpeechBatch(start_time=current_time)
            self.logger.debug("🆕 Nouveau batch de parole créé")
        
        # Vérifier si on doit finaliser le batch actuel
        should_finalize = False
        
        # Batch trop long
        max_duration = self.max_batch_duration * 0.95  # Augmenté à 0.95 pour maximiser la longueur des phrases
        if self.current_batch.total_duration >= max_duration:
            should_finalize = True
            self.logger.debug(f"📏 Batch finalisé (durée max atteinte: {self.current_batch.total_duration:.1f}s)")
        
        # Ajouter le segment au batch actuel
        self.current_batch.add_segment(segment)
        self.stats['segments_processed'] += 1
        
        self.logger.debug(f"➕ Segment ajouté au batch (total: {len(self.current_batch.segments)} segments, {self.current_batch.total_duration:.1f}s)")
        
        # Vérifier si on doit finaliser après l'ajout du segment (cas de la durée maximale)
        if should_finalize:
            self._finalize_current_batch()
            return
        
        # Faire une transcription partielle après quelques segments
        if len(self.current_batch.segments) >= 3:  # Après 3 segments (au lieu de 5)
            self._queue_partial_transcription()
            
        # Force finalisation après un certain nombre de segments
        if len(self.current_batch.segments) >= 40:  # Forcer après 40 segments (au lieu de 20)
            self.logger.debug(f"🔄 Forçage de finalisation après {len(self.current_batch.segments)} segments")
            self._finalize_current_batch()
            return
    
    def _handle_pause(self):
        """Gère une pause dans la parole."""
        if self.current_batch and self.current_batch.segments:
            current_time = time.time()
            pause_duration = current_time - self.current_batch.last_activity_time
            
            # Finaliser rapidement si pause significative (>1s) 
            # mais avec un batch minimum (au moins 2 segments ou 0.5s d'audio)
            min_batch_size = len(self.current_batch.segments) >= 2
            min_batch_duration = self.current_batch.total_duration >= 0.5
            has_sufficient_content = min_batch_size and min_batch_duration
            
            # Si pause de plus de 1s avec contenu suffisant, finaliser immédiatement
            if pause_duration >= 1.0 and has_sufficient_content:
                self.logger.info(f"⏸️ Pause significative détectée ({pause_duration:.1f}s), finalisation immédiate du batch")
                self._finalize_current_batch()
                return
            
            # Pour les pauses plus longues, utiliser le seuil adaptatif
            effective_pause_threshold = self.pause_threshold * 2.0  # Réduit pour être plus réactif
            
            # Adapter le seuil en fonction de la longueur du batch actuel
            if self.current_batch.total_duration > 3.0:
                batch_factor = min(1.5, self.current_batch.total_duration / 3.0)
                effective_pause_threshold *= batch_factor
                self.logger.debug(f"⏸️ Seuil de pause adapté: {effective_pause_threshold:.1f}s (batch={self.current_batch.total_duration:.1f}s)")
            
            # Si la pause est très longue, finaliser le batch
            if pause_duration >= effective_pause_threshold:
                self.logger.debug(f"⏸️ Pause longue détectée ({pause_duration:.1f}s >= {effective_pause_threshold:.1f}s), finalisation du batch")
                self._finalize_current_batch()
            else:
                self.logger.debug(f"⏸️ Pause courte ({pause_duration:.1f}s < {effective_pause_threshold:.1f}s), continuation du batch")
                # Pour les pauses modérées, ne rien faire
    
    def _finalize_current_batch(self):
        """Finalise le batch actuel et lance la transcription finale."""
        if not self.current_batch or not self.current_batch.segments:
            return
        
        self.current_batch.state = SpeechSegmentState.COMPLETED
        
        # Log détaillé pour le débogage
        self.logger.info(f"✅ Finalisation batch: {len(self.current_batch.segments)} segments, "
                         f"{self.current_batch.total_duration:.1f}s, "
                         f"{len(self.current_batch.accumulated_audio)} échantillons")
        
        # Ajouter à la queue de traitement pour transcription finale
        self.processing_queue.put(('final_transcription', self.current_batch))
        
        # Archiver le batch
        self.completed_batches.append(self.current_batch)
        self.stats['batches_completed'] += 1
        
        self.logger.debug(f"✅ Batch finalisé: {len(self.current_batch.segments)} segments, "
                         f"{self.current_batch.total_duration:.1f}s")
        
        self.current_batch = None
    
    def _queue_partial_transcription(self):
        """Met en queue une transcription partielle du batch actuel."""
        if self.current_batch and self.current_batch.accumulated_audio is not None:
            # Copier les données pour la transcription partielle
            batch_copy = SpeechBatch()
            batch_copy.accumulated_audio = self.current_batch.accumulated_audio.copy()
            batch_copy.state = SpeechSegmentState.TRANSCRIBING
            
            self.processing_queue.put(('partial_transcription', batch_copy))
    
    def _processing_loop(self):
        """Boucle de traitement des transcriptions."""
        self.logger.info("🔄 Boucle de traitement démarrée")
        
        last_pause_check = time.time()
        
        while self.running:
            try:
                # Attendre une tâche de transcription avec timeout court pour vérifier les pauses fréquemment
                task = self.processing_queue.get(timeout=0.3)  # Timeout réduit pour vérifier les pauses plus souvent
                task_type, batch = task
                
                if task_type == 'partial_transcription':
                    self._do_partial_transcription(batch)
                elif task_type == 'final_transcription':
                    self._do_final_transcription(batch)
                
                self.processing_queue.task_done()
                
            except queue.Empty:
                # Vérifier périodiquement les pauses
                current_time = time.time()
                # Vérifier les pauses plus fréquemment (toutes les 300ms)
                if current_time - last_pause_check >= 0.3:
                    self._handle_pause()
                    last_pause_check = current_time
                continue
            except Exception as e:
                self.logger.error(f"❌ Erreur dans la boucle de traitement: {e}")
    
    def _do_partial_transcription(self, batch: SpeechBatch):
        """Effectue une transcription partielle rapide."""
        if batch.accumulated_audio is None:
            return
        
        try:
            start_time = time.time()
            
            # Transcription rapide avec paramètres optimisés pour la vitesse
            # Limiter la taille de l'audio pour les transcriptions partielles pour réduire la latence
            audio_length = len(batch.accumulated_audio)
            # Si l'audio est très long, prendre seulement les dernières 2 secondes (32000 échantillons à 16kHz)
            if audio_length > 32000:  # Plus de 2 secondes
                partial_audio = batch.accumulated_audio[-32000:]
                self.logger.debug(f"🔤 Transcription partielle optimisée: {len(partial_audio)} échantillons (réduit de {audio_length})")
            else:
                partial_audio = batch.accumulated_audio
            
            # Transcription rapide sur un échantillon potentiellement réduit
            result = self.speech_recognizer.transcribe_audio(partial_audio)
            
            if result and result.text.strip():
                processing_time = time.time() - start_time
                
                self.logger.debug(f"🔤 Transcription partielle: '{result.text}' "
                                f"(conf: {result.confidence:.2f}, {processing_time:.2f}s)")
                
                # Appeler le callback avec transcription partielle
                if self.transcription_callback:
                    self.transcription_callback(result.text, False)  # False = pas final
        
        except Exception as e:
            self.logger.error(f"❌ Erreur transcription partielle: {e}")
    
    def _do_final_transcription(self, batch: SpeechBatch):
        """Effectue une transcription finale de haute qualité."""
        if batch.accumulated_audio is None:
            return
        
        try:
            start_time = time.time()
            
            # Transcription finale avec paramètres de haute qualité
            result = self.speech_recognizer.transcribe_audio(
                batch.accumulated_audio,
                use_alignment=True  # Utiliser l'alignement pour une meilleure précision
            )
            
            if result and result.text.strip():
                processing_time = time.time() - start_time
                batch.final_transcription = result.text
                
                self.logger.info(f"✅ Transcription finale: '{result.text}' "
                               f"(conf: {result.confidence:.2f}, {processing_time:.2f}s)")
                
                # Mettre à jour les statistiques
                self.stats['total_audio_duration'] += batch.total_duration
                self.stats['avg_transcription_time'] = (
                    (self.stats['avg_transcription_time'] * (self.stats['batches_completed'] - 1) + processing_time) 
                    / self.stats['batches_completed']
                )
                
                # Appeler le callback avec transcription finale
                if self.transcription_callback:
                    self.transcription_callback(result.text, True)  # True = final
        
        except Exception as e:
            self.logger.error(f"❌ Erreur transcription finale: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du gestionnaire."""
        stats = self.stats.copy()
        
        if self.current_batch:
            stats['current_batch_duration'] = self.current_batch.total_duration
            stats['current_batch_segments'] = len(self.current_batch.segments)
        else:
            stats['current_batch_duration'] = 0.0
            stats['current_batch_segments'] = 0
        
        return stats
    
    def force_finalize_current_batch(self):
        """Force la finalisation du batch actuel."""
        if self.current_batch:
            self.logger.info("🔄 Finalisation forcée du batch actuel")
            self._finalize_current_batch()
