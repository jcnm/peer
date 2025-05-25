# Implémentation de la Structure de Base de Peer

Ce document présente l'implémentation initiale de la structure de base du projet Peer, suivant l'architecture hexagonale et les principes définis dans les spécifications détaillées.

## Structure de Répertoires

```
/
├── src/
│   ├── peer/
│   │   ├── __init__.py
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   ├── entities/
│   │   │   │   └── __init__.py
│   │   │   ├── ports/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── input_ports.py
│   │   │   │   └── output_ports.py
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       ├── peer_assistant_service.py
│   │   │       ├── workflow_service.py
│   │   │       └── code_analysis_service.py
│   │   ├── application/
│   │   │   ├── __init__.py
│   │   │   ├── config/
│   │   │   │   ├── __init__.py
│   │   │   │   └── config_manager.py
│   │   │   ├── event/
│   │   │   │   ├── __init__.py
│   │   │   │   └── event_bus.py
│   │   │   ├── plugins/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── plugin_manager.py
│   │   │   │   └── plugin_registry.py
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       └── core_service.py
│   │   ├── infrastructure/
│   │   │   ├── __init__.py
│   │   │   ├── adapters/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── llm/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   └── ollama_adapter.py
│   │   │   │   ├── tts/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   └── piper_adapter.py
│   │   │   │   ├── code_analysis/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   └── tree_sitter_adapter.py
│   │   │   │   ├── persistence/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   └── sqlite_adapter.py
│   │   │   │   ├── ide/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   └── vscode_adapter.py
│   │   │   │   └── vcs/
│   │   │   │       ├── __init__.py
│   │   │   │       └── git_adapter.py
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       ├── logging_service.py
│   │   │       └── file_system_service.py
│   │   └── interfaces/
│   │       ├── __init__.py
│   │       ├── cli/
│   │       │   ├── __init__.py
│   │       │   └── commands.py
│   │       ├── tui/
│   │       │   ├── __init__.py
│   │       │   └── app.py
│   │       └── api/
│   │           ├── __init__.py
│   │           └── routes.py
│   └── plugins/
│       ├── __init__.py
│       ├── developer/
│       │   ├── __init__.py
│       │   └── plugin.py
│       ├── architect/
│       │   ├── __init__.py
│       │   └── plugin.py
│       ├── reviewer/
│       │   ├── __init__.py
│       │   └── plugin.py
│       └── tester/
│           ├── __init__.py
│           └── plugin.py
├── tests/
│   ├── unit/
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── interfaces/
│   └── integration/
│       ├── workflows/
│       ├── plugins/
│       └── end_to_end/
├── pyproject.toml
├── README.md
├── config/
├── install.sh
├── diagnose.sh
├── .env.example
├── run.sh
├── run_api.sh
├── run_tui.sh
├── run_sui.sh
└── run_tests.sh
```

## Implémentation du Gestionnaire de Configuration

Le gestionnaire de configuration est l'un des premiers composants à implémenter, car il sera utilisé par presque tous les autres composants.

