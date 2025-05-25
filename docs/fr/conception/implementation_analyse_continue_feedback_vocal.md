# Implémentation du Service d'Analyse Continue et Feedback Vocal

Ce document détaille l'implémentation du service d'analyse continue et du feedback vocal pour Peer, permettant une assistance omnisciente en temps réel pendant le développement.

## 1. Service d'Analyse Continue

```python
# src/peer/domain/services/continuous_analysis_service.py

import os
import time
import threading
import queue
from typing import Dict, List, Optional, Any, Callable

from peer.domain.ports.code_analysis_port import CodeAnalysisPort
from peer.domain.ports.ui_port import UIPort
from peer.domain.ports.tts_port import TTSPort
from peer.domain.models.code_context import CodeContext, CodeIssue
from peer.domain.models.session import Session

class ContinuousAnalysisService:
    """Service for continuous code analysis and feedback."""
    
    def __init__(
        self,
        code_analysis_port: CodeAnalysisPort,
        ui_port: UIPort,
        tts_port: TTSPort,
        logger: Any
    ):
        """Initialize the continuous analysis service.
        
        Args:
            code_analysis_port: Port for code analysis
            ui_port: Port for UI interactions
            tts_port: Port for text-to-speech
            logger: Logger instance
        """
        self.code_analysis_port = code_analysis_port
        self.ui_port = ui_port
        self.tts_port = tts_port
        self.logger = logger
        
        # Analysis settings
        self.analysis_interval = 2.0  # seconds
        self.analysis_enabled = True
        self.voice_feedback_enabled = True
        self.notification_enabled = True
        self.cooldown_period = 5.0  # seconds
        
        # Analysis state
        self.file_queue = queue.Queue()
        self.last_analysis_time: Dict[str, float] = {}
        self.last_feedback_time: Dict[str, float] = {}
        self.file_contexts: Dict[str, CodeContext] = {}
        self.running = False
        self.analysis_thread: Optional[threading.Thread] = None
        
        # Callbacks
        self.on_issue_found: List[Callable[[str, CodeIssue], None]] = []
        self.on_analysis_complete: List[Callable[[str, CodeContext], None]] = []
        
    def initialize(self) -> None:
        """Initialize the continuous analysis service."""
        self.running = True
        self.analysis_thread = threading.Thread(
            target=self._analysis_worker,
            daemon=True,
            name="ContinuousAnalysisThread"
        )
        self.analysis_thread.start()
        self.logger.info("Continuous analysis service initialized")
        
    def shutdown(self) -> None:
        """Shutdown the continuous analysis service."""
        self.running = False
        if self.analysis_thread and self.analysis_thread.is_alive():
            self.analysis_thread.join(timeout=2.0)
        self.logger.info("Continuous analysis service shutdown")
        
    def queue_file_for_analysis(self, file_path: str, content: str, session: Session) -> None:
        """Queue a file for analysis.
        
        Args:
            file_path: Path to the file
            content: File content
            session: Current session
        """
        # Skip if analysis is disabled
        if not self.analysis_enabled:
            return
            
        # Skip if file was recently analyzed
        current_time = time.time()
        if file_path in self.last_analysis_time:
            time_since_last_analysis = current_time - self.last_analysis_time[file_path]
            if time_since_last_analysis < self.analysis_interval:
                return
                
        # Queue file for analysis
        self.file_queue.put({
            "file_path": file_path,
            "content": content,
            "session": session,
            "timestamp": current_time
        })
        self.logger.debug(f"Queued file for analysis: {file_path}")
        
    def _analysis_worker(self) -> None:
        """Worker thread for continuous analysis."""
        while self.running:
            try:
                # Get file from queue
                try:
                    file_data = self.file_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                    
                file_path = file_data["file_path"]
                content = file_data["content"]
                session = file_data["session"]
                timestamp = file_data["timestamp"]
                
                # Skip if newer version is in queue
                skip = False
                for _ in range(self.file_queue.qsize()):
                    try:
                        next_file = self.file_queue.get_nowait()
                        if next_file["file_path"] == file_path and next_file["timestamp"] > timestamp:
                            skip = True
                        self.file_queue.put(next_file)  # Put it back
                    except queue.Empty:
                        break
                        
                if skip:
                    continue
                    
                # Analyze file
                self.logger.debug(f"Analyzing file: {file_path}")
                code_context = self.code_analysis_port.analyze_file(file_path, content)
                
                # Update file context
                self.file_contexts[file_path] = code_context
                self.last_analysis_time[file_path] = time.time()
                
                # Notify callbacks
                for callback in self.on_analysis_complete:
                    callback(file_path, code_context)
                    
                # Check for issues
                if code_context.issues:
                    self._handle_issues(file_path, code_context, session)
                    
                # Mark as done
                self.file_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error in analysis worker: {str(e)}")
                
    def _handle_issues(self, file_path: str, code_context: CodeContext, session: Session) -> None:
        """Handle issues found in a file.
        
        Args:
            file_path: Path to the file
            code_context: Code context with issues
            session: Current session
        """
        # Skip if cooldown period hasn't elapsed
        current_time = time.time()
        if file_path in self.last_feedback_time:
            time_since_last_feedback = current_time - self.last_feedback_time[file_path]
            if time_since_last_feedback < self.cooldown_period:
                return
                
        # Count issues by severity
        severity_counts = {
            "error": 0,
            "warning": 0,
            "info": 0
        }
        
        for issue in code_context.issues:
            severity = issue.severity.lower()
            if severity in severity_counts:
                severity_counts[severity] += 1
                
            # Notify callbacks
            for callback in self.on_issue_found:
                callback(file_path, issue)
                
        # Generate feedback message
        feedback = self._generate_feedback_message(file_path, severity_counts, code_context.issues)
        
        # Provide feedback
        if feedback:
            self._provide_feedback(file_path, feedback, session)
            self.last_feedback_time[file_path] = current_time
            
    def _generate_feedback_message(
        self,
        file_path: str,
        severity_counts: Dict[str, int],
        issues: List[CodeIssue]
    ) -> Optional[str]:
        """Generate feedback message for issues.
        
        Args:
            file_path: Path to the file
            severity_counts: Count of issues by severity
            issues: List of issues
            
        Returns:
            Feedback message or None if no issues
        """
        # Skip if no issues
        if sum(severity_counts.values()) == 0:
            return None
            
        # Generate message
        filename = os.path.basename(file_path)
        message_parts = [f"Dans {filename}, j'ai détecté:"]
        
        if severity_counts["error"] > 0:
            message_parts.append(f"{severity_counts['error']} erreur{'s' if severity_counts['error'] > 1 else ''}")
            
        if severity_counts["warning"] > 0:
            message_parts.append(f"{severity_counts['warning']} avertissement{'s' if severity_counts['warning'] > 1 else ''}")
            
        if severity_counts["info"] > 0:
            message_parts.append(f"{severity_counts['info']} suggestion{'s' if severity_counts['info'] > 1 else ''}")
            
        # Add most critical issue
        critical_issues = [i for i in issues if i.severity.lower() == "error"]
        if critical_issues:
            issue = critical_issues[0]
            message_parts.append(f"Problème critique ligne {issue.line}: {issue.message}")
        elif severity_counts["warning"] > 0:
            warning_issues = [i for i in issues if i.severity.lower() == "warning"]
            if warning_issues:
                issue = warning_issues[0]
                message_parts.append(f"Avertissement ligne {issue.line}: {issue.message}")
                
        return " ".join(message_parts)
        
    def _provide_feedback(self, file_path: str, feedback: str, session: Session) -> None:
        """Provide feedback to the user.
        
        Args:
            file_path: Path to the file
            feedback: Feedback message
            session: Current session
        """
        # Voice feedback
        if self.voice_feedback_enabled:
            self.tts_port.speak(feedback)
            
        # UI notification
        if self.notification_enabled:
            self.ui_port.display_notification(feedback, "continuous_analysis")
            
        # Log feedback
        self.logger.info(f"Feedback provided: {feedback}")
        
    def register_issue_callback(self, callback: Callable[[str, CodeIssue], None]) -> None:
        """Register a callback for when an issue is found.
        
        Args:
            callback: Callback function
        """
        self.on_issue_found.append(callback)
        
    def register_analysis_callback(self, callback: Callable[[str, CodeContext], None]) -> None:
        """Register a callback for when analysis is complete.
        
        Args:
            callback: Callback function
        """
        self.on_analysis_complete.append(callback)
        
    def set_analysis_interval(self, interval: float) -> None:
        """Set the analysis interval.
        
        Args:
            interval: Interval in seconds
        """
        self.analysis_interval = max(0.5, interval)
        
    def set_cooldown_period(self, period: float) -> None:
        """Set the feedback cooldown period.
        
        Args:
            period: Period in seconds
        """
        self.cooldown_period = max(1.0, period)
        
    def enable_analysis(self) -> None:
        """Enable continuous analysis."""
        self.analysis_enabled = True
        
    def disable_analysis(self) -> None:
        """Disable continuous analysis."""
        self.analysis_enabled = False
        
    def enable_voice_feedback(self) -> None:
        """Enable voice feedback."""
        self.voice_feedback_enabled = True
        
    def disable_voice_feedback(self) -> None:
        """Disable voice feedback."""
        self.voice_feedback_enabled = False
        
    def enable_notifications(self) -> None:
        """Enable UI notifications."""
        self.notification_enabled = True
        
    def disable_notifications(self) -> None:
        """Disable UI notifications."""
        self.notification_enabled = False
```

