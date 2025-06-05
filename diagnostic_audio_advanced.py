#!/usr/bin/env python3
"""
Script de diagnostic avancé pour la capture audio et la détection de parole.
Affiche en temps réel les niveaux d'énergie et le statut de détection de parole.
"""

import os
import sys
import time
import logging

# Configuration des logs
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Ajouter le chemin source pour l'importation
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, 'src'))
sys.path.insert(0, current_dir)

try:
    from peer.interfaces.sui.stt.audio_io import AudioCapture, AudioFormat, VADMode
    print("✅ Modules importés avec succès")
except ImportError as e:
    print(f"❌ Erreur d'importation: {e}")
    sys.exit(1)

def main():
    print("\n" + "="*80)
    print("🎙️ DIAGNOSTIC AVANCÉ DE CAPTURE AUDIO")
    print("="*80)
    
    # Configuration audio avec sensibilité très élevée
    audio_config = {
        'sample_rate': AudioFormat.SAMPLE_RATE,
        'channels': AudioFormat.CHANNELS,
        'chunk_size': 1600,  # 100ms @ 16kHz
        'vad_sensitivity': 3  # TRÈS AGRESSIF - Mode le plus sensible
    }
    
    # Créer le gestionnaire de capture audio
    audio_capture = AudioCapture(audio_config)
    
    # Lister les périphériques audio
    devices = audio_capture.list_audio_devices()
    print(f"\n📱 Périphériques audio disponibles: {len(devices)}")
    for idx, device in devices.items():
        print(f"   {idx}: {device['name']} ({device['channels']} ch, {device['sample_rate']}Hz)")
    
    print("\n🧪 Test du microphone pendant 3 secondes...")
    mic_test = audio_capture.test_microphone(duration=3.0)
    
    if not mic_test['success']:
        print(f"❌ Échec du test microphone: {mic_test.get('error', 'Erreur inconnue')}")
        return
    
    print("✅ Test microphone réussi:")
    print(f"   Durée: {mic_test['duration']:.2f}s")
    print(f"   Segments: {mic_test['segments_count']}")
    print(f"   Segments avec parole: {mic_test['speech_segments']} ({mic_test['speech_ratio']:.1%})")
    print(f"   Énergie moyenne: {mic_test['avg_energy']:.3f}")
    print(f"   Énergie min/max: {mic_test['min_energy']:.3f} / {mic_test['max_energy']:.3f}")
    
    print("\n🎤 Démarrage de la capture audio continue...")
    print("Parlez dans le microphone, je vais afficher les niveaux d'énergie et la détection de parole")
    print("Appuyez sur Ctrl+C pour terminer")
    
    if not audio_capture.start_recording():
        print("❌ Impossible de démarrer l'enregistrement")
        return
    
    try:
        # Variables de suivi
        total_segments = 0
        speech_segments = 0
        start_time = time.time()
        energies = []
        
        # Affichage des statistiques
        last_stats_time = time.time()
        stats_interval = 5.0  # Afficher les stats toutes les 5 secondes
        
        while True:
            segment = audio_capture.get_audio_segment(timeout=0.5)
            if not segment:
                continue
            
            total_segments += 1
            if segment.has_speech:
                speech_segments += 1
                status = "🗣️ PAROLE"
            else:
                status = "🔇 Silence"
            
            energies.append(segment.energy_level)
            
            # Affichage en temps réel
            energy_bar = "█" * int(segment.energy_level * 50)
            print(f"\r{status} | Énergie: {segment.energy_level:.3f} {energy_bar}", end="")
            
            # Affichage périodique des statistiques
            current_time = time.time()
            if current_time - last_stats_time >= stats_interval:
                speech_ratio = speech_segments / total_segments if total_segments > 0 else 0
                avg_energy = sum(energies) / len(energies) if energies else 0
                
                print("\n\n--- Statistiques ---")
                print(f"Durée: {current_time - start_time:.1f}s")
                print(f"Total segments: {total_segments}")
                print(f"Segments avec parole: {speech_segments} ({speech_ratio:.1%})")
                print(f"Énergie moyenne: {avg_energy:.3f}")
                if energies:
                    print(f"Énergie min/max: {min(energies):.3f} / {max(energies):.3f}")
                print("-------------------\n")
                
                # Réinitialiser pour la prochaine période
                last_stats_time = current_time
                
    except KeyboardInterrupt:
        print("\n\n⌨️ Arrêt demandé")
    finally:
        audio_capture.stop_recording()
        
        # Statistiques finales
        duration = time.time() - start_time
        speech_ratio = speech_segments / total_segments if total_segments > 0 else 0
        avg_energy = sum(energies) / len(energies) if energies else 0
        
        print("\n" + "="*80)
        print("📊 RÉSULTATS DU DIAGNOSTIC")
        print("="*80)
        print(f"Durée: {duration:.1f}s")
        print(f"Segments analysés: {total_segments}")
        print(f"Segments avec parole: {speech_segments} ({speech_ratio:.1%})")
        print(f"Taux de segments: {total_segments/duration:.1f} segments/seconde")
        print(f"Énergie moyenne: {avg_energy:.3f}")
        if energies:
            print(f"Énergie min/max: {min(energies):.3f} / {max(energies):.3f}")
        
        print("\n✅ Diagnostic terminé")

if __name__ == "__main__":
    main()
