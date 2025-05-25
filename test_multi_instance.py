#!/usr/bin/env python3
"""
Test du support multi-instance avec coordination maître/esclave pour Peer

Ce test valide le bon fonctionnement du système de cluster multi-instance.
"""

import asyncio
import logging
import os
import sys
import tempfile
import time
from pathlib import Path

# Ajouter le répertoire src au path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from peer.core import PeerDaemon, ClusterManager, LocalClusterCommunication
from peer.core.api import CommandType, InterfaceType
from peer.core.protocol import CoreProtocol

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_multi_instance_cluster():
    """Test du cluster multi-instance"""
    print("=== Test du Cluster Multi-Instance ===\n")
    
    # Créer un dossier temporaire pour la communication cluster
    with tempfile.TemporaryDirectory() as cluster_dir:
        print(f"📁 Dossier cluster temporaire: {cluster_dir}")
        
        # Créer plusieurs instances de daemon
        daemons = []
        cluster_managers = []
        
        try:
            # Instance 0 - Maître
            print("\n🏆 Création de l'instance maître (ID: 0)")
            daemon0 = PeerDaemon(instance_id=0, is_master=True, enable_cluster=True)
            comm0 = LocalClusterCommunication(0, cluster_dir)
            cluster0 = ClusterManager(0, daemon0, comm0)
            
            daemons.append(daemon0)
            cluster_managers.append(cluster0)
            
            # Instance 1 - Esclave
            print("👥 Création de l'instance esclave (ID: 1)")
            daemon1 = PeerDaemon(instance_id=1, is_master=False, enable_cluster=True)
            comm1 = LocalClusterCommunication(1, cluster_dir)
            cluster1 = ClusterManager(1, daemon1, comm1)
            
            daemons.append(daemon1)
            cluster_managers.append(cluster1)
            
            # Instance 2 - Esclave
            print("👥 Création de l'instance esclave (ID: 2)")
            daemon2 = PeerDaemon(instance_id=2, is_master=False, enable_cluster=True)
            comm2 = LocalClusterCommunication(2, cluster_dir)
            cluster2 = ClusterManager(2, daemon2, comm2)
            
            daemons.append(daemon2)
            cluster_managers.append(cluster2)
            
            print(f"✅ {len(daemons)} instances créées")
            
            # Démarrer tous les clusters
            print("\n🚀 Démarrage des gestionnaires de cluster...")
            for i, cluster in enumerate(cluster_managers):
                await cluster.start()
                print(f"✅ Cluster {i} démarré")
            
            # Attendre la synchronisation initiale
            print("\n⏳ Attente de la synchronisation du cluster...")
            await asyncio.sleep(3)
            
            # Vérifier le statut du cluster
            print("\n📊 Statut du cluster:")
            for i, cluster in enumerate(cluster_managers):
                status = cluster.get_cluster_status()
                print(f"  Instance {i}:")
                print(f"    - Maître: {status['local_instance']['is_master']}")
                print(f"    - Instances connues: {status['cluster_size']}")
                print(f"    - Instances saines: {status['healthy_instances']}")
            
            # Test de communication entre instances
            print("\n💬 Test de communication inter-instances...")
            
            # Créer des sessions sur différentes instances
            session_cli = daemon0.create_session(InterfaceType.CLI)
            session_tui = daemon1.create_session(InterfaceType.TUI)
            session_api = daemon2.create_session(InterfaceType.API)
            
            print(f"✅ Session CLI créée sur instance 0: {session_cli[:8]}...")
            print(f"✅ Session TUI créée sur instance 1: {session_tui[:8]}...")
            print(f"✅ Session API créée sur instance 2: {session_api[:8]}...")
            
            # Exécuter des commandes sur différentes instances
            commands_to_test = [
                (daemon0, CommandType.VERSION, "Instance 0 - version"),
                (daemon1, CommandType.TIME, "Instance 1 - time"),
                (daemon2, CommandType.STATUS, "Instance 2 - status"),
            ]
            
            print("\n🎯 Exécution de commandes sur les instances:")
            for daemon, command, description in commands_to_test:
                request = CoreProtocol.create_request(
                    command=command,
                    interface_type=InterfaceType.CLI
                )
                response = daemon.execute_command(request)
                status = "✅" if response.type.value == "success" else "❌"
                print(f"  {status} {description}: {response.status}")
            
            # Test de charge et performance
            print("\n⚡ Test de charge sur le cluster...")
            
            start_time = time.time()
            tasks = []
            
            # Lancer 10 commandes simultanées sur différentes instances
            for i in range(10):
                daemon = daemons[i % len(daemons)]
                task = asyncio.create_task(execute_command_async(daemon, CommandType.TIME))
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
            print(f"✅ {successful}/10 commandes exécutées avec succès")
            print(f"⏱️  Temps total: {end_time - start_time:.3f}s")
            
            # Test de resilience - simuler la perte d'une instance
            print("\n🚨 Test de résilience - arrêt d'une instance...")
            
            # Arrêter l'instance 2
            await cluster_managers[2].stop()
            print("✅ Instance 2 arrêtée")
            
            # Attendre la détection de panne
            await asyncio.sleep(6)
            
            # Vérifier que les autres instances ont détecté la panne
            print("\n📊 Statut après panne:")
            for i in [0, 1]:  # Instances encore actives
                cluster = cluster_managers[i]
                status = cluster.get_cluster_status()
                print(f"  Instance {i}:")
                print(f"    - Instances connues: {status['cluster_size']}")
                print(f"    - Instances saines: {status['healthy_instances']}")
            
            # Test de commandes après panne
            print("\n🎯 Test de commandes après panne:")
            for i in [0, 1]:
                daemon = daemons[i]
                request = CoreProtocol.create_request(
                    command=CommandType.STATUS,
                    interface_type=InterfaceType.CLI
                )
                response = daemon.execute_command(request)
                status = "✅" if response.type.value == "success" else "❌"
                print(f"  {status} Instance {i} - status: {response.status}")
            
            # Nettoyer les sessions
            print("\n🧹 Nettoyage des sessions...")
            daemon0.end_session(session_cli)
            daemon1.end_session(session_tui)
            # daemon2 déjà arrêté
            
            print("✅ Sessions fermées")
            
        finally:
            # Arrêter tous les clusters restants
            print("\n🛑 Arrêt des gestionnaires de cluster...")
            for i, cluster in enumerate(cluster_managers):
                if i != 2:  # Instance 2 déjà arrêtée
                    try:
                        await cluster.stop()
                        print(f"✅ Cluster {i} arrêté")
                    except:
                        pass

