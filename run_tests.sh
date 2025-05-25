#!/bin/bash
# Script d'exécution des tests pour Peer Minimal

# Vérifier si l'environnement virtuel existe
if [ ! -d "vepeer" ]; then
    echo "L'environnement virtuel n'existe pas. Exécutez d'abord install.sh."
    exit 1
fi

# Activer l'environnement virtuel
source vepeer/bin/activate

# Exécuter les tests
echo "Exécution des tests unitaires..."
pytest tests/unit

echo "Exécution des tests d'intégration..."
pytest tests/integration

# Désactiver l'environnement virtuel à la fin
deactivate