## 2. Adaptateur Text-to-Speech (Piper)

```python
# src/peer/infrastructure/adapters/tts/piper_adapter.py

import os
import subprocess
import tempfile
import threading
import queue
from typing import Optional, Any, List, Dict

from peer.domain.ports.tts_port import TTSPort

class PiperTTSAdapter(TTSPort):
    """Adapter for Piper text-to-speech engine."""
    
    def __init__(self, logger: Any, config: Dict[str, Any]):
        """Initialize the Piper TTS adapter.
        
        Args:
            logger: Logger instance
            config: Configuration dictionary
        """
        self.logger = logger
        self.config = config
        
        # Piper configuration
        self.piper_path = config.get("piper_path", "piper")
        self.model_path = config.get("model_path", "")
        self.voice = config.get("voice", "fr_FR-siwis-medium")
        self.output_device = config.get("output_device", "default")
        
        # Speech queue
        self.speech_queue = queue.Queue()
        self.current_speech: Optional[subprocess.Popen] = None
        self.speech_thread: Optional[threading.Thread] = None
        self.running = False
        
        # Ensure model exists
        self._ensure_model()
        
    def initialize(self) -> None:
        """Initialize the TTS adapter."""
        self.running = True
        self.speech_thread = threading.Thread(
            target=self._speech_worker,
            daemon=True,
            name="PiperTTSThread"
        )
        self.speech_thread.start()
        self.logger.info("Piper TTS adapter initialized")
        
    def shutdown(self) -> None:
        """Shutdown the TTS adapter."""
        self.running = False
        if self.current_speech:
            self.current_speech.terminate()
            self.current_speech = None
            
        if self.speech_thread and self.speech_thread.is_alive():
            self.speech_thread.join(timeout=2.0)
            
        self.logger.info("Piper TTS adapter shutdown")
        
    def speak(self, text: str, priority: int = 0) -> None:
        """Speak text using Piper.
        
        Args:
            text: Text to speak
            priority: Priority (0 = normal, 1 = high)
        """
        self.speech_queue.put({
            "text": text,
            "priority": priority
        })
        
    def is_speaking(self) -> bool:
        """Check if currently speaking.
        
        Returns:
            True if speaking, False otherwise
        """
        return self.current_speech is not None
        
    def stop_speaking(self) -> None:
        """Stop current speech."""
        if self.current_speech:
            self.current_speech.terminate()
            self.current_speech = None
            
    def _ensure_model(self) -> None:
        """Ensure Piper model exists."""
        if not self.model_path:
            # Use default model path
            home_dir = os.path.expanduser("~")
            self.model_path = os.path.join(home_dir, ".local", "share", "piper", "voices", f"{self.voice}.onnx")
            
        # Check if model exists
        if not os.path.exists(self.model_path):
            self.logger.warning(f"Piper model not found: {self.model_path}")
            self.logger.info("Downloading Piper model...")
            
            # Create directory
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            
            # Download model
            try:
                subprocess.run(
                    ["pip", "install", "piper-tts"],
                    check=True,
                    capture_output=True
                )
                
                subprocess.run(
                    ["piper-download", "--voices", self.voice],
                    check=True,
                    capture_output=True
                )
                
                self.logger.info(f"Piper model downloaded: {self.model_path}")
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Failed to download Piper model: {str(e)}")
                self.logger.error(f"Output: {e.output.decode('utf-8')}")
                self.logger.error(f"Error: {e.stderr.decode('utf-8')}")
                
    def _speech_worker(self) -> None:
        """Worker thread for speech queue."""
        while self.running:
            try:
                # Get speech from queue
                try:
                    speech_data = self.speech_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                    
                text = speech_data["text"]
                priority = speech_data["priority"]
                
                # Skip if empty text
                if not text:
                    self.speech_queue.task_done()
                    continue
                    
                # Stop current speech if higher priority
                if self.current_speech and priority > 0:
                    self.current_speech.terminate()
                    self.current_speech = None
                    
                # Wait for current speech to finish
                while self.current_speech:
                    if self.current_speech.poll() is not None:
                        self.current_speech = None
                    else:
                        time.sleep(0.1)
                        
                # Speak text
                self._speak_text(text)
                
                # Mark as done
                self.speech_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error in speech worker: {str(e)}")
                
    def _speak_text(self, text: str) -> None:
        """Speak text using Piper.
        
        Args:
            text: Text to speak
        """
        try:
            # Create temporary file for text
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
                f.write(text)
                text_file = f.name
                
            # Create command
            cmd = [
                self.piper_path,
                "--model", self.model_path,
                "--output-raw", "|",
                "aplay", "-r", "22050", "-f", "S16_LE", "-D", self.output_device
            ]
            
            # Start process
            self.current_speech = subprocess.Popen(
                cmd,
                stdin=open(text_file, "r"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True
            )
            
            # Wait for process to finish
            stdout, stderr = self.current_speech.communicate()
            
            # Check for errors
            if self.current_speech.returncode != 0:
                self.logger.error(f"Piper error: {stderr.decode('utf-8')}")
                
            # Clean up
            self.current_speech = None
            os.unlink(text_file)
            
        except Exception as e:
            self.logger.error(f"Error speaking text: {str(e)}")
            if self.current_speech:
                self.current_speech = None
```

## 3. Adaptateur Text-to-Speech (pyttsx3)

