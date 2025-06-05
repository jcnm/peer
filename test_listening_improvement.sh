#!/bin/bash

# Script pour tester les améliorations de la durée d'écoute
# Ce script exécute le test d'amélioration de la durée d'écoute et sauvegarde les résultats

# Couleurs pour un meilleur affichage
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=======================================================${NC}"
echo -e "${YELLOW}    TEST D'AMÉLIORATION DE LA DURÉE D'ÉCOUTE          ${NC}"
echo -e "${YELLOW}=======================================================${NC}"
echo -e "${GREEN}Ce test vérifie si les modifications permettent de capturer${NC}"
echo -e "${GREEN}des phrases plus longues sans interruption prématurée.${NC}"
echo ""

# Créer le dossier des logs s'il n'existe pas
mkdir -p logs

# Timestamp pour le nom du fichier de log
timestamp=$(date +"%Y%m%d_%H%M%S")
log_file="logs/test_listening_duration_${timestamp}.log"

echo -e "${YELLOW}Démarrage du test d'écoute améliorée...${NC}"
echo -e "${YELLOW}Le résultat sera enregistré dans: ${GREEN}${log_file}${NC}"
echo ""
echo -e "${RED}Parlez dans le microphone lorsque le test démarre${NC}"
echo -e "${RED}Utilisez Ctrl+C pour arrêter le test manuellement${NC}"
echo ""

# Exécuter le test et sauvegarder la sortie
python3 test_improved_listening_duration.py 2>&1 | tee "$log_file"

echo ""
echo -e "${YELLOW}=======================================================${NC}"
echo -e "${GREEN}Test terminé. Résultats enregistrés dans: ${log_file}${NC}"
echo -e "${YELLOW}=======================================================${NC}"
