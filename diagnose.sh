#!/usr/bin/env bash

# Script de diagnostic pour l'environnement Peer
# Ce script analyse l'environnement virtuel et identifie les problèmes potentiels
# Aussi diagnostic pour l'installation de Whisper et autres moteurs STT

set -euo pipefail
IFS=$'\n\t'

# Variables globales
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly VENV_NAME="vepeer"
readonly VENV_PATH="$SCRIPT_DIR/$VENV_NAME"

# Couleurs pour une meilleure lisibilité
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages d'information
info() {
    echo -e "${BLUE}INFO:${NC} $1"
}

# Fonction pour afficher les messages de succès
success() {
    echo -e "${GREEN}SUCCÈS:${NC} $1"
}

# Fonction pour afficher les messages d'avertissement
warning() {
    echo -e "${YELLOW}ATTENTION:${NC} $1"
}

# Fonction pour afficher les messages d'erreur
error() {
    echo -e "${RED}ERREUR:${NC} $1"
}
# Fonction pour afficher les messages
print_message() {
    local level="$1"
    local message="$2"
    
    case "$level" in
        "info")
            info "$message"
            ;;
        "success")
            success "$message"
            ;;
        "warning")
            warning "$message"
            ;;
        "error")
            error "$message"
            ;;
        *)
            echo "$message"
            ;;
    esac
}

# Fonction pour vérifier si une commande existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Fonction pour vérifier si un module Python est importable
python_module_exists() {
    python -c "import $1" >/dev/null 2>&1
}

# Fonction pour obtenir le chemin d'installation d'un module Python
get_python_module_path() {
    python -c "import $1; print($1.__path__[0] if hasattr($1, '__path__') else $1.__file__)" 2>/dev/null
}

# Fonction pour vérifier si l'environnement virtuel est activé
check_venv() {
    if [ -z "$VIRTUAL_ENV" ]; then
        warning "Aucun environnement virtuel n'est activé."
        if [ -d "vepeer" ]; then
            info "L'environnement virtuel 'vepeer' existe. Activez-le avec: source vepeer/bin/activate"
        else
            info "Créez un environnement virtuel avec: python -m venv vepeer && source vepeer/bin/activate"
        fi
        return 1
    else
        success "Environnement virtuel activé: $VIRTUAL_ENV"
        return 0
    fi
}
# Vérifier si l'environnement virtuel est activé
check_venv_activated() {
    print_message "info" "Vérification de l'environnement virtuel..."
    
    if [[ -z "${VIRTUAL_ENV:-}" ]]; then
        if [[ -f "$VENV_PATH/bin/activate" ]]; then
            print_message "info" "Activation de l'environnement virtuel: $VENV_PATH - 'source $VENV_PATH/bin/activate'"
            source "$VENV_PATH/bin/activate"
            print_message "success" "Environnement virtuel activé: $VIRTUAL_ENV"
        else
            print_message "error" "Environnement virtuel non trouvé: $VENV_PATH"
            print_message "info" "Veuillez exécuter ./install.sh pour créer l'environnement virtuel - 'python -m venv $VENV_PATH && source $VENV_PATH/bin/activate'"
            exit 1
        fi
    else
        print_message "success" "Environnement virtuel activé: $VIRTUAL_ENV"
    fi
}