```python
# src/peer/application/config/config_manager.py

import os
import json
from typing import Dict, List, Any, Optional
from dynaconf import Dynaconf
import toml

class ConfigManager:
    def __init__(self, logger=None):
        self.settings = None
        self.config_file = None
        self.config_cache = {}
        self.logger = logger or self._get_default_logger()
        
    def initialize(self) -> None:
        """Initialize the configuration manager."""
        # Determine default config file path
        default_config_dir = os.path.expanduser("~/.config/peer")
        os.makedirs(default_config_dir, exist_ok=True)
        self.config_file = os.path.join(default_config_dir, "config.toml")
        
        # Initialize Dynaconf with default settings
        self.settings = Dynaconf(
            settings_files=[self.config_file],
            environments=True,
            env_prefix="PEER",
            load_dotenv=True,
            lowercase_read=False
        )
        
        # Load or create config file
        if not os.path.exists(self.config_file):
            self.logger.info(f"Config file not found, creating default at {self.config_file}")
            self.reset_to_defaults()
        else:
            self.logger.info(f"Loading config from {self.config_file}")
            
        # Validate config
        self.validate_config()
        
        self.logger.info("Configuration manager initialized")
        
    def load_config(self, config_file: Optional[str] = None) -> None:
        """Load configuration from file."""
        if config_file:
            config_file = os.path.abspath(os.path.expanduser(config_file))
            if not os.path.exists(config_file):
                self.logger.warn(f"Config file not found: {config_file}")
                return
                
            self.config_file = config_file
            
        # Reload settings
        self.settings.reload()
        
        # Clear cache
        self.config_cache = {}
        
        # Validate config
        self.validate_config()
        
        self.logger.info(f"Configuration loaded from {self.config_file}")
        
    def get_config(self, section: str) -> Dict[str, Any]:
        """Get configuration for a specific section."""
        # Check cache first
        if section in self.config_cache:
            return self.config_cache[section]
            
        # Get from settings
        if section in self.settings:
            config = dict(self.settings.get(section, {}))
        else:
            # If section doesn't exist, use defaults
            config = self.get_section_defaults(section)
            
        # Cache for future use
        self.config_cache[section] = config
        
        return config
        
    def get_sections(self) -> List[str]:
        """Get list of available configuration sections."""
        # Get sections from settings and defaults
        sections = set(self.settings.keys())
        sections.update(self.get_default_config().keys())
        
        # Filter out non-section keys
        sections = [s for s in sections if isinstance(self.settings.get(s, {}), dict) or s in self.get_default_config()]
        
        return sorted(sections)
        
    def set_config(self, section: str, key: str, value: Any) -> None:
        """Set configuration value for a specific section and key."""
        # Ensure section exists
        if section not in self.settings:
            self.settings[section] = {}
            
        # Set value
        self.settings[section][key] = value
        
        # Invalidate cache
        if section in self.config_cache:
            del self.config_cache[section]
            
        self.logger.info(f"Configuration updated: {section}.{key} = {value}")
        
    def save_config(self) -> None:
        """Save current configuration to file."""
        # Convert settings to dict
        config_dict = {}
        for section in self.get_sections():
            config_dict[section] = self.get_config(section)
            
        # Write to file
        with open(self.config_file, "w") as f:
            toml.dump(config_dict, f)
            
        self.logger.info(f"Configuration saved to {self.config_file}")
        
    def reset_to_defaults(self) -> None:
        """Reset configuration to default values."""
        # Get default config
        default_config = self.get_default_config()
        
        # Clear current settings
        for section in self.get_sections():
            del self.settings[section]
            
        # Set defaults
        for section, section_config in default_config.items():
            self.settings[section] = section_config
            
        # Clear cache
        self.config_cache = {}
        
        # Save to file
        self.save_config()
        
        self.logger.info("Configuration reset to defaults")
        
    def validate_config(self) -> None:
        """Validate configuration against schema."""
        try:
            # Convert settings to dict for validation
            config_dict = {}
            for section in self.get_sections():
                config_dict[section] = self.get_config(section)
                
            # Basic validation for required sections
            required_sections = ["core", "llm", "tts", "code_analysis", "logging"]
            for section in required_sections:
                if section not in config_dict:
                    raise ValueError(f"Required configuration section '{section}' is missing")
                    
            # Validate paths
            self._validate_paths(config_dict)
            
            self.logger.info("Configuration validation successful")
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {str(e)}")
            raise
            
    def _validate_paths(self, config: Dict[str, Any]) -> None:
        """Validate paths in configuration."""
        # Example: Validate that parent directories of required paths exist
        paths_to_check = [
            config.get("core", {}).get("plugins_dir", ""),
            config.get("core", {}).get("data_dir", ""),
            config.get("core", {}).get("cache_dir", ""),
            config.get("logging", {}).get("file", ""),
            config.get("session", {}).get("sqlite_config", {}).get("db_path", "")
        ]
        
        for path in paths_to_check:
            if path:
                # Expand user directory
                path = os.path.expanduser(path)
                
                # Check parent directory
                parent_dir = os.path.dirname(path)
                if parent_dir and not os.path.exists(parent_dir):
                    # We don't raise an error here, just create the directory
                    try:
                        os.makedirs(parent_dir, exist_ok=True)
                    except Exception as e:
                        raise ValueError(f"Failed to create directory {parent_dir}: {str(e)}")
                        
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "core": {
                "project_root": None,
                "default_mode": "developer",
                "plugins_dir": "~/.local/share/peer/plugins",
                "data_dir": "~/.local/share/peer/data",
                "cache_dir": "~/.cache/peer",
                "max_history_size": 1000,
                "auto_save_interval_seconds": 60
            },
            "cli": {
                "default_mode": "developer",
                "show_traceback": False,
                "color_output": True,
                "verbose": False
            },
            "tui": {
                "theme": "dark",
                "layout": "default",
                "auto_refresh_interval_seconds": 1,
                "max_output_lines": 1000
            },
            "api": {
                "host": "0.0.0.0",
                "port": 8000,
                "debug": False,
                "enable_docs": True,
                "cors_origins": ["*"],
                "auth_enabled": False,
                "auth_token_expiry_minutes": 60
            },
            "llm": {
                "provider": "ollama",
                "model": "codellama:7b",
                "temperature": 0.7,
                "max_tokens": 2048,
                "top_p": 0.95,
                "timeout_seconds": 60,
                "retry_attempts": 3,
                "retry_delay_seconds": 1,
                "ollama_base_url": "http://localhost:11434",
                "cache_enabled": True,
                "cache_size_mb": 1024
            },
            "tts": {
                "provider": "piper",
                "voice": "en_US-lessac-medium",
                "rate": 1.0,
                "volume": 1.0,
                "piper_model_dir": "~/.local/share/peer/tts/piper",
                "enabled": True
            },
            "code_analysis": {
                "enabled": True,
                "use_tree_sitter": True,
                "use_ruff": True,
                "use_mypy": False,
                "max_file_size_kb": 1024,
                "ignore_patterns": [
                    "**/.git/**",
                    "**/node_modules/**",
                    "**/__pycache__/**",
                    "**/.venv/**"
                ]
            },
            "session": {
                "repository_type": "sqlite",
                "sqlite_config": {
                    "db_path": "~/.local/share/peer/data/sessions.db"
                },
                "auto_save_interval_seconds": 60,
                "session_expiry_days": 30
            },
            "logging": {
                "level": "INFO",
                "file": "~/.local/share/peer/logs/peer.log",
                "max_size_mb": 10,
                "backup_count": 5,
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "console_level": "INFO"
            },
            "plugins": {
                "enabled": True,
                "auto_discover": True,
                "disabled_plugins": []
            },
            "ide_integration": {
                "vscode_extension_id": "peer-ai.peer-vscode",
                "pycharm_plugin_id": "com.peer-ai.peer-pycharm",
                "watch_file_changes": True,
                "suggest_on_save": True
            },
            "vcs": {
                "provider": "git",
                "watch_changes": True,
                "suggest_on_commit": True
            }
        }
        
    def get_section_defaults(self, section: str) -> Dict[str, Any]:
        """Get default configuration for a specific section."""
        default_config = self.get_default_config()
        if section in default_config:
            return default_config[section].copy()
        else:
            return {}
            
    def _get_default_logger(self):
        """Get a default logger when none is provided."""
        import logging
        logger = logging.getLogger("peer.config")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
```

## Implémentation du Service de Logging

Le service de logging est également un composant fondamental qui sera utilisé par tous les autres composants.

