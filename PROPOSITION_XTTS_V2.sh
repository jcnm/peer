#!/bin/bash

# Proposition d'amélioration TTS pour install.sh
# Ajout d'XTTS v2 comme option premium

# Fonction pour installer XTTS v2 (Coqui TTS)
install_xtts_v2() {
    print_message "info" "Installation de XTTS v2 (Coqui TTS) - Solution TTS premium..."
    
    # Vérifier si XTTS v2 est déjà installé
    if python -c "import TTS; print('TTS version:', TTS.__version__)" >/dev/null 2>&1 && [[ "$FORCE_INSTALL" != true ]]; then
        print_message "success" "XTTS v2 (Coqui TTS) est déjà installé"
        return 0
    fi
    
    # Installer les dépendances système pour XTTS v2
    print_message "info" "Installation des dépendances système pour XTTS v2..."
    if [[ "$OS" == "linux" ]]; then
        if command_exists apt-get; then
            sudo apt-get update && sudo apt-get install -y \
                libsndfile1-dev ffmpeg espeak-ng || print_message "warning" "Certaines dépendances ont échoué"
        elif command_exists dnf; then
            sudo dnf install -y \
                libsndfile-devel ffmpeg espeak-ng || print_message "warning" "Certaines dépendances ont échoué"
        elif command_exists pacman; then
            sudo pacman -S --noconfirm \
                libsndfile ffmpeg espeak-ng || print_message "warning" "Certaines dépendances ont échoué"
        fi
    elif [[ "$OS" == "macos" ]]; then
        if command_exists brew; then
            brew install libsndfile ffmpeg espeak-ng || print_message "warning" "Certaines dépendances ont échoué"
        fi
    fi
    
    # Installer XTTS v2 via pip
    print_message "info" "Installation de XTTS v2 via pip..."
    if pip install TTS>=0.22.0; then
        print_message "success" "XTTS v2 installé avec succès"
        
        # Tester l'installation
        if python -c "from TTS.api import TTS; tts = TTS('tts_models/multilingual/multi-dataset/xtts_v2')" >/dev/null 2>&1; then
            print_message "success" "XTTS v2 fonctionne correctement"
        else
            print_message "warning" "XTTS v2 installé mais le modèle de base n'est pas accessible"
        fi
        
        return 0
    else
        print_message "error" "Échec de l'installation de XTTS v2"
        return 1
    fi
}

# Architecture TTS à trois niveaux
install_tts_suite() {
    print_message "info" "Installation de la suite TTS complète..."
    
    # Niveau 1: TTS de base (fallback)
    print_message "info" "Installation pyttsx3 (TTS de base)..."
    pip install pyttsx3 || print_message "warning" "Échec pyttsx3"
    
    # Niveau 2: TTS équilibré (votre implémentation actuelle)
    install_piper_tts
    
    # Niveau 3: TTS premium (nouveau)
    if [[ "${INSTALL_PREMIUM_TTS:-true}" == "true" ]]; then
        install_xtts_v2
    else
        print_message "info" "Installation XTTS v2 désactivée (variable INSTALL_PREMIUM_TTS=false)"
    fi
}

# Fonction de vérification TTS complète
verify_tts_installation() {
    print_message "info" "Vérification de l'installation TTS..."
    
    local tts_engines=0
    
    # Vérifier pyttsx3
    if python -c "import pyttsx3; pyttsx3.init()" >/dev/null 2>&1; then
        print_message "success" "pyttsx3 (TTS de base) disponible"
        ((tts_engines++))
    fi
    
    # Vérifier Piper TTS
    if command_exists piper || [[ -x "$VIRTUAL_ENV/bin/piper" ]] || [[ -x "$SCRIPT_DIR/piper/install/piper" ]]; then
        print_message "success" "Piper TTS (TTS équilibré) disponible"
        ((tts_engines++))
    fi
    
    # Vérifier XTTS v2
    if python -c "from TTS.api import TTS" >/dev/null 2>&1; then
        print_message "success" "XTTS v2 (TTS premium) disponible"
        ((tts_engines++))
    fi
    
    if [[ "$tts_engines" -ge 2 ]]; then
        print_message "success" "Suite TTS complète installée ($tts_engines/3 moteurs)"
    elif [[ "$tts_engines" -eq 1 ]]; then
        print_message "warning" "Installation TTS partielle ($tts_engines/3 moteurs)"
    else
        print_message "error" "Aucun moteur TTS fonctionnel"
    fi
}

