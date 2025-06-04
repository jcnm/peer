#!/bin/bash

# Script to install STT/TTS models and generate configuration
# Exit on any error
set -e

# --- Configuration ---
PEER_DIR="$HOME/.peer"
MODELS_DIR="$PEER_DIR/models"
CONFIG_DIR="$PEER_DIR/config/sui"
MODELS_CONFIG_FILE="$CONFIG_DIR/models.yaml"

# STT Model specific dirs
VOSK_MODELS_DIR="$MODELS_DIR/stt/vosk" # Changed path
WHISPERX_USER_DATA_DIR="$MODELS_DIR/stt/whisperx/user_data" # New for WhisperX
SILERO_USER_DATA_DIR="$MODELS_DIR/stt/silero/user_data" # New for Silero (consistency)

# TTS Model specific dirs
PIPER_MODELS_DIR="$MODELS_DIR/tts/piper" # Changed path
XTTS_USER_DATA_DIR="$MODELS_DIR/tts/xtts_v2/user_data"
SPEECHBRAIN_USER_DATA_DIR="$MODELS_DIR/tts/speechbrain/user_data"
PIPER_USER_DATA_DIR="$MODELS_DIR/tts/piper/user_data"
BARK_USER_DATA_DIR="$MODELS_DIR/tts/bark/user_data" # New for Bark

# Vosk Model Details
VOSK_EN_MODEL_NAME="vosk-model-small-en-us-0.15"
VOSK_EN_URL="https://alphacephei.com/vosk/models/${VOSK_EN_MODEL_NAME}.zip"
VOSK_FR_MODEL_NAME="vosk-model-small-fr-0.22"
VOSK_FR_URL="https://alphacephei.com/vosk/models/${VOSK_FR_MODEL_NAME}.zip"

# Piper Voice Details
PIPER_VOICE_EN_NAME="en_US-lessac-medium"
PIPER_VOICE_EN_ONNX_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/${PIPER_VOICE_EN_NAME}.onnx"
PIPER_VOICE_EN_JSON_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/${PIPER_VOICE_EN_NAME}.onnx.json"

PIPER_VOICE_FR_NAME="fr_FR-siwis-medium"
PIPER_VOICE_FR_ONNX_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium/${PIPER_VOICE_FR_NAME}.onnx"
PIPER_VOICE_FR_JSON_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium/${PIPER_VOICE_FR_NAME}.onnx.json"

# --- Helper Functions ---
check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo "Error: Required command '$1' is not installed. Please install it and re-run the script."
        exit 1
    fi
}

download_file() {
    local url="$1"
    local output_path="$2"
    echo "Downloading $url to $output_path..."
    if command -v wget &> /dev/null; then
        wget -q --show-progress -O "$output_path" "$url"
    elif command -v curl &> /dev/null; then
        # Check if curl version supports --parallel for later, not used here for single files
        curl --progress-bar -L -o "$output_path" "$url"
    else
        echo "Error: Neither wget nor curl is available. Please install one."
        exit 1
    fi
    if [ $? -ne 0 ]; then
        echo "Error downloading $url. Please check the URL and your internet connection."
        # Consider removing partial download: rm -f "$output_path"
        exit 1
    fi
}

# --- Main Setup ---
echo "🚀 Starting Peer AI Models Installation and Configuration..."
echo "--------------------------------------------------------"

# 1. Check for necessary tools
echo "Checking for required tools (wget/curl, unzip)..."
if ! (command -v wget &> /dev/null || command -v curl &> /dev/null); then
  echo "Error: Neither wget nor curl is installed. Please install one of them."
  exit 1
fi
check_command "unzip"
echo "✅ Tools check passed."

# 2. Create directories
echo "Creating necessary directories under $PEER_DIR..."
mkdir -p "$MODELS_DIR/stt" # Create base STT dir
mkdir -p "$MODELS_DIR/tts" # Create base TTS dir
mkdir -p "$CONFIG_DIR"
mkdir -p "$VOSK_MODELS_DIR"
mkdir -p "$WHISPERX_USER_DATA_DIR"
mkdir -p "$SILERO_USER_DATA_DIR"
mkdir -p "$PIPER_MODELS_DIR"
mkdir -p "$XTTS_USER_DATA_DIR"
mkdir -p "$SPEECHBRAIN_USER_DATA_DIR"
mkdir -p "$PIPER_USER_DATA_DIR"
mkdir -p "$BARK_USER_DATA_DIR"
echo "✅ Directories created."

