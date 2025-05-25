#!/bin/bash
# Script d'exécution de l'API pour Peer Minimal

# Vérifier si l'environnement virtuel existe
if [ ! -d "vepeer" ]; then
    echo "L'environnement virtuel n'existe pas. Exécutez d'abord install.sh."
    exit 1
fi

# Activer l'environnement virtuel
source vepeer/bin/activate

# Exécuter l'API
echo "Démarrage de l'API sur http://localhost:8000..."
uvicorn peer.interfaces.api.api:app --host 0.0.0.0 --port 8000

# Désactiver l'environnement virtuel à la fin
deactivate
