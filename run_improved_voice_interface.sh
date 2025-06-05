#!/bin/bash

# Script pour démarrer l'interface vocale améliorée
# Ce script lance l'interface vocale avec les améliorations de durée d'écoute

# Couleurs pour un meilleur affichage
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=======================================================${NC}"
echo -e "${YELLOW}    INTERFACE VOCALE AMÉLIORÉE - PHRASES LONGUES       ${NC}"
echo -e "${YELLOW}=======================================================${NC}"
echo -e "${GREEN}Interface avec durée d'écoute améliorée pour capturer${NC}"
echo -e "${GREEN}des phrases complètes, même longues.${NC}"
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

echo -e "${YELLOW}Démarrage de l'interface vocale améliorée...${NC}"
echo -e "${GREEN}Vous pouvez parler naturellement, même des phrases longues${NC}"
echo -e "${RED}Utilisez Ctrl+C pour arrêter l'interface${NC}"
echo ""

# Exécuter l'interface vocale
python3 realtime_voice_interface.py

echo ""
echo -e "${YELLOW}=======================================================${NC}"
echo -e "${GREEN}Interface vocale arrêtée${NC}"
echo -e "${YELLOW}=======================================================${NC}"