# Vérifier les dépendances problématiques
check_problematic_dependencies() {
    print_message "info" "Vérification des dépendances problématiques..."
    
    # Vérifier asyncio
    if python -c "import asyncio; print(f'asyncio version: {asyncio.__version__}')" 2>/dev/null; then
        local asyncio_version
        asyncio_version=$(python -c "import asyncio; print(asyncio.__version__)" 2>/dev/null)
        print_message "success" "asyncio version $asyncio_version est installé"
        
        # Vérifier si la version est trop ancienne
        if [[ "$asyncio_version" < "3.4.3" ]]; then
            print_message "error" "Version d'asyncio trop ancienne. Version 3.4.3+ requise."
            print_message "info" "Correction: pip install 'asyncio>=3.4.3' --force-reinstall"
        fi
    else
        print_message "error" "Impossible d'importer asyncio"
    fi
    
    # Vérifier torch
    if python -c "import torch; print(f'torch version: {torch.__version__}')" 2>/dev/null; then
        local torch_version
        torch_version=$(python -c "import torch; print(torch.__version__)" 2>/dev/null)
        print_message "success" "torch version $torch_version est installé"
    else
        print_message "warning" "torch n'est pas installé ou importable"
    fi
    
    # Vérifier numpy
    if python -c "import numpy; print(f'numpy version: {numpy.__version__}')" 2>/dev/null; then
        local numpy_version
        numpy_version=$(python -c "import numpy; print(numpy.__version__)" 2>/dev/null)
        print_message "success" "numpy version $numpy_version est installé"
        
        # Vérifier si la version est compatible
        if [[ "$numpy_version" != 1.* ]]; then
            print_message "error" "Version de numpy incompatible. Version 1.x requise."
            print_message "info" "Correction: pip install 'numpy<2.0' --force-reinstall"
        fi
    else
        print_message "error" "numpy n'est pas installé ou importable"
    fi
    
    # Vérifier whisper
    if python -c "import whisper" 2>/dev/null; then
        print_message "success" "whisper est installé et importable"
    else
        print_message "warning" "whisper n'est pas installé ou importable"
    fi
}


# Vérifier les conflits de packages
check_package_conflicts() {
    print_message "info" "Analyse des conflits de packages..."
    
    # Lister tous les packages installés avec leurs dépendances
    pip freeze > "$SCRIPT_DIR/pip_freeze.txt"
    print_message "info" "Liste des packages installés sauvegardée dans pip_freeze.txt"
    
    # Vérifier les conflits connus
    if grep -q "torch==1." "$SCRIPT_DIR/pip_freeze.txt" && python -c "import sys; sys.exit(0 if sys.version_info.minor >= 10 else 1)" 2>/dev/null; then
        print_message "warning" "Possible conflit: torch 1.x avec Python 3.10+"
        print_message "info" "Correction: pip install torch==2.0.0 --force-reinstall"
    fi
    
    # Vérifier si asyncio est installé via pip (ce qui peut causer des problèmes)
    if grep -q "asyncio==" "$SCRIPT_DIR/pip_freeze.txt"; then
        print_message "warning" "asyncio est installé via pip, ce qui peut causer des conflits"
        print_message "info" "asyncio est un module standard de Python et ne devrait pas être installé via pip"
        print_message "info" "Correction: pip uninstall -y asyncio"
    fi
}

# Vérifier les moteurs de reconnaissance vocale
check_speech_recognition_engines() {
    print_message "info" "Vérification des moteurs de reconnaissance vocale..."
    
    local engines_available=false
    
    # Vérifier Whisper
    if python -c "import whisper" 2>/dev/null; then
        engines_available=true
        print_message "success" "Whisper (OpenAI) est disponible"
    fi
    
    # Vérifier Vosk
    if python -c "import vosk" 2>/dev/null; then
        engines_available=true
        print_message "success" "Vosk est disponible"
    fi
    
    # Vérifier Wav2Vec2
    if python -c "import transformers, torch, torchaudio, soundfile" 2>/dev/null; then
        engines_available=true
        print_message "success" "Wav2Vec2 (Meta) est disponible"
    fi
    
    if [[ "$engines_available" == false ]]; then
        print_message "error" "Aucun moteur de reconnaissance vocale n'est disponible."
        print_message "info" "Veuillez installer l'un des moteurs suivants:"
        print_message "info" "  - Whisper (OpenAI): pip install openai-whisper torch"
        print_message "info" "  - Vosk: pip install vosk"
        print_message "info" "  - Wav2Vec2 (Meta): pip install transformers torch torchaudio soundfile"
    fi
}

