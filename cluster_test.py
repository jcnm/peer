#!/usr/bin/env python3
"""
Script de test manuel pour le cluster multi-instance Peer.
Permet de démarrer et tester des instances en interactif.
"""

import asyncio
import json
import sys
import time
from pathlib import Path

# Ajouter le src au path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from peer.core import PeerDaemon, ClusterManager, LocalClusterCommunication
from peer.core.api import CoreRequest, CommandType, InterfaceType


class ClusterTestShell:
    def __init__(self):
        self.instances = {}
        self.cluster_dir = "/tmp/peer_cluster_manual"
        
    async def start_instance(self, instance_id: int):
        """Démarre une nouvelle instance"""
        if instance_id in self.instances:
            print(f"❌ Instance {instance_id} déjà active")
            return
            
        # Créer l'instance
        communication = LocalClusterCommunication(instance_id, self.cluster_dir)
        daemon = PeerDaemon(
            instance_id=instance_id,
            is_master=(instance_id == 0),
            enable_cluster=True,
            cluster_communication=communication
        )
        
        # Démarrer le cluster
        await daemon.start_cluster()
        
        self.instances[instance_id] = daemon
        print(f"✅ Instance {instance_id} démarrée")
        
    async def stop_instance(self, instance_id: int):
        """Arrête une instance"""
        if instance_id not in self.instances:
            print(f"❌ Instance {instance_id} non trouvée")
            return
            
        daemon = self.instances[instance_id]
        await daemon.stop_cluster()
        del self.instances[instance_id]
        print(f"✅ Instance {instance_id} arrêtée")
        
    async def cluster_status(self):
        """Affiche le statut du cluster"""
        print("\n📊 Statut du Cluster:")
        print("=" * 50)
        
        for instance_id, daemon in self.instances.items():
            status = daemon.get_cluster_status()
            print(f"  Instance {instance_id}:")
            print(f"    - Maître: {status.get('local_instance', {}).get('is_master', False)}")
            print(f"    - Taille cluster: {status.get('cluster_size', 0)}")
            print(f"    - Instances saines: {status.get('healthy_instances', 0)}")
            
            other_instances = status.get('other_instances', {})
            if other_instances:
                print(f"    - Autres instances: {list(other_instances.keys())}")
            else:
                print(f"    - Autres instances: Aucune")
        print()
        
    async def test_command(self, instance_id: int, command: str):
        """Test une commande sur une instance"""
        if instance_id not in self.instances:
            print(f"❌ Instance {instance_id} non trouvée")
            return
            
        daemon = self.instances[instance_id]
        
        # Créer une session
        session_id = daemon.create_session(InterfaceType.CLI)
        
        # Exécuter la commande
        request = CoreRequest(
            command=CommandType(command),
            data={},
            interface=InterfaceType.CLI,
            session_id=session_id
        )
        
        response = daemon.execute_command(request)
        print(f"🎯 Instance {instance_id} - {command}: {response.status}")
        
        if response.data:
            print(f"    Données: {json.dumps(response.data, indent=2)}")
        
        # Fermer la session
        daemon.end_session(session_id)
        
    def print_help(self):
        """Affiche l'aide"""
        print("""
🔧 Commandes disponibles:
  start <id>     - Démarre une instance avec l'ID spécifié
  stop <id>      - Arrête l'instance avec l'ID spécifié
  status         - Affiche le statut du cluster
  test <id> <cmd> - Exécute une commande sur une instance
  instances      - Liste les instances actives
  clear          - Efface la console
  help           - Affiche cette aide
  quit           - Quitte le shell

📝 Exemples:
  start 0        - Démarre l'instance maître
  start 1        - Démarre une instance esclave
  status         - Montre l'état du cluster
  test 0 version - Teste la commande version sur l'instance 0
  test 1 time    - Teste la commande time sur l'instance 1
        """)
        
    async def run_shell(self):
        """Lance le shell interactif"""
        print("🚀 Shell de Test Cluster Multi-Instance Peer")
        print("Type 'help' pour voir les commandes disponibles")
        self.print_help()
        
        while True:
            try:
                command = input("\n> ").strip().lower()
                
                if not command:
                    continue
                    
                parts = command.split()
                cmd = parts[0]
                
                if cmd == "quit" or cmd == "exit":
                    break
                elif cmd == "help":
                    self.print_help()
                elif cmd == "clear":
                    print("\n" * 50)
                elif cmd == "instances":
                    print(f"Instances actives: {list(self.instances.keys())}")
                elif cmd == "status":
                    await self.cluster_status()
                elif cmd == "start" and len(parts) == 2:
                    try:
                        instance_id = int(parts[1])
                        await self.start_instance(instance_id)
                    except ValueError:
                        print("❌ ID d'instance invalide")
                elif cmd == "stop" and len(parts) == 2:
                    try:
                        instance_id = int(parts[1])
                        await self.stop_instance(instance_id)
                    except ValueError:
                        print("❌ ID d'instance invalide")
                elif cmd == "test" and len(parts) == 3:
                    try:
                        instance_id = int(parts[1])
                        command_name = parts[2]
                        await self.test_command(instance_id, command_name)
                    except ValueError:
                        print("❌ ID d'instance invalide")
                    except Exception as e:
                        print(f"❌ Erreur lors de l'exécution: {e}")
                else:
                    print("❌ Commande inconnue. Tapez 'help' pour l'aide.")
                    
            except KeyboardInterrupt:
                break
            except EOFError:
                break
            except Exception as e:
                print(f"❌ Erreur: {e}")
                
        # Nettoyage
        print("\n🧹 Arrêt de toutes les instances...")
        for instance_id in list(self.instances.keys()):
            await self.stop_instance(instance_id)
        print("👋 Au revoir!")


async def main():
    """Point d'entrée principal"""
    shell = ClusterTestShell()
    await shell.run_shell()


if __name__ == "__main__":
    asyncio.run(main())