```python
# src/peer/infrastructure/adapters/tts/pyttsx3_adapter.py

import threading
import queue
import time
from typing import Optional, Any, Dict

import pyttsx3

from peer.domain.ports.tts_port import TTSPort

class Pyttsx3Adapter(TTSPort):
    """Adapter for pyttsx3 text-to-speech engine."""
    
    def __init__(self, logger: Any, config: Dict[str, Any]):
        """Initialize the pyttsx3 adapter.
        
        Args:
            logger: Logger instance
            config: Configuration dictionary
        """
        self.logger = logger
        self.config = config
        
        # pyttsx3 configuration
        self.rate = config.get("rate", 175)
        self.volume = config.get("volume", 1.0)
        self.voice = config.get("voice", "french")
        
        # Initialize engine
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", self.rate)
        self.engine.setProperty("volume", self.volume)
        
        # Set voice
        voices = self.engine.getProperty("voices")
        for voice in voices:
            if self.voice.lower() in voice.name.lower() or self.voice.lower() in voice.id.lower():
                self.engine.setProperty("voice", voice.id)
                break
                
        # Speech queue
        self.speech_queue = queue.Queue()
        self.speaking = False
        self.speech_thread: Optional[threading.Thread] = None
        self.running = False
        
    def initialize(self) -> None:
        """Initialize the TTS adapter."""
        self.running = True
        self.speech_thread = threading.Thread(
            target=self._speech_worker,
            daemon=True,
            name="Pyttsx3Thread"
        )
        self.speech_thread.start()
        self.logger.info("pyttsx3 adapter initialized")
        
    def shutdown(self) -> None:
        """Shutdown the TTS adapter."""
        self.running = False
        self.engine.stop()
        
        if self.speech_thread and self.speech_thread.is_alive():
            self.speech_thread.join(timeout=2.0)
            
        self.logger.info("pyttsx3 adapter shutdown")
        
    def speak(self, text: str, priority: int = 0) -> None:
        """Speak text using pyttsx3.
        
        Args:
            text: Text to speak
            priority: Priority (0 = normal, 1 = high)
        """
        self.speech_queue.put({
            "text": text,
            "priority": priority
        })
        
    def is_speaking(self) -> bool:
        """Check if currently speaking.
        
        Returns:
            True if speaking, False otherwise
        """
        return self.speaking
        
    def stop_speaking(self) -> None:
        """Stop current speech."""
        if self.speaking:
            self.engine.stop()
            self.speaking = False
            
    def _speech_worker(self) -> None:
        """Worker thread for speech queue."""
        while self.running:
            try:
                # Get speech from queue
                try:
                    speech_data = self.speech_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                    
                text = speech_data["text"]
                priority = speech_data["priority"]
                
                # Skip if empty text
                if not text:
                    self.speech_queue.task_done()
                    continue
                    
                # Stop current speech if higher priority
                if self.speaking and priority > 0:
                    self.engine.stop()
                    self.speaking = False
                    
                # Wait for current speech to finish
                while self.speaking:
                    time.sleep(0.1)
                    
                # Speak text
                self._speak_text(text)
                
                # Mark as done
                self.speech_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error in speech worker: {str(e)}")
                
    def _speak_text(self, text: str) -> None:
        """Speak text using pyttsx3.
        
        Args:
            text: Text to speak
        """
        try:
            self.speaking = True
            
            # Define callback
            def on_done(name, completed):
                self.speaking = False
                
            # Set callback
            self.engine.connect("finished-utterance", on_done)
            
            # Speak
            self.engine.say(text)
            self.engine.runAndWait()
            
        except Exception as e:
            self.logger.error(f"Error speaking text: {str(e)}")
            self.speaking = False
```

## 4. Intégration avec le Service Peer Assistant