# Vérifier les problèmes spécifiques à macOS
check_macos_specific_issues() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        print_message "info" "Vérification des problèmes spécifiques à macOS..."
        
        # Vérifier si Homebrew est installé
        if command -v brew >/dev/null 2>&1; then
            print_message "success" "Homebrew est installé"
            
            # Vérifier si portaudio est installé
            if brew list portaudio >/dev/null 2>&1; then
                print_message "success" "portaudio est installé via Homebrew"
            else
                print_message "warning" "portaudio n'est pas installé via Homebrew"
                print_message "info" "Correction: brew install portaudio"
            fi
        else
            print_message "warning" "Homebrew n'est pas installé"
            print_message "info" "Homebrew est recommandé pour installer les dépendances système sur macOS"
            print_message "info" "Installation: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        fi
        
        # Vérifier les problèmes de PYTHONPATH
        if [[ -z "${PYTHONPATH:-}" ]]; then
            print_message "warning" "PYTHONPATH n'est pas défini"
            print_message "info" "Cela peut causer des problèmes d'importation de modules"
            
            # Suggérer une correction
            local site_packages
            site_packages=$(python -c "import site; print(site.getsitepackages()[0])" 2>/dev/null)
            if [[ -n "$site_packages" ]]; then
                print_message "info" "Correction: export PYTHONPATH=\"$site_packages:\$PYTHONPATH\""
            fi
        else
            print_message "success" "PYTHONPATH est défini: $PYTHONPATH"
        fi
    fi
}

# Fonction pour corriger les problèmes courants
fix_common_issues() {
    print_message "info" "Tentative de correction des problèmes courants..."
    
    # Désinstaller asyncio si installé via pip
    if grep -q "asyncio==" "$SCRIPT_DIR/pip_freeze.txt"; then
        print_message "info" "Désinstallation d'asyncio installé via pip..."
        pip uninstall -y asyncio
    fi
    
    # Forcer l'installation de numpy 1.x
    print_message "info" "Installation de numpy 1.x..."
    pip install "numpy<2.0" --force-reinstall
    
    # Corriger les problèmes de torch avec Python 3.10+
    if python -c "import sys; sys.exit(0 if sys.version_info.minor >= 10 else 1)" 2>/dev/null; then
        print_message "info" "Installation de torch 2.0.0 pour Python 3.10+..."
        pip install torch==2.0.0 --force-reinstall
    fi
    
    # Créer un fichier .pth pour ajouter le site-packages au PYTHONPATH
    if [[ "$OSTYPE" == "darwin"* ]]; then
        local site_packages
        site_packages=$(python -c "import site; print(site.getsitepackages()[0])" 2>/dev/null)
        local pth_file="$site_packages/peer_pythonpath.pth"
        
        print_message "info" "Création d'un fichier .pth pour corriger les problèmes de PYTHONPATH..."
        echo "$site_packages" > "$pth_file"
        print_message "success" "Fichier .pth créé: $pth_file"
    fi
    
    print_message "success" "Corrections appliquées. Veuillez redémarrer votre terminal et réessayer."
}

# Fonction pour vérifier la version de Python
check_python_version() {
    info "Vérification de la version de Python..."
    
    PYTHON_VERSION=$(python --version 2>&1)
    PYTHON_VERSION_NUM=$(echo $PYTHON_VERSION | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION_NUM | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION_NUM | cut -d. -f2)
    
    if [ "$PYTHON_MAJOR" = "3" ] && [ "$PYTHON_MINOR" = "10" ]; then
        success "Version de Python correcte: $PYTHON_VERSION_NUM"
    else
        error "Version de Python incorrecte: $PYTHON_VERSION_NUM"
        warning "Cette application nécessite Python 3.10 spécifiquement pour la compatibilité avec PyTorch et Whisper."
        
        # Vérifier si Python 3.10 est disponible
        if command_exists python3.10; then
            info "Python 3.10 est disponible sur votre système. Utilisez-le pour créer l'environnement virtuel:"
            echo ""
            echo "python3.10 -m venv vepeer"
            echo "source vepeer/bin/activate"
            echo "./install.sh"
            echo ""
        else
            info "Python 3.10 n'est pas installé sur votre système. Veuillez l'installer:"
            echo ""
            echo "# Sur macOS:"
            echo "brew install python@3.10"
            echo ""
            echo "# Sur Ubuntu/Debian:"
            echo "sudo apt-get install python3.10 python3.10-venv python3.10-dev"
            echo ""
            echo "# Sur Fedora:"
            echo "sudo dnf install python3.10 python3.10-devel"
            echo ""
            echo "# Sur Windows:"
            echo "Téléchargez Python 3.10 depuis https://www.python.org/downloads/release/python-3100/"
            echo ""
        fi
    fi
}


