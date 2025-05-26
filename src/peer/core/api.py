"""
Peer Core API - Unified API protocol for all interfaces

This module defines the standard protocol that ALL interfaces must use
to communicate with the Peer core daemon. This ensures consistency
across CLI, TUI, SUI, and API interfaces.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
import json
import uuid
from datetime import datetime


class CommandType(Enum):
    """Standard command types supported by the core"""
    # Core system commands
    HELP = "help"
    STATUS = "status"
    VERSION = "version"
    CAPABILITIES = "capabilities"
    
    # Session management
    SESSION_CREATE = "session_create"
    SESSION_END = "session_end"
    SESSION_INFO = "session_info"
    SESSION_LIST = "session_list"
    
    # Cluster management
    CLUSTER_STATUS = "cluster_status"
    CLUSTER_INSTANCES = "cluster_instances"
    CLUSTER_START = "cluster_start"
    CLUSTER_STOP = "cluster_stop"
    
    # Analysis and AI commands
    ANALYZE = "analyze"
    SUGGEST = "suggest"
    EXECUTE = "execute"
    QUERY = "query"
    EXPLAIN = "explain"
    PROMPT = "prompt"
    
    # File and project operations
    FILE_ANALYZE = "file_analyze"
    FILE_EDIT = "file_edit"
    PROJECT_ANALYZE = "project_analyze"
    
    # Configuration
    CONFIG_GET = "config_get"
    CONFIG_SET = "config_set"
    
    # Utility commands
    ECHO = "echo"
    TIME = "time"
    DATE = "date"
    QUIT = "quit"
    DIRECT_QUIT = "direct_quit"  # Arrêt immédiat sans confirmation
    SOFT_QUIT = "soft_quit"      # Arrêt avec demande de confirmation
    
    # Mode switching
    MODE_SWITCH = "mode_switch"


class ResponseType(Enum):
    """Standard response types from the core"""
    SUCCESS = "success"
    ERROR = "error"
    INFO = "info"
    WARNING = "warning"
    PROGRESS = "progress"
    DATA = "data"


class InterfaceType(Enum):
    """Types of interfaces that can connect to the core"""
    CLI = "cli"
    TUI = "tui"
    SUI = "sui"  # Speech User Interface
    API = "api"
    INTERNAL = "internal"


@dataclass
class CoreRequest:
    """Standard request format for all core communications"""
    command: CommandType
    session_id: Optional[str] = None
    instance_id: int = 0  # 0 = master instance by default
    parameters: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    interface_type: InterfaceType = InterfaceType.INTERNAL
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['command'] = self.command.value if isinstance(self.command, CommandType) else self.command
        result['interface_type'] = self.interface_type.value if isinstance(self.interface_type, InterfaceType) else self.interface_type
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CoreRequest':
        """Create from dictionary"""
        if isinstance(data.get('command'), str):
            data['command'] = CommandType(data['command'])
        if isinstance(data.get('interface_type'), str):
            data['interface_type'] = InterfaceType(data['interface_type'])
        return cls(**data)
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), default=str)


@dataclass
class CoreResponse:
    """Standard response format from the core"""
    type: ResponseType
    status: str
    message: str
    data: Optional[Dict[str, Any]] = field(default_factory=dict)
    session_id: Optional[str] = None
    instance_id: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    request_id: Optional[str] = None
    response_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['type'] = self.type.value if isinstance(self.type, ResponseType) else self.type
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CoreResponse':
        """Create from dictionary"""
        if isinstance(data.get('type'), str):
            data['type'] = ResponseType(data['type'])
        return cls(**data)
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), default=str)


@dataclass
class CommandCapability:
    """Describes a command's capabilities and metadata"""
    command: CommandType
    description: str
    parameters: List[str] = field(default_factory=list)
    required_parameters: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    category: str = "general"
    available_in_interfaces: List[InterfaceType] = field(default_factory=lambda: list(InterfaceType))


class CoreAPI(ABC):
    """Abstract interface for the Peer Core API"""
    
    @abstractmethod
    def execute_command(self, request: CoreRequest) -> CoreResponse:
        """Execute a command and return response"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """Get available commands and their capabilities"""
        pass
    
    @abstractmethod
    def get_status(self, instance_id: int = 0) -> Dict[str, Any]:
        """Get core status and health"""
        pass
    
    @abstractmethod
    def get_help(self, command: Optional[CommandType] = None, interface_type: InterfaceType = InterfaceType.INTERNAL) -> Dict[str, Any]:
        """Get help information about commands, optionally filtered for interface type"""
        pass
    
    @abstractmethod
    def create_session(self, interface_type: InterfaceType) -> str:
        """Create a new session and return session ID"""
        pass
    
    @abstractmethod
    def end_session(self, session_id: str) -> bool:
        """End a session"""
        pass
    
    @abstractmethod
    def get_version(self) -> str:
        """Get core version"""
        pass