```python
# src/peer/domain/services/peer_assistant_service.py

import os
import time
import threading
import queue
from typing import Dict, List, Optional, Any, Callable

from peer.domain.ports.llm_port import LLMPort
from peer.domain.ports.tts_port import TTSPort
from peer.domain.ports.ui_port import UIPort
from peer.domain.ports.vcs_port import VCSPort
from peer.domain.services.code_analysis_service import CodeAnalysisService
from peer.domain.services.continuous_analysis_service import ContinuousAnalysisService
from peer.domain.models.code_context import CodeContext, CodeIssue
from peer.domain.models.session import Session

class PeerAssistantService:
    """Service for the Peer Assistant omniscient capabilities."""
    
    def __init__(
        self,
        llm_port: LLMPort,
        tts_port: TTSPort,
        code_analysis_service: CodeAnalysisService,
        continuous_analysis_service: ContinuousAnalysisService,
        ui_port: UIPort,
        vcs_port: VCSPort,
        logger: Any
    ):
        """Initialize the Peer Assistant service.
        
        Args:
            llm_port: Port for LLM interactions
            tts_port: Port for text-to-speech
            code_analysis_service: Service for code analysis
            continuous_analysis_service: Service for continuous analysis
            ui_port: Port for UI interactions
            vcs_port: Port for VCS interactions
            logger: Logger instance
        """
        self.llm_port = llm_port
        self.tts_port = tts_port
        self.code_analysis_service = code_analysis_service
        self.continuous_analysis_service = continuous_analysis_service
        self.ui_port = ui_port
        self.vcs_port = vcs_port
        self.logger = logger
        
        # Assistant settings
        self.feedback_enabled = True
        self.voice_feedback_enabled = True
        self.feedback_cooldown = 5  # seconds
        self.suggestion_confidence_threshold = 0.7
        
        # Assistant state
        self.event_queue = queue.Queue()
        self.running = False
        self.assistant_thread: Optional[threading.Thread] = None
        self.last_feedback_time: Dict[str, float] = {}
        
        # Register callbacks
        self.continuous_analysis_service.register_issue_callback(self._on_issue_found)
        self.continuous_analysis_service.register_analysis_callback(self._on_analysis_complete)
        
    def initialize(self) -> None:
        """Initialize the Peer Assistant service."""
        self.running = True
        self.assistant_thread = threading.Thread(
            target=self._assistant_worker,
            daemon=True,
            name="PeerAssistantThread"
        )
        self.assistant_thread.start()
        self.logger.info("Peer Assistant service initialized")
        
    def shutdown(self) -> None:
        """Shutdown the Peer Assistant service."""
        self.running = False
        if self.assistant_thread and self.assistant_thread.is_alive():
            self.assistant_thread.join(timeout=2.0)
        self.logger.info("Peer Assistant service shutdown")
        
    def add_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Add an event to the queue.
        
        Args:
            event_type: Type of event
            data: Event data
        """
        self.event_queue.put({
            "type": event_type,
            "data": data,
            "timestamp": time.time()
        })
        
    def provide_proactive_assistance(self, session: Session) -> None:
        """Provide proactive assistance based on session context.
        
        Args:
            session: Current session
        """
        self.add_event("proactive_assistance", {
            "session_id": session.id,
            "context": session.context
        })
        
    def _assistant_worker(self) -> None:
        """Worker thread for the assistant."""
        while self.running:
            try:
                # Get event from queue
                try:
                    event = self.event_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                    
                # Process event
                event_type = event["type"]
                data = event["data"]
                
                if event_type == "file_change":
                    self._handle_file_change_event(data)
                elif event_type == "command":
                    self._handle_command_event(data)
                elif event_type == "feedback":
                    self._handle_feedback_event(data)
                elif event_type == "proactive_assistance":
                    self._handle_proactive_assistance_event(data)
                    
                # Mark as done
                self.event_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error in assistant worker: {str(e)}")
                
    def _handle_file_change_event(self, data: Dict[str, Any]) -> None:
        """Handle file change event.
        
        Args:
            data: Event data
        """
        file_path = data["file_path"]
        content = data["content"]
        session_id = data["session_id"]
        
        # Skip if feedback is disabled
        if not self.feedback_enabled:
            return
            
        # Skip if file was recently analyzed
        current_time = time.time()
        if file_path in self.last_feedback_time:
            time_since_last_feedback = current_time - self.last_feedback_time[file_path]
            if time_since_last_feedback < self.feedback_cooldown:
                return
                
        # Analyze file
        code_context = self.code_analysis_service.analyze_file(file_path, content)
        
        # Generate feedback
        feedback = self._generate_feedback(file_path, code_context)
        
        # Provide feedback
        if feedback:
            # Update last feedback time
            self.last_feedback_time[file_path] = current_time
            
            # Voice feedback
            if self.voice_feedback_enabled:
                self.tts_port.speak(feedback)
                
            # UI notification
            self.ui_port.display_notification(feedback, "peer_assistant")
            
    def _handle_command_event(self, data: Dict[str, Any]) -> None:
        """Handle command event.
        
        Args:
            data: Event data
        """
        command = data["command"]
        args = data["args"]
        session_id = data["session_id"]
        
        if command == "enable_feedback":
            self.feedback_enabled = True
            self.continuous_analysis_service.enable_analysis()
            self.ui_port.display_notification("Feedback enabled", "peer_assistant")
            
        elif command == "disable_feedback":
            self.feedback_enabled = False
            self.continuous_analysis_service.disable_analysis()
            self.ui_port.display_notification("Feedback disabled", "peer_assistant")
            
        elif command == "enable_voice":
            self.voice_feedback_enabled = True
            self.continuous_analysis_service.enable_voice_feedback()
            self.ui_port.display_notification("Voice feedback enabled", "peer_assistant")
            
        elif command == "disable_voice":
            self.voice_feedback_enabled = False
            self.continuous_analysis_service.disable_voice_feedback()
            self.ui_port.display_notification("Voice feedback disabled", "peer_assistant")
            
        elif command == "set_cooldown":
            if args and len(args) > 0:
                try:
                    cooldown = float(args[0])
                    self.feedback_cooldown = max(1.0, cooldown)
                    self.continuous_analysis_service.set_cooldown_period(self.feedback_cooldown)
                    self.ui_port.display_notification(f"Feedback cooldown set to {self.feedback_cooldown} seconds", "peer_assistant")
                except ValueError:
                    self.ui_port.display_notification(f"Invalid cooldown value: {args[0]}", "peer_assistant")
                    
    def _handle_feedback_event(self, data: Dict[str, Any]) -> None:
        """Handle feedback event.
        
        Args:
            data: Event data
        """
        feedback_type = data["feedback_type"]
        details = data["details"]
        session_id = data["session_id"]
        
        if feedback_type == "helpful":
            # User found feedback helpful
            pass
            
        elif feedback_type == "not_helpful":
            # User did not find feedback helpful
            pass
            
        elif feedback_type == "too_frequent":
            # User found feedback too frequent
            self.feedback_cooldown *= 2
            self.continuous_analysis_service.set_cooldown_period(self.feedback_cooldown)
            
        elif feedback_type == "too_infrequent":
            # User found feedback too infrequent
            self.feedback_cooldown = max(1.0, self.feedback_cooldown / 2)
            self.continuous_analysis_service.set_cooldown_period(self.feedback_cooldown)
            
    def _handle_proactive_assistance_event(self, data: Dict[str, Any]) -> None:
        """Handle proactive assistance event.
        
        Args:
            data: Event data
        """
        session_id = data["session_id"]
        context = data["context"]
        
        # TODO: Implement proactive assistance based on context
        
    def _generate_feedback(self, file_path: str, code_context: CodeContext) -> Optional[str]:
        """Generate feedback for a file.
        
        Args:
            file_path: Path to the file
            code_context: Code context with issues
            
        Returns:
            Feedback message or None if no issues
        """
        # Skip if no issues
        if not code_context.issues:
            return None
            
        # Count issues by severity
        severity_counts = {
            "error": 0,
            "warning": 0,
            "info": 0
        }
        
        for issue in code_context.issues:
            severity = issue.severity.lower()
            if severity in severity_counts:
                severity_counts[severity] += 1
                
        # Generate message
        filename = os.path.basename(file_path)
        message_parts = [f"Dans {filename}, j'ai détecté:"]
        
        if severity_counts["error"] > 0:
            message_parts.append(f"{severity_counts['error']} erreur{'s' if severity_counts['error'] > 1 else ''}")
            
        if severity_counts["warning"] > 0:
            message_parts.append(f"{severity_counts['warning']} avertissement{'s' if severity_counts['warning'] > 1 else ''}")
            
        if severity_counts["info"] > 0:
            message_parts.append(f"{severity_counts['info']} suggestion{'s' if severity_counts['info'] > 1 else ''}")
            
        # Add most critical issue
        critical_issues = [i for i in code_context.issues if i.severity.lower() == "error"]
        if critical_issues:
            issue = critical_issues[0]
            message_parts.append(f"Problème critique ligne {issue.line}: {issue.message}")
        elif severity_counts["warning"] > 0:
            warning_issues = [i for i in code_context.issues if i.severity.lower() == "warning"]
            if warning_issues:
                issue = warning_issues[0]
                message_parts.append(f"Avertissement ligne {issue.line}: {issue.message}")
                
        return " ".join(message_parts)
        
    def _generate_suggestions(
        self,
        session: Session,
        file_path: str,
        code_context: CodeContext
    ) -> List[Dict[str, Any]]:
        """Generate suggestions for a file.
        
        Args:
            session: Current session
            file_path: Path to the file
            code_context: Code context
            
        Returns:
            List of suggestions
        """
        suggestions = []
        
        # Check if plugin manager is available
        plugin_manager = session.context.get("plugin_manager")
        if plugin_manager:
            # Get suggestions from plugins
            plugin_suggestions = plugin_manager.call_hook(
                "peer_suggest_improvements",
                file_path=file_path,
                content=code_context.content,
                context={"current_mode": session.current_mode}
            )
            
            if plugin_suggestions:
                suggestions.extend(plugin_suggestions)
                
        # If no suggestions from plugins, use LLM
        if not suggestions:
            # Prepare prompt
            prompt = f"""
            Analyze the following code and suggest improvements.
            Focus on: {', '.join(session.context.get('focus_areas', ['code_quality', 'readability', 'performance']))}
            Current mode: {session.current_mode}
            
            File: {os.path.basename(file_path)}
            
            ```
            {code_context.content}
            ```
            
            Provide suggestions in the following format:
            1. Line X-Y: [type] Description
            2. Line Z: [type] Description
            
            Where type is one of: refactoring, style, performance, security, bug
            """
            
            # Generate suggestions
            response = self.llm_port.generate_text(prompt)
            
            # Parse suggestions
            if response:
                lines = response.strip().split("\n")
                for line in lines:
                    line = line.strip()
                    if not line or not line[0].isdigit():
                        continue
                        
                    # Parse line
                    try:
                        # Extract line numbers
                        line_part = line.split(":")[0].split(".")[1].strip()
                        if "-" in line_part:
                            line_start, line_end = map(int, line_part.split("Line ")[1].split("-"))
                        else:
                            line_start = line_end = int(line_part.split("Line ")[1])
                            
                        # Extract type
                        type_part = line.split("[")[1].split("]")[0].strip()
                        
                        # Extract description
                        description = line.split("]")[1].strip()
                        
                        # Add suggestion
                        suggestions.append({
                            "line_start": line_start,
                            "line_end": line_end,
                            "suggestion_type": type_part,
                            "description": description,
                            "confidence": 0.8
                        })
                    except Exception as e:
                        self.logger.error(f"Error parsing suggestion: {line} - {str(e)}")
                        
        # Filter suggestions by confidence
        suggestions = [s for s in suggestions if s.get("confidence", 0) >= self.suggestion_confidence_threshold]
        
        return suggestions
        
    def _on_issue_found(self, file_path: str, issue: CodeIssue) -> None:
        """Callback for when an issue is found.
        
        Args:
            file_path: Path to the file
            issue: Code issue
        """
        # Log issue
        self.logger.debug(f"Issue found in {file_path}: {issue.message}")
        
    def _on_analysis_complete(self, file_path: str, code_context: CodeContext) -> None:
        """Callback for when analysis is complete.
        
        Args:
            file_path: Path to the file
            code_context: Code context
        """
        # Log completion
        self.logger.debug(f"Analysis complete for {file_path}")
```

## 5. Intégration avec l'Interface Utilisateur Textuelle (TUI)