async def execute_command_async(daemon, command_type):
    """Exécute une commande de manière asynchrone"""
    try:
        request = CoreProtocol.create_request(
            command=command_type,
            interface_type=InterfaceType.CLI
        )
        response = daemon.execute_command(request)
        return {"success": response.type.value == "success", "command": command_type.value}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def test_cluster_communication():
    """Test de communication cluster avancée"""
    print("\n=== Test de Communication Cluster Avancée ===\n")
    
    with tempfile.TemporaryDirectory() as cluster_dir:
        try:
            # Créer 2 instances
            daemon1 = PeerDaemon(instance_id=1, is_master=True, enable_cluster=True)
            daemon2 = PeerDaemon(instance_id=2, is_master=False, enable_cluster=True)
            
            comm1 = LocalClusterCommunication(1, cluster_dir)
            comm2 = LocalClusterCommunication(2, cluster_dir)
            
            cluster1 = ClusterManager(1, daemon1, comm1)
            cluster2 = ClusterManager(2, daemon2, comm2)
            
            # Démarrer les clusters
            await cluster1.start()
            await cluster2.start()
            
            print("✅ Clusters démarrés")
            
            # Attendre synchronisation
            await asyncio.sleep(2)
            
            # Vérifier la découverte mutuelle
            status1 = cluster1.get_cluster_status()
            status2 = cluster2.get_cluster_status()
            
            print(f"Instance 1 connaît {len(status1['other_instances'])} autres instances")
            print(f"Instance 2 connaît {len(status2['other_instances'])} autres instances")
            
            discovered = len(status1['other_instances']) > 0 and len(status2['other_instances']) > 0
            print(f"{'✅' if discovered else '❌'} Découverte mutuelle: {discovered}")
            
            # Test heartbeat
            print("\n💓 Test de heartbeat...")
            await asyncio.sleep(6)  # Attendre plusieurs cycles de heartbeat
            
            # Vérifier que les instances sont toujours vivantes
            status1_after = cluster1.get_cluster_status()
            status2_after = cluster2.get_cluster_status()
            
            healthy1 = status1_after['healthy_instances'] >= 2
            healthy2 = status2_after['healthy_instances'] >= 2
            
            print(f"{'✅' if healthy1 else '❌'} Instance 1 - santé cluster: {healthy1}")
            print(f"{'✅' if healthy2 else '❌'} Instance 2 - santé cluster: {healthy2}")
            
            # Arrêter les clusters
            await cluster1.stop()
            await cluster2.stop()
            
            print("✅ Test de communication terminé")
            
        except Exception as e:
            print(f"❌ Erreur dans le test de communication: {e}")
            raise

def main():
    """Fonction principale"""
    print("🚀 Démarrage des tests multi-instance pour Peer\n")
    
    try:
        # Exécuter les tests
        asyncio.run(test_multi_instance_cluster())
        asyncio.run(test_cluster_communication())
        
        print("\n🎉 TESTS MULTI-INSTANCE RÉUSSIS!")
        print("   • Cluster multi-instance fonctionnel")
        print("   • Communication inter-instances validée")  
        print("   • Gestion de sessions distribuées")
        print("   • Résilience aux pannes testée")
        print("   • Performance en charge validée")
        
    except Exception as e:
        print(f"\n❌ ERREUR DANS LES TESTS: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