```python
# src/peer/infrastructure/services/logging_service.py

import os
import json
import logging
import threading
import time
from typing import Dict, List, Any, Optional, Type
from datetime import datetime
import structlog
from structlog.processors import TimeStamper, JSONRenderer, ExceptionPrettyPrinter
from structlog.stdlib import add_log_level, add_logger_name

class LoggingService:
    def __init__(self):
        self.config = None
        self.handlers = []
        self.processors = []
        self.metrics = None
        self.traces = None
        self.context = {}
        self._loggers = {}
        self._export_thread = None
        self._stop_event = threading.Event()
        
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the logging service."""
        self.config = config
        
        # Configure structlog
        self._configure_structlog()
        
        # Configure handlers
        self._configure_handlers()
        
        # Initialize metrics collector if enabled
        metrics_enabled = config.get("metrics_enabled", False)
        if metrics_enabled:
            self.metrics = MetricsCollector()
            self.metrics.initialize(config.get("metrics", {}))
            
        # Initialize trace collector if enabled
        traces_enabled = config.get("traces_enabled", False)
        if traces_enabled:
            self.traces = TraceCollector()
            self.traces.initialize(config.get("traces", {}))
            
        # Start export thread if metrics or traces are enabled
        if self.metrics or self.traces:
            self._start_export_thread()
            
        # Create root logger
        self.logger = self.get_logger("peer")
        self.logger.info("Logging service initialized")
        
    def _configure_structlog(self) -> None:
        """Configure structlog."""
        # Define processors
        include_timestamp = self.config.get("include_timestamp", True)
        include_level = self.config.get("include_level", True)
        include_logger_name = self.config.get("include_logger_name", True)
        json_format = self.config.get("json_format", True)
        console_color = self.config.get("console_color", True)
        
        processors = [
            # Add context from thread local storage
            structlog.threadlocal.merge_threadlocal_context,
            # Add timestamps
            TimeStamper(fmt="iso") if include_timestamp else structlog.processors.identity,
            # Add log level
            add_log_level if include_level else structlog.processors.identity,
            # Add logger name
            add_logger_name if include_logger_name else structlog.processors.identity,
            # Format exceptions
            ExceptionPrettyPrinter(),
            # Convert to JSON
            JSONRenderer() if json_format else structlog.dev.ConsoleRenderer(colors=console_color)
        ]
        
        # Configure structlog
        structlog.configure(
            processors=processors,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True
        )
        
    def _configure_handlers(self) -> None:
        """Configure log handlers."""
        # Create file handler
        file_path = self.config.get("file")
        if file_path:
            file_path = os.path.expanduser(file_path)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            file_handler = FileHandler()
            file_handler.initialize({
                "file_path": file_path,
                "max_size_mb": self.config.get("max_size_mb", 10),
                "backup_count": self.config.get("backup_count", 5),
                "format": self.config.get("format")
            })
            self.handlers.append(file_handler)
            
        # Create console handler if enabled
        console_enabled = self.config.get("console_enabled", True)
        if console_enabled:
            console_handler = ConsoleHandler()
            console_handler.initialize({
                "level": self.config.get("console_level", "INFO"),
                "format": self.config.get("format"),
                "color_enabled": self.config.get("console_color", True)
            })
            self.handlers.append(console_handler)
            
    def _start_export_thread(self) -> None:
        """Start the metrics and traces export thread."""
        def export_loop():
            while not self._stop_event.is_set():
                try:
                    # Export metrics if enabled
                    if self.metrics:
                        self.metrics.export_metrics()
                        
                    # Export traces if enabled
                    if self.traces:
                        self.traces.export_traces()
                except Exception as e:
                    self.logger.error("Error exporting metrics or traces", exception=e)
                    
                # Sleep until next export
                export_interval = self.config.get("metrics_export_interval_seconds", 60)
                self._stop_event.wait(export_interval)
                
        # Start thread
        self._export_thread = threading.Thread(target=export_loop, daemon=True)
        self._export_thread.start()
        
    def get_logger(self, name: str) -> 'Logger':
        """Get a logger instance for the specified name."""
        if name in self._loggers:
            return self._loggers[name]
            
        # Create new logger
        logger = Logger(name, self)
        self._loggers[name] = logger
        
        return logger
        
    def info(self, message: str, **kwargs: Any) -> None:
        """Log an info message."""
        self._log("INFO", message, None, **kwargs)
        
    def warn(self, message: str, **kwargs: Any) -> None:
        """Log a warning message."""
        self._log("WARNING", message, None, **kwargs)
        
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs: Any) -> None:
        """Log an error message."""
        self._log("ERROR", message, exception, **kwargs)
        
    def debug(self, message: str, **kwargs: Any) -> None:
        """Log a debug message."""
        self._log("DEBUG", message, None, **kwargs)
        
    def critical(self, message: str, **kwargs: Any) -> None:
        """Log a critical message."""
        self._log("CRITICAL", message, None, **kwargs)
        
    def _log(self, level: str, message: str, exception: Optional[Exception] = None, **kwargs: Any) -> None:
        """Internal method to log a message."""
        # Create log record
        record = LogRecord(
            timestamp=datetime.now(),
            level=level,
            message=message,
            logger_name="peer",
            context={**self.context, **kwargs},
            exception=self._format_exception(exception) if exception else None
        )
        
        # Process record
        for processor in self.processors:
            record = processor.process(record)
            
        # Send to handlers
        for handler in self.handlers:
            handler.handle(record)
            
    def _format_exception(self, exception: Exception) -> Dict[str, Any]:
        """Format an exception for logging."""
        import traceback
        return {
            "type": type(exception).__name__,
            "message": str(exception),
            "traceback": traceback.format_exception(type(exception), exception, exception.__traceback__)
        }
        
    def start_span(self, name: str, **kwargs: Any) -> Optional['Span']:
        """Start a new trace span."""
        if not self.traces:
            return None
            
        return self.traces.start_span(name, **kwargs)
        
    def record_metric(self, name: str, value: float, **kwargs: Any) -> None:
        """Record a metric."""
        if not self.metrics:
            return
            
        self.metrics.record(name, value, **kwargs)
        
    def set_context(self, key: str, value: Any) -> None:
        """Set a context value for all loggers."""
        self.context[key] = value
        structlog.threadlocal.bind_threadlocal(**{key: value})
        
    def clear_context(self) -> None:
        """Clear all context values."""
        self.context = {}
        structlog.threadlocal.clear_threadlocal()
        
    def shutdown(self) -> None:
        """Shutdown the logging service."""
        # Stop export thread
        if self._export_thread:
            self._stop_event.set()
            self._export_thread.join(timeout=5)
            
        # Export final metrics and traces
        if self.metrics:
            self.metrics.export_metrics()
            
        if self.traces:
            self.traces.export_traces()
            
        # Close handlers
        for handler in self.handlers:
            if hasattr(handler, "close"):
                handler.close()


class Logger:
    def __init__(self, name: str, service: 'LoggingService'):
        self.name = name
        self.service = service
        self.context = {}
        
    def info(self, message: str, **kwargs: Any) -> None:
        """Log an info message."""
        self._log("INFO", message, None, **kwargs)
        
    def warn(self, message: str, **kwargs: Any) -> None:
        """Log a warning message."""
        self._log("WARNING", message, None, **kwargs)
        
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs: Any) -> None:
        """Log an error message."""
        self._log("ERROR", message, exception, **kwargs)
        
    def debug(self, message: str, **kwargs: Any) -> None:
        """Log a debug message."""
        self._log("DEBUG", message, None, **kwargs)
        
    def critical(self, message: str, **kwargs: Any) -> None:
        """Log a critical message."""
        self._log("CRITICAL", message, None, **kwargs)
        
    def _log(self, level: str, message: str, exception: Optional[Exception] = None, **kwargs: Any) -> None:
        """Internal method to log a message."""
        # Create log record
        record = LogRecord(
            timestamp=datetime.now(),
            level=level,
            message=message,
            logger_name=self.name,
            context={**self.context, **kwargs},
            exception=self.service._format_exception(exception) if exception else None
        )
        
        # Process record
        for processor in self.service.processors:
            record = processor.process(record)
            
        # Send to handlers
        for handler in self.service.handlers:
            handler.handle(record)
            
    def bind(self, **kwargs: Any) -> 'Logger':
        """Create a new logger with bound context values."""
        logger = Logger(self.name, self.service)
        logger.context = {**self.context, **kwargs}
        return logger


class LogRecord:
    def __init__(self, timestamp, level, message, logger_name, context=None, exception=None,
                 thread_id=None, process_id=None, file=None, line=None, function=None):
        self.timestamp = timestamp
        self.level = level
        self.message = message
        self.logger_name = logger_name
        self.context = context or {}
        self.exception = exception
        self.thread_id = thread_id
        self.process_id = process_id
        self.file = file
        self.line = line
        self.function = function
        self.record_id = str(uuid.uuid4())
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert log record to dictionary."""
        result = {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "message": self.message,
            "logger": self.logger_name,
            "record_id": self.record_id
        }
        
        # Add optional fields if present
        if self.context:
            result["context"] = self.context
        if self.exception:
            result["exception"] = self.exception
        if self.thread_id is not None:
            result["thread_id"] = self.thread_id
        if self.process_id is not None:
            result["process_id"] = self.process_id
        if self.file:
            result["file"] = self.file
        if self.line is not None:
            result["line"] = self.line
        if self.function:
            result["function"] = self.function
            
        return result


class FileHandler:
    def __init__(self):
        self.file_path = None
        self.max_size_mb = 10
        self.backup_count = 5
        self.format = None
        self.handler = None
        
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the file handler."""
        self.file_path = os.path.expanduser(config["file_path"])
        self.max_size_mb = config.get("max_size_mb", 10)
        self.backup_count = config.get("backup_count", 5)
        self.format = config.get("format")
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        
        # Create handler
        self.handler = logging.handlers.RotatingFileHandler(
            self.file_path,
            maxBytes=self.max_size_mb * 1024 * 1024,
            backupCount=self.backup_count
        )
        
    def handle(self, record: LogRecord) -> None:
        """Handle a log record."""
        # Convert record to string
        if self.format:
            # Use custom format
            formatted_record = self._format_record(record)
        else:
            # Use JSON format
            formatted_record = json.dumps(record.to_dict())
            
        # Write to file
        self.handler.stream.write(formatted_record + "\n")
        self.handler.stream.flush()
        
    def _format_record(self, record: LogRecord) -> str:
        """Format a log record according to the specified format."""
        # Simple formatting implementation
        result = self.format
        result = result.replace("%(asctime)s", record.timestamp.strftime("%Y-%m-%d %H:%M:%S"))
        result = result.replace("%(name)s", record.logger_name)
        result = result.replace("%(levelname)s", record.level)
        result = result.replace("%(message)s", record.message)
        
        return result
        
    def close(self) -> None:
        """Close the handler."""
        if self.handler:
            self.handler.close()


class ConsoleHandler:
    def __init__(self):
        self.format = None
        self.level = "INFO"
        self.color_enabled = True
        self.colors = {
            "DEBUG": "\033[36m",     # Cyan
            "INFO": "\033[32m",      # Green
            "WARNING": "\033[33m",   # Yellow
            "ERROR": "\033[31m",     # Red
            "CRITICAL": "\033[35m",  # Magenta
            "RESET": "\033[0m"       # Reset
        }
        
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the console handler."""
        self.format = config.get("format")
        self.level = config.get("level", "INFO")
        self.color_enabled = config.get("color_enabled", True)
        
    def handle(self, record: LogRecord) -> None:
        """Handle a log record."""
        # Check level
        if not self._should_log(record.level):
            return
            
        # Convert record to string
        if self.format:
            # Use custom format
            formatted_record = self._format_record(record)
        else:
            # Use JSON format
            formatted_record = json.dumps(record.to_dict())
            
        # Add color if enabled
        if self.color_enabled:
            formatted_record = self._add_color(formatted_record, record.level)
            
        # Write to console
        print(formatted_record, file=sys.stderr if record.level in ["ERROR", "CRITICAL"] else sys.stdout)
        
    def _should_log(self, level: str) -> bool:
        """Check if the record should be logged based on level."""
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        record_level_idx = levels.index(level) if level in levels else 0
        handler_level_idx = levels.index(self.level) if self.level in levels else 0
        
        return record_level_idx >= handler_level_idx
        
    def _format_record(self, record: LogRecord) -> str:
        """Format a log record according to the specified format."""
        # Simple formatting implementation
        result = self.format
        result = result.replace("%(asctime)s", record.timestamp.strftime("%Y-%m-%d %H:%M:%S"))
        result = result.replace("%(name)s", record.logger_name)
        result = result.replace("%(levelname)s", record.level)
        result = result.replace("%(message)s", record.message)
        
        return result
        
    def _add_color(self, message: str, level: str) -> str:
        """Add color to a message based on level."""
        if level in self.colors:
            return f"{self.colors[level]}{message}{self.colors['RESET']}"
        return message


class MetricsCollector:
    def __init__(self):
        self.metrics = {}
        self.export_path = None
        self.export_interval_seconds = 60
        
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the metrics collector."""
        self.export_path = os.path.expanduser(config.get("export_path", "~/.local/share/peer/metrics"))
        self.export_interval_seconds = config.get("export_interval_seconds", 60)
        
        # Create export directory if it doesn't exist
        os.makedirs(self.export_path, exist_ok=True)
        
    def record(self, name: str, value: float, **kwargs: Any) -> None:
        """Record a metric value."""
        # Get or create metric
        if name not in self.metrics:
            # Determine metric type based on name
            if name.endswith("_count") or name.endswith("_total"):
                metric_type = "counter"
            elif name.endswith("_time") or name.endswith("_duration"):
                metric_type = "histogram"
            else:
                metric_type = "gauge"
                
            # Determine unit based on name
            if name.endswith("_time") or name.endswith("_duration"):
                unit = "seconds"
            elif name.endswith("_bytes") or name.endswith("_size"):
                unit = "bytes"
            elif name.endswith("_count") or name.endswith("_total"):
                unit = "count"
            else:
                unit = "unknown"
                
            # Create metric
            self.metrics[name] = Metric(
                name=name,
                type=metric_type,
                description=name.replace("_", " ").title(),
                unit=unit
            )
            
        # Add value to metric
        self.metrics[name].add_value(value, datetime.now(), **kwargs)
        
    def get_metric(self, name: str) -> Optional[Metric]:
        """Get a metric by name."""
        return self.metrics.get(name)
        
    def export_metrics(self) -> None:
        """Export metrics to file."""
        if not self.metrics:
            return
            
        # Create export file path
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        export_file = os.path.join(self.export_path, f"metrics-{timestamp}.json")
        
        # Export metrics
        with open(export_file, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "metrics": {name: metric.to_dict() for name, metric in self.metrics.items()}
            }, f, indent=2)


class Metric:
    def __init__(self, name, type, description, unit):
        self.name = name
        self.type = type
        self.description = description
        self.unit = unit
        self.values = []
        
    def add_value(self, value, timestamp=None, **labels):
        """Add a value to the metric."""
        self.values.append({
            "value": value,
            "timestamp": timestamp or datetime.now(),
            "labels": labels
        })
        
    def to_dict(self):
        """Convert metric to dictionary."""
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "unit": self.unit,
            "values": [
                {
                    "value": v["value"],
                    "timestamp": v["timestamp"].isoformat(),
                    "labels": v["labels"]
                }
                for v in self.values
            ]
        }


class TraceCollector:
    def __init__(self):
        self.active_spans = {}
        self.completed_spans = []
        self.export_path = None
        self.enabled = True
        self.sampling_rate = 1.0
        self.max_events_per_span = 100
        self.max_attributes_per_span = 50
        
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the trace collector."""
        self.export_path = os.path.expanduser(config.get("export_path", "~/.local/share/peer/traces"))
        self.enabled = config.get("enabled", True)
        self.sampling_rate = config.get("sampling_rate", 1.0)
        self.max_events_per_span = config.get("max_events_per_span", 100)
        self.max_attributes_per_span = config.get("max_attributes_per_span", 50)
        
        # Create export directory if it doesn't exist
        os.makedirs(self.export_path, exist_ok=True)
        
    def start_span(self, name: str, parent_id: Optional[str] = None, **attributes: Any) -> Optional[Span]:
        """Start a new span."""
        if not self.enabled:
            return None
            
        # Apply sampling
        if random.random() > self.sampling_rate:
            return None
            
        # Create span
        span_id = str(uuid.uuid4())
        span = Span(
            id=span_id,
            name=name,
            start_time=datetime.now(),
            parent_id=parent_id,
            attributes=attributes
        )
        
        # Store span
        self.active_spans[span_id] = span
        
        return span
        
    def end_span(self, span_id: str, timestamp: Optional[datetime] = None) -> None:
        """End a span."""
        if span_id not in self.active_spans:
            return
            
        # Get span
        span = self.active_spans[span_id]
        
        # End span
        span.end(timestamp)
        
        # Move to completed spans
        self.completed_spans.append(span)
        del self.active_spans[span_id]
        
    def add_event(self, span_id: str, name: str, timestamp: Optional[datetime] = None, **attributes: Any) -> None:
        """Add an event to a span."""
        if span_id not in self.active_spans:
            return
            
        # Get span
        span = self.active_spans[span_id]
        
        # Check if max events reached
        if len(span.events) >= self.max_events_per_span:
            return
            
        # Add event
        span.add_event(name, timestamp, **attributes)
        
    def set_attribute(self, span_id: str, key: str, value: Any) -> None:
        """Set an attribute on a span."""
        if span_id not in self.active_spans:
            return
            
        # Get span
        span = self.active_spans[span_id]
        
        # Check if max attributes reached
        if len(span.attributes) >= self.max_attributes_per_span:
            return
            
        # Set attribute
        span.attributes[key] = value
        
    def export_traces(self) -> None:
        """Export traces to file."""
        if not self.completed_spans:
            return
            
        # Create export file path
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        export_file = os.path.join(self.export_path, f"traces-{timestamp}.json")
        
        # Export traces
        with open(export_file, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "spans": [span.to_dict() for span in self.completed_spans]
            }, f, indent=2)
            
        # Clear completed spans
        self.completed_spans = []


class Span:
    def __init__(self, id, name, start_time, parent_id=None, attributes=None):
        self.id = id
        self.name = name
        self.start_time = start_time
        self.end_time = None
        self.parent_id = parent_id
        self.attributes = attributes or {}
        self.events = []
        self.links = []
        self.status = "unset"
        self.status_message = None
        
    def add_event(self, name, timestamp=None, **attributes):
        """Add an event to the span."""
        self.events.append({
            "name": name,
            "timestamp": timestamp or datetime.now(),
            "attributes": attributes
        })
        
    def add_link(self, span_id, **attributes):
        """Add a link to another span."""
        self.links.append({
            "span_id": span_id,
            "attributes": attributes
        })
        
    def set_status(self, status, message=None):
        """Set the status of the span."""
        self.status = status
        self.status_message = message
        
    def end(self, timestamp=None):
        """End the span."""
        self.end_time = timestamp or datetime.now()
        
    def to_dict(self):
        """Convert span to dictionary."""
        result = {
            "id": self.id,
            "name": self.name,
            "start_time": self.start_time.isoformat(),
            "attributes": self.attributes,
            "status": self.status
        }
        
        if self.end_time:
            result["end_time"] = self.end_time.isoformat()
        if self.parent_id:
            result["parent_id"] = self.parent_id
        if self.events:
            result["events"] = [
                {
                    "name": e["name"],
                    "timestamp": e["timestamp"].isoformat(),
                    "attributes": e["attributes"]
                }
                for e in self.events
            ]
        if self.links:
            result["links"] = self.links
        if self.status_message:
            result["status_message"] = self.status_message
            
        return result
```