```python
# src/peer/interfaces/tui/tui_interface.py

import os
import threading
import asyncio
import time
from typing import Dict, List, Optional, Any, Callable

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Input, Button, Tree, Label, Markdown
from textual.widgets.tree import TreeNode
from textual.reactive import reactive
from textual.message import Message
from textual.binding import Binding

from peer.domain.ports.ui_port import UIPort
from peer.application.peer_application import PeerApplication

class NotificationArea(Static):
    """Widget for displaying notifications."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.notifications = []
        
    def add_notification(self, text: str, source: str) -> None:
        """Add a notification.
        
        Args:
            text: Notification text
            source: Notification source
        """
        self.notifications.append({
            "text": text,
            "source": source,
            "timestamp": time.time()
        })
        
        # Limit to 10 notifications
        if len(self.notifications) > 10:
            self.notifications.pop(0)
            
        # Update content
        self.update_content()
        
    def update_content(self) -> None:
        """Update widget content."""
        if not self.notifications:
            self.update("Aucune notification")
            return
            
        content = []
        for notification in reversed(self.notifications):
            timestamp = time.strftime("%H:%M:%S", time.localtime(notification["timestamp"]))
            source = notification["source"]
            text = notification["text"]
            content.append(f"[{timestamp}] [{source}] {text}")
            
        self.update("\n".join(content))
        
class CodeEditor(Static):
    """Widget for editing code."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file_path = ""
        self.content = ""
        self.issues = []
        
    def set_file(self, file_path: str, content: str) -> None:
        """Set file content.
        
        Args:
            file_path: Path to the file
            content: File content
        """
        self.file_path = file_path
        self.content = content
        self.update_content()
        
    def set_issues(self, issues: List[Dict[str, Any]]) -> None:
        """Set code issues.
        
        Args:
            issues: List of issues
        """
        self.issues = issues
        self.update_content()
        
    def update_content(self) -> None:
        """Update widget content."""
        if not self.file_path:
            self.update("Aucun fichier ouvert")
            return
            
        # Format content with line numbers
        lines = self.content.split("\n")
        content = []
        
        for i, line in enumerate(lines):
            line_number = i + 1
            
            # Check for issues on this line
            line_issues = [issue for issue in self.issues if issue["line"] == line_number]
            
            if line_issues:
                # Add issue markers
                markers = []
                for issue in line_issues:
                    severity = issue["severity"]
                    if severity == "error":
                        markers.append("🔴")
                    elif severity == "warning":
                        markers.append("🟠")
                    else:
                        markers.append("🔵")
                        
                content.append(f"{line_number:4d} {' '.join(markers)} {line}")
            else:
                content.append(f"{line_number:4d}    {line}")
                
        self.update("\n".join(content))
        
class FileTree(Tree):
    """Widget for displaying file tree."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.root_path = ""
        
    def set_root(self, root_path: str) -> None:
        """Set root path.
        
        Args:
            root_path: Root path
        """
        self.root_path = root_path
        self.clear()
        self.root.label = os.path.basename(root_path)
        self.populate_tree(self.root, root_path)
        
    def populate_tree(self, node: TreeNode, path: str) -> None:
        """Populate tree node.
        
        Args:
            node: Tree node
            path: Path to populate
        """
        try:
            # List directory
            items = sorted(os.listdir(path))
            
            # Add directories first
            for item in items:
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path) and not item.startswith("."):
                    child = node.add(item, expand=False)
                    self.populate_tree(child, item_path)
                    
            # Add files
            for item in items:
                item_path = os.path.join(path, item)
                if os.path.isfile(item_path) and not item.startswith("."):
                    node.add_leaf(item)
        except Exception as e:
            node.add_leaf(f"Error: {str(e)}")
            
class PeerTUI(App, UIPort):
    """Textual UI for Peer."""
    
    BINDINGS = [
        Binding("q", "quit", "Quitter"),
        Binding("o", "open_file", "Ouvrir"),
        Binding("s", "save_file", "Sauvegarder"),
        Binding("r", "refresh", "Rafraîchir"),
        Binding("f", "toggle_feedback", "Activer/Désactiver Feedback"),
        Binding("v", "toggle_voice", "Activer/Désactiver Voix"),
        Binding("h", "toggle_help", "Aide")
    ]
    
    def __init__(self, peer_app: PeerApplication, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.peer_app = peer_app
        self.session_id = None
        self.feedback_enabled = True
        self.voice_enabled = True
        
    def compose(self) -> ComposeResult:
        """Compose the UI."""
        yield Header(show_clock=True)
        
        with Container():
            with Horizontal():
                with Vertical(id="sidebar", classes="sidebar"):
                    yield Label("Projet")
                    yield FileTree("Projet", id="file_tree")
                    
                with Vertical(id="main_area", classes="main"):
                    yield Label("Éditeur", id="editor_label")
                    yield CodeEditor(id="code_editor", classes="editor")
                    
                    yield Label("Notifications", id="notifications_label")
                    yield NotificationArea(id="notifications", classes="notifications")
                    
                    with Horizontal(id="command_area", classes="command"):
                        yield Input(placeholder="Entrez une commande...", id="command_input")
                        yield Button("Exécuter", id="execute_button")
                        
        yield Footer()
        
    def on_mount(self) -> None:
        """Event handler called when the app is mounted."""
        # Initialize session
        self.initialize_session()
        
        # Set up event handlers
        self.query_one("#execute_button").on_click(self.on_execute_command)
        self.query_one("#command_input").on_submit(self.on_execute_command)
        self.query_one("#file_tree").on_tree_node_selected(self.on_file_selected)
        
    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()
        
    def action_open_file(self) -> None:
        """Open a file."""
        # TODO: Implement file dialog
        pass
        
    def action_save_file(self) -> None:
        """Save the current file."""
        # TODO: Implement file saving
        pass
        
    def action_refresh(self) -> None:
        """Refresh the UI."""
        self.refresh_file_tree()
        
    def action_toggle_feedback(self) -> None:
        """Toggle feedback."""
        self.feedback_enabled = not self.feedback_enabled
        
        if self.session_id:
            command = "enable_feedback" if self.feedback_enabled else "disable_feedback"
            self.peer_app.execute_command(self.session_id, command, [])
            
        self.display_notification(
            f"Feedback {'activé' if self.feedback_enabled else 'désactivé'}",
            "system"
        )
        
    def action_toggle_voice(self) -> None:
        """Toggle voice feedback."""
        self.voice_enabled = not self.voice_enabled
        
        if self.session_id:
            command = "enable_voice" if self.voice_enabled else "disable_voice"
            self.peer_app.execute_command(self.session_id, command, [])
            
        self.display_notification(
            f"Feedback vocal {'activé' if self.voice_enabled else 'désactivé'}",
            "system"
        )
        
    def action_toggle_help(self) -> None:
        """Toggle help."""
        # TODO: Implement help dialog
        pass
        
    def initialize_session(self) -> None:
        """Initialize session."""
        try:
            # Get current directory
            current_dir = os.getcwd()
            
            # Initialize session
            session_data = self.peer_app.initialize_session(current_dir)
            self.session_id = session_data["id"]
            
            # Set file tree root
            self.query_one("#file_tree").set_root(current_dir)
            
            # Display notification
            self.display_notification(f"Session initialisée: {self.session_id}", "system")
            
        except Exception as e:
            self.display_notification(f"Erreur lors de l'initialisation de la session: {str(e)}", "error")
            
    def refresh_file_tree(self) -> None:
        """Refresh file tree."""
        if self.session_id:
            current_dir = self.peer_app.get_session_data(self.session_id)["project_root"]
            self.query_one("#file_tree").set_root(current_dir)
            
    def on_execute_command(self, event: Any) -> None:
        """Execute command.
        
        Args:
            event: Button click or input submit event
        """
        if not self.session_id:
            self.display_notification("Aucune session active", "error")
            return
            
        # Get command
        command_input = self.query_one("#command_input")
        command_text = command_input.value
        
        if not command_text:
            return
            
        # Clear input
        command_input.value = ""
        
        # Execute command
        try:
            result = self.peer_app.execute_command(self.session_id, "query", [command_text])
            
            # Display result
            if result:
                self.display_notification(f"Résultat: {result}", "command")
                
        except Exception as e:
            self.display_notification(f"Erreur lors de l'exécution de la commande: {str(e)}", "error")
            
    def on_file_selected(self, event: Any) -> None:
        """Handle file selection.
        
        Args:
            event: Tree node selected event
        """
        if not self.session_id:
            return
            
        # Get selected node
        node = event.node
        
        # Skip if not a leaf
        if not node.is_leaf:
            return
            
        # Get file path
        file_path = self._get_file_path(node)
        
        # Read file
        try:
            with open(file_path, "r") as f:
                content = f.read()
                
            # Set file in editor
            self.query_one("#code_editor").set_file(file_path, content)
            
            # Analyze file
            issues = self.peer_app.analyze_code_snippet(self.session_id, file_path, content)
            
            # Set issues in editor
            self.query_one("#code_editor").set_issues(issues)
            
            # Handle file change
            self.peer_app.handle_file_change(self.session_id, file_path, content)
            
        except Exception as e:
            self.display_notification(f"Erreur lors de l'ouverture du fichier: {str(e)}", "error")
            
    def _get_file_path(self, node: TreeNode) -> str:
        """Get file path from tree node.
        
        Args:
            node: Tree node
            
        Returns:
            File path
        """
        path_parts = [node.label]
        current = node.parent
        
        while current and current != self.query_one("#file_tree").root:
            path_parts.insert(0, current.label)
            current = current.parent
            
        return os.path.join(self.query_one("#file_tree").root_path, *path_parts)
        
    def display_notification(self, text: str, source: str) -> None:
        """Display a notification.
        
        Args:
            text: Notification text
            source: Notification source
        """
        self.query_one("#notifications").add_notification(text, source)
```

