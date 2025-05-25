"""
Module de gestion de cluster multi-instance pour Peer.
Implémente un système maître/esclave pour coordination des instances.
"""

import asyncio
import json
import logging
import os
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from datetime import datetime

from .api import CommandType, InterfaceType


class InstanceStatus(Enum):
    """Status d'une instance dans le cluster"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"


class MessageType(Enum):
    """Types de messages entre instances"""
    HEARTBEAT = "heartbeat"
    COMMAND_REQUEST = "command_request"
    COMMAND_RESPONSE = "command_response"
    INSTANCE_REGISTER = "instance_register"
    INSTANCE_UNREGISTER = "instance_unregister"
    MASTER_ELECTION = "master_election"
    COORDINATION = "coordination"


@dataclass
class InstanceInfo:
    """Information sur une instance dans le cluster"""
    instance_id: int
    uuid: str
    status: InstanceStatus
    is_master: bool
    interfaces: List[InterfaceType]
    last_heartbeat: float
    load: float  # Charge CPU/mémoire 0.0-1.0
    capabilities: Set[str]
    host: str
    port: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        data = asdict(self)
        data['interfaces'] = [i.value for i in self.interfaces]
        data['capabilities'] = list(self.capabilities)
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InstanceInfo':
        """Crée depuis un dictionnaire"""
        return cls(
            instance_id=data['instance_id'],
            uuid=data['uuid'],
            status=InstanceStatus(data['status']),
            is_master=data['is_master'],
            interfaces=[InterfaceType(i) for i in data['interfaces']],
            last_heartbeat=data['last_heartbeat'],
            load=data['load'],
            capabilities=set(data['capabilities']),
            host=data['host'],
            port=data['port']
        )


@dataclass
class ClusterMessage:
    """Message échangé entre instances"""
    type: MessageType
    sender_id: int
    sender_uuid: str
    target_id: Optional[int]
    timestamp: float
    data: Dict[str, Any]
    
    def to_json(self) -> str:
        """Sérialise en JSON"""
        return json.dumps({
            'type': self.type.value,
            'sender_id': self.sender_id,
            'sender_uuid': self.sender_uuid,
            'target_id': self.target_id,
            'timestamp': self.timestamp,
            'data': self.data
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ClusterMessage':
        """Désérialise depuis JSON"""
        data = json.loads(json_str)
        return cls(
            type=MessageType(data['type']),
            sender_id=data['sender_id'],
            sender_uuid=data['sender_uuid'],
            target_id=data['target_id'],
            timestamp=data['timestamp'],
            data=data['data']
        )


class ClusterCommunication(ABC):
    """Interface abstraite pour la communication entre instances"""
    
    @abstractmethod
    async def send_message(self, message: ClusterMessage) -> bool:
        """Envoie un message à une autre instance"""
        pass
    
    @abstractmethod
    async def receive_messages(self) -> List[ClusterMessage]:
        """Reçoit les messages en attente"""
        pass
    
    @abstractmethod
    async def broadcast_message(self, message: ClusterMessage) -> int:
        """Diffuse un message à toutes les instances"""
        pass


class LocalClusterCommunication(ClusterCommunication):
    """Communication locale via fichiers pour test/développement"""
    
    def __init__(self, instance_id: int, cluster_dir: str = "/tmp/peer_cluster"):
        self.instance_id = instance_id
        self.cluster_dir = cluster_dir
        self.logger = logging.getLogger(f"ClusterComm-{instance_id}")
        
        # Créer le dossier de cluster
        os.makedirs(cluster_dir, exist_ok=True)
    
    async def send_message(self, message: ClusterMessage) -> bool:
        """Envoie via fichier local"""
        try:
            target_file = f"{self.cluster_dir}/instance_{message.target_id}_inbox.json"
            
            # Lire les messages existants
            messages = []
            try:
                with open(target_file, 'r') as f:
                    messages = json.load(f)
            except FileNotFoundError:
                pass
            
            # Ajouter le nouveau message
            messages.append(json.loads(message.to_json()))
            
            # Écrire les messages
            with open(target_file, 'w') as f:
                json.dump(messages, f, indent=2)
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            return False
    
    async def receive_messages(self) -> List[ClusterMessage]:
        """Reçoit via fichier local"""
        try:
            inbox_file = f"{self.cluster_dir}/instance_{self.instance_id}_inbox.json"
            
            if not os.path.exists(inbox_file):
                return []
            
            with open(inbox_file, 'r') as f:
                message_data = json.load(f)
            
            # Vider la boîte de réception
            os.remove(inbox_file)
            
            return [ClusterMessage.from_json(json.dumps(msg)) for msg in message_data]
        
        except Exception as e:
            self.logger.error(f"Failed to receive messages: {e}")
            return []
    
    async def broadcast_message(self, message: ClusterMessage) -> int:
        """Diffuse à toutes les instances connues"""
        sent_count = 0
        
        # Trouver toutes les instances via les fichiers
        instance_files = [f for f in os.listdir(self.cluster_dir) if f.startswith("instance_") and f.endswith("_info.json")]
        
        for file in instance_files:
            try:
                instance_id = int(file.split("_")[1])
                if instance_id != self.instance_id:
                    message.target_id = instance_id
                    if await self.send_message(message):
                        sent_count += 1
            except:
                continue
        
        return sent_count


class ClusterManager:
    """Gestionnaire principal du cluster multi-instance"""
    
    def __init__(self, instance_id: int, daemon, communication: ClusterCommunication):
        self.instance_id = instance_id
        self.daemon = daemon
        self.communication = communication
        self.logger = logging.getLogger(f"ClusterManager-{instance_id}")
        
        # État du cluster
        self.instance_uuid = str(uuid.uuid4())
        self.is_master = instance_id == 0  # Instance 0 est maître par défaut
        self.instances: Dict[int, InstanceInfo] = {}
        self.last_heartbeat = time.time()
        
        # Configuration
        self.heartbeat_interval = 5.0  # secondes
        self.heartbeat_timeout = 15.0  # secondes
        self.master_election_timeout = 10.0  # secondes
        
        # Tâches asynchrones
        self.running = False
        self.tasks: List[asyncio.Task] = []
    
    def get_instance_info(self) -> InstanceInfo:
        """Retourne les infos de cette instance"""
        return InstanceInfo(
            instance_id=self.instance_id,
            uuid=self.instance_uuid,
            status=InstanceStatus.ACTIVE,
            is_master=self.is_master,
            interfaces=[InterfaceType.CLI, InterfaceType.TUI, InterfaceType.SUI, InterfaceType.API],  # Toutes supportées
            last_heartbeat=self.last_heartbeat,
            load=0.1,  # TODO: mesure réelle
            capabilities={"command_processing", "session_management"},
            host="localhost",
            port=8000 + self.instance_id
        )
    
    async def start(self):
        """Démarre le gestionnaire de cluster"""
        self.running = True
        self.logger.info(f"Starting cluster manager for instance {self.instance_id}")
        
        # Découvrir les instances existantes d'abord
        await self._discover_existing_instances()
        
        # Enregistrer cette instance
        await self._register_instance()
        
        # Démarrer les tâches de fond
        self.tasks = [
            asyncio.create_task(self._heartbeat_loop()),
            asyncio.create_task(self._message_processor()),
            asyncio.create_task(self._health_monitor())
        ]
        
        self.logger.info(f"Cluster manager started (master: {self.is_master})")
    
    async def _discover_existing_instances(self):
        """Découvre les instances existantes dans le cluster"""
        try:
            instance_files = [f for f in os.listdir(self.communication.cluster_dir) 
                             if f.startswith("instance_") and f.endswith("_info.json")]
            
            for file in instance_files:
                try:
                    instance_id = int(file.split("_")[1])
                    if instance_id != self.instance_id:
                        # Lire les infos de l'instance
                        info_file = f"{self.communication.cluster_dir}/{file}"
                        with open(info_file, 'r') as f:
                            instance_data = json.load(f)
                        
                        # Vérifier si l'instance est récente (heartbeat récent)
                        current_time = time.time()
                        if current_time - instance_data.get('last_heartbeat', 0) < self.heartbeat_timeout:
                            instance_info = InstanceInfo.from_dict(instance_data)
                            self.instances[instance_id] = instance_info
                            self.logger.info(f"Discovered existing instance {instance_id}")
                        else:
                            # Instance trop ancienne, supprimer le fichier
                            os.remove(info_file)
                            self.logger.info(f"Removed stale instance file: {file}")
                except Exception as e:
                    self.logger.warning(f"Error processing instance file {file}: {e}")
            
            # Si on a découvert des instances, recalculer qui est le maître
            if self.instances:
                await self._trigger_master_election()
                
        except Exception as e:
            self.logger.error(f"Error discovering existing instances: {e}")
    
    async def stop(self):
        """Arrête le gestionnaire de cluster"""
        self.running = False
        self.logger.info(f"Stopping cluster manager for instance {self.instance_id}")
        
        # Désenregistrer cette instance
        await self._unregister_instance()
        
        # Arrêter les tâches
        for task in self.tasks:
            task.cancel()
        
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()
        
        self.logger.info("Cluster manager stopped")
    
    async def _register_instance(self):
        """Enregistre cette instance dans le cluster"""
        # Sauvegarder les infos localement
        info_file = f"{self.communication.cluster_dir}/instance_{self.instance_id}_info.json"
        with open(info_file, 'w') as f:
            json.dump(self.get_instance_info().to_dict(), f, indent=2)
        
        # Notifier les autres instances
        message = ClusterMessage(
            type=MessageType.INSTANCE_REGISTER,
            sender_id=self.instance_id,
            sender_uuid=self.instance_uuid,
            target_id=None,
            timestamp=time.time(),
            data=self.get_instance_info().to_dict()
        )
        
        await self.communication.broadcast_message(message)
        self.logger.info(f"Instance {self.instance_id} registered in cluster")
    
    async def _unregister_instance(self):
        """Désenregistre cette instance du cluster"""
        # Supprimer le fichier d'info
        info_file = f"{self.communication.cluster_dir}/instance_{self.instance_id}_info.json"
        try:
            os.remove(info_file)
        except FileNotFoundError:
            pass
        
        # Notifier les autres instances
        message = ClusterMessage(
            type=MessageType.INSTANCE_UNREGISTER,
            sender_id=self.instance_id,
            sender_uuid=self.instance_uuid,
            target_id=None,
            timestamp=time.time(),
            data={"instance_id": self.instance_id}
        )
        
        await self.communication.broadcast_message(message)
        self.logger.info(f"Instance {self.instance_id} unregistered from cluster")
    
    async def _heartbeat_loop(self):
        """Boucle d'envoi de heartbeat"""
        while self.running:
            try:
                await self._send_heartbeat()
                await asyncio.sleep(self.heartbeat_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(1)
    
    async def _send_heartbeat(self):
        """Envoie un heartbeat aux autres instances"""
        self.last_heartbeat = time.time()
        
        message = ClusterMessage(
            type=MessageType.HEARTBEAT,
            sender_id=self.instance_id,
            sender_uuid=self.instance_uuid,
            target_id=None,
            timestamp=self.last_heartbeat,
            data=self.get_instance_info().to_dict()
        )
        
        sent_count = await self.communication.broadcast_message(message)
        if sent_count > 0:
            self.logger.debug(f"Heartbeat sent to {sent_count} instances")
    
    async def _message_processor(self):
        """Traite les messages reçus"""
        while self.running:
            try:
                messages = await self.communication.receive_messages()
                for message in messages:
                    await self._handle_message(message)
                await asyncio.sleep(1)  # Check messages every second
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error processing messages: {e}")
                await asyncio.sleep(1)
    
    async def _handle_message(self, message: ClusterMessage):
        """Traite un message reçu"""
        if message.type == MessageType.HEARTBEAT:
            await self._handle_heartbeat(message)
        elif message.type == MessageType.INSTANCE_REGISTER:
            await self._handle_instance_register(message)
        elif message.type == MessageType.INSTANCE_UNREGISTER:
            await self._handle_instance_unregister(message)
        elif message.type == MessageType.COMMAND_REQUEST:
            await self._handle_command_request(message)
        elif message.type == MessageType.MASTER_ELECTION:
            await self._handle_master_election(message)
        else:
            self.logger.debug(f"Received message type: {message.type}")
    
    async def _handle_heartbeat(self, message: ClusterMessage):
        """Traite un heartbeat d'une autre instance"""
        instance_info = InstanceInfo.from_dict(message.data)
        self.instances[message.sender_id] = instance_info
        
        self.logger.debug(f"Received heartbeat from instance {message.sender_id}")
    
    async def _handle_instance_register(self, message: ClusterMessage):
        """Traite l'enregistrement d'une nouvelle instance"""
        instance_info = InstanceInfo.from_dict(message.data)
        self.instances[message.sender_id] = instance_info
        
        self.logger.info(f"Instance {message.sender_id} registered in cluster")
    
    async def _handle_instance_unregister(self, message: ClusterMessage):
        """Traite le désenregistrement d'une instance"""
        instance_id = message.data.get('instance_id')
        if instance_id in self.instances:
            del self.instances[instance_id]
        
        self.logger.info(f"Instance {instance_id} unregistered from cluster")
        
        # Si c'était le maître, déclencher élection
        if instance_id == 0:  # Le maître était l'instance 0
            await self._trigger_master_election()
    
    async def _handle_command_request(self, message: ClusterMessage):
        """Traite une requête de commande d'une autre instance"""
        # TODO: Implémenter le routage de commandes entre instances
        self.logger.info(f"Received command request from instance {message.sender_id}")
    
    async def _handle_master_election(self, message: ClusterMessage):
        """Traite un message d'élection de maître"""
        # TODO: Implémenter l'algorithme d'élection de maître
        self.logger.info(f"Master election message from instance {message.sender_id}")
    
    async def _health_monitor(self):
        """Surveille la santé des instances"""
        while self.running:
            try:
                current_time = time.time()
                dead_instances = []
                
                for instance_id, info in self.instances.items():
                    if current_time - info.last_heartbeat > self.heartbeat_timeout:
                        dead_instances.append(instance_id)
                
                # Nettoyer les instances mortes
                for instance_id in dead_instances:
                    del self.instances[instance_id]
                    self.logger.warning(f"Instance {instance_id} marked as dead (no heartbeat)")
                
                await asyncio.sleep(self.heartbeat_interval)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health monitor: {e}")
                await asyncio.sleep(1)
    
    async def _trigger_master_election(self):
        """Déclenche une élection de maître"""
        self.logger.info("Triggering master election")
        
        # Si pas d'autres instances, devenir maître
        if not self.instances:
            self.is_master = True
            self.logger.info(f"Instance {self.instance_id} became master (no other instances)")
            return
        
        # Sinon, instance avec l'ID le plus bas devient maître
        min_instance_id = min([self.instance_id] + list(self.instances.keys()))
        if min_instance_id == self.instance_id:
            self.is_master = True
            self.logger.info(f"Instance {self.instance_id} became master (lowest ID)")
        else:
            self.is_master = False
            self.logger.info(f"Instance {min_instance_id} is the new master")
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """Retourne le statut du cluster"""
        return {
            "local_instance": self.get_instance_info().to_dict(),
            "other_instances": {
                str(iid): info.to_dict() 
                for iid, info in self.instances.items()
            },
            "master_instance": self.instance_id if self.is_master else next(
                (iid for iid, info in self.instances.items() if info.is_master), 
                None
            ),
            "cluster_size": len(self.instances) + 1,
            "healthy_instances": len([
                info for info in self.instances.values() 
                if time.time() - info.last_heartbeat < self.heartbeat_timeout
            ]) + 1
        }