## Implémentation du Bus d'Événements

Le bus d'événements est un composant central qui permet la communication entre les différents composants de l'architecture.

```python
# src/peer/application/event/event_bus.py

import threading
from typing import Dict, List, Any, Callable

class EventBus:
    def __init__(self):
        self.subscribers = {}
        self._lock = threading.Lock()
        
    def subscribe(self, event_type: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Subscribe to an event type."""
        with self._lock:
            if event_type not in self.subscribers:
                self.subscribers[event_type] = []
                
            if callback not in self.subscribers[event_type]:
                self.subscribers[event_type].append(callback)
                
    def unsubscribe(self, event_type: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Unsubscribe from an event type."""
        with self._lock:
            if event_type in self.subscribers and callback in self.subscribers[event_type]:
                self.subscribers[event_type].remove(callback)
                
    def publish(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Publish an event."""
        callbacks = []
        
        with self._lock:
            if event_type in self.subscribers:
                callbacks = self.subscribers[event_type].copy()
                
        for callback in callbacks:
            try:
                callback(event_data)
            except Exception as e:
                # Log error but continue with other callbacks
                print(f"Error in event handler for {event_type}: {str(e)}")
```

## Implémentation du Gestionnaire de Plugins

Le gestionnaire de plugins est un composant clé qui permet l'extensibilité de Peer.

