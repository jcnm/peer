# Implémentation de la Couche Domaine et des Ports de Peer

Ce document détaille l'implémentation de la couche Domaine et des Ports (interfaces) pour le projet Peer, conformément à l'architecture hexagonale et aux spécifications.

## Définition des Ports

Les ports définissent les contrats d'interaction entre la couche Application/Interfaces et la couche Domaine, ainsi qu'entre la couche Domaine et la couche Infrastructure.

### Ports d'Entrée (Input Ports)

Ces ports définissent comment les couches externes (Application, Interfaces) interagissent avec le Domaine.

```python
# src/peer/domain/ports/input_ports.py

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

class PeerInputPort(ABC):
    """Interface for interacting with the Peer core domain logic."""

    @abstractmethod
    def initialize_session(self, project_root: str) -> Dict[str, Any]:
        """Initialize a new Peer session for a project."""
        pass

    @abstractmethod
    def execute_command(self, session_id: str, command: str, args: List[str]) -> Any:
        """Execute a specific command within a session."""
        pass

    @abstractmethod
    def analyze_code_snippet(self, session_id: str, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Analyze a given code snippet."""
        pass

    @abstractmethod
    def suggest_improvements(self, session_id: str, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Suggest improvements for a given code snippet."""
        pass

    @abstractmethod
    def handle_file_change(self, session_id: str, file_path: str, content: Optional[str] = None) -> None:
        """Handle a file change event (create, update, delete)."""
        pass

    @abstractmethod
    def handle_vcs_change(self, session_id: str, changed_files: List[Dict[str, Any]]) -> None:
        """Handle a version control system change event."""
        pass

    @abstractmethod
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get the current status of a session."""
        pass

    @abstractmethod
    def provide_feedback(self, session_id: str, feedback_type: str, details: Dict[str, Any]) -> None:
        """Provide feedback to the Peer assistant."""
        pass

    @abstractmethod
    def get_configuration(self, session_id: str, section: Optional[str] = None) -> Dict[str, Any]:
        """Get the current configuration for the session."""
        pass

    @abstractmethod
    def update_configuration(self, session_id: str, section: str, key: str, value: Any) -> None:
        """Update the configuration for the session."""
        pass
```

### Ports de Sortie (Output Ports)

Ces ports définissent comment la couche Domaine interagit avec les services externes (Infrastructure).

```python
# src/peer/domain/ports/output_ports.py

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

# --- LLM Port ---
class LLMOutputPort(ABC):
    """Interface for interacting with Language Models."""

    @abstractmethod
    def generate_text(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate text based on a prompt and context."""
        pass

    @abstractmethod
    def generate_code(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate code based on a prompt and context."""
        pass

    @abstractmethod
    def analyze_prompt(self, prompt: str) -> Dict[str, Any]:
        """Analyze a prompt to understand intent and entities."""
        pass

# --- TTS Port ---
class TTSOutputPort(ABC):
    """Interface for interacting with Text-to-Speech services."""

    @abstractmethod
    def speak(self, text: str, voice: Optional[str] = None) -> None:
        """Speak the given text using the specified voice."""
        pass

    @abstractmethod
    def get_available_voices(self) -> List[str]:
        """Get a list of available voices."""
        pass

# --- Code Analysis Port ---
class CodeAnalysisOutputPort(ABC):
    """Interface for interacting with code analysis tools."""

    @abstractmethod
    def parse_code(self, file_path: str, content: str) -> Dict[str, Any]:
        """Parse code to generate an Abstract Syntax Tree (AST) or similar structure."""
        pass

    @abstractmethod
    def lint_code(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Lint code to find style issues and potential errors."""
        pass

    @abstractmethod
    def check_types(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Perform static type checking on code."""
        pass

# --- Persistence Port ---
class PersistenceOutputPort(ABC):
    """Interface for interacting with data storage."""

    @abstractmethod
    def save_session(self, session_id: str, session_data: Dict[str, Any]) -> None:
        """Save session data."""
        pass

    @abstractmethod
    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session data."""
        pass

    @abstractmethod
    def delete_session(self, session_id: str) -> None:
        """Delete session data."""
        pass

    @abstractmethod
    def save_analysis_result(self, file_path: str, result: Dict[str, Any]) -> None:
        """Save code analysis results."""
        pass

    @abstractmethod
    def load_analysis_result(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Load code analysis results."""
        pass

# --- User Interface Port ---
class UserInterfaceOutputPort(ABC):
    """Interface for interacting with the user interface (CLI, TUI, API)."""

    @abstractmethod
    def display_message(self, message: str, level: str = "INFO") -> None:
        """Display a message to the user."""
        pass

    @abstractmethod
    def display_analysis_results(self, results: List[Dict[str, Any]]) -> None:
        """Display code analysis results."""
        pass

    @abstractmethod
    def display_suggestions(self, suggestions: List[Dict[str, Any]]) -> None:
        """Display improvement suggestions."""
        pass

    @abstractmethod
    def ask_question(self, question: str, options: Optional[List[str]] = None) -> str:
        """Ask the user a question and return the answer."""
        pass

    @abstractmethod
    def show_progress(self, task_name: str, progress: float) -> None:
        """Show progress for a long-running task."""
        pass

# --- File System Port ---
class FileSystemOutputPort(ABC):
    """Interface for interacting with the file system."""

    @abstractmethod
    def read_file(self, file_path: str) -> str:
        """Read the content of a file."""
        pass

    @abstractmethod
    def write_file(self, file_path: str, content: str) -> None:
        """Write content to a file."""
        pass

    @abstractmethod
    def file_exists(self, file_path: str) -> bool:
        """Check if a file exists."""
        pass

    @abstractmethod
    def list_directory(self, dir_path: str) -> List[str]:
        """List the contents of a directory."""
        pass

# --- VCS Port ---
class VCSOutputPort(ABC):
    """Interface for interacting with Version Control Systems."""

    @abstractmethod
    def get_changed_files(self, repo_path: str) -> List[Dict[str, Any]]:
        """Get a list of changed files in the repository."""
        pass

    @abstractmethod
    def get_file_diff(self, repo_path: str, file_path: str) -> str:
        """Get the diff for a specific file."""
        pass

    @abstractmethod
    def get_current_branch(self, repo_path: str) -> str:
        """Get the current branch name."""
        pass
```

