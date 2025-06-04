#!/usr/bin/env python3
import os
import time

def demo():
    print("🎯 SYSTÈME VOCAL FRANÇAIS PEER - DÉMONSTRATION")
    print("=" * 50)
    
    messages = [
        "Système vocal français activé.",
        "Interface Peer SUI opérationnelle.",
        "Voix française premium disponible.",
        "Démonstration terminée avec succès."
    ]
    
    for i, msg in enumerate(messages, 1):
        print(f"[{i}/4] {msg}")
        os.system(f'say -v Audrey "{msg}"')
        time.sleep(1)
    
    print("\n✅ Système prêt pour utilisation !")

if __name__ == "__main__":
    demo()