# 3. Download and set up Vosk Models
echo "--- STT: Vosk Models Setup ---"
VOSK_EN_ZIP_PATH="$VOSK_MODELS_DIR/${VOSK_EN_MODEL_NAME}.zip"
VOSK_EN_MODEL_PATH="$VOSK_MODELS_DIR/${VOSK_EN_MODEL_NAME}"
VOSK_FR_ZIP_PATH="$VOSK_MODELS_DIR/${VOSK_FR_MODEL_NAME}.zip"
VOSK_FR_MODEL_PATH="$VOSK_MODELS_DIR/${VOSK_FR_MODEL_NAME}"

if [ ! -d "$VOSK_EN_MODEL_PATH" ]; then
    echo "Downloading Vosk English model ($VOSK_EN_MODEL_NAME)..."
    download_file "$VOSK_EN_URL" "$VOSK_EN_ZIP_PATH"
    echo "Extracting Vosk English model..."
    unzip -q "$VOSK_EN_ZIP_PATH" -d "$VOSK_MODELS_DIR"
    rm "$VOSK_EN_ZIP_PATH"
    echo "✅ Vosk English model installed."
else
    echo "ℹ️ Vosk English model ($VOSK_EN_MODEL_NAME) already present."
fi

if [ ! -d "$VOSK_FR_MODEL_PATH" ]; then
    echo "Downloading Vosk French model ($VOSK_FR_MODEL_NAME)..."
    download_file "$VOSK_FR_URL" "$VOSK_FR_ZIP_PATH"
    echo "Extracting Vosk French model..."
    unzip -q "$VOSK_FR_ZIP_PATH" -d "$VOSK_MODELS_DIR"
    rm "$VOSK_FR_ZIP_PATH"
    echo "✅ Vosk French model installed."
else
    echo "ℹ️ Vosk French model ($VOSK_FR_MODEL_NAME) already present."
fi

# 4. Download and set up Piper Voices
echo "--- TTS: Piper Voices Setup ---"
PIPER_VOICE_EN_ONNX_PATH="$PIPER_MODELS_DIR/${PIPER_VOICE_EN_NAME}.onnx"
PIPER_VOICE_EN_JSON_PATH="$PIPER_MODELS_DIR/${PIPER_VOICE_EN_NAME}.onnx.json"
PIPER_VOICE_FR_ONNX_PATH="$PIPER_MODELS_DIR/${PIPER_VOICE_FR_NAME}.onnx"
PIPER_VOICE_FR_JSON_PATH="$PIPER_MODELS_DIR/${PIPER_VOICE_FR_NAME}.onnx.json"

if [ ! -f "$PIPER_VOICE_EN_ONNX_PATH" ] || [ ! -f "$PIPER_VOICE_EN_JSON_PATH" ]; then
    echo "Downloading Piper English voice ($PIPER_VOICE_EN_NAME)..."
    download_file "$PIPER_VOICE_EN_ONNX_URL" "$PIPER_VOICE_EN_ONNX_PATH"
    download_file "$PIPER_VOICE_EN_JSON_URL" "$PIPER_VOICE_EN_JSON_PATH"
    echo "✅ Piper English voice installed."
else
    echo "ℹ️ Piper English voice ($PIPER_VOICE_EN_NAME) already present."
fi

if [ ! -f "$PIPER_VOICE_FR_ONNX_PATH" ] || [ ! -f "$PIPER_VOICE_FR_JSON_PATH" ]; then
    echo "Downloading Piper French voice ($PIPER_VOICE_FR_NAME)..."
    download_file "$PIPER_VOICE_FR_ONNX_URL" "$PIPER_VOICE_FR_ONNX_PATH"
    download_file "$PIPER_VOICE_FR_JSON_URL" "$PIPER_VOICE_FR_JSON_PATH"
    echo "✅ Piper French voice installed."
else
    echo "ℹ️ Piper French voice ($PIPER_VOICE_FR_NAME) already present."
fi

# 5. Generate models.yaml configuration file
echo "--- Configuration File Generation ---"
echo "Generating $MODELS_CONFIG_FILE..."