# Fonction pour corriger les problèmes courants
fix_common_issues() {
    print_message "info" "Tentative de correction des problèmes courants..."
    
    # Désinstaller asyncio si installé via pip
    if grep -q "asyncio==" "$SCRIPT_DIR/pip_freeze.txt"; then
        print_message "info" "Désinstallation d'asyncio installé via pip..."
        pip uninstall -y asyncio
    fi
    
    # Forcer l'installation de numpy 1.x
    print_message "info" "Installation de numpy 1.x..."
    pip install "numpy<2.0" --force-reinstall
    
    # Corriger les problèmes de torch avec Python 3.10+
    if python -c "import sys; sys.exit(0 if sys.version_info.minor >= 10 else 1)" 2>/dev/null; then
        print_message "info" "Installation de torch 2.2.2 pour Python 3.10+..."
        pip install torch==2.2.2 --force-reinstall
    fi
    
    # Créer un fichier .pth pour ajouter le site-packages au PYTHONPATH
    if [[ "$OSTYPE" == "darwin"* ]]; then
        local site_packages
        site_packages=$(python -c "import site; print(site.getsitepackages()[0])" 2>/dev/null)
        local pth_file="$site_packages/peer_pythonpath.pth"
        
        print_message "info" "Création d'un fichier .pth pour corriger les problèmes de PYTHONPATH..."
        echo "$site_packages" > "$pth_file"
        print_message "success" "Fichier .pth créé: $pth_file"
    fi
    
    print_message "success" "Corrections appliquées. Veuillez redémarrer votre terminal et réessayer."
}

