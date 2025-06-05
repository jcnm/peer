#!/bin/bash
# Script de lancement de l'interface vocale temps réel avec WhisperX

# Vérifier si l'environnement virtuel existe
if [ ! -d "vepeer" ]; then
    echo "❌ L'environnement virtuel n'existe pas. Exécutez d'abord install.sh."
    exit 1
fi

# Activer l'environnement virtuel
source vepeer/bin/activate

echo "🚀 Lancement de l'interface vocale temps réel avec WhisperX..."
echo "📋 Fonctionnalités:"
echo "   • Communication orale bidirectionnelle en français"
echo "   • Transcription en temps réel avec gestion des pauses"
echo "   • Batching intelligent des segments de parole"
echo "   • Affichage progressif de la transcription"
echo ""
echo "🎙️ Préparez-vous à parler... L'interface va démarrer."
echo ""

# Lancer l'interface
python realtime_voice_interface.py

echo ""
echo "👋 Interface fermée. À bientôt!"
