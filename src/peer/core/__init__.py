"""
Peer Core Module - Central daemon/service that provides unified API

This module contains the core daemon that acts as the central hub for all
Peer functionality. All interfaces communicate with this daemon through
a standardized protocol.
"""

from .daemon import PeerDaemon, get_daemon, shutdown_daemon
from .api import CoreAPI, CoreRequest, CoreResponse, CommandType, ResponseType, InterfaceType
from .protocol import CoreProtocol, InterfaceAdapter, CLIAdapter, TUIAdapter, SUAdapter, APIAdapter
from .cluster import ClusterManager, LocalClusterCommunication, InstanceInfo, ClusterMessage, MessageType, InstanceStatus

__all__ = [
    'PeerDaemon',
    'get_daemon',
    'shutdown_daemon',
    'CoreAPI', 
    'CoreRequest', 
    'CoreResponse', 
    'CommandType', 
    'ResponseType',
    'InterfaceType',
    'CoreProtocol',
    'InterfaceAdapter',
    'CLIAdapter',
    'TUIAdapter', 
    'SUAdapter',
    'APIAdapter',
    'ClusterManager',
    'LocalClusterCommunication',
    'InstanceInfo',
    'ClusterMessage',
    'MessageType',
    'InstanceStatus'
]
