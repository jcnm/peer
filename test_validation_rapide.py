#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de validation rapide du système vocal français
Version simplifiée et fonctionnelle
"""

import sys
import os
import subprocess
import time
from pathlib import Path

def test_quick_french_voice():
    """Test rapide du système vocal français"""
    
    print("🎯 TEST RAPIDE SYSTÈME VOCAL FRANÇAIS")
    print("=" * 45)
    
    # Test 1: Vérification de la voix Audrey
    print("\n1️⃣ Test voix Audrey (macOS)...")
    try:
        result = subprocess.run([
            'say', '-v', 'Audrey', 
            'Test rapide de validation du système vocal français haute qualité.'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ Voix Audrey : Fonctionnelle")
            audrey_ok = True
        else:
            print(f"❌ Voix Audrey : Erreur - {result.stderr}")
            audrey_ok = False
    except Exception as e:
        print(f"❌ Voix Audrey : Exception - {e}")
        audrey_ok = False
    
    # Test 2: Configuration SUI
    print("\n2️⃣ Test configuration SUI...")
    config_file = Path("/Users/smpceo/.peer/config/sui/models.yaml")
    
    if config_file.exists():
        print(f"✅ Configuration SUI trouvée : {config_file}")
        config_ok = True
    else:
        print(f"❌ Configuration SUI manquante : {config_file}")
        config_ok = False
    
    # Test 3: Script SUI
    print("\n3️⃣ Test script de lancement SUI...")
    sui_script = Path("/Users/smpceo/Desktop/peer/run_sui.sh")
    
    if sui_script.exists():
        print(f"✅ Script SUI trouvé : {sui_script}")
        script_ok = True
    else:
        print(f"❌ Script SUI manquant : {sui_script}")
        script_ok = False
    
    # Test 4: Test de synthèse complète
    print("\n4️⃣ Test synthèse française complète...")
    try:
        phrases = [
            "Bonjour ! Système vocal français opérationnel.",
            "La qualité de synthèse est maintenant optimale.",
            "Assistant prêt pour les commandes vocales."
        ]
        
        syntheses_ok = 0
        for i, phrase in enumerate(phrases, 1):
            print(f"   [{i}/3] Synthèse : {phrase[:30]}...")
            try:
                subprocess.run([
                    'say', '-v', 'Audrey', '-r', '200', phrase
                ], timeout=8, check=True)
                syntheses_ok += 1
                print(f"   ✅ Synthèse {i} réussie")
            except:
                print(f"   ❌ Synthèse {i} échouée")
        
        synthesis_ok = syntheses_ok >= 2
        print(f"📊 Synthèses réussies : {syntheses_ok}/3")
        
    except Exception as e:
        print(f"❌ Erreur test synthèse : {e}")
        synthesis_ok = False
    
    # Calcul du score
    tests = [audrey_ok, config_ok, script_ok, synthesis_ok]
    score = sum(tests) / len(tests)
    
    print(f"\n🏆 RÉSULTAT VALIDATION RAPIDE")
    print("=" * 35)
    print(f"Score : {sum(tests)}/{len(tests)} ({score*100:.0f}%)")
    
    if score >= 0.75:
        print("🎉 ✅ SYSTÈME VOCAL FRANÇAIS VALIDÉ !")
        print("🚀 Prêt pour utilisation avec ./run_sui.sh")
        
        # Test final avec message de réussite
        print("\n🔊 Message de validation finale...")
        try:
            subprocess.run([
                'say', '-v', 'Audrey', '-r', '200',
                'Félicitations ! Le système vocal français haute qualité est maintenant opérationnel et prêt pour l\'utilisation en production.'
            ], timeout=15)
        except:
            pass
        
        return True
    else:
        print("⚠️ ❌ Système nécessite des corrections")
        print("💡 Vérifiez les composants en échec")
        return False

def show_next_steps():
    """Affiche les prochaines étapes"""
    
    print("\n📋 PROCHAINES ÉTAPES RECOMMANDÉES")
    print("=" * 40)
    print("1. Démarrer SUI : ./run_sui.sh")
    print("2. Tester commandes vocales en français")
    print("3. Utiliser la voix Audrey pour la meilleure qualité")
    print("4. Configurer selon vos préférences")
    print()
    print("🎯 COMMANDES UTILES :")
    print("   • Test vocal : python demo_voice_system.py")
    print("   • Démo production : python demo_production_ready.py")
    print("   • Configuration : ~/.peer/config/sui/models.yaml")

def main():
    """Point d'entrée principal"""
    
    print("🚀 VALIDATION RAPIDE SYSTÈME VOCAL FRANÇAIS")
    print("=" * 50)
    print("🎯 Test des composants essentiels")
    print()
    
    try:
        success = test_quick_french_voice()
        
        if success:
            show_next_steps()
            print("\n✨ VALIDATION RÉUSSIE ! ✨")
            return 0
        else:
            print("\n🔧 CORRECTIONS NÉCESSAIRES")
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️ Test interrompu")
        return 130
    except Exception as e:
        print(f"\n💥 Erreur : {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
