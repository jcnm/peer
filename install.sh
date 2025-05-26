#!/usr/bin/env bash

# Peer Installation Script
# Automatically detects OS, checks for existing dependencies,
# creates virtual environment, and installs Peer with proper error handling

set -euo pipefail  # Exit on error, undefined vars, and pipe failures
IFS=$'\n\t'       # Secure Internal Field Separator

# Global variables
readonly SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly VENV_NAME="vepeer"
readonly MIN_PYTHON_MAJOR=3
readonly MIN_PYTHON_MINOR=8
readonly MAX_PYTHON_MINOR=10

# Configuration variables (can be overridden by command line arguments)
CREATE_VENV=true
VENV_DIR=""
FORCE_INSTALL=false
VERBOSE=false
COPY_ENV_FROM=""
SKIP_MODELS_DOWNLOAD=false

# Color and formatting functions
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly BOLD='\033[1m'
readonly NC='\033[0m' # No Color

print_message() {
    local level="$1"
    local message="$2"
    local timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    
    case "$level" in
        "info")
            echo -e "${BLUE}[INFO]${NC} ${timestamp} - $message" >&2
            ;;
        "success")
            echo -e "${GREEN}[SUCCESS]${NC} ${timestamp} - $message" >&2
            ;;
        "warning")
            echo -e "${YELLOW}[WARNING]${NC} ${timestamp} - $message" >&2
            ;;
        "error")
            echo -e "${RED}[ERROR]${NC} ${timestamp} - $message" >&2
            ;;
        "debug")
            if [[ "$VERBOSE" == true ]]; then
                echo -e "[DEBUG] ${timestamp} - $message" >&2
            fi
            ;;
        *)
            echo "$message" >&2
            ;;
    esac
}

# Logging function for debugging
log_debug() {
    print_message "debug" "$1"
}

# Error handling function
handle_error() {
    local exit_code=$?
    local line_number=$1
    print_message "error" "Script failed at line $line_number with exit code $exit_code"
    exit $exit_code
}

# Set up error trap
trap 'handle_error $LINENO' ERR

# Help function
show_help() {
    cat << EOF
Usage: $SCRIPT_NAME [OPTIONS]

Peer Installation Script - Automatically installs Peer with proper dependency management

OPTIONS:
    -h, --help              Show this help message
    -v, --verbose           Enable verbose output
    -f, --force             Force installation even if dependencies exist
    --no-venv               Skip virtual environment creation
    --venv-dir DIR          Specify custom virtual environment directory
    --venv-name NAME        Specify custom virtual environment name (default: $VENV_NAME)
    --copy-env-from PATH    Copy existing environment from specified path
    --skip-models-download  Skip downloading models (use existing or download on first use)

EXAMPLES:
    $SCRIPT_NAME                           # Standard installation
    $SCRIPT_NAME --no-venv                 # Install without virtual environment
    $SCRIPT_NAME --venv-dir /opt/peer      # Install venv in custom directory
    $SCRIPT_NAME -v --force                # Verbose mode with forced installation
    $SCRIPT_NAME --copy-env-from ~/old_env # Copy environment from existing path
    $SCRIPT_NAME --skip-models-download    # Skip downloading models

EOF
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -f|--force)
                FORCE_INSTALL=true
                shift
                ;;
            --no-venv)
                CREATE_VENV=false
                shift
                ;;
            --venv-dir)
                VENV_DIR="$2"
                shift 2
                ;;
            --venv-name)
                VENV_NAME="$2"
                shift 2
                ;;
            --copy-env-from)
                COPY_ENV_FROM="$2"
                shift 2
                ;;
            --skip-models-download)
                SKIP_MODELS_DOWNLOAD=true
                shift
                ;;
            *)
                print_message "error" "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if running as root (should be avoided for pip installs)
check_root() {
    if [[ $EUID -eq 0 ]] && [[ "$FORCE_INSTALL" != true ]]; then
        print_message "error" "Running as root is not recommended. Use --force to override."
        exit 1
    fi
}