## 6. Intégration avec l'Interface en Ligne de Commande (CLI)

```python
# src/peer/interfaces/cli/cli_interface.py

import os
import sys
import time
import threading
import queue
import readline
import atexit
from typing import Dict, List, Optional, Any, Callable

import typer
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

from peer.domain.ports.ui_port import UIPort
from peer.application.peer_application import PeerApplication

class PeerCLI(UIPort):
    """Command-line interface for Peer."""
    
    def __init__(self, peer_app: PeerApplication, logger: Any):
        """Initialize the CLI.
        
        Args:
            peer_app: Peer application
            logger: Logger instance
        """
        self.peer_app = peer_app
        self.logger = logger
        self.console = Console()
        self.app = typer.Typer(help="Peer - Assistant de développement omniscient")
        
        # CLI state
        self.session_id = None
        self.current_file = None
        self.notification_queue = queue.Queue()
        self.notification_thread = None
        self.running = False
        self.history_file = os.path.expanduser("~/.peer_history")
        
        # Register commands
        self._register_commands()
        
        # Set up readline history
        self._setup_readline()
        
    def initialize(self) -> None:
        """Initialize the CLI."""
        self.running = True
        self.notification_thread = threading.Thread(
            target=self._notification_worker,
            daemon=True,
            name="NotificationThread"
        )
        self.notification_thread.start()
        self.logger.info("CLI initialized")
        
    def shutdown(self) -> None:
        """Shutdown the CLI."""
        self.running = False
        if self.notification_thread and self.notification_thread.is_alive():
            self.notification_thread.join(timeout=2.0)
        self.logger.info("CLI shutdown")
        
    def run(self) -> None:
        """Run the CLI."""
        self.app()
        
    def display_notification(self, text: str, source: str) -> None:
        """Display a notification.
        
        Args:
            text: Notification text
            source: Notification source
        """
        self.notification_queue.put({
            "text": text,
            "source": source,
            "timestamp": time.time()
        })
        
    def _notification_worker(self) -> None:
        """Worker thread for notifications."""
        while self.running:
            try:
                # Get notification from queue
                try:
                    notification = self.notification_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                    
                # Display notification
                text = notification["text"]
                source = notification["source"]
                timestamp = time.strftime("%H:%M:%S", time.localtime(notification["timestamp"]))
                
                self.console.print(f"[{timestamp}] [{source}] {text}")
                
                # Mark as done
                self.notification_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error in notification worker: {str(e)}")
                
    def _register_commands(self) -> None:
        """Register CLI commands."""
        app = self.app
        
        @app.command("init")
        def init(
            project_dir: str = typer.Argument(
                ".",
                help="Répertoire du projet"
            ),
            mode: str = typer.Option(
                "developer",
                "--mode", "-m",
                help="Mode initial (developer, architect, reviewer, tester)"
            )
        ):
            """Initialiser une session Peer."""
            try:
                # Get absolute path
                project_dir = os.path.abspath(project_dir)
                
                # Initialize session
                session_data = self.peer_app.initialize_session(project_dir, mode)
                self.session_id = session_data["id"]
                
                # Display session info
                self.console.print(f"Session initialisée: {self.session_id}")
                self.console.print(f"Répertoire du projet: {project_dir}")
                self.console.print(f"Mode: {session_data['current_mode']}")
                
            except Exception as e:
                self.console.print(f"[bold red]Erreur:[/bold red] {str(e)}")
                
        @app.command("analyze")
        def analyze(
            file_path: str = typer.Argument(
                ...,
                help="Chemin du fichier à analyser"
            )
        ):
            """Analyser un fichier."""
            if not self.session_id:
                self.console.print("[bold red]Erreur:[/bold red] Aucune session active. Utilisez 'peer init' pour initialiser une session.")
                return
                
            try:
                # Get absolute path
                file_path = os.path.abspath(file_path)
                
                # Read file
                with open(file_path, "r") as f:
                    content = f.read()
                    
                # Analyze file
                issues = self.peer_app.analyze_code_snippet(self.session_id, file_path, content)
                
                # Display issues
                if not issues:
                    self.console.print(f"Aucun problème détecté dans {file_path}")
                    return
                    
                # Create table
                table = Table(title=f"Problèmes détectés dans {os.path.basename(file_path)}")
                table.add_column("Ligne")
                table.add_column("Colonne")
                table.add_column("Sévérité")
                table.add_column("Code")
                table.add_column("Message")
                
                for issue in issues:
                    severity = issue["severity"]
                    severity_color = {
                        "error": "red",
                        "warning": "yellow",
                        "info": "blue"
                    }.get(severity.lower(), "white")
                    
                    table.add_row(
                        str(issue["line"]),
                        str(issue["column"]),
                        f"[{severity_color}]{severity}[/{severity_color}]",
                        issue["code"],
                        issue["message"]
                    )
                    
                self.console.print(table)
                
                # Set current file
                self.current_file = file_path
                
            except Exception as e:
                self.console.print(f"[bold red]Erreur:[/bold red] {str(e)}")
                
        @app.command("suggest")
        def suggest(
            file_path: str = typer.Argument(
                None,
                help="Chemin du fichier pour lequel suggérer des améliorations"
            )
        ):
            """Suggérer des améliorations pour un fichier."""
            if not self.session_id:
                self.console.print("[bold red]Erreur:[/bold red] Aucune session active. Utilisez 'peer init' pour initialiser une session.")
                return
                
            try:
                # Use current file if not specified
                if not file_path:
                    if not self.current_file:
                        self.console.print("[bold red]Erreur:[/bold red] Aucun fichier spécifié et aucun fichier courant.")
                        return
                    file_path = self.current_file
                else:
                    file_path = os.path.abspath(file_path)
                    
                # Read file
                with open(file_path, "r") as f:
                    content = f.read()
                    
                # Get suggestions
                suggestions = self.peer_app.suggest_improvements(self.session_id, file_path, content)
                
                # Display suggestions
                if not suggestions:
                    self.console.print(f"Aucune suggestion pour {file_path}")
                    return
                    
                # Create table
                table = Table(title=f"Suggestions pour {os.path.basename(file_path)}")
                table.add_column("Lignes")
                table.add_column("Type")
                table.add_column("Description")
                table.add_column("Confiance")
                
                for suggestion in suggestions:
                    line_range = f"{suggestion['line_start']}"
                    if suggestion['line_start'] != suggestion['line_end']:
                        line_range += f"-{suggestion['line_end']}"
                        
                    suggestion_type = suggestion["suggestion_type"]
                    type_color = {
                        "refactoring": "green",
                        "style": "blue",
                        "performance": "yellow",
                        "security": "red",
                        "bug": "red"
                    }.get(suggestion_type.lower(), "white")
                    
                    confidence = suggestion.get("confidence", 0.0)
                    confidence_str = f"{confidence:.0%}"
                    
                    table.add_row(
                        line_range,
                        f"[{type_color}]{suggestion_type}[/{type_color}]",
                        suggestion["description"],
                        confidence_str
                    )
                    
                self.console.print(table)
                
            except Exception as e:
                self.console.print(f"[bold red]Erreur:[/bold red] {str(e)}")
                
        @app.command("query")
        def query(
            question: str = typer.Argument(
                ...,
                help="Question ou commande à exécuter"
            )
        ):
            """Poser une question ou exécuter une commande."""
            if not self.session_id:
                self.console.print("[bold red]Erreur:[/bold red] Aucune session active. Utilisez 'peer init' pour initialiser une session.")
                return
                
            try:
                # Execute command
                result = self.peer_app.execute_command(self.session_id, "query", [question])
                
                # Display result
                if result:
                    if isinstance(result, str) and result.startswith("```"):
                        # Markdown code block
                        self.console.print(Markdown(result))
                    else:
                        self.console.print(result)
                else:
                    self.console.print("Aucun résultat")
                    
            except Exception as e:
                self.console.print(f"[bold red]Erreur:[/bold red] {str(e)}")
                
        @app.command("mode")
        def mode(
            new_mode: str = typer.Argument(
                None,
                help="Nouveau mode (developer, architect, reviewer, tester)"
            )
        ):
            """Afficher ou changer le mode actuel."""
            if not self.session_id:
                self.console.print("[bold red]Erreur:[/bold red] Aucune session active. Utilisez 'peer init' pour initialiser une session.")
                return
                
            try:
                if new_mode:
                    # Change mode
                    self.peer_app.change_mode(self.session_id, new_mode)
                    self.console.print(f"Mode changé à: {new_mode}")
                else:
                    # Display current mode
                    session_data = self.peer_app.get_session_data(self.session_id)
                    self.console.print(f"Mode actuel: {session_data['current_mode']}")
                    
            except Exception as e:
                self.console.print(f"[bold red]Erreur:[/bold red] {str(e)}")
                
        @app.command("feedback")
        def feedback(
            enabled: bool = typer.Argument(
                None,
                help="Activer ou désactiver le feedback"
            )
        ):
            """Activer ou désactiver le feedback."""
            if not self.session_id:
                self.console.print("[bold red]Erreur:[/bold red] Aucune session active. Utilisez 'peer init' pour initialiser une session.")
                return
                
            try:
                if enabled is None:
                    # Display current status
                    self.console.print("Usage: peer feedback [true|false]")
                    return
                    
                # Change feedback status
                command = "enable_feedback" if enabled else "disable_feedback"
                self.peer_app.execute_command(self.session_id, command, [])
                
                self.console.print(f"Feedback {'activé' if enabled else 'désactivé'}")
                
            except Exception as e:
                self.console.print(f"[bold red]Erreur:[/bold red] {str(e)}")
                
        @app.command("voice")
        def voice(
            enabled: bool = typer.Argument(
                None,
                help="Activer ou désactiver le feedback vocal"
            )
        ):
            """Activer ou désactiver le feedback vocal."""
            if not self.session_id:
                self.console.print("[bold red]Erreur:[/bold red] Aucune session active. Utilisez 'peer init' pour initialiser une session.")
                return
                
            try:
                if enabled is None:
                    # Display current status
                    self.console.print("Usage: peer voice [true|false]")
                    return
                    
                # Change voice status
                command = "enable_voice" if enabled else "disable_voice"
                self.peer_app.execute_command(self.session_id, command, [])
                
                self.console.print(f"Feedback vocal {'activé' if enabled else 'désactivé'}")
                
            except Exception as e:
                self.console.print(f"[bold red]Erreur:[/bold red] {str(e)}")
                
        @app.command("watch")
        def watch(
            file_path: str = typer.Argument(
                ...,
                help="Chemin du fichier à surveiller"
            )
        ):
            """Surveiller un fichier pour des changements."""
            if not self.session_id:
                self.console.print("[bold red]Erreur:[/bold red] Aucune session active. Utilisez 'peer init' pour initialiser une session.")
                return
                
            try:
                # Get absolute path
                file_path = os.path.abspath(file_path)
                
                # Check if file exists
                if not os.path.isfile(file_path):
                    self.console.print(f"[bold red]Erreur:[/bold red] Le fichier {file_path} n'existe pas.")
                    return
                    
                # Set current file
                self.current_file = file_path
                
                # Read initial content
                with open(file_path, "r") as f:
                    last_content = f.read()
                    
                # Analyze initial content
                self.peer_app.handle_file_change(self.session_id, file_path, last_content)
                
                self.console.print(f"Surveillance de {file_path}. Appuyez sur Ctrl+C pour arrêter.")
                
                # Watch file
                try:
                    last_mtime = os.path.getmtime(file_path)
                    
                    while True:
                        time.sleep(1)
                        
                        # Check if file was modified
                        mtime = os.path.getmtime(file_path)
                        if mtime > last_mtime:
                            # Read new content
                            with open(file_path, "r") as f:
                                content = f.read()
                                
                            # Skip if content is unchanged
                            if content == last_content:
                                continue
                                
                            # Handle file change
                            self.peer_app.handle_file_change(self.session_id, file_path, content)
                            
                            # Update last content and mtime
                            last_content = content
                            last_mtime = mtime
                            
                except KeyboardInterrupt:
                    self.console.print("Surveillance arrêtée.")
                    
            except Exception as e:
                self.console.print(f"[bold red]Erreur:[/bold red] {str(e)}")
                
        @app.command("interactive")
        def interactive():
            """Démarrer le mode interactif."""
            if not self.session_id:
                self.console.print("[bold red]Erreur:[/bold red] Aucune session active. Utilisez 'peer init' pour initialiser une session.")
                return
                
            self.console.print("Mode interactif. Tapez 'exit' ou 'quit' pour quitter.")
            
            while True:
                try:
                    # Get input
                    prompt = self.console.input("[bold green]peer>[/bold green] ")
                    
                    # Check for exit
                    if prompt.lower() in ["exit", "quit"]:
                        break
                        
                    # Skip empty input
                    if not prompt:
                        continue
                        
                    # Execute command
                    result = self.peer_app.execute_command(self.session_id, "query", [prompt])
                    
                    # Display result
                    if result:
                        if isinstance(result, str) and result.startswith("```"):
                            # Markdown code block
                            self.console.print(Markdown(result))
                        else:
                            self.console.print(result)
                            
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    self.console.print(f"[bold red]Erreur:[/bold red] {str(e)}")
                    
            self.console.print("Mode interactif terminé.")
            
    def _setup_readline(self) -> None:
        """Set up readline history."""
        try:
            # Read history file
            if os.path.exists(self.history_file):
                readline.read_history_file(self.history_file)
                
            # Set history length
            readline.set_history_length(1000)
            
            # Save history on exit
            atexit.register(readline.write_history_file, self.history_file)
            
        except Exception as e:
            self.logger.error(f"Error setting up readline: {str(e)}")