```python
# src/peer/application/plugins/plugin_manager.py

import os
import sys
import importlib
import importlib.util
from typing import Dict, List, Any, Optional, Type
import pluggy

from peer.application.plugins.plugin_registry import PluginRegistry

class PluginManager:
    def __init__(self, config_manager, logger):
        self.config_manager = config_manager
        self.logger = logger
        self.plugin_registry = PluginRegistry()
        self.plugin_hook_spec = None
        self.plugin_manager = None
        self.loaded_plugins = {}
        
    def initialize(self) -> None:
        """Initialize the plugin manager."""
        # Get configuration
        config = self.config_manager.get_config("plugins")
        
        # Create pluggy hook specification
        self.plugin_hook_spec = pluggy.HookspecMarker("peer")
        self.plugin_hook_impl = pluggy.HookimplMarker("peer")
        
        # Create pluggy plugin manager
        self.plugin_manager = pluggy.PluginManager("peer")
        
        # Define hook specifications
        self._define_hook_specifications()
        
        # Register hook specifications
        self.plugin_manager.add_hookspecs(self)
        
        # Auto-discover plugins if enabled
        if config.get("auto_discover", True):
            self._discover_plugins()
            
        self.logger.info("Plugin manager initialized")
        
    def _define_hook_specifications(self) -> None:
        """Define hook specifications for plugins."""
        class PeerHookSpec:
            @self.plugin_hook_spec
            def peer_initialize(self, config: Dict[str, Any]) -> None:
                """Initialize the plugin."""
                
            @self.plugin_hook_spec
            def peer_shutdown(self) -> None:
                """Shutdown the plugin."""
                
            @self.plugin_hook_spec
            def peer_get_commands(self) -> List[Dict[str, Any]]:
                """Get commands provided by the plugin."""
                
            @self.plugin_hook_spec
            def peer_handle_command(self, command: str, args: List[str]) -> Any:
                """Handle a command."""
                
            @self.plugin_hook_spec
            def peer_analyze_code(self, file_path: str, content: str) -> List[Dict[str, Any]]:
                """Analyze code."""
                
            @self.plugin_hook_spec
            def peer_suggest_improvements(self, file_path: str, content: str) -> List[Dict[str, Any]]:
                """Suggest improvements for code."""
                
            @self.plugin_hook_spec
            def peer_handle_file_change(self, file_path: str, content: str) -> None:
                """Handle a file change event."""
                
            @self.plugin_hook_spec
            def peer_handle_pre_commit(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
                """Handle a pre-commit event."""
                
        # Register hook specifications
        self.plugin_manager.add_hookspecs(PeerHookSpec)
        
    def _discover_plugins(self) -> None:
        """Discover and load plugins."""
        # Get configuration
        config = self.config_manager.get_config("plugins")
        plugins_dir = os.path.expanduser(self.config_manager.get_config("core").get("plugins_dir", "~/.local/share/peer/plugins"))
        disabled_plugins = config.get("disabled_plugins", [])
        
        # Ensure plugins directory exists
        os.makedirs(plugins_dir, exist_ok=True)
        
        # Add plugins directory to Python path
        if plugins_dir not in sys.path:
            sys.path.append(plugins_dir)
            
        # Discover built-in plugins
        self._discover_builtin_plugins(disabled_plugins)
        
        # Discover external plugins
        self._discover_external_plugins(plugins_dir, disabled_plugins)
        
    def _discover_builtin_plugins(self, disabled_plugins: List[str]) -> None:
        """Discover and load built-in plugins."""
        # Get built-in plugins directory
        builtin_plugins_dir = os.path.join(os.path.dirname(__file__), "..", "..", "plugins")
        
        # Iterate over directories in built-in plugins directory
        for plugin_name in os.listdir(builtin_plugins_dir):
            # Skip disabled plugins
            if plugin_name in disabled_plugins:
                self.logger.info(f"Skipping disabled built-in plugin: {plugin_name}")
                continue
                
            # Check if directory contains plugin.py
            plugin_file = os.path.join(builtin_plugins_dir, plugin_name, "plugin.py")
            if os.path.isfile(plugin_file):
                try:
                    # Load plugin
                    module_name = f"peer.plugins.{plugin_name}.plugin"
                    plugin_module = importlib.import_module(module_name)
                    
                    # Register plugin
                    self.plugin_manager.register(plugin_module)
                    
                    # Store loaded plugin
                    self.loaded_plugins[plugin_name] = {
                        "name": plugin_name,
                        "module": plugin_module,
                        "path": plugin_file,
                        "type": "builtin"
                    }
                    
                    self.logger.info(f"Loaded built-in plugin: {plugin_name}")
                except Exception as e:
                    self.logger.error(f"Error loading built-in plugin {plugin_name}: {str(e)}")
                    
    def _discover_external_plugins(self, plugins_dir: str, disabled_plugins: List[str]) -> None:
        """Discover and load external plugins."""
        # Iterate over directories in plugins directory
        for plugin_name in os.listdir(plugins_dir):
            # Skip disabled plugins
            if plugin_name in disabled_plugins:
                self.logger.info(f"Skipping disabled external plugin: {plugin_name}")
                continue
                
            # Check if directory contains plugin.py
            plugin_dir = os.path.join(plugins_dir, plugin_name)
            plugin_file = os.path.join(plugin_dir, "plugin.py")
            
            if os.path.isdir(plugin_dir) and os.path.isfile(plugin_file):
                try:
                    # Load plugin
                    spec = importlib.util.spec_from_file_location(f"peer_plugin_{plugin_name}", plugin_file)
                    plugin_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(plugin_module)
                    
                    # Register plugin
                    self.plugin_manager.register(plugin_module)
                    
                    # Store loaded plugin
                    self.loaded_plugins[plugin_name] = {
                        "name": plugin_name,
                        "module": plugin_module,
                        "path": plugin_file,
                        "type": "external"
                    }
                    
                    self.logger.info(f"Loaded external plugin: {plugin_name}")
                except Exception as e:
                    self.logger.error(f"Error loading external plugin {plugin_name}: {str(e)}")
                    
    def get_plugin(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a plugin by name."""
        return self.loaded_plugins.get(name)
        
    def get_plugins(self) -> Dict[str, Dict[str, Any]]:
        """Get all loaded plugins."""
        return self.loaded_plugins
        
    def call_hook(self, hook_name: str, *args, **kwargs) -> Any:
        """Call a hook on all plugins."""
        hook = getattr(self.plugin_manager.hook, hook_name, None)
        if hook:
            return hook(*args, **kwargs)
        return None
        
    def shutdown(self) -> None:
        """Shutdown the plugin manager."""
        # Call shutdown hook on all plugins
        self.call_hook("peer_shutdown")
        
        self.logger.info("Plugin manager shutdown")
```