# Detect operating system and package manager
detect_os() {
    print_message "info" "Detecting operating system and package manager..."
    
    # Initialize variables
    OS=""
    PACKAGE_MANAGER=""
    INSTALL_CMD=""
    UPDATE_CMD=""
    
    # Detect OS with better macOS detection
    case "$OSTYPE" in
        linux-gnu*)
            OS="linux"
            ;;
        darwin*)
            OS="macos"
            # Check for macOS version
            if command_exists sw_vers; then
                local macos_version
                macos_version=$(sw_vers -productVersion)
                log_debug "macOS version: $macos_version"
            fi
            ;;
        msys*|mingw*|cygwin*)
            OS="windows"
            ;;
        *)
            print_message "error" "Unsupported operating system: $OSTYPE"
            return 1
            ;;
    esac
    
    # Detect package manager based on OS with timeout protection
    case "$OS" in
        linux)
            # Linux package manager detection
            if command_exists apt-get; then
                PACKAGE_MANAGER="apt"
                UPDATE_CMD="apt-get update"
                INSTALL_CMD="apt-get install -y"
            elif command_exists dnf; then
                PACKAGE_MANAGER="dnf"
                UPDATE_CMD="dnf update -y"
                INSTALL_CMD="dnf install -y"
            elif command_exists yum; then
                PACKAGE_MANAGER="yum"
                UPDATE_CMD="yum update -y"
                INSTALL_CMD="yum install -y"
            elif command_exists pacman; then
                PACKAGE_MANAGER="pacman"
                UPDATE_CMD="pacman -Syu --noconfirm"
                INSTALL_CMD="pacman -S --noconfirm"
            elif command_exists zypper; then
                PACKAGE_MANAGER="zypper"
                UPDATE_CMD="zypper refresh"
                INSTALL_CMD="zypper install -y"
            elif command_exists apk; then
                PACKAGE_MANAGER="apk"
                UPDATE_CMD="apk update"
                INSTALL_CMD="apk add"
            else
                print_message "warning" "No supported package manager found on Linux"
                PACKAGE_MANAGER="unknown"
            fi
            ;;
        macos)
            # Improved macOS detection with timeout protection
            print_message "info" "Checking for Homebrew installation..."
            if command_exists brew; then
                # Test brew with timeout to avoid hanging
                local brew_test_result=1
                if command_exists timeout; then
                    timeout 15 brew --version >/dev/null 2>&1 && brew_test_result=0
                else
                    # Fallback without timeout
                    brew --version >/dev/null 2>&1 && brew_test_result=0
                fi
                
                if [[ $brew_test_result -eq 0 ]]; then
                    PACKAGE_MANAGER="brew"
                    UPDATE_CMD="brew update"
                    INSTALL_CMD="brew install"
                    print_message "success" "Homebrew found and working"
                else
                    print_message "warning" "Homebrew found but not responding properly"
                    PACKAGE_MANAGER="unknown"
                fi
            else
                print_message "warning" "Homebrew not found."
                print_message "info" "Install Homebrew from: https://brew.sh/"
                print_message "info" "Or continue without it (some features may require manual setup)"
                PACKAGE_MANAGER="unknown"
            fi
            ;;
        windows)
            # Windows detection
            if command_exists choco; then
                PACKAGE_MANAGER="choco"
                UPDATE_CMD="choco upgrade all -y"
                INSTALL_CMD="choco install -y"
            elif command_exists winget; then
                PACKAGE_MANAGER="winget"
                UPDATE_CMD="winget upgrade --all"
                INSTALL_CMD="winget install"
            else
                print_message "warning" "No package manager found on Windows. Manual installation may be required."
                PACKAGE_MANAGER="unknown"
            fi
            ;;
    esac
    
    log_debug "Detected OS: $OS, Package Manager: $PACKAGE_MANAGER"
    print_message "success" "System detected: $OS with package manager: ${PACKAGE_MANAGER:-None}"
    
    # Export for use in other functions
    export OS PACKAGE_MANAGER UPDATE_CMD INSTALL_CMD
}

# Check if we have timeout command, if not create a simple version
ensure_timeout_available() {
    if [[ "$OS" == "macos" ]] && ! command_exists timeout; then
        # Create a simple timeout function for macOS
        timeout() {
            local duration=$1
            shift
            (
                "$@" &
                local pid=$!
                (
                    sleep "$duration"
                    kill -TERM $pid 2>/dev/null
                    sleep 2
                    kill -KILL $pid 2>/dev/null
                ) &
                local watcher=$!
                wait $pid
                local result=$?
                kill -TERM $watcher 2>/dev/null
                return $result
            )
        }
        export -f timeout
    fi
}

# Check and get Python command
get_python_command() {
    local python_cmd=""
    
    # Try different Python commands in order of preference
    for cmd in python3.10 python3.9 python3.8 python3 python; do
        if command_exists "$cmd"; then
            python_cmd="$cmd"
            break
        fi
    done
    
    if [[ -z "$python_cmd" ]]; then
        return 1
    fi
    
    echo "$python_cmd"
}

# Validate Python version
validate_python_version() {
    local python_cmd="$1"
    
    # Get Python version
    local version_output
    if ! version_output=$($python_cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>/dev/null); then
        return 1
    fi
    
    local major minor micro
    IFS='.' read -r major minor micro <<< "$version_output"
    
    # Check minimum and maximum version requirements
    if [[ "$major" -lt $MIN_PYTHON_MAJOR ]] || \
       ([[ "$major" -eq $MIN_PYTHON_MAJOR ]] && [[ "$minor" -lt $MIN_PYTHON_MINOR ]]) || \
       ([[ "$major" -eq $MIN_PYTHON_MAJOR ]] && [[ "$minor" -gt $MAX_PYTHON_MINOR ]]); then
        print_message "error" "Python $MIN_PYTHON_MAJOR.$MIN_PYTHON_MINOR to $MIN_PYTHON_MAJOR.$MAX_PYTHON_MINOR required. Found: $version_output"
        return 1
    fi
    
    print_message "success" "Compatible Python version found: $version_output ($python_cmd)"
    echo "$python_cmd"
}