# Fonction pour vérifier l'installation de Whisper
check_whisper() {
    info "Vérification de l'installation de Whisper..."
    
    # Vérifier si Whisper est installé via Homebrew (macOS)
    if command_exists brew && brew list | grep -q openai-whisper; then
        success "Whisper est installé via Homebrew"
        WHISPER_HOMEBREW=true
        
        # Trouver le chemin d'installation de Whisper via Homebrew
        HOMEBREW_PREFIX=$(brew --prefix)
        PYTHON_VERSION="3.10"
        POTENTIAL_PATHS=(
            "$HOMEBREW_PREFIX/lib/python$PYTHON_VERSION/site-packages"
            "$HOMEBREW_PREFIX/Cellar/openai-whisper/*/lib/python$PYTHON_VERSION/site-packages"
        )
        
        WHISPER_PATH=""
        for path in "${POTENTIAL_PATHS[@]}"; do
            for dir in $path; do
                if [ -d "$dir/whisper" ]; then
                    WHISPER_PATH="$dir"
                    break 2
                fi
            done
        done
        
        if [ -n "$WHISPER_PATH" ]; then
            success "Chemin d'installation de Whisper via Homebrew: $WHISPER_PATH"
        else
            warning "Impossible de trouver le chemin d'installation de Whisper via Homebrew"
        fi
    else
        WHISPER_HOMEBREW=false
        info "Whisper n'est pas installé via Homebrew"
    fi
    
    # Vérifier si le module Python whisper est importable
    if python_module_exists whisper; then
        success "Le module Python 'whisper' est importable"
        WHISPER_MODULE_PATH=$(get_python_module_path whisper)
        success "Chemin du module whisper: $WHISPER_MODULE_PATH"
        
        # Vérifier si torch est importable (dépendance de Whisper)
        if python_module_exists torch; then
            success "Le module Python 'torch' est importable"
            
            # Vérifier la version de PyTorch
            TORCH_VERSION=$(python -c "import torch; print(torch.__version__)" 2>/dev/null)
            success "Version de PyTorch: $TORCH_VERSION"
            
            # Vérifier si CUDA est disponible
            if python -c "import torch; print(torch.cuda.is_available())" 2>/dev/null | grep -q "True"; then
                success "CUDA est disponible pour PyTorch"
            else
                info "CUDA n'est pas disponible pour PyTorch (CPU uniquement)"
            fi
        else
            error "Le module Python 'torch' n'est pas importable (dépendance de Whisper)"
        fi
        
        # Vérifier si le modèle base peut être chargé
        info "Tentative de chargement du modèle Whisper 'base'..."
        if python -c "import whisper; whisper.load_model('base')" >/dev/null 2>&1; then
            success "Le modèle Whisper 'base' a été chargé avec succès"
        else
            error "Impossible de charger le modèle Whisper 'base'"
            info "Cela peut être dû à un problème de téléchargement ou de permissions"
        fi
    else
        error "Le module Python 'whisper' n'est pas importable"
        
        # Si Whisper est installé via Homebrew mais pas importable, suggérer une solution
        if [ "$WHISPER_HOMEBREW" = true ] && [ -n "$WHISPER_PATH" ]; then
            info "Whisper est installé via Homebrew mais n'est pas accessible depuis Python"
            info "Solution: Ajoutez le chemin suivant à votre PYTHONPATH:"
            echo ""
            echo "export PYTHONPATH=\"$WHISPER_PATH:\$PYTHONPATH\""
            echo ""
            info "Ou créez un fichier .pth dans votre site-packages:"
            echo ""
            SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])")
            echo "echo \"$WHISPER_PATH\" > \"$SITE_PACKAGES/homebrew-whisper.pth\""
            echo ""
            info "Ou installez Whisper directement dans l'environnement virtuel:"
            echo ""
            echo "pip install openai-whisper torch==2.0.1"
            echo ""
        else
            info "Solution: Installez Whisper avec l'une des commandes suivantes:"
            echo ""
            echo "pip install openai-whisper torch==2.0.1"
            echo "# ou"
            echo "pip install git+https://github.com/openai/whisper.git torch==2.0.1"
            echo ""
        fi
    fi
}

# Fonction pour vérifier l'installation de Vosk
check_vosk() {
    info "Vérification de l'installation de Vosk..."
    
    # Vérifier si le module Python vosk est importable
    if python_module_exists vosk; then
        success "Le module Python 'vosk' est importable"
        VOSK_MODULE_PATH=$(get_python_module_path vosk)
        success "Chemin du module vosk: $VOSK_MODULE_PATH"
        
        # Vérifier si le modèle français est disponible
        VOSK_MODEL_PATH="vepeer/models/vosk/vosk-model-fr-0.22"
        if [ -d "$VOSK_MODEL_PATH" ]; then
            success "Le modèle Vosk français est disponible: $VOSK_MODEL_PATH"
            
            # Vérifier si le modèle peut être chargé
            info "Tentative de chargement du modèle Vosk..."
            if python -c "from vosk import Model; model = Model('$VOSK_MODEL_PATH')" >/dev/null 2>&1; then
                success "Le modèle Vosk a été chargé avec succès"
            else
                error "Impossible de charger le modèle Vosk"
                info "Cela peut être dû à un problème de téléchargement ou de permissions"
            fi
        else
            warning "Le modèle Vosk français n'est pas disponible"
            info "Solution: Téléchargez le modèle français avec:"
            echo ""
            echo "mkdir -p vepeer/models/vosk"
            echo "curl -L -o vepeer/models/vosk/vosk-model-fr-0.22.zip https://alphacephei.com/vosk/models/vosk-model-fr-0.22.zip"
            echo "unzip vepeer/models/vosk/vosk-model-fr-0.22.zip -d vepeer/models/vosk/"
            echo "rm vepeer/models/vosk/vosk-model-fr-0.22.zip"
            echo ""
        fi
    else
        info "Le module Python 'vosk' n'est pas importable"
        info "Solution: Installez Vosk avec:"
        echo ""
        echo "pip install vosk"
        echo ""
    fi
}