## Implémentation du Registre de Plugins

```python
# src/peer/application/plugins/plugin_registry.py

from typing import Dict, List, Any, Optional, Type

class PluginRegistry:
    def __init__(self):
        self.plugins = {}
        self.commands = {}
        
    def register_plugin(self, name: str, plugin: Any) -> None:
        """Register a plugin."""
        self.plugins[name] = plugin
        
    def unregister_plugin(self, name: str) -> None:
        """Unregister a plugin."""
        if name in self.plugins:
            del self.plugins[name]
            
        # Remove commands from this plugin
        self.commands = {cmd_name: cmd for cmd_name, cmd in self.commands.items() if cmd.get("plugin") != name}
        
    def register_command(self, name: str, command: Dict[str, Any]) -> None:
        """Register a command."""
        self.commands[name] = command
        
    def unregister_command(self, name: str) -> None:
        """Unregister a command."""
        if name in self.commands:
            del self.commands[name]
            
    def get_plugin(self, name: str) -> Optional[Any]:
        """Get a plugin by name."""
        return self.plugins.get(name)
        
    def get_plugins(self) -> Dict[str, Any]:
        """Get all registered plugins."""
        return self.plugins
        
    def get_command(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a command by name."""
        return self.commands.get(name)
        
    def get_commands(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered commands."""
        return self.commands
```

