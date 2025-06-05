#!/bin/bash

# Script de lancement de l'interface vocale instantanée avec modèle SMALL
# Bon compromis vitesse/précision

echo "🚀 Lancement de l'interface vocale instantanée avec modèle SMALL (244 MB)"
echo "📊 Modèle: small - Compromis vitesse/précision optimal"
echo ""

cd /Users/smpceo/Desktop/peer
source vepeer/bin/activate
python instantaneous_voice_interface_small.py