## Entités du Domaine

Les entités représentent les objets métiers principaux.

```python
# src/peer/domain/entities/__init__.py

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime

@dataclass
class CodeAnalysisIssue:
    line: int
    column: int
    code: str
    message: str
    severity: str # e.g., 'error', 'warning', 'info'
    source: str # e.g., 'ruff', 'mypy', 'tree-sitter'

@dataclass
class CodeSuggestion:
    line_start: int
    line_end: int
    suggestion_type: str # e.g., 'refactor', 'performance', 'security', 'style'
    description: str
    suggested_code: Optional[str] = None
    confidence: Optional[float] = None # 0.0 to 1.0
    source: str # e.g., 'llm', 'peer_assistant'

@dataclass
class CodeContext:
    file_path: str
    content: str
    language: Optional[str] = None
    ast: Optional[Dict[str, Any]] = None
    issues: List[CodeAnalysisIssue] = field(default_factory=list)
    suggestions: List[CodeSuggestion] = field(default_factory=list)
    last_analyzed: Optional[datetime] = None

@dataclass
class Session:
    id: str
    project_root: str
    start_time: datetime
    last_activity: datetime
    current_mode: str
    context: Dict[str, Any] = field(default_factory=dict) # General session context
    file_contexts: Dict[str, CodeContext] = field(default_factory=dict) # Context per file
    history: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class UserFeedback:
    timestamp: datetime
    feedback_type: str # e.g., 'suggestion_accepted', 'suggestion_rejected', 'issue_ignored'
    details: Dict[str, Any]
    session_id: str
```

## Services du Domaine

Les services contiennent la logique métier principale.

### Service de Workflow

```python
# src/peer/domain/services/workflow_service.py

from typing import Dict, List, Any, Optional

class WorkflowService:
    def __init__(self, llm_port: LLMOutputPort, ui_port: UserInterfaceOutputPort, logger):
        self.llm_port = llm_port
        self.ui_port = ui_port
        self.logger = logger

    def execute_task(self, task_description: str, session_context: Dict[str, Any]) -> Any:
        """Execute a task based on its description and session context."""
        self.logger.info(f"Executing task: {task_description}")
        self.ui_port.show_progress(task_description, 0.1)

        # 1. Analyze task description using LLM (simplified)
        prompt = f"Analyze the following task and break it down into steps: {task_description}"
        analysis = self.llm_port.analyze_prompt(prompt)
        steps = analysis.get("steps", [task_description]) # Fallback if analysis fails

        results = []
        total_steps = len(steps)
        for i, step in enumerate(steps):
            self.logger.info(f"Executing step {i+1}/{total_steps}: {step}")
            self.ui_port.show_progress(task_description, (i + 1) / total_steps * 0.8 + 0.1)

            # 2. Execute step (simplified - uses LLM for generation)
            step_prompt = f"Perform the following step based on the context: {step}\nContext: {session_context}"
            step_result = self.llm_port.generate_text(step_prompt)
            results.append(step_result)
            self.logger.debug(f"Step result: {step_result}")

        self.ui_port.show_progress(task_description, 1.0)
        self.logger.info(f"Task '{task_description}' completed.")
        return results # Or a more structured result
```

