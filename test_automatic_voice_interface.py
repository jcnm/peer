#!/usr/bin/env python3
"""
Test automatique de l'interface vocale en temps réel 
avec arrêt propre après un certain temps.
"""

import os
import sys
import time
import logging
import threading

# Ajouter le chemin source pour l'importation
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, 'src'))
sys.path.insert(0, current_dir)

# Configuration des logs
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Importer l'interface vocale
try:
    from realtime_voice_interface import RealTimeSpeechInterface
    print("✅ Interface vocale importée avec succès")
except ImportError as e:
    print(f"❌ Erreur d'importation: {e}")
    sys.exit(1)

def main():
    print("\n" + "="*80)
    print("🎙️ TEST AUTOMATIQUE DE L'INTERFACE VOCALE EN TEMPS RÉEL")
    print("="*80)
    
    # Durée du test en secondes
    test_duration = 30
    
    print(f"Démarrage du test pour {test_duration} secondes...")
    
    # Créer et démarrer l'interface
    interface = RealTimeSpeechInterface()
    
    # Définir un timer pour arrêter l'interface après la durée spécifiée
    def stop_interface():
        time.sleep(test_duration)
        print("\n\n⏰ Temps écoulé, arrêt de l'interface...")
        interface.stop()
    
    # Démarrer le timer dans un thread séparé
    timer_thread = threading.Thread(target=stop_interface, daemon=True)
    timer_thread.start()
    
    # Démarrer l'interface
    try:
        interface.start()
    except KeyboardInterrupt:
        print("\n⌨️ Arrêt demandé par l'utilisateur")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    print("\n" + "="*80)
    print("✅ TEST TERMINÉ")
    print("="*80)

if __name__ == "__main__":
    main()