# Fonction pour vérifier l'installation de Wav2Vec2
check_wav2vec2() {
    info "Vérification de l'installation de Wav2Vec2..."
    
    # Vérifier si les modules Python nécessaires sont importables
    MODULES_OK=true
    for module in transformers torch torchaudio soundfile; do
        if python_module_exists $module; then
            success "Le module Python '$module' est importable"
            
            # Vérifier la version de PyTorch
            if [ "$module" = "torch" ]; then
                TORCH_VERSION=$(python -c "import torch; print(torch.__version__)" 2>/dev/null)
                success "Version de PyTorch: $TORCH_VERSION"
            fi
        else
            error "Le module Python '$module' n'est pas importable"
            MODULES_OK=false
        fi
    done
    
    if [ "$MODULES_OK" = true ]; then
        # Vérifier si le modèle français est disponible
        WAV2VEC2_MODEL_PATH="vepeer/models/wav2vec2"
        if [ -d "$WAV2VEC2_MODEL_PATH" ]; then
            success "Le modèle Wav2Vec2 français est disponible: $WAV2VEC2_MODEL_PATH"
            
            # Vérifier si le modèle peut être chargé
            info "Tentative de chargement du modèle Wav2Vec2..."
            if python -c "from transformers import Wav2Vec2Processor; processor = Wav2Vec2Processor.from_pretrained('$WAV2VEC2_MODEL_PATH')" >/dev/null 2>&1; then
                success "Le modèle Wav2Vec2 a été chargé avec succès"
            else
                error "Impossible de charger le modèle Wav2Vec2"
                info "Cela peut être dû à un problème de téléchargement ou de permissions"
            fi
        else
            warning "Le modèle Wav2Vec2 français n'est pas disponible localement"
            info "Le modèle sera téléchargé depuis Hugging Face lors de la première utilisation"
        fi
    else
        info "Solution: Installez les dépendances de Wav2Vec2 avec:"
        echo ""
        echo "pip install transformers torch==2.0.1 torchaudio soundfile"
        echo ""
    fi
}

# Fonction pour vérifier l'installation de PyAudio
check_pyaudio() {
    info "Vérification de l'installation de PyAudio..."
    
    # Vérifier si le module Python pyaudio est importable
    if python_module_exists pyaudio; then
        success "Le module Python 'pyaudio' est importable"
        
        # Vérifier si les périphériques audio sont disponibles
        info "Tentative de listage des périphériques audio..."
        if python -c "import pyaudio; p = pyaudio.PyAudio(); print(f'Périphériques audio disponibles: {p.get_device_count()}'); p.terminate()" >/dev/null 2>&1; then
            DEVICE_COUNT=$(python -c "import pyaudio; p = pyaudio.PyAudio(); print(p.get_device_count()); p.terminate()")
            success "PyAudio fonctionne correctement. Périphériques audio disponibles: $DEVICE_COUNT"
        else
            error "Impossible de lister les périphériques audio"
            info "Cela peut être dû à un problème de permissions ou de configuration audio"
        fi
    else
        error "Le module Python 'pyaudio' n'est pas importable"
        
        # Suggestions spécifiques à la plateforme
        if [[ "$OSTYPE" == "darwin"* ]]; then
            info "Solution pour macOS: Installez les dépendances et PyAudio avec:"
            echo ""
            echo "brew install portaudio"
            echo "pip install pyaudio"
            echo ""
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            info "Solution pour Linux: Installez les dépendances et PyAudio avec:"
            echo ""
            echo "sudo apt-get install python3-pyaudio portaudio19-dev"
            echo "pip install pyaudio"
            echo ""
        else
            info "Solution: Installez PyAudio avec:"
            echo ""
            echo "pip install pyaudio"
            echo ""
        fi
    fi
}

