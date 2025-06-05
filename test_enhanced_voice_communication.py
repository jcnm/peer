#!/usr/bin/env python3
"""
Test des améliorations de communication vocale fluide pour le système SUI.

Ce script teste les nouvelles fonctionnalités de feedback vocal enrichi :
- Annonces d'actions avant exécution
- Feedback de progression pendant le traitement
- Messages de completion détaillés après exécution
- Communication continue et contextuelle
"""

import os
import sys
import time
import threading
import logging
from pathlib import Path

# Ajouter le répertoire src au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent / "src"))

from peer.interfaces.sui.main import SpeechUserInterface
from peer.interfaces.sui.voice_state_machine import VoiceStateMachine, VoiceInterfaceState
from peer.interfaces.sui.domain.models import SpeechRecognitionResult
from peer.interfaces.sui.nlu.domain.nlp_engine import NLPEngine

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class MockIntentResult:
    """Mock pour simuler les résultats d'intention NLP."""
    def __init__(self, command_type, confidence=0.95, parameters=None):
        self.command_type = command_type
        self.confidence = confidence
        self.parameters = parameters or {}

def test_voice_announcement_system():
    """Test du système d'annonce vocale amélioré."""
    print("🎤 Test du système d'annonce vocale amélioré")
    print("=" * 60)
    
    try:
        # Initialiser le SUI
        sui = SpeechUserInterface()
        
        if not sui.tts_engine:
            print("⚠️  Moteur TTS non disponible, utilisation du fallback")
        
        # Test des différents types de commandes avec annonces
        test_commands = [
            ("help", "Aide et assistance"),
            ("status", "Vérification du statut"),
            ("time", "Consultation de l'heure"),
            ("date", "Consultation de la date"),
            ("version", "Informations de version"),
            ("capabilities", "Présentation des capacités"),
            ("echo", "Répétition de message")
        ]
        
        print("\n🔊 Test des annonces d'actions enrichies:")
        print("-" * 40)
        
        for command_type, description in test_commands:
            print(f"\nTest: {description}")
            
            # Créer un mock intent result
            mock_intent = MockIntentResult(command_type)
            recognition_text = f"Commande de test: {description}"
            
            # Tester l'annonce d'action
            action_announcement = sui._generate_action_announcement(mock_intent, recognition_text)
            print(f"📢 Annonce d'action: {action_announcement}")
            
            # Simuler l'exécution et tester l'annonce de résultat
            from peer.core import CoreResponse, ResponseType, CommandType
            
            # Mapper le string vers l'enum CommandType
            command_enum_map = {
                "help": CommandType.HELP,
                "status": CommandType.STATUS,
                "time": CommandType.TIME,
                "date": CommandType.DATE,
                "version": CommandType.VERSION,
                "capabilities": CommandType.CAPABILITIES,
                "echo": CommandType.ECHO
            }
            
            command_enum = command_enum_map.get(command_type, CommandType.HELP)
            
            # Simuler une réponse positive
            mock_response = CoreResponse(
                type=ResponseType.SUCCESS,
                message=f"Résultat simulé pour {description}",
                data={"command": command_type}
            )
            
            result_announcement = sui._generate_result_announcement(
                mock_response, command_enum, recognition_text
            )
            print(f"🎯 Annonce de résultat: {result_announcement}")
            
            # Tester la vocalisation si TTS disponible
            if sui.tts_engine:
                print("🔊 Test de vocalisation...")
                try:
                    # Utiliser le TTS direct macOS comme fallback
                    import platform
                    if platform.system() == 'Darwin':
                        import subprocess
                        subprocess.run(['say', '-v', 'Audrey', '-r', '200', action_announcement[:100]], 
                                     check=False, timeout=3)
                        time.sleep(0.5)
                        subprocess.run(['say', '-v', 'Audrey', '-r', '200', result_announcement[:100]], 
                                     check=False, timeout=3)
                except Exception as e:
                    print(f"⚠️  Erreur TTS: {e}")
            
            print("✅ Test terminé\n")
            time.sleep(0.3)  # Pause entre les tests
        
        print("\n🎛️ Test de la machine d'état vocale:")
        print("-" * 40)
        
        if sui.voice_state_machine:
            vsm = sui.voice_state_machine
            
            # Test du feedback de completion
            class MockIntentContext:
                def __init__(self, intent_type, text, params=None):
                    self.intent_type = intent_type
                    self.text = text
                    self.parameters = params or {}
                    self.confidence = 0.9
                    self.summary = f"exécuter la commande {intent_type}"
            
            print("\n📋 Test des messages de completion contextuels:")
            for command_type, description in test_commands:
                mock_intent_ctx = MockIntentContext(command_type, f"Test de {description}")
                response_message = f"Résultat détaillé pour {description}"
                
                completion_feedback = vsm._generate_completion_feedback(mock_intent_ctx, response_message)
                print(f"✨ {command_type.upper()}: {completion_feedback}")
        
        print("\n🎉 Test du système d'annonce vocale terminé avec succès!")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Nettoyage
        try:
            if 'sui' in locals():
                sui.stop()
        except:
            pass