# Expand ~ to absolute paths for YAML
ABS_MODELS_DIR=$(eval echo "$MODELS_DIR")
ABS_CONFIG_DIR=$(eval echo "$CONFIG_DIR")
ABS_VOSK_MODELS_DIR=$(eval echo "$VOSK_MODELS_DIR")
ABS_PIPER_MODELS_DIR=$(eval echo "$PIPER_MODELS_DIR")
ABS_XTTS_USER_DATA_DIR=$(eval echo "$XTTS_USER_DATA_DIR")
ABS_SPEECHBRAIN_USER_DATA_DIR=$(eval echo "$SPEECHBRAIN_USER_DATA_DIR")
ABS_PIPER_USER_DATA_DIR=$(eval echo "$PIPER_USER_DATA_DIR")
ABS_WHISPERX_USER_DATA_DIR=$(eval echo "$WHISPERX_USER_DATA_DIR") # New
ABS_SILERO_USER_DATA_DIR=$(eval echo "$SILERO_USER_DATA_DIR") # New
ABS_BARK_USER_DATA_DIR=$(eval echo "$BARK_USER_DATA_DIR") # New

cat << EOF > "$MODELS_CONFIG_FILE"
# Peer Application Model Configuration
# Auto-generated by install_models.sh on $(date +"%Y-%m-%d %H:%M:%S")

# Global settings defining storage locations
global:
  model_storage_base_dir: "$ABS_MODELS_DIR"
  config_base_dir: "$ABS_CONFIG_DIR"
  # Path for user-specific data related to models
  user_data_paths:
    whisperx: "$ABS_WHISPERX_USER_DATA_DIR"
    silero_stt: "$ABS_SILERO_USER_DATA_DIR" # Renamed for clarity
    xtts_v2: "$ABS_XTTS_USER_DATA_DIR"
    speechbrain_tts: "$ABS_SPEECHBRAIN_USER_DATA_DIR" # Renamed for clarity
    piper_tts: "$ABS_PIPER_USER_DATA_DIR" # Renamed for clarity
    bark_tts: "$ABS_BARK_USER_DATA_DIR" # Renamed for clarity

stt:
  default_engine: whisperx # Primary STT engine changed to whisperx
  engines:
    whisperx:
      name: WhisperX (Optimized Whisper)
      type: library_managed
      notes: "Advanced STT with word-level timestamps and speaker diarization. Requires 'whisperx' Python library and 'ffmpeg' system utility. Models are based on faster-whisper."
      settings:
        available_sizes: # Based on faster-whisper models
          - "tiny"
          - "tiny.en"
          - "base"
          - "base.en"
          - "small"
          - "small.en"
          - "medium"
          - "medium.en"
          - "large-v1"
          - "large-v2"
          - "large-v3"
        recommended_set:
          - "tiny.en"
          - "base.en"
          - "small.en"
          - "medium.en"
        default_size: "base.en" # Good balance for English
        ffmpeg_required: true
        # compute_type: "int8" # Example: can be configured for CPU (int8, float32) or GPU (float16, int8_float16 etc.)
      supported_languages: ["en", "fr", "es", "de", "it", "ja", "ko", "nl", "pl", "pt", "ru", "sv", "tr", "uk", "zh", "ar", "bg", "ca", "cs", "da", "el", "fi", "he", "hi", "hr", "hu", "id", "lt", "lv", "mk", "ms", "no", "ro", "sk", "sl", "sr", "th", "vi"] # Extensive list from Whisper
      user_data_path: "$ABS_WHISPERX_USER_DATA_DIR" # For potential future use or specific WhisperX caches

    vosk:
      name: Vosk
      type: local_path # Indicates models are stored locally at specified paths
      notes: "Lightweight, offline STT engine. Good for resource-constrained environments."
      models_base_path: "$ABS_VOSK_MODELS_DIR" # Base directory for Vosk models
      models:
        - language: en
          name: "$VOSK_EN_MODEL_NAME"
          path: "$ABS_VOSK_MODELS_DIR/$VOSK_EN_MODEL_NAME"
          # url: "$VOSK_EN_URL" # Original download URL (for reference)
        - language: fr
          name: "$VOSK_FR_MODEL_NAME"
          path: "$ABS_VOSK_MODELS_DIR/$VOSK_FR_MODEL_NAME"
          # url: "$VOSK_FR_URL" # Original download URL (for reference)
      supported_languages: ["en", "fr"]

    silero:
      name: Silero STT
      type: library_managed
      notes: "Lightweight and fast STT. Models managed by 'silero' Python library."
      # model_name: "silero_stt" # Specific model names/tags handled by the app's Silero integration
      supported_languages: ["en", "fr", "de", "es"]
      user_data_path: "$ABS_SILERO_USER_DATA_DIR"