# Check Python installation
check_python() {
    print_message "info" "Checking Python installation..."
    
    local python_cmd
    if python_cmd=$(get_python_command); then
        if python_cmd=$(validate_python_version "$python_cmd"); then
            export PYTHON_CMD="$python_cmd"
            export PYTHON_VERSION=$($python_cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
            export AUTHORIZED_PYTHON_VERSION="python$PYTHON_VERSION"
            return 0
        fi
    fi
    
    print_message "error" "No compatible Python installation found"
    print_message "info" "Please install Python $MIN_PYTHON_MAJOR.$MIN_PYTHON_MINOR to $MIN_PYTHON_MAJOR.$MAX_PYTHON_MINOR"
    return 1
}

# Check pip installation and get pip command
check_pip() {
    print_message "info" "Checking pip installation..."
    
    local pip_cmd=""
    
    # Try different pip commands in order of preference
    for cmd in pip3 pip; do
        if command_exists "$cmd"; then
            # Check if pip is for the correct Python version
            if pip_python=$($cmd --version 2>/dev/null | grep -o "python [0-9.]*" | cut -d' ' -f2); then
                local python_version
                python_version=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
                
                if [[ "$pip_python" == "${python_version%.*}"* ]]; then
                    pip_cmd="$cmd"
                    break
                fi
            fi
        fi
    done
    
    # Fallback to python -m pip
    if [[ -z "$pip_cmd" ]]; then
        if $PYTHON_CMD -m pip --version >/dev/null 2>&1; then
            pip_cmd="$PYTHON_CMD -m pip"
        else
            print_message "error" "pip not found or not compatible with Python installation"
            return 1
        fi
    fi
    
    export PIP_CMD="$pip_cmd"
    print_message "success" "pip found: $pip_cmd"
    return 0
}

# Install system dependencies
install_system_dependencies() {
    print_message "info" "Checking system dependencies..."
    
    if [[ "$PACKAGE_MANAGER" == "unknown" ]]; then
        print_message "warning" "No package manager detected. Skipping system dependency installation."
        return 0
    fi
    
    # Define packages for each package manager with proper array declaration
    local missing_packages=()
    
    case "$PACKAGE_MANAGER" in
        apt)
            local package_checks=(
                "python3-pip:pip3"
                "python3-venv:python3 -m venv --help"
                "python3-dev:python3-config"
                "build-essential:gcc"
                "portaudio19-dev:pkg-config --exists portaudio-2.0"
                "git:git"
            )
            ;;
        dnf|yum)
            local package_checks=(
                "python3-pip:pip3"
                "python3-devel:python3-config"
                "gcc:gcc"
                "portaudio-devel:pkg-config --exists portaudio-2.0"
                "git:git"
            )
            ;;
        pacman)
            local package_checks=(
                "python-pip:pip3"
                "base-devel:gcc"
                "portaudio:pkg-config --exists portaudio-2.0"
                "git:git"
            )
            ;;
        brew)
            # macOS with Homebrew - different approach
            local package_checks=(
                "python@3.10:python3"
                "python@3.9:python3"
                "python@3.8:python3"
                "portaudio:pkg-config --exists portaudio-2.0"
                "git:git"
            )
            ;;
        *)
            print_message "warning" "Unsupported package manager: $PACKAGE_MANAGER"
            return 0
            ;;
    esac
    
    # Check which packages are missing - with timeout for macOS
    for package_info in "${package_checks[@]}"; do
        local package_name="${package_info%%:*}"
        local check_cmd="${package_info##*:}"
        
        log_debug "Checking for package: $package_name with command: $check_cmd"
        
        # Add timeout for macOS to prevent hanging
        local check_result=1
        if [[ "$OS" == "macos" ]]; then
            # Use timeout command if available, otherwise use different approach
            if command_exists timeout; then
                timeout 10 bash -c "$check_cmd" >/dev/null 2>&1 && check_result=0
            else
                # Fallback for macOS without timeout command
                eval "$check_cmd" >/dev/null 2>&1 && check_result=0
            fi
        else
            eval "$check_cmd" >/dev/null 2>&1 && check_result=0
        fi
        
        if [[ $check_result -ne 0 ]]; then
            # Special handling for Python on macOS
            if [[ "$OS" == "macos" ]] && [[ "$package_name" == python* ]]; then
                # Skip Python packages if we already have Python working
                if [[ -n "${PYTHON_CMD:-}" ]] && command_exists "$PYTHON_CMD"; then
                    log_debug "Python already available, skipping: $package_name"
                    continue
                fi
            fi
            missing_packages+=("$package_name")
            log_debug "Missing package: $package_name"
        else
            log_debug "Package already installed: $package_name"
        fi
    done
    
    # Install missing packages
    if [[ ${#missing_packages[@]} -gt 0 ]]; then
        print_message "info" "Installing missing system packages: ${missing_packages[*]}"
        
        # Update package database (skip for brew as it's not needed)
        if [[ -n "$UPDATE_CMD" ]] && [[ "$PACKAGE_MANAGER" != "brew" ]]; then
            print_message "info" "Updating package database..."
            if [[ "$PACKAGE_MANAGER" == "apt" ]]; then
                if ! sudo $UPDATE_CMD; then
                    print_message "warning" "Failed to update package database. Continuing anyway..."
                fi
            else
                $UPDATE_CMD || print_message "warning" "Package update failed, continuing..."
            fi
        fi
        
        
        # Install packages - no sudo for brew
        local install_success=true
        if [[ "$PACKAGE_MANAGER" == "brew" ]]; then
            for package in "${missing_packages[@]}"; do
                print_message "info" "Installing $package via Homebrew..."
                if command_exists "$package"; then
                    print_message "info" "$package is already installed"
                else
                    if ! $INSTALL_CMD "$package"; then
                        print_message "warning" "Failed to install $package via $INSTALL_CMD, but continuing..."
                        install_success=false
                    fi
                fi
            done
        else
            if ! sudo $INSTALL_CMD "${missing_packages[@]}"; then
                print_message "error" "Failed to install system dependencies"
                return 1
            fi
        fi
   
        print_message "success" "System dependencies installed successfully"
    else
        print_message "success" "All required system dependencies are already installed"
    fi
    
    return 0
}

# Check if a Python module is importable
python_module_exists() {
    $PYTHON_CMD -c "import $1" >/dev/null 2>&1
    return $?
}

# Copy existing environment
copy_environment() {
    local source_path="$1"
    local target_path="$2"
    
    print_message "info" "Copying environment from $source_path to $target_path..."
    
    # Check if source exists
    if [[ ! -d "$source_path" ]]; then
        print_message "error" "Source environment directory does not exist: $source_path"
        return 1
    fi
    
    # Check if source is a valid venv
    if [[ ! -f "$source_path/bin/activate" ]]; then
        print_message "error" "Source directory is not a valid virtual environment: $source_path"
        return 1
    fi
    
    # Create target directory if it doesn't exist
    if [[ ! -d "$(dirname "$target_path")" ]]; then
        mkdir -p "$(dirname "$target_path")"
    fi
    
    # Remove target if it exists and force is enabled
    if [[ -d "$target_path" ]]; then
        if [[ "$FORCE_INSTALL" == true ]]; then
            print_message "info" "Removing existing target environment: $target_path"
            rm -rf "$target_path"
        else
            print_message "error" "Target environment already exists: $target_path. Use --force to override."
            return 1
        fi
    fi
    
    # Copy environment
    print_message "info" "Copying environment files (this may take a while)..."
    cp -r "$source_path" "$target_path"
    
    # Update paths in activation script
    local activate_script="$target_path/bin/activate"
    if [[ -f "$activate_script" ]]; then
        print_message "info" "Updating paths in activation script..."
        sed -i.bak "s|$source_path|$target_path|g" "$activate_script"
        
        # Update other scripts if they exist
        for script in "$target_path/bin/activate.csh" "$target_path/bin/activate.fish" "$target_path/bin/Activate.ps1"; do
            if [[ -f "$script" ]]; then
                sed -i.bak "s|$source_path|$target_path|g" "$script"
            fi
        done
    fi
    
    # Copy models directory if it exists
    if [[ -d "$source_path/models" ]]; then
        print_message "info" "Copying models directory..."
        mkdir -p "$target_path/models"
        cp -r "$source_path/models"/* "$target_path/models/"
    fi
    
    print_message "success" "Environment copied successfully from $source_path to $target_path"
    return 0
}

# Setup virtual environment
setup_virtual_environment() {
    if [[ "$CREATE_VENV" != true ]]; then
        print_message "info" "Skipping virtual environment creation as requested"
        return 0
    fi
    
    print_message "info" "Setting up virtual environment..."
    
    # Determine venv directory
    local venv_path
    if [[ -n "$VENV_DIR" ]]; then
        venv_path="$VENV_DIR/$VENV_NAME"
    else
        venv_path="$SCRIPT_DIR/$VENV_NAME"
    fi
    
    # Check if copying from existing environment
    if [[ -n "$COPY_ENV_FROM" ]]; then
        if copy_environment "$COPY_ENV_FROM" "$venv_path"; then
            # Activate the copied environment
            source "$venv_path/bin/activate"
            
            # Verify activation
            if [[ -z "${VIRTUAL_ENV:-}" ]]; then
                print_message "error" "Failed to activate copied virtual environment"
                return 1
            fi
            
            print_message "success" "Using copied virtual environment at $venv_path"
            return 0
        else
            print_message "error" "Failed to copy environment from $COPY_ENV_FROM"
            return 1
        fi
    fi
    
    # Check if venv already exists
    if [[ -d "$venv_path" ]] && [[ -f "$venv_path/bin/activate" ]]; then
        if [[ "$FORCE_INSTALL" == true ]]; then
            print_message "info" "Removing existing virtual environment at $venv_path"
            rm -rf "$venv_path"
        else
            print_message "info" "Using existing virtual environment at $venv_path"
            source "$venv_path/bin/activate"
            
            # Verify activation
            if [[ -z "${VIRTUAL_ENV:-}" ]]; then
                print_message "error" "Failed to activate virtual environment"
                return 1
            fi
            
            return 0
        fi
    fi
    
    # Create venv directory if it doesn't exist
    if [[ -n "$VENV_DIR" ]] && [[ ! -d "$VENV_DIR" ]]; then
        mkdir -p "$VENV_DIR"
    fi
    
    # Create virtual environment
    print_message "info" "Creating new virtual environment at $venv_path"
    if ! $PYTHON_CMD -m venv "$venv_path"; then
        print_message "error" "Failed to create virtual environment"
        return 1
    fi
    
    # Activate virtual environment
    source "$venv_path/bin/activate"
    
    # Verify activation
    if [[ -z "${VIRTUAL_ENV:-}" ]]; then
        print_message "error" "Failed to activate virtual environment"
        return 1
    fi
    
    print_message "success" "Virtual environment created and activated at $venv_path"
    
    # Modification des scripts d'activation pour gérer PYTHONPATH
    ACTIVATE_SCRIPT="$venv_path/bin/activate"
    DEACTIVATE_SCRIPT="$venv_path/bin/activate.d/deactivate_pythonpath.sh"

    # Créer le répertoire activate.d s'il n'existe pas
    mkdir -p "$venv_path/bin/activate.d"

    # Sauvegarder l'ancien PYTHONPATH dans le script d'activation
    cat >> "$ACTIVATE_SCRIPT" << EOF

# Sauvegarde et configuration du PYTHONPATH
if [ -z "\$PYTHONPATH_OLD" ]; then
    export PYTHONPATH_OLD="\$PYTHONPATH"
fi
export PYTHONPATH="$venv_path/lib/$AUTHORIZED_PYTHON_VERSION/site-packages:\$PYTHONPATH"
EOF

    # Créer le script de désactivation pour restaurer PYTHONPATH
    cat > "$DEACTIVATE_SCRIPT" << EOF
# Restauration du PYTHONPATH original
if [ -n "\$PYTHONPATH_OLD" ]; then
    export PYTHONPATH="\$PYTHONPATH_OLD"
    unset PYTHONPATH_OLD
else
    unset PYTHONPATH
fi
EOF

    # Modifier le script deactivate pour appeler notre script de désactivation
    sed -i.bak '/deactivate () {/a \
        # Source all files in ~/.vepeer/bin/activate.d/ directory\
        if [ -d "$VIRTUAL_ENV/bin/activate.d" ]; then\
            for file in $(find "$VIRTUAL_ENV/bin/activate.d" -type f -name "*.sh"); do\
                source "$file"\
            done\
        fi' "$ACTIVATE_SCRIPT" || print_message "warning" "Impossible de modifier le script d'activation, mais on continue..."
    
    print_message "success" "PYTHONPATH configuré pour inclure: $venv_path/lib/$AUTHORIZED_PYTHON_VERSION/site-packages"
    
    return 0
}

# Install Python dependencies
install_python_dependencies() {
    print_message "info" "Installing Python dependencies..."
    
    # Check if we should skip installation
    if [[ -n "$COPY_ENV_FROM" ]] && [[ "$FORCE_INSTALL" != true ]]; then
        print_message "info" "Using dependencies from copied environment. Skipping installation."
        return 0
    fi
    
    # Upgrade pip, setuptools, and wheel
    print_message "info" "Upgrading pip, setuptools, and wheel..."
    if ! pip install --upgrade pip setuptools wheel; then
        print_message "warning" "Failed to upgrade pip, setuptools, and wheel. Continuing anyway..."
    fi
    
    # Check if NumPy is already installed
    local numpy_installed=false
    local numpy_version=""
    
    if python_module_exists numpy; then
        numpy_installed=true
        numpy_version=$(python -c "import numpy; print(numpy.__version__)" 2>/dev/null)
        
        # Check if NumPy version is 1.x
        if [[ $numpy_version == 1.* ]]; then
            print_message "success" "NumPy version $numpy_version already installed (compatible)"
        else
            print_message "warning" "NumPy version $numpy_version detected. Version 1.x is required for compatibility."
            
            if [[ "$FORCE_INSTALL" == true ]]; then
                print_message "info" "Forcing reinstallation of NumPy 1.x..."
                numpy_installed=false
            else
                print_message "warning" "Using existing NumPy $numpy_version. Use --force to reinstall NumPy 1.x."
            fi
        fi
    fi
    
    # Install NumPy 1.x if needed
    if [[ "$numpy_installed" == false ]]; then
        print_message "info" "Installing NumPy 1.x for compatibility with binary modules..."
        if ! pip install "numpy<2.0" --force-reinstall; then
            print_message "error" "Failed to install NumPy 1.x. This is critical for compatibility."
            return 1
        fi
        
        # Verify NumPy installation and version
        if python_module_exists numpy; then
            numpy_version=$(python -c "import numpy; print(numpy.__version__)" 2>/dev/null)
            if [[ $numpy_version == 1.* ]]; then
                print_message "success" "NumPy version $numpy_version installed successfully"
            else
                print_message "error" "NumPy version $numpy_version detected. Version 1.x is required for compatibility."
                print_message "info" "Attempting to force NumPy 1.x installation again..."
                if ! pip install "numpy<2.0" --force-reinstall; then
                    print_message "error" "Failed to install NumPy 1.x after second attempt."
                    return 1
                fi
                
                # Verify again after second attempt
                numpy_version=$(python -c "import numpy; print(numpy.__version__)" 2>/dev/null)
                if [[ $numpy_version == 1.* ]]; then
                    print_message "success" "NumPy version $numpy_version installed successfully after second attempt"
                else
                    print_message "error" "Failed to install NumPy 1.x after multiple attempts."
                    return 1
                fi
            fi
        else
            print_message "error" "NumPy module is not importable after installation."
            return 1
        fi
    fi
    
    # Install basic dependencies
    print_message "info" "Installing basic dependencies..."
    if ! pip install -e .; then
        print_message "warning" "Failed to install package in development mode. Continuing anyway..."
    fi
    
    # Install web server dependencies
    print_message "info" "Installing web server dependencies..."
    if ! pip install fastapi uvicorn; then
        print_message "warning" "Failed to install web server dependencies. Continuing anyway..."
    fi
    
    # Install Windows-specific dependencies if on Windows
    if [[ "$OS" == "windows" ]]; then
        print_message "info" "Installing Windows-specific dependencies..."
        pip install windows-curses || print_message "warning" "Failed to install windows-curses. Continuing anyway..."
    fi
    
    # Install TTS dependencies
    print_message "info" "Installing text-to-speech dependencies..."
    if ! pip install pyttsx3; then
        print_message "warning" "Failed to install pyttsx3. Continuing anyway..."
    fi
    
    # Install audio dependencies based on OS
    print_message "info" "Installing audio dependencies..."
    if [[ "$OS" == "linux" ]]; then
        if command_exists apt-get; then
            sudo apt-get update && sudo apt-get install -y python3-pyaudio portaudio19-dev espeak || 
                print_message "warning" "Failed to install system audio dependencies. Continuing anyway..."
        elif command_exists dnf; then
            sudo dnf install -y python3-pyaudio portaudio-devel espeak || 
                print_message "warning" "Failed to install system audio dependencies. Continuing anyway..."
        elif command_exists pacman; then
            sudo pacman -S --noconfirm python-pyaudio portaudio espeak || 
                print_message "warning" "Failed to install system audio dependencies. Continuing anyway..."
        fi
    elif [[ "$OS" == "macos" ]]; then
        if command_exists brew; then
            brew install portaudio || 
                print_message "warning" "Failed to install portaudio. Continuing anyway..."
        fi
    fi
    
    # Install PyAudio
    if ! pip install pyaudio; then
        print_message "warning" "Failed to install pyaudio. Continuing anyway..."
    fi
    
    # Install system analysis tools
    print_message "info" "Installing system analysis tools..."
    if ! pip install psutil; then
        print_message "warning" "Failed to install psutil. Continuing anyway..."
    fi
    
    print_message "success" "Python dependencies installed successfully"
    return 0
}

# Install speech recognition engines
install_speech_recognition() {
    print_message "info" "Installing speech recognition engines..."
    
    # Check if we should skip installation
    if [[ -n "$COPY_ENV_FROM" ]] && [[ "$FORCE_INSTALL" != true ]]; then
        print_message "info" "Using speech recognition engines from copied environment. Skipping installation."
        return 0
    fi
    
    # Create models directory
    mkdir -p "$VIRTUAL_ENV/models"
    
    # Variables to track installation status
    local whisper_installed=false
    local vosk_installed=false
    local wav2vec2_installed=false
    
    # Check if engines are already installed
    if python_module_exists whisper && [[ "$FORCE_INSTALL" != true ]]; then
        whisper_installed=true
        print_message "success" "Whisper is already installed"
    elif python_module_exists vosk && [[ "$FORCE_INSTALL" != true ]]; then
        vosk_installed=true
        print_message "success" "Vosk is already installed"
    elif python_module_exists transformers && python_module_exists torch && python_module_exists torchaudio && python_module_exists soundfile && [[ "$FORCE_INSTALL" != true ]]; then
        wav2vec2_installed=true
        print_message "success" "Wav2Vec2 dependencies are already installed"
    fi
    
    # If no engines are installed or force installation is requested, proceed with installation
    if [[ "$whisper_installed" == false ]] && [[ "$vosk_installed" == false ]] && [[ "$wav2vec2_installed" == false ]] || [[ "$FORCE_INSTALL" == true ]]; then
        # Determine PyTorch version based on Python version
        local torch_version
        local python_minor_version
        python_minor_version=$(python -c "import sys; print(sys.version_info.minor)")
        
        if [[ "$python_minor_version" -eq 10 ]]; then
            torch_version="2.2.2"
        elif [[ "$python_minor_version" -eq 9 ]]; then
            torch_version="2.2.2"
        elif [[ "$python_minor_version" -eq 8 ]]; then
            torch_version="1.13.1"
        else
            torch_version="2.2.2"  # Fallback
        fi
        
        print_message "info" "Using PyTorch version $torch_version for Python 3.$python_minor_version"
        
        # 1. Try to install Whisper (OpenAI)
        print_message "info" "Attempting to install Whisper (OpenAI)..."
        
        # Check for Homebrew installation on macOS
        if [[ "$OS" == "macos" ]] && command_exists brew && brew list | grep -q openai-whisper; then
            print_message "info" "Whisper is already installed via Homebrew"
            
            # Configure PYTHONPATH to include Homebrew modules
            local homebrew_prefix
            homebrew_prefix=$(brew --prefix)
            local homebrew_site_packages="$homebrew_prefix/lib/python$PYTHON_VERSION/site-packages"
            
            # Create a .pth file in the virtual environment site-packages
            local venv_site_packages
            venv_site_packages=$(python -c "import site; print(site.getsitepackages()[0])")
            echo "$homebrew_site_packages" > "$venv_site_packages/homebrew-whisper.pth"
            
            # Verify importability
            if python_module_exists whisper; then
                whisper_installed=true
                print_message "success" "Homebrew Whisper configuration successful"
            else
                print_message "warning" "Homebrew Whisper configuration failed, trying pip installation..."
                
                # Add Homebrew Python bin to PATH as a fallback
                export PATH="$homebrew_prefix/opt/python@$PYTHON_VERSION/bin:$PATH"
                
                # Try again after PATH update
                if python_module_exists whisper; then
                    whisper_installed=true
                    print_message "success" "Homebrew Whisper configuration successful after PATH update"
                else
                    print_message "warning" "Homebrew Whisper still not importable after PATH update"
                fi
            fi
        elif [[ "$OS" == "macos" ]] && command_exists brew; then
            # Try to install Whisper via Homebrew
            print_message "info" "Attempting to install Whisper via Homebrew..."
            if brew install openai-whisper; then
                # Configure PYTHONPATH for Homebrew modules
                local homebrew_prefix
                homebrew_prefix=$(brew --prefix)
                local homebrew_site_packages="$homebrew_prefix/lib/python$PYTHON_VERSION/site-packages"
                
                # Create a .pth file in the virtual environment site-packages
                local venv_site_packages
                venv_site_packages=$(python -c "import site; print(site.getsitepackages()[0])")
                echo "$homebrew_site_packages" > "$venv_site_packages/homebrew-whisper.pth"
                
                # Add symlinks to ensure Python can find the modules
                mkdir -p "$venv_site_packages/whisper"
                ln -sf "$homebrew_site_packages/whisper"/* "$venv_site_packages/whisper/" 2>/dev/null || true
                
                # Verify importability
                if python_module_exists whisper; then
                    whisper_installed=true
                    print_message "success" "Homebrew Whisper installation and configuration successful"
                else
                    print_message "warning" "Homebrew Whisper configuration failed, trying pip installation..."
                    
                    # Add Homebrew Python bin to PATH as a fallback
                    export PATH="$homebrew_prefix/opt/python@$PYTHON_VERSION/bin:$PATH"
                    
                    # Try again after PATH update
                    if python_module_exists whisper; then
                        whisper_installed=true
                        print_message "success" "Homebrew Whisper configuration successful after PATH update"
                    else
                        print_message "warning" "Homebrew Whisper still not importable after PATH update"
                    fi
                fi
            else
                print_message "warning" "Homebrew Whisper installation failed, trying pip installation..."
            fi
        fi
        
        # Try pip installation if Homebrew installation failed or not on macOS
        if [[ "$whisper_installed" == false ]]; then
            print_message "info" "Attempting to install Whisper via pip..."
            
            # First ensure NumPy 1.x is installed and importable
            if ! python_module_exists numpy; then
                print_message "warning" "NumPy not found, installing NumPy 1.x first..."
                pip install "numpy<2.0" --force-reinstall
            else
                numpy_version=$(python -c "import numpy; print(numpy.__version__)" 2>/dev/null)
                if [[ $numpy_version != 1.* ]]; then
                    print_message "warning" "NumPy version $numpy_version detected. Reinstalling NumPy 1.x..."
                    pip install "numpy<2.0" --force-reinstall
                fi
            fi
            
            # Now install PyTorch and Whisper
            if pip install "torch==$torch_version" && pip install openai-whisper; then
                # Verify importability
                
                if pip install git+https://github.com/openai/whisper.git && python_module_exists whisper && python_module_exists torch; then
                    whisper_installed=true
                    print_message "success" "Pip Whisper installation successful"
                else
                    print_message "warning" "Pip Whisper installation failed (modules not importable), trying git installation..."
                fi
            else
                print_message "warning" "Pip Whisper installation failed, trying git installation..."
            fi
        fi
        
        # Try git installation if pip installation failed
        if [[ "$whisper_installed" == false ]]; then
            print_message "info" "Attempting to install Whisper via git..."
            
            # First ensure NumPy 1.x and PyTorch are installed
            pip install "numpy<2.0" --force-reinstall
            pip install "torch==$torch_version"
            
            # Now install Whisper from git
            if pip install git+https://github.com/openai/whisper.git; then
                # Verify importability
                if python_module_exists whisper && python_module_exists torch; then
                    whisper_installed=true
                    print_message "success" "Git Whisper installation successful"
                else
                    print_message "warning" "Git Whisper installation failed (modules not importable)"
                fi
            else
                print_message "warning" "Git Whisper installation failed"
            fi
        fi
        
        # Download Whisper model if installation was successful and not skipped
        if [[ "$whisper_installed" == true ]] && [[ "$SKIP_MODELS_DOWNLOAD" != true ]]; then
            # Check if model already exists
            local model_exists=false
            if [[ -d "$HOME/.cache/whisper" ]]; then
                if ls "$HOME/.cache/whisper/base"* >/dev/null 2>&1; then
                    model_exists=true
                    print_message "success" "Whisper base model already downloaded"
                fi
            fi
            
            if [[ "$model_exists" == false ]]; then
                print_message "info" "Downloading Whisper base model (this may take a few minutes)..."
                if python -c "import whisper; whisper.load_model('base')" 2>/dev/null; then
                    print_message "success" "Whisper model download successful"
                else
                    print_message "warning" "Whisper model download failed, it will be downloaded on first use"
                fi
            fi
        fi
        
        # 2. Try to install Vosk if Whisper installation failed
        if [[ "$whisper_installed" == false ]]; then
            print_message "info" "Attempting to install Vosk (lightweight offline solution)..."
            if pip install vosk; then
                # Verify importability
                if python_module_exists vosk; then
                    vosk_installed=true
                    print_message "success" "Vosk installation successful"
                    
                    # Download French Vosk model if not skipped
                    if [[ "$SKIP_MODELS_DOWNLOAD" != true ]]; then
                        # Check if model already exists
                        local vosk_model_exists=false
                        if [[ -d "$VIRTUAL_ENV/models/vosk/vosk-model-fr-0.22" ]]; then
                            vosk_model_exists=true
                            print_message "success" "Vosk French model already downloaded"
                        fi
                        
                        if [[ "$vosk_model_exists" == false ]]; then
                            print_message "info" "Downloading French Vosk model (this may take a few minutes)..."
                            mkdir -p "$VIRTUAL_ENV/models/vosk"
                            if command_exists wget; then
                                wget -O "$VIRTUAL_ENV/models/vosk/vosk-model-fr-0.22.zip" https://alphacephei.com/vosk/models/vosk-model-fr-0.22.zip
                                unzip "$VIRTUAL_ENV/models/vosk/vosk-model-fr-0.22.zip" -d "$VIRTUAL_ENV/models/vosk/"
                                rm "$VIRTUAL_ENV/models/vosk/vosk-model-fr-0.22.zip"
                            elif command_exists curl; then
                                curl -L -o "$VIRTUAL_ENV/models/vosk/vosk-model-fr-0.22.zip" https://alphacephei.com/vosk/models/vosk-model-fr-0.22.zip
                                unzip "$VIRTUAL_ENV/models/vosk/vosk-model-fr-0.22.zip" -d "$VIRTUAL_ENV/models/vosk/"
                                rm "$VIRTUAL_ENV/models/vosk/vosk-model-fr-0.22.zip"
                            else
                                print_message "warning" "Neither wget nor curl is available. Please download the French Vosk model manually from https://alphacephei.com/vosk/models/vosk-model-fr-0.22.zip and extract it to $VIRTUAL_ENV/models/vosk/"
                            fi
                        fi
                    fi
                else
                    print_message "warning" "Vosk installation failed (module not importable)"
                fi
            else
                print_message "warning" "Vosk installation failed"
            fi
        fi
        
        # 3. Try to install Wav2Vec2 if both Whisper and Vosk installation failed
        if [[ "$whisper_installed" == false ]] && [[ "$vosk_installed" == false ]]; then
            print_message "info" "Attempting to install Wav2Vec2 (Meta)..."
            
            # First ensure NumPy 1.x is installed
            pip install "numpy<2.0" --force-reinstall
            
            if pip install transformers "torch==$torch_version" torchaudio soundfile; then
                # Verify importability
                if python_module_exists transformers && python_module_exists torch && python_module_exists torchaudio && python_module_exists soundfile; then
                    wav2vec2_installed=true
                    print_message "success" "Wav2Vec2 installation successful"
                    
                    # Download French Wav2Vec2 model if not skipped
                    if [[ "$SKIP_MODELS_DOWNLOAD" != true ]]; then
                        # Check if model already exists
                        local wav2vec2_model_exists=false
                        if [[ -d "$VIRTUAL_ENV/models/wav2vec2" ]]; then
                            wav2vec2_model_exists=true
                            print_message "success" "Wav2Vec2 French model already downloaded"
                        fi
                        
                        if [[ "$wav2vec2_model_exists" == false ]]; then
                            print_message "info" "Downloading French Wav2Vec2 model (this may take a few minutes)..."
                            if python -c "from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor; processor = Wav2Vec2Processor.from_pretrained('facebook/wav2vec2-large-xlsr-53-french'); model = Wav2Vec2ForCTC.from_pretrained('facebook/wav2vec2-large-xlsr-53-french'); processor.save_pretrained('$VIRTUAL_ENV/models/wav2vec2'); model.save_pretrained('$VIRTUAL_ENV/models/wav2vec2')" 2>/dev/null; then
                                print_message "success" "Wav2Vec2 model download successful"
                            else
                                print_message "warning" "Wav2Vec2 model download failed, it will be downloaded on first use"
                            fi
                        fi
                    fi
                else
                    print_message "warning" "Wav2Vec2 installation failed (modules not importable)"
                fi
            else
                print_message "warning" "Wav2Vec2 installation failed"
            fi
        fi
    fi
    
    # Create status file
    print_message "info" "Creating speech recognition engines status file..."
    echo "{\"whisper\": $whisper_installed, \"vosk\": $vosk_installed, \"wav2vec2\": $wav2vec2_installed}" > "$VIRTUAL_ENV/stt_engines.json"
    
    # Installation summary
    print_message "info" "Speech recognition engines installation summary:"
    if [[ "$whisper_installed" == true ]]; then
        print_message "success" "✓ Whisper (OpenAI) installed and will be used for speech recognition"
    elif [[ "$vosk_installed" == true ]]; then
        print_message "success" "✓ Vosk installed and will be used for speech recognition"
    elif [[ "$wav2vec2_installed" == true ]]; then
        print_message "success" "✓ Wav2Vec2 (Meta) installed and will be used for speech recognition"
    else
        print_message "error" "✗ No speech recognition engine could be installed"
        print_message "info" "The SUI interface will work in degraded mode"
        print_message "info" "Run ./diagnose.sh to diagnose the problem"
    fi
    
    return 0
}

# Verify installation
verify_installation() {
    print_message "info" "Verifying installation..."
    
    # Check NumPy
    if python_module_exists numpy; then
        local numpy_version
        numpy_version=$(python -c "import numpy; print(numpy.__version__)" 2>/dev/null)
        if [[ $numpy_version == 1.* ]]; then
            print_message "success" "NumPy version $numpy_version verified"
        else
            print_message "warning" "NumPy version $numpy_version detected. Version 1.x is recommended for compatibility."
        fi
    else
        print_message "error" "NumPy is not importable"
    fi
    
    # Check PyTorch
    if python_module_exists torch; then
        local torch_version
        torch_version=$(python -c "import torch; print(torch.__version__)" 2>/dev/null)
        print_message "success" "PyTorch version $torch_version verified"
    else
        print_message "warning" "PyTorch is not importable (required for Whisper)"
    fi
    
    # Check Whisper
    if python_module_exists whisper; then
        print_message "success" "Whisper is importable"
    else
        print_message "warning" "Whisper is not importable"
    fi
    
    # Check Vosk
    if python_module_exists vosk; then
        print_message "success" "Vosk is importable"
    else
        print_message "info" "Vosk is not importable (alternative to Whisper)"
    fi
    
    # Check Wav2Vec2
    if python_module_exists transformers && python_module_exists torchaudio && python_module_exists soundfile; then
        print_message "success" "Wav2Vec2 dependencies are importable"
    else
        print_message "info" "Wav2Vec2 dependencies are not importable (alternative to Whisper)"
    fi
    
    # Check PyAudio
    if python_module_exists pyaudio; then
        print_message "success" "PyAudio is importable"
    else
        print_message "warning" "PyAudio is not importable (required for audio input)"
    fi
    
    # Check pyttsx3
    if python_module_exists pyttsx3; then
        print_message "success" "pyttsx3 is importable"
    else
        print_message "warning" "pyttsx3 is not importable (required for text-to-speech)"
    fi
    
    # Check PYTHONPATH
    if [[ -n "${PYTHONPATH:-}" ]]; then
        print_message "success" "PYTHONPATH is set: $PYTHONPATH"
    else
        print_message "warning" "PYTHONPATH is not set"
    fi
    
    return 0
}

# Print installation summary
print_summary() {
    echo ""
    echo -e "${GREEN}=======================================${NC}"
    echo -e "${GREEN}  Installation Complete!${NC}"
    echo -e "${GREEN}=======================================${NC}"
    echo ""
    echo "Python: $(python --version 2>&1)"
    echo "NumPy: $(python -c "import numpy; print(numpy.__version__)" 2>/dev/null || echo "Not installed")"
    echo "PYTHONPATH configured to include: $VIRTUAL_ENV/lib/$AUTHORIZED_PYTHON_VERSION/site-packages"
    echo ""
    echo "To activate the environment: source $VENV_NAME/bin/activate"
    echo "To run the application: ./run.sh"
    echo "To run the API server: ./run_api.sh"
    echo "To run the TUI interface: ./run_tui.sh"
    echo "To run the SUI interface: ./run_sui.sh"
    echo "To run tests: ./run_tests.sh"
    echo "To diagnose problems: ./diagnose.sh"
    echo ""
}

# Main function
main() {
    # Parse command line arguments
    parse_arguments "$@"
    
    # Display banner
    echo -e "${BLUE}=======================================${NC}"
    echo -e "${BLUE}  Peer Installation Script${NC}"
    echo -e "${BLUE}=======================================${NC}"
    echo ""
    
    # Check if running as root
    check_root
    
    # Detect operating system
    detect_os
    
    # Ensure timeout command is available
    ensure_timeout_available
    
    # Check Python installation
    check_python
    
    # Check pip installation
    check_pip
    
    # Install system dependencies
    install_system_dependencies
    
    # Setup virtual environment
    setup_virtual_environment
    
    # Install Python dependencies
    install_python_dependencies
    
    # Install speech recognition engines
    install_speech_recognition
    
    # Verify installation
    verify_installation
    
    # Print summary
    print_summary
    
    return 0
}

# Run main function
main "$@"