### Service d'Analyse de Code

```python
# src/peer/domain/services/code_analysis_service.py

from typing import Dict, List, Any, Optional
from datetime import datetime
from peer.domain.entities import CodeContext, CodeAnalysisIssue
from peer.domain.ports.output_ports import CodeAnalysisOutputPort, PersistenceOutputPort

class CodeAnalysisService:
    def __init__(self, analysis_port: CodeAnalysisOutputPort, persistence_port: PersistenceOutputPort, logger):
        self.analysis_port = analysis_port
        self.persistence_port = persistence_port
        self.logger = logger

    def analyze_file(self, file_path: str, content: str) -> CodeContext:
        """Analyze a file's content and return its context."""
        self.logger.info(f"Analyzing file: {file_path}")
        issues = []
        ast = None

        try:
            # 1. Parse code (e.g., using Tree-sitter)
            ast = self.analysis_port.parse_code(file_path, content)
            self.logger.debug(f"AST generated for {file_path}")
        except Exception as e:
            self.logger.warn(f"Failed to parse {file_path}: {e}")

        try:
            # 2. Lint code (e.g., using Ruff)
            lint_issues = self.analysis_port.lint_code(file_path, content)
            issues.extend([CodeAnalysisIssue(**issue, source='linter') for issue in lint_issues])
            self.logger.debug(f"Linting found {len(lint_issues)} issues in {file_path}")
        except Exception as e:
            self.logger.warn(f"Failed to lint {file_path}: {e}")

        # 3. Type check (optional, could be slow)
        # try:
        #     type_issues = self.analysis_port.check_types(file_path, content)
        #     issues.extend([CodeAnalysisIssue(**issue, source='type_checker') for issue in type_issues])
        # except Exception as e:
        #     self.logger.warn(f"Failed to type check {file_path}: {e}")

        code_context = CodeContext(
            file_path=file_path,
            content=content, # Consider storing only hash or diff for large files
            ast=ast,
            issues=issues,
            last_analyzed=datetime.now()
        )

        # 4. Persist analysis results (optional)
        # self.persistence_port.save_analysis_result(file_path, code_context.to_dict()) # Assuming to_dict method

        self.logger.info(f"Analysis complete for {file_path}. Found {len(issues)} issues.")
        return code_context
```

### Service de Gestion des Sessions

```python
# src/peer/domain/services/session_management_service.py

import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from peer.domain.entities import Session
from peer.domain.ports.output_ports import PersistenceOutputPort

class SessionManagementService:
    def __init__(self, persistence_port: PersistenceOutputPort, logger):
        self.persistence_port = persistence_port
        self.logger = logger
        self.active_sessions: Dict[str, Session] = {}

    def create_session(self, project_root: str, initial_mode: str = "developer") -> Session:
        """Create a new session."""
        session_id = str(uuid.uuid4())
        now = datetime.now()
        session = Session(
            id=session_id,
            project_root=project_root,
            start_time=now,
            last_activity=now,
            current_mode=initial_mode
        )
        self.active_sessions[session_id] = session
        self.persistence_port.save_session(session_id, session.__dict__) # Assuming Session is serializable
        self.logger.info(f"Created new session {session_id} for project {project_root}")
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get an active session or load from persistence."""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session.last_activity = datetime.now()
            return session

        # Try loading from persistence
        session_data = self.persistence_port.load_session(session_id)
        if session_data:
            session = Session(**session_data) # Assuming Session can be created from dict
            session.last_activity = datetime.now()
            self.active_sessions[session_id] = session
            self.logger.info(f"Loaded session {session_id} from persistence.")
            return session

        self.logger.warn(f"Session {session_id} not found.")
        return None

    def update_session_context(self, session_id: str, context_updates: Dict[str, Any]) -> None:
        """Update the context of a session."""
        session = self.get_session(session_id)
        if session:
            session.context.update(context_updates)
            session.last_activity = datetime.now()
            self.persistence_port.save_session(session_id, session.__dict__)
            self.logger.debug(f"Updated context for session {session_id}")

    def add_file_context(self, session_id: str, file_path: str, code_context: 'CodeContext') -> None:
        """Add or update the context for a specific file in the session."""
        session = self.get_session(session_id)
        if session:
            session.file_contexts[file_path] = code_context
            session.last_activity = datetime.now()
            # Consider partial save for performance
            self.persistence_port.save_session(session_id, session.__dict__)
            self.logger.debug(f"Updated file context for {file_path} in session {session_id}")

    def add_history_event(self, session_id: str, event: Dict[str, Any]) -> None:
        """Add an event to the session history."""
        session = self.get_session(session_id)
        if session:
            session.history.append(event)
            # Trim history if needed
            # max_history = self.config_manager.get_config("core").get("max_history_size", 1000)
            # if len(session.history) > max_history:
            #     session.history = session.history[-max_history:]
            session.last_activity = datetime.now()
            self.persistence_port.save_session(session_id, session.__dict__)

    def end_session(self, session_id: str) -> None:
        """End a session and remove from active memory."""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session.last_activity = datetime.now()
            # Final save before removing from memory
            self.persistence_port.save_session(session_id, session.__dict__)
            del self.active_sessions[session_id]
            self.logger.info(f"Ended session {session_id}")
        else:
            self.logger.warn(f"Attempted to end non-active session {session_id}")
```

