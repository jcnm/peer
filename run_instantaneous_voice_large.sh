#!/bin/bash

# Script de lancement de l'interface vocale instantanée avec modèle LARGE-V3
# Précision maximale

echo "🚀 Lancement de l'interface vocale instantanée avec modèle LARGE-V3 (1550 MB)"
echo "📊 Modèle: large-v3 - Précision maximale, vitesse plus lente"
echo "⚠️  Attention: Premier lancement peut prendre du temps (téléchargement du modèle)"
echo ""

cd /Users/smpceo/Desktop/peer
source vepeer/bin/activate
python instantaneous_voice_interface_large.py