## Implémentation du Service de Base

```python
# src/peer/application/services/core_service.py

from typing import Dict, List, Any, Optional

class CoreService:
    def __init__(self, config_manager, logger, event_bus):
        self.config_manager = config_manager
        self.logger = logger
        self.event_bus = event_bus
        self.services = {}
        
    def initialize(self) -> None:
        """Initialize the core service."""
        # Get configuration
        config = self.config_manager.get_config("core")
        
        # Subscribe to events
        self.event_bus.subscribe("peer_shutdown", self.handle_shutdown)
        
        self.logger.info("Core service initialized")
        
    def register_service(self, name: str, service: Any) -> None:
        """Register a service."""
        self.services[name] = service
        self.logger.info(f"Registered service: {name}")
        
    def get_service(self, name: str) -> Optional[Any]:
        """Get a service by name."""
        return self.services.get(name)
        
    def get_services(self) -> Dict[str, Any]:
        """Get all registered services."""
        return self.services
        
    def handle_shutdown(self, event: Dict[str, Any]) -> None:
        """Handle shutdown event."""
        self.logger.info("Shutting down core service")
        
        # Shutdown all services in reverse order
        for name, service in reversed(list(self.services.items())):
            try:
                if hasattr(service, "shutdown"):
                    service.shutdown()
                    self.logger.info(f"Service {name} shutdown")
            except Exception as e:
                self.logger.error(f"Error shutting down service {name}: {str(e)}")
                
        self.logger.info("Core service shutdown complete")
        
    def shutdown(self) -> None:
        """Shutdown the core service."""
        self.event_bus.publish("peer_shutdown", {})
```

## Implémentation du Point d'Entrée Principal

```python
# src/peer/__init__.py

import os
import sys
import argparse
from typing import Dict, List, Any, Optional

from peer.application.config.config_manager import ConfigManager
from peer.infrastructure.services.logging_service import LoggingService
from peer.application.event.event_bus import EventBus
from peer.application.services.core_service import CoreService
from peer.application.plugins.plugin_manager import PluginManager
from peer.interfaces.cli.commands import register_commands

def main():
    """Main entry point for Peer."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Peer - AI Assistant for Development")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    
    # Add subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Parse arguments
    args, unknown = parser.parse_known_args()
    
    # Initialize core components
    config_manager = ConfigManager()
    config_manager.initialize()
    
    # Load configuration from file if specified
    if args.config:
        config_manager.load_config(args.config)
        
    # Initialize logging service
    logging_service = LoggingService()
    logging_service.initialize(config_manager.get_config("logging"))
    logger = logging_service.get_logger("peer")
    
    # Initialize event bus
    event_bus = EventBus()
    
    # Initialize core service
    core_service = CoreService(config_manager, logger, event_bus)
    core_service.initialize()
    
    # Register core services
    core_service.register_service("config_manager", config_manager)
    core_service.register_service("logging_service", logging_service)
    core_service.register_service("event_bus", event_bus)
    
    # Initialize plugin manager
    plugin_manager = PluginManager(config_manager, logger)
    plugin_manager.initialize()
    core_service.register_service("plugin_manager", plugin_manager)
    
    # Register CLI commands
    register_commands(subparsers, core_service)
    
    # Re-parse arguments with all commands registered
    args = parser.parse_args()
    
    # Execute command if specified
    if args.command:
        # Get command handler
        command_handler = plugin_manager.call_hook("peer_handle_command", args.command, unknown)
        
        # If no plugin handled the command, check built-in commands
        if not command_handler:
            # TODO: Handle built-in commands
            pass
    else:
        # No command specified, show help
        parser.print_help()
        
    # Shutdown core service
    core_service.shutdown()

if __name__ == "__main__":
    main()
```