# Fonction pour vérifier l'installation de pyttsx3
check_pyttsx3() {
    info "Vérification de l'installation de pyttsx3..."
    
    # Vérifier si le module Python pyttsx3 est importable
    if python_module_exists pyttsx3; then
        success "Le module Python 'pyttsx3' est importable"
        
        # Vérifier si pyttsx3 peut être initialisé
        info "Tentative d'initialisation de pyttsx3..."
        if python -c "import pyttsx3; engine = pyttsx3.init()" >/dev/null 2>&1; then
            success "pyttsx3 a été initialisé avec succès"
        else
            error "Impossible d'initialiser pyttsx3"
            info "Cela peut être dû à un problème de configuration audio ou de dépendances manquantes"
        fi
    else
        error "Le module Python 'pyttsx3' n'est pas importable"
        info "Solution: Installez pyttsx3 avec:"
        echo ""
        echo "pip install pyttsx3"
        echo ""
    fi
}

# Fonction pour vérifier l'état du fichier stt_engines.json
check_stt_engines_file() {
    info "Vérification du fichier d'état des moteurs STT..."
    
    STT_ENGINES_FILE="vepeer/stt_engines.json"
    if [ -f "$STT_ENGINES_FILE" ]; then
        success "Le fichier d'état des moteurs STT existe: $STT_ENGINES_FILE"
        
        # Afficher le contenu du fichier
        echo "Contenu du fichier:"
        cat "$STT_ENGINES_FILE"
        echo ""
        
        # Vérifier la cohérence du fichier avec l'état réel
        WHISPER_INSTALLED=$(python_module_exists whisper && echo "true" || echo "false")
        VOSK_INSTALLED=$(python_module_exists vosk && echo "true" || echo "false")
        WAV2VEC2_INSTALLED=$(python_module_exists transformers && python_module_exists torch && python_module_exists torchaudio && python_module_exists soundfile && echo "true" || echo "false")
        
        WHISPER_FILE=$(grep -o '"whisper": *[^,}]*' "$STT_ENGINES_FILE" | grep -o '[^:]*$' | tr -d ' ')
        VOSK_FILE=$(grep -o '"vosk": *[^,}]*' "$STT_ENGINES_FILE" | grep -o '[^:]*$' | tr -d ' ')
        WAV2VEC2_FILE=$(grep -o '"wav2vec2": *[^,}]*' "$STT_ENGINES_FILE" | grep -o '[^:]*$' | tr -d ' ')
        
        if [ "$WHISPER_INSTALLED" != "$WHISPER_FILE" ]; then
            warning "Incohérence pour Whisper: fichier=$WHISPER_FILE, réel=$WHISPER_INSTALLED"
        fi
        
        if [ "$VOSK_INSTALLED" != "$VOSK_FILE" ]; then
            warning "Incohérence pour Vosk: fichier=$VOSK_FILE, réel=$VOSK_INSTALLED"
        fi
        
        if [ "$WAV2VEC2_INSTALLED" != "$WAV2VEC2_FILE" ]; then
            warning "Incohérence pour Wav2Vec2: fichier=$WAV2VEC2_FILE, réel=$WAV2VEC2_INSTALLED"
        fi
        
        # Suggérer une correction si nécessaire
        if [ "$WHISPER_INSTALLED" != "$WHISPER_FILE" ] || [ "$VOSK_INSTALLED" != "$VOSK_FILE" ] || [ "$WAV2VEC2_INSTALLED" != "$WAV2VEC2_FILE" ]; then
            info "Solution: Mettez à jour le fichier d'état avec:"
            echo ""
            echo "echo '{\"whisper\": $WHISPER_INSTALLED, \"vosk\": $VOSK_INSTALLED, \"wav2vec2\": $WAV2VEC2_INSTALLED}' > $STT_ENGINES_FILE"
            echo ""
        fi
    else
        warning "Le fichier d'état des moteurs STT n'existe pas"
        info "Solution: Créez le fichier avec:"
        echo ""
        WHISPER_INSTALLED=$(python_module_exists whisper && echo "true" || echo "false")
        VOSK_INSTALLED=$(python_module_exists vosk && echo "true" || echo "false")
        WAV2VEC2_INSTALLED=$(python_module_exists transformers && python_module_exists torch && python_module_exists torchaudio && python_module_exists soundfile && echo "true" || echo "false")
        echo "mkdir -p vepeer"
        echo "echo '{\"whisper\": $WHISPER_INSTALLED, \"vosk\": $VOSK_INSTALLED, \"wav2vec2\": $WAV2VEC2_INSTALLED}' > $STT_ENGINES_FILE"
        echo ""
    fi
}

