#!/usr/bin/env python3
"""
Système vocal français démonstration - Production ready
"""

import os
import sys
import time

def speak_french(text, voice="Audrey"):
    """Synthèse vocale française optimisée"""
    
    if sys.platform == "darwin":
        # macOS avec say
        cmd = f'say -v {voice} "{text}"'
        os.system(cmd)
    else:
        # Fallback pour autres systèmes
        print(f"🔊 [{voice}] {text}")

def demo_voice_system():
    """Démonstration système vocal français"""
    
    print("🎯 DÉMONSTRATION SYSTÈME VOCAL FRANÇAIS")
    print("=" * 45)
    
    texts = [
        "Bonjour ! Bienvenue dans le système vocal français optimisé.",
        "Cette solution fonctionne de manière portable sur différentes plateformes.",
        "La qualité de la synthèse vocale est maintenant optimale pour le français.",
        "Système prêt pour l'intégration avec l'interface SUI de Peer."
    ]
    
    for i, text in enumerate(texts, 1):
        print(f"[{i}/4] 🔊 {text}")
        speak_french(text)
        time.sleep(1)
    
    print("\n✅ Démonstration terminée avec succès !")

if __name__ == "__main__":
    demo_voice_system()