## Implémentation des Commandes CLI

```python
# src/peer/interfaces/cli/commands.py

import os
import sys
from typing import Dict, List, Any, Optional

def register_commands(subparsers, core_service):
    """Register CLI commands."""
    # Get services
    logger = core_service.get_service("logging_service").get_logger("peer.cli")
    config_manager = core_service.get_service("config_manager")
    plugin_manager = core_service.get_service("plugin_manager")
    
    # Register built-in commands
    register_config_commands(subparsers, core_service)
    register_plugin_commands(subparsers, core_service)
    
    # Register plugin commands
    plugin_commands = plugin_manager.call_hook("peer_get_commands")
    if plugin_commands:
        for commands in plugin_commands:
            for command in commands:
                name = command.get("name")
                help_text = command.get("help", "")
                arguments = command.get("arguments", [])
                
                # Create subparser for command
                command_parser = subparsers.add_parser(name, help=help_text)
                
                # Add arguments
                for arg in arguments:
                    arg_name = arg.get("name")
                    arg_help = arg.get("help", "")
                    arg_type = arg.get("type", str)
                    arg_required = arg.get("required", False)
                    arg_default = arg.get("default")
                    arg_choices = arg.get("choices")
                    
                    if arg.get("positional", False):
                        command_parser.add_argument(arg_name, help=arg_help, type=arg_type, default=arg_default, choices=arg_choices)
                    else:
                        command_parser.add_argument(f"--{arg_name}", help=arg_help, type=arg_type, required=arg_required, default=arg_default, choices=arg_choices)

def register_config_commands(subparsers, core_service):
    """Register configuration commands."""
    # Get services
    logger = core_service.get_service("logging_service").get_logger("peer.cli")
    config_manager = core_service.get_service("config_manager")
    
    # Create config command
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_subparsers = config_parser.add_subparsers(dest="config_command", help="Configuration command")
    
    # Get command
    get_parser = config_subparsers.add_parser("get", help="Get configuration value")
    get_parser.add_argument("section", help="Configuration section")
    get_parser.add_argument("key", nargs="?", help="Configuration key")
    
    # Set command
    set_parser = config_subparsers.add_parser("set", help="Set configuration value")
    set_parser.add_argument("section", help="Configuration section")
    set_parser.add_argument("key", help="Configuration key")
    set_parser.add_argument("value", help="Configuration value")
    
    # List command
    list_parser = config_subparsers.add_parser("list", help="List configuration sections")
    
    # Reset command
    reset_parser = config_subparsers.add_parser("reset", help="Reset configuration to defaults")
    reset_parser.add_argument("--confirm", action="store_true", help="Confirm reset")

def register_plugin_commands(subparsers, core_service):
    """Register plugin commands."""
    # Get services
    logger = core_service.get_service("logging_service").get_logger("peer.cli")
    plugin_manager = core_service.get_service("plugin_manager")
    
    # Create plugin command
    plugin_parser = subparsers.add_parser("plugin", help="Manage plugins")
    plugin_subparsers = plugin_parser.add_subparsers(dest="plugin_command", help="Plugin command")
    
    # List command
    list_parser = plugin_subparsers.add_parser("list", help="List installed plugins")
    
    # Enable command
    enable_parser = plugin_subparsers.add_parser("enable", help="Enable a plugin")
    enable_parser.add_argument("name", help="Plugin name")
    
    # Disable command
    disable_parser = plugin_subparsers.add_parser("disable", help="Disable a plugin")
    disable_parser.add_argument("name", help="Plugin name")
```

## Fichier pyproject.toml

```toml
[build-system]
requires = ["setuptools>=42", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "peer"
version = "0.1.0"
description = "Peer - AI Assistant for Development"
readme = "README.md"
authors = [
    {name = "Peer Team", email = "info@peer-ai.com"}
]
license = {text = "MIT"}
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
]
requires-python = ">=3.9"
dependencies = [
    "dynaconf>=3.2.0",
    "toml>=0.10.2",
    "structlog>=23.1.0",
    "pluggy>=1.2.0",
    "typer>=0.9.0",
    "rich>=13.4.2",
    "textual>=0.27.0",
    "fastapi>=0.100.0",
    "uvicorn>=0.22.0",
    "sqlalchemy>=2.0.0",
    "requests>=2.31.0",
    "tree-sitter>=0.20.1",
    "ruff>=0.0.275",
    "gitpython>=3.1.31",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.3.1",
    "pytest-cov>=4.1.0",
    "black>=23.3.0",
    "isort>=5.12.0",
    "mypy>=1.3.0",
    "pre-commit>=3.3.3",
]
tts = [
    "piper-tts>=1.2.0",
]
llm = [
    "ollama>=0.1.0",
]

[project.scripts]
peer = "peer:main"

[tool.setuptools]
packages = ["peer"]
package-dir = {"" = "src"}

[tool.black]
line-length = 100
target-version = ["py39", "py310", "py311"]

[tool.isort]
profile = "black"
line_length = 100

[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_functions = "test_*"
```

## Conclusion

Cette implémentation initiale fournit la structure de base pour le projet Peer, en suivant l'architecture hexagonale et les principes définis dans les spécifications détaillées. Les composants fondamentaux comme le gestionnaire de configuration, le service de logging, le bus d'événements et le gestionnaire de plugins sont implémentés, ce qui permet de commencer à développer les autres composants de l'architecture.

Les prochaines étapes consisteront à implémenter les ports et interfaces du domaine, les services du domaine, les adaptateurs d'infrastructure, et les interfaces utilisateur, conformément au plan d'implémentation progressive.
