#!/bin/bash

# Script de sélection de modèle WhisperX pour l'interface vocale

echo "🎙️ INTERFACE VOCALE INSTANTANÉE - SÉLECTION DE MODÈLE WHISPERX"
echo "=================================================================="
echo ""
echo "Modèles disponibles:"
echo ""
echo "1. 🏃‍♂️ TINY (39 MB) - Vitesse maximale"
echo "   • ./run_instantaneous_voice.sh"
echo "   • Idéal pour: Tests rapides, réactivité maximale"
echo ""
echo "2. 🚀 SMALL (244 MB) - Compromis optimal"
echo "   • ./run_instantaneous_voice_small.sh"
echo "   • Idéal pour: Usage quotidien, bon équilibre"
echo ""
echo "3. 🎯 MEDIUM (769 MB) - Précision améliorée"
echo "   • ./run_instantaneous_voice_medium.sh"
echo "   • Idéal pour: Dictée, transcription importante"
echo ""
echo "4. 🏆 LARGE-V3 (1550 MB) - Précision maximale"
echo "   • ./run_instantaneous_voice_large.sh"
echo "   • Idéal pour: Qualité professionnelle"
echo ""
echo "=================================================================="
echo "💡 Conseil: Commencez par SMALL pour un bon compromis."
echo "⚠️  Plus gros = plus précis mais plus lent"
echo ""

read -p "Quel modèle voulez-vous lancer? (tiny/small/medium/large): " choice

case $choice in
    "tiny")
        echo "🏃‍♂️ Lancement du modèle TINY..."
        ./run_instantaneous_voice.sh
        ;;
    "small")
        echo "🚀 Lancement du modèle SMALL..."
        ./run_instantaneous_voice_small.sh
        ;;
    "medium")
        echo "🎯 Lancement du modèle MEDIUM..."
        ./run_instantaneous_voice_medium.sh
        ;;
    "large")
        echo "🏆 Lancement du modèle LARGE-V3..."
        ./run_instantaneous_voice_large.sh
        ;;
    *)
        echo "❌ Choix invalide. Options: tiny, small, medium, large"
        exit 1
        ;;
esac
