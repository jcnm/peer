"""
Core Protocol and Interface Adapters

This module defines the protocol for interface adapters and provides
base classes for creating interface-specific adapters that translate
between interface formats and the unified core API.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from .api import CoreRequest, CoreResponse, CommandType, InterfaceType


class CoreProtocol:
    """
    Standard protocol for communicating with the Peer core.
    
    This class provides utility methods for creating properly formatted
    requests and handling responses according to the core protocol.
    """
    
    @staticmethod
    def create_request(
        command: CommandType,
        parameters: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        interface_type: InterfaceType = InterfaceType.INTERNAL,
        instance_id: int = 0
    ) -> CoreRequest:
        """Create a standardized core request"""
        return CoreRequest(
            command=command,
            parameters=parameters or {},
            context=context or {},
            session_id=session_id,
            interface_type=interface_type,
            instance_id=instance_id
        )
    
    @staticmethod
    def create_help_request(
        command: Optional[CommandType] = None,
        interface_type: InterfaceType = InterfaceType.INTERNAL,
        session_id: Optional[str] = None
    ) -> CoreRequest:
        """Create a help request"""
        parameters = {}
        if command:
            parameters['command'] = command.value
        
        return CoreProtocol.create_request(
            command=CommandType.HELP,
            parameters=parameters,
            interface_type=interface_type,
            session_id=session_id
        )
    
    @staticmethod
    def create_capabilities_request(
        interface_type: InterfaceType = InterfaceType.INTERNAL,
        session_id: Optional[str] = None
    ) -> CoreRequest:
        """Create a capabilities request"""
        return CoreProtocol.create_request(
            command=CommandType.CAPABILITIES,
            interface_type=interface_type,
            session_id=session_id
        )


class InterfaceAdapter(ABC):
    """
    Abstract base for interface adapters that translate between
    interface-specific formats and the unified core API.
    
    Each interface (CLI, TUI, SUI, API) should implement this adapter
    to handle the translation of commands and responses according to
    their specific conventions.
    """
    
    def __init__(self, interface_type: InterfaceType):
        self.interface_type = interface_type
        self.session_id: Optional[str] = None
    
    @abstractmethod
    def translate_to_core(self, interface_input: Any) -> CoreRequest:
        """
        Translate interface-specific input to core request
        
        Args:
            interface_input: Input in the interface's native format
            
        Returns:
            CoreRequest: Standardized request for the core
        """
        pass
    
    @abstractmethod
    def translate_from_core(self, core_response: CoreResponse) -> Any:
        """
        Translate core response to interface-specific format
        
        Args:
            core_response: Response from the core
            
        Returns:
            Interface-specific formatted response
        """
        pass
    
    @abstractmethod
    def format_help(self, help_data) -> str:
        """
        Format help information for this interface
        
        Args:
            help_data: Help data from the core (can be string or dict)
            
        Returns:
            str: Formatted help text for this interface
        """
        pass
    
    @abstractmethod
    def format_error(self, error_response) -> str:
        """
        Format error response for this interface
        
        Args:
            error_response: Error response from the core (CoreResponse or string)
            
        Returns:
            str: Formatted error message
        """
        pass
    
    def set_session_id(self, session_id: str):
        """Set the session ID for this adapter"""
        self.session_id = session_id
    
    def get_session_id(self) -> Optional[str]:
        """Get the current session ID"""
        return self.session_id


class CLIAdapter(InterfaceAdapter):
    """CLI-specific adapter for translating command line inputs"""
    
    def __init__(self):
        super().__init__(InterfaceType.CLI)
        # CLI-specific command mappings
        self.command_mappings = {
            'help': CommandType.HELP,
            'aide': CommandType.HELP,
            'status': CommandType.STATUS,
            'version': CommandType.VERSION,
            'echo': CommandType.ECHO,
            'time': CommandType.TIME,
            'heure': CommandType.TIME,
            'date': CommandType.DATE,
            'analyze': CommandType.ANALYZE,
            'analyse': CommandType.ANALYZE,
            'capabilities': CommandType.CAPABILITIES,
            'config': CommandType.CONFIG_GET,
        }
    
    def translate_to_core(self, interface_input: Dict[str, Any]) -> CoreRequest:
        """Translate CLI args to core request"""
        command_str = interface_input.get('command', 'help')
        args = interface_input.get('args', [])
        
        # Map CLI command to core command
        command_type = self.command_mappings.get(command_str.lower(), CommandType.HELP)
        
        # Build parameters from args
        parameters = {}
        if args:
            if command_type == CommandType.ECHO:
                parameters['text'] = ' '.join(args)
            elif command_type == CommandType.HELP and args:
                # Help for specific command
                help_command = self.command_mappings.get(args[0].lower())
                if help_command:
                    parameters['command'] = help_command.value
            else:
                parameters['args'] = args
        
        return CoreProtocol.create_request(
            command=command_type,
            parameters=parameters,
            interface_type=self.interface_type,
            session_id=self.session_id
        )
    
    def translate_from_core(self, core_response: CoreResponse) -> str:
        """Translate core response to CLI output"""
        if core_response.type.value == 'error':
            return f"Error: {core_response.message}"
        elif core_response.type.value == 'warning':
            return f"Warning: {core_response.message}"
        else:
            return core_response.message
    
    def format_help(self, help_data) -> str:
        """Format help for CLI"""
        if isinstance(help_data, str):
            return help_data
        
        commands = help_data.get('commands', {}) if isinstance(help_data, dict) else {}
        help_text = "Available commands:\n"
        
        for cmd_name, cmd_info in commands.items():
            description = cmd_info.get('description', 'No description')
            aliases = cmd_info.get('aliases', [])
            
            help_text += f"  {cmd_name}"
            if aliases:
                help_text += f" ({', '.join(aliases)})"
            help_text += f" - {description}\n"
        
        help_text += "\nUse 'help <command>' for detailed information about a specific command."
        return help_text
    
    def format_error(self, error_response) -> str:
        """Format error for CLI"""
        if isinstance(error_response, str):
            return f"Error: {error_response}"
        return f"Error: {error_response.message}"


class TUIAdapter(InterfaceAdapter):
    """TUI-specific adapter"""
    
    def __init__(self):
        super().__init__(InterfaceType.TUI)
    
    def translate_to_core(self, interface_input: Any) -> CoreRequest:
        """Translate TUI input to core request"""
        # TUI input would be similar to CLI but may have additional context
        if isinstance(interface_input, str):
            parts = interface_input.split()
            command_str = parts[0] if parts else 'help'
            args = parts[1:] if len(parts) > 1 else []
            
            # Use CLI adapter logic for now, can be specialized later
            cli_adapter = CLIAdapter()
            return cli_adapter.translate_to_core({
                'command': command_str,
                'args': args
            })
        
        return CoreProtocol.create_request(CommandType.HELP)
    
    def translate_from_core(self, core_response: CoreResponse) -> Dict[str, Any]:
        """Translate core response to TUI format (rich formatting data)"""
        return {
            'type': core_response.type.value,
            'status': core_response.status,
            'message': core_response.message,
            'data': core_response.data,
            'timestamp': core_response.timestamp
        }
    
    def format_help(self, help_data) -> str:
        """Format help for TUI with rich formatting"""
        if isinstance(help_data, str):
            return f"[bold blue]Help[/bold blue]\n\n{help_data}"
        
        commands = help_data.get('commands', {}) if isinstance(help_data, dict) else {}
        help_text = "[bold blue]Available Commands[/bold blue]\n\n"
        
        for cmd_name, cmd_info in commands.items():
            description = cmd_info.get('description', 'No description')
            help_text += f"[green]{cmd_name}[/green] - {description}\n"
        
        return help_text
    
    def format_error(self, error_response) -> str:
        """Format error for TUI"""
        if isinstance(error_response, str):
            return f"[red]Error:[/red] {error_response}"
        return f"[red]Error:[/red] {error_response.message}"


class SUAdapter(InterfaceAdapter):
    """SUI (Speech User Interface) specific adapter"""
    
    def __init__(self):
        super().__init__(InterfaceType.SUI)
        # SUI-specific voice command mappings
        self.voice_commands = {
            'aide': CommandType.HELP,
            'help': CommandType.HELP,
            'status': CommandType.STATUS,
            'version': CommandType.VERSION,
            'echo': CommandType.ECHO,
            'répète': CommandType.ECHO,
            'heure': CommandType.TIME,
            'time': CommandType.TIME,
            'date': CommandType.DATE,
            'analyse': CommandType.ANALYZE,
            'analyze': CommandType.ANALYZE,
        }
    
    def translate_to_core(self, interface_input: Dict[str, Any]) -> CoreRequest:
        """Translate voice input to core request"""
        text = interface_input.get('text', '').lower().strip()
        confidence = interface_input.get('confidence', 0.0)
        
        # Simple command extraction (can be made more sophisticated)
        words = text.split()
        if not words:
            return CoreProtocol.create_request(CommandType.HELP)
        
        first_word = words[0]
        command_type = self.voice_commands.get(first_word, CommandType.HELP)
        
        parameters = {
            'original_text': text,
            'confidence': confidence
        }
        
        if command_type == CommandType.ECHO and len(words) > 1:
            parameters['text'] = ' '.join(words[1:])
        elif len(words) > 1:
            parameters['args'] = words[1:]
        
        return CoreProtocol.create_request(
            command=command_type,
            parameters=parameters,
            interface_type=self.interface_type,
            session_id=self.session_id,
            context={'voice_input': True}
        )
    
    def translate_from_core(self, core_response: CoreResponse) -> Dict[str, Any]:
        """Translate core response to SUI format (voice + text)"""
        return {
            'text_response': core_response.message,
            'should_speak': True,
            'type': core_response.type.value,
            'data': core_response.data
        }
    
    def format_help(self, help_data) -> str:
        """Format help for voice output (concise)"""
        if isinstance(help_data, str):
            return help_data
        
        commands = help_data.get('commands', {}) if isinstance(help_data, dict) else {}
        
        # For voice, provide a summary of main commands
        main_commands = ['help', 'status', 'time', 'date', 'echo']
        help_text = "Commandes principales disponibles: "
        
        available_main = [cmd for cmd in main_commands if cmd in commands]
        help_text += ', '.join(available_main)
        
        help_text += ". Dites 'aide' suivi du nom d'une commande pour plus de détails."
        return help_text
    
    def format_error(self, error_response) -> str:
        """Format error for voice output"""
        if isinstance(error_response, str):
            return f"Erreur: {error_response}"
        return f"Erreur: {error_response.message}"


class APIAdapter(InterfaceAdapter):
    """REST API specific adapter"""
    
    def __init__(self):
        super().__init__(InterfaceType.API)
    
    def translate_to_core(self, interface_input: Dict[str, Any]) -> CoreRequest:
        """Translate REST API request to core request"""
        command_str = interface_input.get('command', 'help')
        parameters = interface_input.get('parameters', {})
        context = interface_input.get('context', {})
        
        # Map string command to enum
        try:
            command_type = CommandType(command_str)
        except ValueError:
            command_type = CommandType.HELP
        
        return CoreProtocol.create_request(
            command=command_type,
            parameters=parameters,
            context=context,
            interface_type=self.interface_type,
            session_id=self.session_id
        )
    
    def translate_from_core(self, core_response: CoreResponse) -> Dict[str, Any]:
        """Translate core response to REST API JSON format"""
        return core_response.to_dict()
    
    def format_help(self, help_data) -> str:
        """Format help for API (return raw data)"""
        if isinstance(help_data, str):
            return help_data
        
        import json
        return json.dumps(help_data, indent=2) if isinstance(help_data, dict) else str(help_data)
    
    def format_error(self, error_response) -> str:
        """Format error for API"""
        if isinstance(error_response, str):
            import json
            return json.dumps({"error": error_response})
        return error_response.to_json()