tts:
  default_engine: xtts_v2
  engines:
    xtts_v2:
      name: XTTS_v2 (Coqui)
      type: library_managed
      model_name: "tts_models/multilingual/multi-dataset/xtts_v2"
      notes: "High-quality multilingual TTS with voice cloning capabilities. Requires 'TTS' Python library."
      speaker_wav_backup_path: "$ABS_XTTS_USER_DATA_DIR/speaker_voices_backup"
      finetuning_data_backup_path: "$ABS_XTTS_USER_DATA_DIR/finetuning_data_backup"
      supported_languages: ["en", "fr", "es", "de", "it", "pt", "pl", "tr", "ru", "nl", "cs", "ar", "zh-cn", "ja", "hu", "ko"]
      user_data_path: "$ABS_XTTS_USER_DATA_DIR"

    piper:
      name: Piper TTS
      type: local_path
      notes: "Fast, local, and good quality TTS engine. Voices are downloaded locally."
      voices_base_path: "$ABS_PIPER_MODELS_DIR" # Base directory for Piper voice files
      voices:
        - language: en
          name: "$PIPER_VOICE_EN_NAME"
          path_onnx: "$ABS_PIPER_MODELS_DIR/${PIPER_VOICE_EN_NAME}.onnx"
          path_json: "$ABS_PIPER_MODELS_DIR/${PIPER_VOICE_EN_NAME}.onnx.json"
          # onnx_url: "$PIPER_VOICE_EN_ONNX_URL" # Reference
          # json_url: "$PIPER_VOICE_EN_JSON_URL" # Reference
        - language: fr
          name: "$PIPER_VOICE_FR_NAME"
          path_onnx: "$ABS_PIPER_MODELS_DIR/${PIPER_VOICE_FR_NAME}.onnx"
          path_json: "$ABS_PIPER_MODELS_DIR/${PIPER_VOICE_FR_NAME}.onnx.json"
          # onnx_url: "$PIPER_VOICE_FR_ONNX_URL" # Reference
          # json_url: "$PIPER_VOICE_FR_JSON_URL" # Reference
      supported_languages: ["en", "fr"]
      user_data_path: "$ABS_PIPER_USER_DATA_DIR"

    speechbrain:
      name: SpeechBrain TTS
      type: library_managed
      notes: "TTS from SpeechBrain. Models managed by 'speechbrain' Python library."
      models: # Example model identifiers, app needs to map these to actual SpeechBrain model hub IDs
        en:
          model_name: "speechbrain/tts-fastspeech2-ljspeech"
          vocoder_name: "speechbrain/tts-hifigan-ljspeech"
        fr:
          model_name: "speechbrain/tts-tacotron2-fr-css10" # Example, verify actual model
          vocoder_name: "speechbrain/tts-hifigan-css10" # Example, verify actual model
      supported_languages: ["en", "fr"]
      user_data_path: "$ABS_SPEECHBRAIN_USER_DATA_DIR"

    bark:
      name: Bark (Suno AI)
      type: library_managed
      notes: "Generative multilingual TTS model. Requires 'bark' Python library. Known for realistic voice generation but can be slower."
      # model_name_or_path: "suno/bark" # Or "suno/bark-small". Library handles specifics.
      settings:
        # Bark has different generation parameters, e.g., history prompts for voice style.
        # These would be managed by the application's Bark integration.
        # Example: text_temp, waveform_temp
        use_small_models: false # Can be a toggle for faster, lower quality generation
      supported_languages: ["en", "fr", "de", "es", "it", "ja", "ko", "pl", "pt", "ru", "tr", "zh"] # Bark supports many languages
      user_data_path: "$ABS_BARK_USER_DATA_DIR" # For storing history prompts or other user-specific Bark assets

EOF

echo "✅ Configuration file $MODELS_CONFIG_FILE generated successfully."
echo "--------------------------------------------------------"
echo "🎉 Peer AI Models Installation and Configuration Complete!"
echo ""
echo "Next Steps:"
echo "1. Ensure this script ('install_models.sh') is executable: chmod +x install_models.sh"
echo "2. Call this script from your main './install.sh' script if it's not already."
echo "3. Make sure Python dependencies for library-managed models are installed in your project's virtual environment:"
echo "   Example: pip install openai-whisper whisperx TTS silero-models speechbrain bark"
echo "4. Your application can now use '$MODELS_CONFIG_FILE' to load and manage STT/TTS engines."
echo "--------------------------------------------------------"

exit 0