```

## 7. Intégration avec l'API REST

```python
# src/peer/interfaces/api/api_interface.py

import os
import time
import threading
import asyncio
from typing import Dict, List, Optional, Any, Callable

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from peer.domain.ports.ui_port import UIPort
from peer.application.peer_application import PeerApplication

# API models
class SessionRequest(BaseModel):
    """Request model for session initialization."""
    
    project_root: str = Field(..., description="Project root directory")
    mode: str = Field("developer", description="Initial mode")
    
class SessionResponse(BaseModel):
    """Response model for session data."""
    
    id: str = Field(..., description="Session ID")
    project_root: str = Field(..., description="Project root directory")
    current_mode: str = Field(..., description="Current mode")
    start_time: str = Field(..., description="Session start time")
    
class FileRequest(BaseModel):
    """Request model for file operations."""
    
    file_path: str = Field(..., description="File path")
    content: str = Field(..., description="File content")
    
class IssueResponse(BaseModel):
    """Response model for code issues."""
    
    line: int = Field(..., description="Line number")
    column: int = Field(..., description="Column number")
    code: str = Field(..., description="Issue code")
    message: str = Field(..., description="Issue message")
    severity: str = Field(..., description="Issue severity")
    
class SuggestionResponse(BaseModel):
    """Response model for code suggestions."""
    
    line_start: int = Field(..., description="Start line number")
    line_end: int = Field(..., description="End line number")
    suggestion_type: str = Field(..., description="Suggestion type")
    description: str = Field(..., description="Suggestion description")
    confidence: float = Field(..., description="Confidence score")
    
