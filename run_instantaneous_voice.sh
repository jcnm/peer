#!/bin/bash

# Script pour lancer l'interface vocale ultra-rapide
# Ce script démarre l'interface vocale avec transcription instantanée

# Couleurs pour un meilleur affichage
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=======================================================${NC}"
echo -e "${YELLOW}    INTERFACE VOCALE ULTRA-RAPIDE                      ${NC}"
echo -e "${YELLOW}=======================================================${NC}"
echo -e "${GREEN}Interface avec transcription immédiate sans délai${NC}"
echo -e "${GREEN}Affichage en temps réel de ce qui est écouté${NC}"
echo ""

# Vérifier si le fichier Python existe
if [ ! -f "instantaneous_voice_interface.py" ]; then
    echo -e "${RED}Erreur: Le fichier instantaneous_voice_interface.py n'existe pas${NC}"
    exit 1
fi

# Activer l'environnement virtuel si nécessaire
if [ -d "vepeer" ]; then
    echo -e "${YELLOW}Activation de l'environnement virtuel...${NC}"
    source vepeer/bin/activate
fi

# Rendre le script exécutable si nécessaire
chmod +x instantaneous_voice_interface.py

echo -e "${YELLOW}Démarrage de l'interface vocale ultra-rapide...${NC}"
echo -e "${GREEN}Vous pouvez parler naturellement et voir la transcription immédiatement${NC}"
echo -e "${RED}Utilisez Ctrl+C pour arrêter l'interface${NC}"
echo ""

# Exécuter l'interface vocale
python3 instantaneous_voice_interface.py

echo ""
echo -e "${YELLOW}=======================================================${NC}"
echo -e "${GREEN}Interface vocale arrêtée${NC}"
echo -e "${YELLOW}=======================================================${NC}"
