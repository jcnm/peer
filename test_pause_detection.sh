#!/bin/bash

# Script pour tester l'interface vocale optimisée pour les pauses
# Ce script lance l'interface vocale avec les modifications pour réduire le décalage

# Couleurs pour un meilleur affichage
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=======================================================${NC}"
echo -e "${YELLOW}    INTERFACE VOCALE OPTIMISÉE POUR LES PAUSES         ${NC}"
echo -e "${YELLOW}=======================================================${NC}"
echo -e "${GREEN}Cette version finalise rapidement les transcriptions${NC}"
echo -e "${GREEN}après une pause détectée (>1s) pour réduire le décalage.${NC}"
echo ""

# Vérifier si le fichier Python existe
if [ ! -f "realtime_voice_interface.py" ]; then
    echo -e "${RED}Erreur: Le fichier realtime_voice_interface.py n'existe pas${NC}"
    exit 1
fi

# Activer l'environnement virtuel si nécessaire
if [ -d "vepeer" ]; then
    echo -e "${YELLOW}Activation de l'environnement virtuel...${NC}"
    source vepeer/bin/activate
fi

echo -e "${YELLOW}Instructions de test:${NC}"
echo -e "${GREEN}1. Parlez puis faites une pause de plus d'une seconde${NC}"
echo -e "${GREEN}2. Observez que le système finalise la transcription rapidement${NC}"
echo -e "${GREEN}3. Comparez la réactivité avec la version précédente${NC}"
echo ""
echo -e "${RED}Utilisez Ctrl+C pour arrêter l'interface${NC}"
echo ""

# Exécuter l'interface vocale
python3 realtime_voice_interface.py

echo ""
echo -e "${YELLOW}=======================================================${NC}"
echo -e "${GREEN}Interface vocale arrêtée${NC}"
echo -e "${YELLOW}=======================================================${NC}"