# Fonction pour générer un rapport de diagnostic
generate_report() {
    info "Génération du rapport de diagnostic..."
    
    echo ""
    echo "======================= RAPPORT DE DIAGNOSTIC ======================="
    echo ""
    # Informations système
    echo "Système: $(uname -s) $(uname -r)"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Version macOS: $(sw_vers -productVersion)"
    fi
    echo "Python: $(python --version 2>&1)"
    echo "Pip: $(pip --version 2>&1)"
    
    # État des moteurs STT
    echo ""
    echo "État des moteurs STT:"
    echo "- Whisper: $(python_module_exists whisper && echo "Disponible" || echo "Non disponible")"
    echo "- Vosk: $(python_module_exists vosk && echo "Disponible" || echo "Non disponible")"
    echo "- Wav2Vec2: $(python_module_exists transformers && python_module_exists torch && python_module_exists torchaudio && python_module_exists soundfile && echo "Disponible" || echo "Non disponible")"
    
    # Recommandations
    echo ""
    echo "Recommandations:"
    
    # Vérifier la version de Python
    PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [ "$PYTHON_MAJOR" != "3" ] || [ "$PYTHON_MINOR" != "10" ]; then
        echo "- Version de Python incorrecte: $PYTHON_VERSION. Cette application nécessite Python 3.10."
        echo "  Installez Python 3.10 et recréez l'environnement virtuel."
    fi
    
    if ! python_module_exists whisper && ! python_module_exists vosk && ! python_module_exists transformers; then
        echo "- Aucun moteur STT n'est disponible. Installez au moins l'un d'entre eux."
    fi
    
    if [[ "$OSTYPE" == "darwin"* ]] && command_exists brew && brew list | grep -q openai-whisper && ! python_module_exists whisper; then
        HOMEBREW_PREFIX=$(brew --prefix)
        PYTHON_VERSION="3.10"
        echo "- Whisper est installé via Homebrew mais n'est pas accessible depuis Python."
        echo "  Ajoutez le chemin Homebrew à votre PYTHONPATH:"
        echo "  export PYTHONPATH=\"$HOMEBREW_PREFIX/lib/python$PYTHON_VERSION/site-packages:\$PYTHONPATH\""
    fi
    
    if ! python_module_exists pyaudio; then
        echo "- PyAudio n'est pas disponible. L'interface SUI ne fonctionnera pas."
    fi
    
    echo ""
    echo "=================================================================="
    echo ""
}

# Fonction principale
main() {
    echo "====== Diagnostic des moteurs de reconnaissance vocale ======"
    echo ""
    
    # Vérifier l'environnement virtuel
    check_venv
    if [ $? -ne 0 ]; then
        check_venv_activated
    fi

    # Vérifier la version de Python
    check_python_version
    echo ""
     # Vérifier les dépendances problématiques
    check_problematic_dependencies
    
    # Vérifier les conflits de packages
    check_package_conflicts
    
    # Vérifier les moteurs de reconnaissance vocale
    check_speech_recognition_engines
    
    # Vérifier les problèmes spécifiques à macOS
    check_macos_specific_issues
    echo ""   
    # Vérifier les installations
    check_whisper
    echo ""
    check_vosk
    echo ""
    check_wav2vec2
    echo ""
    check_pyaudio
    echo ""
    check_pyttsx3
    echo ""
    check_stt_engines_file
    echo ""
    
    # Générer un rapport
    generate_report
}

# Exécuter la fonction principale
main
