# Peer Minimal - Documentation

## Description
Peer Minimal est une version simplifiée de l'application Peer, respectant l'architecture hexagonale. Cette version implémente uniquement les fonctionnalités essentielles :
- Message de bienvenue vocal "Bienvenue my peer" au démarrage
- Vérification de l'état du système via différentes interfaces
- Interface vocale SUI avec reconnaissance vocale 100% locale

## Architecture
Le projet suit une architecture hexagonale (ports et adaptateurs) avec les couches suivantes :
- **Domain** : Entités, ports et services métier
- **Application** : Orchestration des cas d'utilisation
- **Infrastructure** : Adaptateurs techniques (TTS, vérification système)
- **Interfaces** : CLI, API, TUI et SUI

## Prérequis
**IMPORTANT** : Cette application nécessite **Python 3.10** spécifiquement pour garantir la compatibilité avec PyTorch et les moteurs de reconnaissance vocale.

Les versions plus récentes de Python (3.11, 3.12, 3.13) ne sont pas compatibles avec certaines dépendances critiques comme PyTorch, ce qui empêcherait le fonctionnement des moteurs de reconnaissance vocale.

Pour installer Python 3.10 :
- **macOS** : `brew install python@3.10`
- **Ubuntu/Debian** : `sudo apt-get install python3.10 python3.10-venv python3.10-dev`
- **Fedora** : `sudo dnf install python3.10 python3.10-devel`
- **Windows** : Téléchargez Python 3.10 depuis [python.org](https://www.python.org/downloads/release/python-3100/)

## Installation
```bash
# Rendre le script d'installation exécutable
chmod +x install.sh

# Exécuter le script d'installation
./install.sh
```

Le script d'installation vérifie d'abord que vous utilisez Python 3.10, puis crée un environnement virtuel `vepeer` et installe toutes les dépendances nécessaires. Il tente d'installer les moteurs de reconnaissance vocale dans l'ordre suivant :

1. **Whisper (OpenAI)** - Reconnaissance vocale de haute qualité, 100% locale
2. **Vosk** - Alternative légère, 100% locale
3. **Wav2Vec2 (Meta)** - Alternative puissante, 100% locale

### Installation sur macOS avec Homebrew

Sur macOS, l'installation via Homebrew est automatiquement détectée et configurée :

```bash
# Installation de Python 3.10
brew install python@3.10

# Installation de Whisper via Homebrew
brew install openai-whisper

# Puis exécuter le script d'installation qui configurera automatiquement les chemins
./install.sh
```

Le script d'installation détecte l'installation Homebrew et configure automatiquement l'environnement Python pour utiliser Whisper.

### Diagnostic des problèmes d'installation

Si vous rencontrez des problèmes avec l'installation ou la reconnaissance vocale, utilisez le script de diagnostic :

```bash
# Rendre le script de diagnostic exécutable
chmod +x diagnose.sh

# Exécuter le diagnostic
./diagnose.sh
```

Ce script vérifie :
- La version de Python (doit être 3.10)
- La disponibilité des moteurs de reconnaissance vocale
- L'importabilité réelle des modules Python
- La présence des modèles téléchargés
- La cohérence du fichier d'état
- Les problèmes de configuration spécifiques à votre système

### Installation hors ligne

Pour une installation entièrement hors ligne, vous pouvez préparer les packages et modèles à l'avance :

#### Pour macOS
```bash
# Installation via Homebrew
brew install python@3.10
brew install openai-whisper

# Ou téléchargement des modèles à l'avance
python3.10 -m pip download openai-whisper torch==2.0.1 torchaudio -d ./offline_packages
python3.10 -m pip download vosk -d ./offline_packages
python3.10 -m pip download transformers torch==2.0.1 torchaudio soundfile -d ./offline_packages
```

#### Pour Linux
```bash
# Téléchargement des packages
python3.10 -m pip download openai-whisper torch==2.0.1 torchaudio -d ./offline_packages
python3.10 -m pip download vosk -d ./offline_packages
python3.10 -m pip download transformers torch==2.0.1 torchaudio soundfile -d ./offline_packages

# Installation des dépendances système
sudo apt-get install -y python3-pyaudio portaudio19-dev espeak
```

#### Pour Windows
```bash
# Téléchargement des packages
python3.10 -m pip download openai-whisper torch==2.0.1 torchaudio -d ./offline_packages
python3.10 -m pip download vosk -d ./offline_packages
python3.10 -m pip download transformers torch==2.0.1 torchaudio soundfile -d ./offline_packages
```

Puis, pour installer à partir des packages téléchargés :
```bash
pip install --no-index --find-links=./offline_packages openai-whisper torch==2.0.1
# ou
pip install --no-index --find-links=./offline_packages vosk
# ou
pip install --no-index --find-links=./offline_packages transformers torch==2.0.1 torchaudio soundfile
```

## Utilisation

### Interface CLI
```bash
# Utiliser le script d'exécution
./run.sh

# Vérifier l'état du système
./run.sh --check
```

### Interface API
```bash
# Démarrer le serveur API
./run_api.sh

# Accéder à l'API via un navigateur ou curl
# Message de bienvenue : http://localhost:8000/
# Vérification système : http://localhost:8000/check
```

### Interface TUI
```bash
# Lancer l'interface textuelle
./run_tui.sh

# Naviguer avec les flèches et sélectionner avec Entrée
```

### Interface SUI (Speech User Interface)
```bash
# Lancer l'interface vocale
./run_sui.sh

# Fonctionnalités de l'interface SUI :
# - Analyse de la machine au démarrage avec commentaire humoristique
# - Annonce de l'heure chaque minute
# - Écoute continue des commandes vocales
# - Indicateur visuel d'état (écoute, parole, attente)

# Commandes vocales disponibles :
# - "Comment ça va" : vérifie l'état du système
# - "Quitter" : ferme l'application (fonctionne même pendant que le système parle)
```

### Exécution des tests
```bash
# Exécuter les tests unitaires et d'intégration
./run_tests.sh
```

## Structure des fichiers
```
peer_minimal/
├── src/
│   └── peer/
│       ├── domain/
│       │   ├── entities/
│       │   │   └── message_entities.py
│       │   ├── ports/
│       │   │   ├── tts_port.py
│       │   │   └── system_check_port.py
│       │   └── services/
│       │       ├── message_service.py
│       │       └── system_check_service.py
│       ├── application/
│       ├── infrastructure/
│       │   ├── adapters/
│       │   │   ├── simple_tts_adapter.py
│       │   │   └── simple_system_check_adapter.py
│       │   └── services/
│       └── interfaces/
│           ├── api/
│           │   └── api.py
│           ├── cli/
│           │   └── cli.py
│           ├── tui/
│           │   └── tui.py
│           └── sui/
│               └── sui.py
├── tests/
│   ├── unit/
│   └── integration/
├── config/
├── install.sh
├── diagnose.sh
├── pyproject.toml
├── run.sh
├── run_api.sh
├── run_tui.sh
├── run_sui.sh
└── run_tests.sh
```

## Fonctionnalités
- **Message de bienvenue** : Affiche et vocalise "Bienvenue my peer" au démarrage
- **Vérification système** : Vérifie l'état du système et de ses composants
  - CLI : `peer --check`
  - API : `/check`
  - TUI : Option "Check" dans le menu
  - SUI : Commande vocale "Comment ça va"
- **Interface SUI améliorée** :
  - Utilise plusieurs moteurs de reconnaissance vocale 100% locaux :
    - Whisper (OpenAI) - Haute qualité
    - Vosk - Léger et rapide
    - Wav2Vec2 (Meta) - Alternative puissante
  - Analyse la machine au démarrage avec commentaire humoristique
  - Annonce l'heure chaque minute pendant l'écoute
  - Fournit un indicateur visuel d'état (écoute, parole, attente)
  - Permet d'interrompre le système en disant "quitter" à tout moment

## Résolution des problèmes courants

### Problème : "Version de Python incorrecte"
Ce problème se produit lorsque vous n'utilisez pas Python 3.10, qui est requis pour la compatibilité avec PyTorch et Whisper.

**Solution** :
1. Installez Python 3.10 selon votre système d'exploitation
2. Supprimez l'environnement virtuel existant : `rm -rf vepeer`
3. Réexécutez le script d'installation : `./install.sh`

### Problème : "Whisper est marqué comme installé mais les bibliothèques ne sont pas disponibles"
Ce problème se produit généralement sur macOS lorsque Whisper est installé via Homebrew mais n'est pas accessible depuis l'environnement virtuel Python.

**Solution** :
1. Exécutez le script de diagnostic : `./diagnose.sh`
2. Suivez les recommandations spécifiques à votre système
3. Pour macOS avec Homebrew, le script d'installation devrait maintenant configurer automatiquement les chemins

### Problème : "Aucun moteur de reconnaissance vocale n'est disponible"
Ce problème se produit lorsqu'aucun des moteurs STT (Whisper, Vosk, Wav2Vec2) n'a pu être installé correctement.

**Solution** :
1. Exécutez le script de diagnostic : `./diagnose.sh`
2. Installez manuellement l'un des moteurs recommandés :
   ```bash
   source vepeer/bin/activate
   pip install openai-whisper torch==2.0.1
   # ou
   pip install vosk
   # ou
   pip install transformers torch==2.0.1 torchaudio soundfile
   ```
3. Mettez à jour le fichier d'état selon les instructions du diagnostic

## Notes techniques
- Cette application nécessite spécifiquement Python 3.10 pour la compatibilité avec PyTorch et les moteurs de reconnaissance vocale
- Tous les moteurs de reconnaissance vocale fonctionnent entièrement en local, sans aucune communication avec l'extérieur
- L'interface SUI détecte automatiquement le moteur disponible et l'utilise de manière transparente
- La synthèse vocale (TTS) utilise pyttsx3 qui fonctionne également entièrement en local
- L'interface est conçue pour fonctionner en continu, avec écoute même pendant la parole
- Aucune connexion internet n'est requise pour le fonctionnement de l'application