### Service de Détection de Contexte (Simplifié)

```python
# src/peer/domain/services/context_detection_service.py

from typing import Dict, List, Any, Optional

class ContextDetectionService:
    def __init__(self, logger):
        self.logger = logger

    def detect_mode(self, session_context: Dict[str, Any], user_input: Optional[str] = None) -> str:
        """Detect the most appropriate mode based on context and input."""
        # Simple rule-based detection for now
        # TODO: Implement more sophisticated detection (e.g., using LLM or heuristics)

        current_mode = session_context.get("current_mode", "developer")
        active_file = session_context.get("active_file_path")

        if user_input:
            if "architect" in user_input.lower() or "design" in user_input.lower():
                return "architect"
            if "review" in user_input.lower() or "critique" in user_input.lower():
                return "reviewer"
            if "test" in user_input.lower() or "coverage" in user_input.lower():
                return "tester"

        if active_file:
            if "test" in active_file.lower():
                return "tester"
            if "README" in active_file or ".md" in active_file:
                 # Could be PMO or Architect, default to current or developer
                 pass

        # Default to current mode or developer
        self.logger.debug(f"Detected mode: {current_mode}")
        return current_mode
```

### Service Peer Assistant Omniscient (Cœur)

```python
# src/peer/domain/services/peer_assistant_service.py

from typing import Dict, List, Any, Optional
from peer.domain.entities import CodeContext, CodeSuggestion
from peer.domain.ports.output_ports import (LLMOutputPort, TTSOutputPort,
                                            CodeAnalysisOutputPort, UserInterfaceOutputPort,
                                            VCSOutputPort)
from peer.domain.services.code_analysis_service import CodeAnalysisService

class PeerAssistantService:
    def __init__(self, llm_port: LLMOutputPort, tts_port: TTSOutputPort,
                 analysis_service: CodeAnalysisService, ui_port: UserInterfaceOutputPort,
                 vcs_port: VCSOutputPort, logger):
        self.llm_port = llm_port
        self.tts_port = tts_port
        self.analysis_service = analysis_service
        self.ui_port = ui_port
        self.vcs_port = vcs_port
        self.logger = logger
        self.suggestion_cache: Dict[str, List[CodeSuggestion]] = {}

    def provide_proactive_assistance(self, session: 'Session') -> None:
        """Provide proactive assistance based on the current session context."""
        self.logger.info(f"Providing proactive assistance for session {session.id}")

        # Analyze currently active files or changed files
        files_to_process = self._get_relevant_files(session)

        for file_path, code_context in files_to_process.items():
            if not code_context:
                continue # Skip if context is missing

            # 1. Identify critical issues from analysis
            critical_issues = [issue for issue in code_context.issues if issue.severity == 'error']
            if critical_issues:
                message = f"Found {len(critical_issues)} critical issues in {os.path.basename(file_path)}."
                self.logger.warn(message)
                self.ui_port.display_message(message, level="WARNING")
                self.tts_port.speak(message) # Vocal feedback
                # Optionally display details
                # self.ui_port.display_analysis_results(critical_issues)
                continue # Focus on critical issues first

            # 2. Generate suggestions if no critical issues
            suggestions = self._generate_suggestions(session, file_path, code_context)
            if suggestions:
                message = f"I have {len(suggestions)} suggestions for {os.path.basename(file_path)}."
                self.logger.info(message)
                self.ui_port.display_message(message)
                self.tts_port.speak(message) # Vocal feedback
                # Optionally display details
                # self.ui_port.display_suggestions(suggestions)

    def _get_relevant_files(self, session: 'Session') -> Dict[str, Optional[CodeContext]]:
        """Determine which files need processing based on recent activity."""
        # Simple strategy: process the most recently active file context
        # TODO: Implement more sophisticated strategy (e.g., based on VCS changes, open files in IDE)
        if not session.file_contexts:
            return {}

        # Find the file context with the most recent activity (e.g., last_analyzed)
        latest_file = max(session.file_contexts.items(), key=lambda item: item[1].last_analyzed if item[1] and item[1].last_analyzed else datetime.min)
        if latest_file and latest_file[1]:
             return {latest_file[0]: latest_file[1]}
        return {}

    def _generate_suggestions(self, session: 'Session', file_path: str, code_context: CodeContext) -> List[CodeSuggestion]:
        """Generate improvement suggestions using LLM and analysis results."""
        # Check cache first (simple time-based cache)
        # if file_path in self.suggestion_cache and (datetime.now() - code_context.last_analyzed).total_seconds() < 60:
        #     return self.suggestion_cache[file_path]

        self.logger.info(f"Generating suggestions for {file_path}")

        # Prepare prompt for LLM
        prompt = f"Analyze the following code from file '{file_path}' and provide suggestions for improvement (refactoring, performance, security, style). Focus on actionable advice.
        """
        {code_context.content}
        """
        Analysis Issues Found:
        " + "\n".join([f"- L{i.line}: {i.message} ({i.code})" for i in code_context.issues]) + "
        Provide suggestions in a structured format (e.g., JSON list with line_start, line_end, suggestion_type, description)."

        try:
            llm_response = self.llm_port.generate_text(prompt, context=session.context)
            # Parse LLM response into CodeSuggestion objects
            # TODO: Implement robust parsing of LLM response
            suggestions = self._parse_llm_suggestions(llm_response)
            self.logger.info(f"Generated {len(suggestions)} suggestions for {file_path} using LLM.")

            # Add suggestions to code context
            code_context.suggestions = suggestions
            # Update session (might require SessionManagementService)
            # self.session_service.add_file_context(session.id, file_path, code_context)

            # Update cache
            self.suggestion_cache[file_path] = suggestions
            return suggestions
        except Exception as e:
            self.logger.error(f"Failed to generate suggestions for {file_path}: {e}")
            return []

    def _parse_llm_suggestions(self, llm_response: str) -> List[CodeSuggestion]:
        """Parse the LLM response string into a list of CodeSuggestion objects."""
        # Placeholder implementation - requires robust JSON parsing or regex
        suggestions = []
        try:
            # Attempt to parse as JSON list
            parsed_list = json.loads(llm_response)
            if isinstance(parsed_list, list):
                for item in parsed_list:
                    if isinstance(item, dict) and all(k in item for k in ["line_start", "line_end", "suggestion_type", "description"]):
                        suggestions.append(CodeSuggestion(
                            line_start=item["line_start"],
                            line_end=item["line_end"],
                            suggestion_type=item["suggestion_type"],
                            description=item["description"],
                            suggested_code=item.get("suggested_code"),
                            confidence=item.get("confidence"),
                            source='llm'
                        ))
        except json.JSONDecodeError:
            self.logger.warn("LLM suggestion response was not valid JSON. Attempting regex parsing.")
            # TODO: Implement regex parsing as fallback
            pass
        except Exception as e:
             self.logger.error(f"Error parsing LLM suggestions: {e}")

        if not suggestions:
             self.logger.warn("Could not parse any suggestions from LLM response.")

        return suggestions

```

## Conclusion

Cette implémentation de la couche Domaine et des Ports fournit le cœur logique de Peer. Elle définit les contrats d'interaction (Ports), les objets métiers (Entités) et la logique principale (Services), y compris le service Peer Assistant Omniscient.

Les prochaines étapes consisteront à implémenter les adaptateurs de la couche Infrastructure qui réaliseront concrètement les interactions définies par les Ports de Sortie (connexion aux LLMs, TTS, outils d'analyse, etc.) et à connecter les Interfaces Utilisateur aux Ports d'Entrée.
