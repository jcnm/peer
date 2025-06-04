#!/bin/bash
# Script d'exécution de l'interface SUI pour Peer Minimal

# Vérifier si l'environnement virtuel existe
if [ ! -d "vepeer" ]; then
    echo "L'environnement virtuel n'existe pas. Exécutez d'abord install.sh."
    exit 1
fi

# Activer l'environnement virtuel
source vepeer/bin/activate

# Ajouter le répertoire src au PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)/src

# Exécuter l'interface SUI
python -m peer.interfaces.sui.main

# Désactiver l'environnement virtuel à la fin
deactivate
