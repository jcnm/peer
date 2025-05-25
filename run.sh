#!/bin/bash
# Script d'exécution principal pour Peer Minimal

# Vérifier si l'environnement virtuel existe
if [ ! -d "vepeer" ]; then
    echo "L'environnement virtuel n'existe pas. Exécutez d'abord install.sh."
    exit 1
fi

# Activer l'environnement virtuel
source vepeer/bin/activate

# Exécuter l'interface CLI par défaut
python -m peer.interfaces.cli.cli "$@"

# Désactiver l'environnement virtuel à la fin
deactivate
