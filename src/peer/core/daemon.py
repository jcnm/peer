"""
Peer Core Daemon - Central service that implements the unified API

This daemon acts as the central hub for all Peer functionality.
All interfaces communicate with this daemon through the standardized protocol.
"""

import asyncio
import logging
import threading
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

from .api import (
    CoreAPI, CoreRequest, CoreResponse, CommandType, ResponseType, 
    InterfaceType, CommandCapability
)
from .cluster import ClusterManager, LocalClusterCommunication
from ..domain.services.command_service import CommandService
from ..domain.services.message_service import MessageService
from ..domain.services.system_check_service import SystemCheckService
from ..infrastructure.adapters.simple_system_check_adapter import SimpleSystemCheckAdapter


class PeerDaemon(CoreAPI):
    """
    Central Peer daemon that implements the unified API.
    
    This daemon coordinates all Peer functionality and provides a standardized
    interface for all user interfaces (CLI, TUI, SUI, API).
    """
    
    def __init__(self, instance_id: int = 0, is_master: bool = True, enable_cluster: bool = False):
        """
        Initialize the Peer daemon.
        
        Args:
            instance_id: Unique identifier for this daemon instance
            is_master: Whether this is the master instance (default: True)
            enable_cluster: Whether to enable multi-instance cluster support
        """
        self.instance_id = instance_id
        self.is_master = is_master
        self.enable_cluster = enable_cluster
        self.version = "0.3.0"  # Version du daemon
        self.logger = logging.getLogger(f"PeerDaemon-{instance_id}")
        
        # Shutdown management
        self._should_shutdown = False
        self.shutdown_event = threading.Event()
        
        # Initialize core services
        self._init_services()
        
        # Session management
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.session_lock = threading.Lock()
        
        # Command capabilities registry
        self.capabilities = self._register_capabilities()
        
        # Cluster management (optional)
        self.cluster_manager: Optional[ClusterManager] = None
        if enable_cluster:
            self._init_cluster()
        
        self.logger.info(f"Peer daemon initialized (instance {instance_id}, master: {is_master}, cluster: {enable_cluster})")
    
    def get_version(self) -> str:
        """Get daemon version"""
        return self.version
    
    def get_shutdown_event(self) -> threading.Event:
        """Get the shutdown event for external monitoring"""
        return self.shutdown_event
    
    def should_shutdown(self) -> bool:
        """Check if daemon should shutdown"""
        return self._should_shutdown
    
    def _init_services(self):
        """Initialize all core services"""
        try:
            self.command_service = CommandService()
            self.message_service = MessageService()
            self.system_check_service = SystemCheckService(SimpleSystemCheckAdapter())
            self.logger.info("Core services initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize core services: {e}")
            raise
    
    def _init_cluster(self):
        """Initialize cluster management"""
        try:
            communication = LocalClusterCommunication(self.instance_id)
            self.cluster_manager = ClusterManager(self.instance_id, self, communication)
            self.logger.info(f"Cluster manager initialized for instance {self.instance_id}")
        except Exception as e:
            self.logger.error(f"Failed to initialize cluster: {e}")
            self.enable_cluster = False
            raise

    def _register_capabilities(self) -> Dict[str, CommandCapability]:
        """Register all available command capabilities"""
        capabilities = {}
        
        # Help commands
        capabilities['help'] = CommandCapability(
            command=CommandType.HELP,
            description="Get help information about available commands",
            parameters=['command'],
            examples=['help', 'help status'],
            aliases=['aide'],
            category="system"
        )
        
        # System commands
        capabilities['status'] = CommandCapability(
            command=CommandType.STATUS,
            description="Get system status and health information",
            examples=['status'],
            category="system"
        )
        
        capabilities['version'] = CommandCapability(
            command=CommandType.VERSION,
            description="Get Peer version information",
            examples=['version'],
            category="system"
        )
        
        capabilities['capabilities'] = CommandCapability(
            command=CommandType.CAPABILITIES,
            description="List all available commands and their capabilities",
            examples=['capabilities'],
            category="system"
        )
        
        # Utility commands
        capabilities['echo'] = CommandCapability(
            command=CommandType.ECHO,
            description="Echo back the provided text",
            parameters=['text'],
            required_parameters=['text'],
            examples=['echo Hello World'],
            aliases=['répète'],
            category="utility"
        )
        
        capabilities['time'] = CommandCapability(
            command=CommandType.TIME,
            description="Get current time",
            examples=['time'],
            aliases=['heure'],
            category="utility"
        )
        
        capabilities['date'] = CommandCapability(
            command=CommandType.DATE,
            description="Get current date",
            examples=['date'],
            category="utility"
        )
        
        # Session management
        capabilities['session_create'] = CommandCapability(
            command=CommandType.SESSION_CREATE,
            description="Create a new session",
            parameters=['interface_type'],
            category="session",
            available_in_interfaces=[InterfaceType.API, InterfaceType.INTERNAL]
        )
        
        capabilities['session_end'] = CommandCapability(
            command=CommandType.SESSION_END,
            description="End a session",
            parameters=['session_id'],
            category="session"
        )
        
        capabilities['session_info'] = CommandCapability(
            command=CommandType.SESSION_INFO,
            description="Get session information",
            examples=['session_info'],
            category="session"
        )
        
        # Cluster management commands
        capabilities['cluster_status'] = CommandCapability(
            command=CommandType.CLUSTER_STATUS,
            description="Get cluster status and information",
            examples=['cluster_status'],
            category="cluster"
        )
        
        capabilities['cluster_instances'] = CommandCapability(
            command=CommandType.CLUSTER_INSTANCES,
            description="List all cluster instances",
            examples=['cluster_instances'],
            category="cluster"
        )
        
        capabilities['cluster_start'] = CommandCapability(
            command=CommandType.CLUSTER_START,
            description="Start cluster management",
            examples=['cluster_start'],
            category="cluster"
        )
        
        capabilities['cluster_stop'] = CommandCapability(
            command=CommandType.CLUSTER_STOP,
            description="Stop cluster management",
            examples=['cluster_stop'],
            category="cluster"
        )
        
        return capabilities
    
    def execute_command(self, request: CoreRequest) -> CoreResponse:
        """
        Execute a command and return response.
        
        Args:
            request: Standardized core request
            
        Returns:
            CoreResponse: Standardized response
        """
        self.logger.info(f"Executing command: {request.command.value} from {request.interface_type.value}")
        
        try:
            # Route command to appropriate handler
            if request.command == CommandType.HELP:
                return self._handle_help(request)
            elif request.command == CommandType.STATUS:
                return self._handle_status(request)
            elif request.command == CommandType.VERSION:
                return self._handle_version(request)
            elif request.command == CommandType.CAPABILITIES:
                return self._handle_capabilities(request)
            elif request.command == CommandType.ECHO:
                return self._handle_echo(request)
            elif request.command == CommandType.TIME:
                return self._handle_time(request)
            elif request.command == CommandType.DATE:
                return self._handle_date(request)
            elif request.command == CommandType.QUIT:
                return self._handle_quit(request)
            elif request.command == CommandType.SESSION_CREATE:
                return self._handle_session_create(request)
            elif request.command == CommandType.SESSION_END:
                return self._handle_session_end(request)
            elif request.command == CommandType.SESSION_INFO:
                return self._handle_session_info(request)
            elif request.command == CommandType.CLUSTER_STATUS:
                return self._handle_cluster_status(request)
            elif request.command == CommandType.CLUSTER_INSTANCES:
                return self._handle_cluster_instances(request)
            elif request.command == CommandType.CLUSTER_START:
                return self._handle_cluster_start(request)
            elif request.command == CommandType.CLUSTER_STOP:
                return self._handle_cluster_stop(request)
            else:
                return CoreResponse(
                    type=ResponseType.ERROR,
                    status="unknown_command",
                    message=f"Unknown command: {request.command.value}",
                    request_id=request.request_id,
                    instance_id=self.instance_id
                )
                
        except Exception as e:
            self.logger.error(f"Error executing command {request.command.value}: {e}")
            return CoreResponse(
                type=ResponseType.ERROR,
                status="execution_error",
                message=f"Error executing command: {str(e)}",
                request_id=request.request_id,
                instance_id=self.instance_id
            )
    
    def _handle_help(self, request: CoreRequest) -> CoreResponse:
        """Handle help command"""
        command_param = request.parameters.get('command')
        interface_type = request.interface_type
        
        if command_param:
            # Help for specific command
            if command_param in self.capabilities:
                capability = self.capabilities[command_param]
                help_data = {
                    'command': capability.command.value,
                    'description': capability.description,
                    'parameters': capability.parameters,
                    'required_parameters': capability.required_parameters,
                    'examples': capability.examples,
                    'aliases': capability.aliases,
                    'category': capability.category
                }
            else:
                return CoreResponse(
                    type=ResponseType.ERROR,
                    status="command_not_found",
                    message=f"Command '{command_param}' not found",
                    request_id=request.request_id,
                    instance_id=self.instance_id
                )
        else:
            # General help - list all commands available for this interface
            available_commands = {}
            for cmd_name, capability in self.capabilities.items():
                if (not capability.available_in_interfaces or 
                    interface_type in capability.available_in_interfaces):
                    available_commands[cmd_name] = {
                        'description': capability.description,
                        'category': capability.category,
                        'aliases': capability.aliases
                    }
            
            help_data = {
                'commands': available_commands,
                'interface_type': interface_type.value,
                'total_commands': len(available_commands)
            }
        
        return CoreResponse(
            type=ResponseType.SUCCESS,
            status="help_provided",
            message="Help information retrieved",
            data=help_data,
            request_id=request.request_id,
            session_id=request.session_id,
            instance_id=self.instance_id
        )
    
    def _handle_status(self, request: CoreRequest) -> CoreResponse:
        """Handle status command"""
        try:
            # Get system status from system check service
            system_status = self.system_check_service.check_system()
            
            status_data = {
                'instance_id': self.instance_id,
                'is_master': self.is_master,
                'system_health': system_status.to_dict() if hasattr(system_status, 'to_dict') else str(system_status),
                'active_sessions': len(self.sessions),
                'uptime': self._get_uptime(),
                'version': self.get_version()
            }
            
            return CoreResponse(
                type=ResponseType.SUCCESS,
                status="status_retrieved",
                message="System status retrieved successfully",
                data=status_data,
                request_id=request.request_id,
                session_id=request.session_id,
                instance_id=self.instance_id
            )
        except Exception as e:
            self.logger.error(f"Error getting status: {e}")
            return CoreResponse(
                type=ResponseType.ERROR,
                status="status_error",
                message=f"Failed to retrieve status: {str(e)}",
                request_id=request.request_id,
                session_id=request.session_id,
                instance_id=self.instance_id
            )
    
    def _handle_version(self, request: CoreRequest) -> CoreResponse:
        """Handle version command"""
        version = self.get_version()
        return CoreResponse(
            type=ResponseType.SUCCESS,
            status="version_retrieved",
            message=f"Peer version {version}",
            data={'version': version},
            request_id=request.request_id,
            session_id=request.session_id,
            instance_id=self.instance_id
        )
    
    def _handle_capabilities(self, request: CoreRequest) -> CoreResponse:
        """Handle capabilities command"""
        capabilities_data = {}
        for cmd_name, capability in self.capabilities.items():
            capabilities_data[cmd_name] = {
                'command': capability.command.value,
                'description': capability.description,
                'parameters': capability.parameters,
                'required_parameters': capability.required_parameters,
                'examples': capability.examples,
                'aliases': capability.aliases,
                'category': capability.category,
                'available_in_interfaces': [iface.value for iface in capability.available_in_interfaces]
            }
        
        return CoreResponse(
            type=ResponseType.SUCCESS,
            status="capabilities_retrieved",
            message=f"Retrieved {len(capabilities_data)} command capabilities",
            data={
                'capabilities': capabilities_data,
                'categories': list(set(cap.category for cap in self.capabilities.values()))
            },
            request_id=request.request_id,
            session_id=request.session_id,
            instance_id=self.instance_id
        )
    
    def _handle_echo(self, request: CoreRequest) -> CoreResponse:
        """Handle echo command"""
        text = request.parameters.get('text', '')
        if not text:
            return CoreResponse(
                type=ResponseType.ERROR,
                status="missing_parameter",
                message="Echo command requires text parameter",
                request_id=request.request_id,
                instance_id=self.instance_id
            )
        
        return CoreResponse(
            type=ResponseType.SUCCESS,
            status="echo_success",
            message=text,
            data={'original_text': text},
            request_id=request.request_id,
            session_id=request.session_id,
            instance_id=self.instance_id
        )
    
    def _handle_time(self, request: CoreRequest) -> CoreResponse:
        """Handle time command"""
        # Use the existing command service for consistency
        result = self.command_service._cmd_time([])
        return CoreResponse(
            type=ResponseType.SUCCESS,
            status="time_retrieved",
            message=result,
            data={'timestamp': datetime.now().isoformat()},
            request_id=request.request_id,
            session_id=request.session_id,
            instance_id=self.instance_id
        )
    
    def _handle_date(self, request: CoreRequest) -> CoreResponse:
        """Handle date command"""
        # Use the existing command service for consistency
        result = self.command_service._cmd_date([])
        return CoreResponse(
            type=ResponseType.SUCCESS,
            status="date_retrieved",
            message=result,
            data={'date': datetime.now().strftime('%d/%m/%Y')},
            request_id=request.request_id,
            session_id=request.session_id,
            instance_id=self.instance_id
        )
    
    def _handle_session_create(self, request: CoreRequest) -> CoreResponse:
        """Handle session creation"""
        interface_type = request.interface_type
        session_id = self.create_session(interface_type)
        
        return CoreResponse(
            type=ResponseType.SUCCESS,
            status="session_created",
            message=f"Session created for {interface_type.value}",
            data={'session_id': session_id, 'interface_type': interface_type.value},
            request_id=request.request_id,
            session_id=session_id,
            instance_id=self.instance_id
        )
    
    def _handle_session_end(self, request: CoreRequest) -> CoreResponse:
        """Handle session termination"""
        session_id = request.session_id or request.parameters.get('session_id')
        
        if not session_id:
            return CoreResponse(
                type=ResponseType.ERROR,
                status="missing_session_id",
                message="Session ID required to end session",
                request_id=request.request_id,
                instance_id=self.instance_id
            )
        
        success = self.end_session(session_id)
        
        if success:
            return CoreResponse(
                type=ResponseType.SUCCESS,
                status="session_ended",
                message="Session ended successfully",
                request_id=request.request_id,
                instance_id=self.instance_id
            )
        else:
            return CoreResponse(
                type=ResponseType.ERROR,
                status="session_not_found",
                message="Session not found or already ended",
                request_id=request.request_id,
                instance_id=self.instance_id
            )
    
    def _handle_session_info(self, request: CoreRequest) -> CoreResponse:
        """Handle session info request"""
        session_id = request.session_id
        
        if not session_id:
            # Return info about all sessions
            sessions_info = {}
            with self.session_lock:
                for sid, session_data in self.sessions.items():
                    sessions_info[sid] = {
                        'interface_type': session_data['interface_type'],
                        'created_at': session_data['created_at'],
                        'last_activity': session_data.get('last_activity', session_data['created_at'])
                    }
            
            return CoreResponse(
                type=ResponseType.SUCCESS,
                status="sessions_info_retrieved",
                message=f"Retrieved info for {len(sessions_info)} sessions",
                data={'sessions': sessions_info, 'total_sessions': len(sessions_info)},
                request_id=request.request_id,
                instance_id=self.instance_id
            )
        else:
            # Return info about specific session
            with self.session_lock:
                if session_id in self.sessions:
                    session_data = self.sessions[session_id].copy()
                    return CoreResponse(
                        type=ResponseType.SUCCESS,
                        status="session_info_retrieved",
                        message="Session info retrieved",
                        data={'session': session_data},
                        request_id=request.request_id,
                        session_id=session_id,
                        instance_id=self.instance_id
                    )
                else:
                    return CoreResponse(
                        type=ResponseType.ERROR,
                        status="session_not_found",
                        message="Session not found",
                        request_id=request.request_id,
                        instance_id=self.instance_id
                    )
    
    def _handle_quit(self, request: CoreRequest) -> CoreResponse:
        """Handle quit command"""
        self.logger.info("Quit command received - initiating shutdown")
        
        # Set shutdown flags
        self._should_shutdown = True
        self.shutdown_event.set()
        
        return CoreResponse(
            type=ResponseType.QUIT,
            status="shutdown_initiated",
            message="Interface arrêtée à la demande de l'utilisateur. À bientôt !",
            data={'quit': True, 'farewell': True, 'shutdown': True},
            request_id=request.request_id,
            session_id=request.session_id,
            instance_id=self.instance_id
        )
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get available commands and their capabilities"""
        return {cmd_name: capability.__dict__ for cmd_name, capability in self.capabilities.items()}
    
    def get_status(self, instance_id: int = 0) -> Dict[str, Any]:
        """Get core status and health"""
        if instance_id != self.instance_id and instance_id != 0:
            return {'error': f'Instance {instance_id} not found'}
        
        return {
            'instance_id': self.instance_id,
            'is_master': self.is_master,
            'active_sessions': len(self.sessions),
            'uptime': self._get_uptime(),
            'version': self.get_version(),
            'status': 'healthy'
        }
    
    def get_help(self, command: Optional[CommandType] = None, interface_type: InterfaceType = InterfaceType.INTERNAL) -> Dict[str, Any]:
        """Get help information about commands"""
        if command:
            cmd_name = command.value
            if cmd_name in self.capabilities:
                capability = self.capabilities[cmd_name]
                return {
                    'command': capability.command.value,
                    'description': capability.description,
                    'parameters': capability.parameters,
                    'examples': capability.examples,
                    'aliases': capability.aliases
                }
            else:
                return {'error': f'Command {cmd_name} not found'}
        else:
            # Return all commands for the interface
            available_commands = {}
            for cmd_name, capability in self.capabilities.items():
                if (not capability.available_in_interfaces or 
                    interface_type in capability.available_in_interfaces):
                    available_commands[cmd_name] = {
                        'description': capability.description,
                        'category': capability.category
                    }
            return {'commands': available_commands}
    
    def create_session(self, interface_type: InterfaceType) -> str:
        """Create a new session and return session ID"""
        session_id = str(uuid.uuid4())
        
        with self.session_lock:
            self.sessions[session_id] = {
                'id': session_id,
                'interface_type': interface_type.value,
                'created_at': datetime.now().isoformat(),
                'instance_id': self.instance_id
            }
        
        self.logger.info(f"Created session {session_id} for {interface_type.value}")
        return session_id
    
    def end_session(self, session_id: str) -> bool:
        """End a session"""
        with self.session_lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                self.logger.info(f"Ended session {session_id}")
                return True
            return False
    
    # Cluster Management Methods
    
    async def start_cluster(self):
        """Start cluster manager if enabled"""
        if self.cluster_manager:
            await self.cluster_manager.start()
            self.logger.info(f"Cluster started for instance {self.instance_id}")
    
    async def stop_cluster(self):
        """Stop cluster manager if enabled"""
        if self.cluster_manager:
            await self.cluster_manager.stop()
            self.logger.info(f"Cluster stopped for instance {self.instance_id}")
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get cluster status information"""
        if not self.cluster_manager:
            return {"cluster_enabled": False, "message": "Cluster not enabled"}
        
        return self.cluster_manager.get_cluster_status()
    
    def is_cluster_master(self) -> bool:
        """Check if this instance is the cluster master"""
        if self.cluster_manager:
            return self.cluster_manager.is_master
        return self.is_master
    
    def get_cluster_instances(self) -> Dict[int, Dict[str, Any]]:
        """Get information about all cluster instances"""
        if not self.cluster_manager:
            return {self.instance_id: {"is_master": self.is_master, "status": "standalone"}}
        
        cluster_status = self.cluster_manager.get_cluster_status()
        instances = {}
        
        # Add local instance
        instances[self.instance_id] = cluster_status["local_instance"]
        
        # Add other instances
        for instance_id, info in cluster_status["other_instances"].items():
            instances[int(instance_id)] = info
        
        return instances

    def get_version(self) -> str:
        """Get core version"""
        return "0.3.0"  # Updated version to reflect new architecture
    
    def _get_uptime(self) -> str:
        """Get daemon uptime (placeholder)"""
        # TODO: Implement actual uptime tracking
        return "Unknown"

    def _handle_cluster_status(self, request: CoreRequest) -> CoreResponse:
        """Handle cluster status command"""
        if not self.enable_cluster or not self.cluster_manager:
            return CoreResponse(
                type=ResponseType.ERROR,
                status="cluster_disabled",
                message="Cluster functionality is not enabled",
                request_id=request.request_id,
                instance_id=self.instance_id
            )
        
        try:
            cluster_status = self.cluster_manager.get_cluster_status()
            return CoreResponse(
                type=ResponseType.SUCCESS,
                status="cluster_status_retrieved",
                message="Cluster status retrieved successfully",
                data=cluster_status,
                request_id=request.request_id,
                session_id=request.session_id,
                instance_id=self.instance_id
            )
        except Exception as e:
            self.logger.error(f"Error getting cluster status: {e}")
            return CoreResponse(
                type=ResponseType.ERROR,
                status="cluster_status_error",
                message=f"Error retrieving cluster status: {str(e)}",
                request_id=request.request_id,
                instance_id=self.instance_id
            )

    def _handle_cluster_instances(self, request: CoreRequest) -> CoreResponse:
        """Handle cluster instances command"""
        if not self.enable_cluster or not self.cluster_manager:
            return CoreResponse(
                type=ResponseType.ERROR,
                status="cluster_disabled",
                message="Cluster functionality is not enabled",
                request_id=request.request_id,
                instance_id=self.instance_id
            )
        
        try:
            instances = self.get_cluster_instances()
            return CoreResponse(
                type=ResponseType.SUCCESS,
                status="cluster_instances_retrieved",
                message="Cluster instances retrieved successfully",
                data={"instances": instances},
                request_id=request.request_id,
                session_id=request.session_id,
                instance_id=self.instance_id
            )
        except Exception as e:
            self.logger.error(f"Error getting cluster instances: {e}")
            return CoreResponse(
                type=ResponseType.ERROR,
                status="cluster_instances_error",
                message=f"Error retrieving cluster instances: {str(e)}",
                request_id=request.request_id,
                instance_id=self.instance_id
            )

    def _handle_cluster_start(self, request: CoreRequest) -> CoreResponse:
        """Handle cluster start command"""
        if not self.enable_cluster or not self.cluster_manager:
            return CoreResponse(
                type=ResponseType.ERROR,
                status="cluster_disabled",
                message="Cluster functionality is not enabled",
                request_id=request.request_id,
                instance_id=self.instance_id
            )
        
        try:
            # Start cluster if not already running
            if not self.cluster_manager.is_running:
                asyncio.create_task(self.cluster_manager.start())
                message = "Cluster start initiated"
            else:
                message = "Cluster is already running"
            
            return CoreResponse(
                type=ResponseType.SUCCESS,
                status="cluster_start_initiated",
                message=message,
                request_id=request.request_id,
                session_id=request.session_id,
                instance_id=self.instance_id
            )
        except Exception as e:
            self.logger.error(f"Error starting cluster: {e}")
            return CoreResponse(
                type=ResponseType.ERROR,
                status="cluster_start_error",
                message=f"Error starting cluster: {str(e)}",
                request_id=request.request_id,
                instance_id=self.instance_id
            )

    def _handle_cluster_stop(self, request: CoreRequest) -> CoreResponse:
        """Handle cluster stop command"""
        if not self.enable_cluster or not self.cluster_manager:
            return CoreResponse(
                type=ResponseType.ERROR,
                status="cluster_disabled",
                message="Cluster functionality is not enabled",
                request_id=request.request_id,
                instance_id=self.instance_id
            )
        
        try:
            # Stop cluster if running
            if self.cluster_manager.is_running:
                asyncio.create_task(self.cluster_manager.stop())
                message = "Cluster stop initiated"
            else:
                message = "Cluster is not running"
            
            return CoreResponse(
                type=ResponseType.SUCCESS,
                status="cluster_stop_initiated",
                message=message,
                request_id=request.request_id,
                session_id=request.session_id,
                instance_id=self.instance_id
            )
        except Exception as e:
            self.logger.error(f"Error stopping cluster: {e}")
            return CoreResponse(
                type=ResponseType.ERROR,
                status="cluster_stop_error",
                message=f"Error stopping cluster: {str(e)}",
                request_id=request.request_id,
                instance_id=self.instance_id
            )


# Global daemon instance (singleton pattern)
_daemon_instance: Optional[PeerDaemon] = None
_daemon_lock = threading.Lock()


def get_daemon(instance_id: int = 0, is_master: bool = True) -> PeerDaemon:
    """
    Get or create the global daemon instance.
    
    Args:
        instance_id: Instance ID for the daemon
        is_master: Whether this should be the master instance
        
    Returns:
        PeerDaemon: The daemon instance
    """
    global _daemon_instance
    
    with _daemon_lock:
        if _daemon_instance is None:
            _daemon_instance = PeerDaemon(instance_id=instance_id, is_master=is_master)
        return _daemon_instance


def shutdown_daemon():
    """Shutdown the global daemon instance"""
    global _daemon_instance
    
    with _daemon_lock:
        if _daemon_instance:
            # Set shutdown flags
            _daemon_instance._should_shutdown = True
            _daemon_instance.shutdown_event.set()
            
            # End all sessions
            for session_id in list(_daemon_instance.sessions.keys()):
                _daemon_instance.end_session(session_id)
            
            _daemon_instance.logger.info("Daemon shutdown")
            _daemon_instance = None