class CommandRequest(BaseModel):
    """Request model for command execution."""
    
    command: str = Field(..., description="Command to execute")
    args: List[str] = Field([], description="Command arguments")
    
class NotificationModel(BaseModel):
    """Model for notifications."""
    
    text: str = Field(..., description="Notification text")
    source: str = Field(..., description="Notification source")
    timestamp: float = Field(..., description="Notification timestamp")
    
class PeerAPI(UIPort):
    """REST API for Peer."""
    
    def __init__(self, peer_app: PeerApplication, logger: Any, config: Dict[str, Any]):
        """Initialize the API.
        
        Args:
            peer_app: Peer application
            logger: Logger instance
            config: Configuration dictionary
        """
        self.peer_app = peer_app
        self.logger = logger
        self.config = config
        
        # API settings
        self.host = config.get("host", "127.0.0.1")
        self.port = config.get("port", 8000)
        self.cors_origins = config.get("cors_origins", ["*"])
        
        # API state
        self.app = FastAPI(
            title="Peer API",
            description="API for Peer - Assistant de développement omniscient",
            version="1.0.0"
        )
        self.notifications: Dict[str, List[NotificationModel]] = {}
        self.running = False
        self.api_thread: Optional[threading.Thread] = None
        
        # Set up CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"]
        )
        
        # Register routes
        self._register_routes()
        
    def initialize(self) -> None:
        """Initialize the API."""
        self.running = True
        self.api_thread = threading.Thread(
            target=self._run_api,
            daemon=True,
            name="APIThread"
        )
        self.api_thread.start()
        self.logger.info(f"API initialized on {self.host}:{self.port}")
        
    def shutdown(self) -> None:
        """Shutdown the API."""
        self.running = False
        if self.api_thread and self.api_thread.is_alive():
            self.api_thread.join(timeout=2.0)
        self.logger.info("API shutdown")
        
    def display_notification(self, text: str, source: str) -> None:
        """Display a notification.
        
        Args:
            text: Notification text
            source: Notification source
        """
        notification = NotificationModel(
            text=text,
            source=source,
            timestamp=time.time()
        )
        
        # Add to all active sessions
        for session_id in self.notifications:
            self.notifications[session_id].append(notification)
            
            # Limit to 100 notifications per session
            if len(self.notifications[session_id]) > 100:
                self.notifications[session_id].pop(0)
                
    def _run_api(self) -> None:
        """Run the API server."""
        import uvicorn
        
        # Create event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run server
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )
        
    def _register_routes(self) -> None:
        """Register API routes."""
        app = self.app
        
        # Session management
        @app.post("/sessions", response_model=SessionResponse)
        async def create_session(request: SessionRequest):
            """Create a new session."""
            try:
                # Initialize session
                session_data = self.peer_app.initialize_session(request.project_root, request.mode)
                
                # Initialize notifications
                session_id = session_data["id"]
                self.notifications[session_id] = []
                
                return session_data
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
                
        @app.get("/sessions/{session_id}", response_model=SessionResponse)
        async def get_session(session_id: str):
            """Get session data."""
            try:
                return self.peer_app.get_session_data(session_id)
            except Exception as e:
                raise HTTPException(status_code=404, detail=f"Session not found: {str(e)}")
                
        @app.delete("/sessions/{session_id}")
        async def delete_session(session_id: str):
            """Delete a session."""
            try:
                self.peer_app.delete_session(session_id)
                
                # Clean up notifications
                if session_id in self.notifications:
                    del self.notifications[session_id]
                    
                return {"status": "success"}
            except Exception as e:
                raise HTTPException(status_code=404, detail=f"Session not found: {str(e)}")
                
        # Code analysis
        @app.post("/sessions/{session_id}/analyze", response_model=List[IssueResponse])
        async def analyze_code(session_id: str, request: FileRequest):
            """Analyze code."""
            try:
                return self.peer_app.analyze_code_snippet(session_id, request.file_path, request.content)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
                
        @app.post("/sessions/{session_id}/suggest", response_model=List[SuggestionResponse])
        async def suggest_improvements(session_id: str, request: FileRequest):
            """Suggest improvements."""
            try:
                return self.peer_app.suggest_improvements(session_id, request.file_path, request.content)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
                
        @app.post("/sessions/{session_id}/file_change", response_model=Dict[str, str])
        async def handle_file_change(session_id: str, request: FileRequest, background_tasks: BackgroundTasks):
            """Handle file change."""
            try:
                # Handle file change in background
                background_tasks.add_task(
                    self.peer_app.handle_file_change,
                    session_id,
                    request.file_path,
                    request.content
                )
                
                return {"status": "processing"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
                
        # Command execution
        @app.post("/sessions/{session_id}/command")
        async def execute_command(session_id: str, request: CommandRequest):
            """Execute command."""
            try:
                result = self.peer_app.execute_command(session_id, request.command, request.args)
                return {"result": result}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
                
        # Notifications
        @app.get("/sessions/{session_id}/notifications", response_model=List[NotificationModel])
        async def get_notifications(
            session_id: str,
            since: Optional[float] = None
        ):
            """Get notifications."""
            try:
                # Check if session exists
                if session_id not in self.notifications:
                    raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
                    
                # Filter notifications by timestamp
                if since is not None:
                    return [n for n in self.notifications[session_id] if n.timestamp > since]
                else:
                    return self.notifications[session_id]
            except Exception as e:
                if isinstance(e, HTTPException):
                    raise e
                raise HTTPException(status_code=500, detail=str(e))
                
        # Settings
        @app.post("/sessions/{session_id}/settings/feedback")
        async def set_feedback(session_id: str, enabled: bool):
            """Set feedback status."""
            try:
                command = "enable_feedback" if enabled else "disable_feedback"
                self.peer_app.execute_command(session_id, command, [])
                return {"status": "success"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
                
        @app.post("/sessions/{session_id}/settings/voice")
        async def set_voice(session_id: str, enabled: bool):
            """Set voice feedback status."""
            try:
                command = "enable_voice" if enabled else "disable_voice"
                self.peer_app.execute_command(session_id, command, [])
                return {"status": "success"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
                
        @app.post("/sessions/{session_id}/settings/mode")
        async def set_mode(session_id: str, mode: str):
            """Set session mode."""
            try:
                self.peer_app.change_mode(session_id, mode)
                return {"status": "success"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
```

## Conclusion

Cette implémentation du service d'analyse continue et du feedback vocal pour Peer permet une assistance omnisciente en temps réel pendant le développement. Les principales fonctionnalités implémentées sont :

1. **Service d'Analyse Continue** : Analyse le code en arrière-plan à intervalles réguliers, détecte les problèmes et fournit un feedback proactif.

2. **Adaptateurs Text-to-Speech** : Deux implémentations alternatives (Piper et pyttsx3) pour le feedback vocal, permettant de choisir la solution la plus adaptée selon l'environnement.

3. **Service Peer Assistant Omniscient** : Coordonne l'analyse continue, le feedback vocal et les suggestions d'amélioration, en s'adaptant au contexte et au mode actuel.

4. **Interfaces Utilisateur** : Intégration avec les interfaces TUI (Textual), CLI (Typer) et API REST (FastAPI) pour une expérience utilisateur complète et flexible.

Cette implémentation respecte l'architecture hexagonale avec une séparation claire entre le domaine, les adaptateurs et les interfaces. Elle fonctionne entièrement en local et peut être facilement étendue avec de nouveaux plugins et modes.

Les prochaines étapes consisteront à intégrer ces composants avec les IDE et les systèmes de contrôle de version, et à valider l'ensemble du système avec des tests d'intégration complets.