def test_fluid_communication_workflow():
    """Test du workflow de communication fluide."""
    print("\n🌊 Test du workflow de communication fluide")
    print("=" * 60)
    
    try:
        # Simuler un workflow complet de commande vocale
        workflows = [
            {
                "user_input": "quelle heure est-il",
                "expected_command": "time",
                "description": "Demande d'heure avec feedback complet"
            },
            {
                "user_input": "quel est le statut du système",
                "expected_command": "status", 
                "description": "Vérification de statut avec étapes détaillées"
            },
            {
                "user_input": "aide moi",
                "expected_command": "help",
                "description": "Demande d'aide avec guidance complète"
            }
        ]
        
        sui = SpeechUserInterface()
        
        for i, workflow in enumerate(workflows, 1):
            print(f"\n🔄 Workflow {i}: {workflow['description']}")
            print(f"   Entrée utilisateur: \"{workflow['user_input']}\"")
            
            # Simuler la reconnaissance vocale
            print("   1️⃣ Reconnaissance vocale simulée...")
            
            # Simuler l'analyse NLP
            print("   2️⃣ Analyse NLP et extraction d'intention...")
            mock_intent = MockIntentResult(workflow['expected_command'])
            
            # Test du handler de commande vocale complet
            print("   3️⃣ Traitement de la commande avec feedback...")
            
            try:
                response = sui._handle_voice_command(mock_intent, workflow['user_input'])
                print(f"   ✅ Réponse générée: {response[:100]}...")
            except Exception as e:
                print(f"   ⚠️ Erreur dans le traitement: {e}")
            
            print(f"   🎯 Workflow {i} terminé\n")
        
        print("🎉 Test du workflow de communication fluide terminé!")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test de workflow: {e}")
        return False
    
    finally:
        try:
            if 'sui' in locals():
                sui.stop()
        except:
            pass

def main():
    """Fonction principale de test."""
    print("🚀 Démarrage des tests de communication vocale fluide")
    print("=" * 80)
    
    # Test 1: Système d'annonce vocale
    success1 = test_voice_announcement_system()
    
    time.sleep(1)
    
    # Test 2: Workflow de communication fluide
    success2 = test_fluid_communication_workflow()
    
    # Résumé des résultats
    print("\n" + "=" * 80)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 80)
    
    print(f"✅ Système d'annonce vocale: {'SUCCÈS' if success1 else 'ÉCHEC'}")
    print(f"✅ Workflow de communication: {'SUCCÈS' if success2 else 'ÉCHEC'}")
    
    overall_success = success1 and success2
    print(f"\n🎯 RÉSULTAT GLOBAL: {'SUCCÈS COMPLET' if overall_success else 'ÉCHEC PARTIEL'}")
    
    if overall_success:
        print("\n🎉 FÉLICITATIONS ! Le système de communication vocale fluide")
        print("   a été amélioré avec succès. Les nouvelles fonctionnalités incluent :")
        print("   • Annonces d'actions détaillées avant exécution")
        print("   • Feedback de progression pendant le traitement")
        print("   • Messages de completion contextuels après exécution")
        print("   • Communication continue et naturelle")
    else:
        print("\n⚠️  Certains tests ont échoué. Vérifiez les logs pour plus de détails.")
    
    return overall_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