echo "# Exemples d'utilisation dans votre code Python:"
cat << 'EOF'

# Classe TTS adaptative pour votre projet
class AdaptiveTTS:
    def __init__(self):
        self.engines = []
        self._initialize_engines()
    
    def _initialize_engines(self):
        """Initialise les moteurs TTS par ordre de préférence"""
        
        # 1. Essayer XTTS v2 (premium)
        try:
            from TTS.api import TTS
            self.xtts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
            self.engines.append("xtts_v2")
            print("✅ XTTS v2 disponible (qualité premium)")
        except:
            self.xtts = None
        
        # 2. Essayer Piper (équilibré)
        try:
            import subprocess
            subprocess.run(["piper", "--help"], capture_output=True)
            self.engines.append("piper")
            print("✅ Piper TTS disponible (qualité équilibrée)")
        except:
            pass
        
        # 3. Fallback pyttsx3 (de base)
        try:
            import pyttsx3
            self.pyttsx3_engine = pyttsx3.init()
            self.engines.append("pyttsx3")
            print("✅ pyttsx3 disponible (qualité de base)")
        except:
            self.pyttsx3_engine = None
    
    def speak(self, text, language="fr", voice_quality="auto"):
        """
        Synthèse vocale adaptative
        
        Args:
            text: Texte à synthétiser
            language: "fr" ou "en"
            voice_quality: "premium", "balanced", "basic" ou "auto"
        """
        
        if voice_quality == "auto":
            # Utiliser le meilleur moteur disponible
            if "xtts_v2" in self.engines:
                return self._speak_xtts_v2(text, language)
            elif "piper" in self.engines:
                return self._speak_piper(text, language)
            elif "pyttsx3" in self.engines:
                return self._speak_pyttsx3(text, language)
        
        elif voice_quality == "premium" and "xtts_v2" in self.engines:
            return self._speak_xtts_v2(text, language)
        
        elif voice_quality == "balanced" and "piper" in self.engines:
            return self._speak_piper(text, language)
        
        elif voice_quality == "basic" and "pyttsx3" in self.engines:
            return self._speak_pyttsx3(text, language)
        
        else:
            raise Exception(f"Moteur TTS '{voice_quality}' non disponible")
    
    def _speak_xtts_v2(self, text, language):
        """Utiliser XTTS v2 pour une qualité premium"""
        output_file = "temp_xtts.wav"
        self.xtts.tts_to_file(text=text, language=language, file_path=output_file)
        self._play_audio(output_file)
    
    def _speak_piper(self, text, language):
        """Utiliser Piper pour une qualité équilibrée"""
        # Votre implémentation Piper existante
        pass
    
    def _speak_pyttsx3(self, text, language):
        """Utiliser pyttsx3 pour une qualité de base"""
        self.pyttsx3_engine.say(text)
        self.pyttsx3_engine.runAndWait()

# Utilisation dans votre application:
tts = AdaptiveTTS()

# Utilisation automatique du meilleur moteur
tts.speak("Bonjour, comment allez-vous ?", language="fr")

# Forcer l'utilisation d'un moteur spécifique
tts.speak("Hello, how are you?", language="en", voice_quality="premium")
EOF

echo ""
echo "Voulez-vous que je modifie votre install.sh pour inclure cette architecture TTS à trois niveaux ?"
