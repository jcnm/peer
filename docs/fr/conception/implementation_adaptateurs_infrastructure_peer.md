# Implémentation des Adaptateurs d'Infrastructure de Peer

Ce document détaille l'implémentation des adaptateurs d'infrastructure pour le projet Peer, conformément à l'architecture hexagonale et aux spécifications.

## Adaptateur LLM (Ollama)

Cet adaptateur implémente le port de sortie `LLMOutputPort` en utilisant Ollama pour l'exécution locale de modèles de langage.

```python
# src/peer/infrastructure/adapters/llm/ollama_adapter.py

import json
import requests
from typing import Dict, List, Any, Optional
import time
import os

from peer.domain.ports.output_ports import LLMOutputPort

class OllamaAdapter(LLMOutputPort):
    """Adapter for Ollama LLM service."""
    
    def __init__(self, config_manager, logger):
        self.config_manager = config_manager
        self.logger = logger
        self.base_url = None
        self.model = None
        self.temperature = None
        self.max_tokens = None
        self.top_p = None
        self.timeout = None
        self.retry_attempts = None
        self.retry_delay = None
        self.cache_enabled = None
        self.cache = {}
        
    def initialize(self) -> None:
        """Initialize the Ollama adapter."""
        config = self.config_manager.get_config("llm")
        
        self.base_url = config.get("ollama_base_url", "http://localhost:11434")
        self.model = config.get("model", "codellama:7b")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 2048)
        self.top_p = config.get("top_p", 0.95)
        self.timeout = config.get("timeout_seconds", 60)
        self.retry_attempts = config.get("retry_attempts", 3)
        self.retry_delay = config.get("retry_delay_seconds", 1)
        self.cache_enabled = config.get("cache_enabled", True)
        
        # Validate connection to Ollama
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            models = response.json().get("models", [])
            
            # Check if our model is available
            model_name = self.model.split(":")[0]
            available_models = [m["name"] for m in models]
            
            if model_name not in available_models:
                self.logger.warn(f"Model {model_name} not found in Ollama. Available models: {available_models}")
                self.logger.info(f"Attempting to pull model {self.model}...")
                self._pull_model(self.model)
            else:
                self.logger.info(f"Model {model_name} is available in Ollama")
                
            self.logger.info("Ollama adapter initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to connect to Ollama at {self.base_url}: {str(e)}")
            self.logger.warn("Ensure Ollama is running and accessible")
            
    def _pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama."""
        try:
            self.logger.info(f"Pulling model {model_name}...")
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name},
                timeout=600  # Longer timeout for model pulling
            )
            response.raise_for_status()
            self.logger.info(f"Successfully pulled model {model_name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to pull model {model_name}: {str(e)}")
            return False
            
    def _get_cache_key(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate a cache key for a prompt and context."""
        if not context:
            return prompt
            
        # Sort context keys for consistent cache keys
        sorted_context = json.dumps(context, sort_keys=True)
        return f"{prompt}|{sorted_context}"
        
    def generate_text(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate text based on a prompt and context."""
        # Check cache if enabled
        if self.cache_enabled:
            cache_key = self._get_cache_key(prompt, context)
            if cache_key in self.cache:
                self.logger.debug("Using cached response for prompt")
                return self.cache[cache_key]
                
        # Prepare system message from context
        system_message = "You are Peer, an AI assistant for software development."
        if context:
            # Extract relevant context for system message
            if "current_mode" in context:
                mode = context["current_mode"]
                if mode == "developer":
                    system_message += " You focus on writing clean, efficient code and solving programming problems."
                elif mode == "architect":
                    system_message += " You focus on software architecture, design patterns, and system design."
                elif mode == "reviewer":
                    system_message += " You focus on code review, identifying issues, and suggesting improvements."
                elif mode == "tester":
                    system_message += " You focus on testing strategies, test cases, and quality assurance."
                    
            # Add project context if available
            if "project_description" in context:
                system_message += f"\nProject context: {context['project_description']}"
                
            # Add language context if available
            if "language" in context:
                system_message += f"\nPrimary language: {context['language']}"
                
        # Prepare request payload
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_message,
            "temperature": self.temperature,
            "num_predict": self.max_tokens,
            "top_p": self.top_p
        }
        
        # Send request with retries
        for attempt in range(self.retry_attempts):
            try:
                self.logger.debug(f"Sending request to Ollama (attempt {attempt+1}/{self.retry_attempts})")
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                # Extract response text
                response_data = response.json()
                generated_text = response_data.get("response", "")
                
                # Cache response if enabled
                if self.cache_enabled:
                    cache_key = self._get_cache_key(prompt, context)
                    self.cache[cache_key] = generated_text
                    
                self.logger.debug("Successfully generated text from Ollama")
                return generated_text
            except requests.exceptions.RequestException as e:
                self.logger.warn(f"Request to Ollama failed (attempt {attempt+1}/{self.retry_attempts}): {str(e)}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay)
                else:
                    self.logger.error("All retry attempts failed")
                    raise Exception(f"Failed to generate text: {str(e)}")
                    
    def generate_code(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate code based on a prompt and context."""
        # Enhance prompt for code generation
        code_prompt = f"Generate only code without explanations for the following request: {prompt}"
        
        # Add language hint if available in context
        if context and "language" in context:
            code_prompt = f"Generate {context['language']} code for the following request: {prompt}"
            
        return self.generate_text(code_prompt, context)
        
    def analyze_prompt(self, prompt: str) -> Dict[str, Any]:
        """Analyze a prompt to understand intent and entities."""
        analysis_prompt = f"""
        Analyze the following prompt and extract key information:
        
        Prompt: "{prompt}"
        
        Provide a structured analysis with the following:
        1. Main intent (e.g., code generation, explanation, refactoring)
        2. Programming language (if applicable)
        3. Key concepts or entities mentioned
        4. Required steps to fulfill the request
        
        Format your response as a JSON object with these fields.
        """
        
        try:
            response = self.generate_text(analysis_prompt)
            
            # Try to parse as JSON
            try:
                analysis = json.loads(response)
                return analysis
            except json.JSONDecodeError:
                # If not valid JSON, try to extract JSON using regex
                import re
                json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
                if json_match:
                    try:
                        analysis = json.loads(json_match.group(1))
                        return analysis
                    except json.JSONDecodeError:
                        pass
                        
                # If still not valid, create a simple structure
                self.logger.warn("Could not parse analysis response as JSON, creating simple structure")
                return {
                    "intent": "unknown",
                    "language": "unknown",
                    "entities": [],
                    "steps": [prompt]  # Default to single step with original prompt
                }
        except Exception as e:
            self.logger.error(f"Error analyzing prompt: {str(e)}")
            return {
                "intent": "unknown",
                "language": "unknown",
                "entities": [],
                "steps": [prompt]
            }
```

## Adaptateur Text-to-Speech (Piper)

Cet adaptateur implémente le port de sortie `TTSOutputPort` en utilisant Piper pour la synthèse vocale locale.

```python
# src/peer/infrastructure/adapters/tts/piper_adapter.py

import os
import subprocess
import tempfile
import threading
from typing import Dict, List, Any, Optional

from peer.domain.ports.output_ports import TTSOutputPort

class PiperAdapter(TTSOutputPort):
    """Adapter for Piper TTS service."""
    
    def __init__(self, config_manager, logger):
        self.config_manager = config_manager
        self.logger = logger
        self.model_dir = None
        self.default_voice = None
        self.rate = None
        self.volume = None
        self.enabled = None
        self.voices = []
        self.piper_path = None
        self.speaking_lock = threading.Lock()
        
    def initialize(self) -> None:
        """Initialize the Piper adapter."""
        config = self.config_manager.get_config("tts")
        
        self.model_dir = os.path.expanduser(config.get("piper_model_dir", "~/.local/share/peer/tts/piper"))
        self.default_voice = config.get("voice", "en_US-lessac-medium")
        self.rate = config.get("rate", 1.0)
        self.volume = config.get("volume", 1.0)
        self.enabled = config.get("enabled", True)
        
        # Ensure model directory exists
        os.makedirs(self.model_dir, exist_ok=True)
        
        # Find piper executable
        self.piper_path = self._find_piper_executable()
        if not self.piper_path:
            self.logger.warn("Piper executable not found, attempting to install")
            self._install_piper()
            self.piper_path = self._find_piper_executable()
            
        if not self.piper_path:
            self.logger.error("Failed to find or install Piper, TTS will be disabled")
            self.enabled = False
            return
            
        # Check for voice models
        self.voices = self._discover_voice_models()
        if not self.voices:
            self.logger.warn("No voice models found, attempting to download default voice")
            self._download_voice_model(self.default_voice)
            self.voices = self._discover_voice_models()
            
        if not self.voices:
            self.logger.error("Failed to find or download voice models, TTS will be disabled")
            self.enabled = False
            return
            
        # Validate default voice
        if self.default_voice not in self.voices:
            self.logger.warn(f"Default voice {self.default_voice} not found, using first available voice")
            self.default_voice = self.voices[0] if self.voices else None
            
        self.logger.info(f"Piper adapter initialized with {len(self.voices)} voices")
        
    def _find_piper_executable(self) -> Optional[str]:
        """Find the Piper executable in the system."""
        # Check common locations
        common_paths = [
            "/usr/bin/piper",
            "/usr/local/bin/piper",
            os.path.expanduser("~/.local/bin/piper")
        ]
        
        for path in common_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
                
        # Try using which
        try:
            result = subprocess.run(["which", "piper"], capture_output=True, text=True, check=False)
            if result.returncode == 0:
                path = result.stdout.strip()
                if path:
                    return path
        except Exception:
            pass
            
        return None
        
    def _install_piper(self) -> bool:
        """Install Piper using pip."""
        try:
            self.logger.info("Installing Piper using pip...")
            result = subprocess.run(
                ["pip", "install", "piper-tts"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                self.logger.info("Successfully installed Piper")
                return True
            else:
                self.logger.error(f"Failed to install Piper: {result.stderr}")
                return False
        except Exception as e:
            self.logger.error(f"Error installing Piper: {str(e)}")
            return False
            
    def _discover_voice_models(self) -> List[str]:
        """Discover available voice models."""
        voices = []
        
        try:
            # Check model directory for .onnx files
            for file in os.listdir(self.model_dir):
                if file.endswith(".onnx"):
                    voice_name = file.replace(".onnx", "")
                    voices.append(voice_name)
        except Exception as e:
            self.logger.error(f"Error discovering voice models: {str(e)}")
            
        return voices
        
    def _download_voice_model(self, voice_name: str) -> bool:
        """Download a voice model."""
        try:
            self.logger.info(f"Downloading voice model {voice_name}...")
            
            # Create model directory if it doesn't exist
            os.makedirs(self.model_dir, exist_ok=True)
            
            # Use piper-download command if available
            download_cmd = ["piper-download", "--model", voice_name, "--output-dir", self.model_dir]
            
            result = subprocess.run(
                download_cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                self.logger.info(f"Successfully downloaded voice model {voice_name}")
                return True
            else:
                self.logger.error(f"Failed to download voice model {voice_name}: {result.stderr}")
                return False
        except Exception as e:
            self.logger.error(f"Error downloading voice model {voice_name}: {str(e)}")
            return False
            
    def speak(self, text: str, voice: Optional[str] = None) -> None:
        """Speak the given text using the specified voice."""
        if not self.enabled:
            self.logger.warn("TTS is disabled, not speaking")
            return
            
        # Use default voice if none specified
        voice_to_use = voice if voice and voice in self.voices else self.default_voice
        
        if not voice_to_use:
            self.logger.error("No voice available for TTS")
            return
            
        # Acquire lock to prevent multiple simultaneous speech
        with self.speaking_lock:
            try:
                # Create temporary file for text
                with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as text_file:
                    text_file.write(text)
                    text_file_path = text_file.name
                    
                # Create temporary file for audio
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as audio_file:
                    audio_file_path = audio_file.name
                    
                try:
                    # Prepare model path
                    model_path = os.path.join(self.model_dir, f"{voice_to_use}.onnx")
                    
                    # Run piper to generate speech
                    cmd = [
                        self.piper_path,
                        "--model", model_path,
                        "--output_file", audio_file_path,
                        "--text_file", text_file_path
                    ]
                    
                    self.logger.debug(f"Running Piper command: {' '.join(cmd)}")
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    
                    if result.returncode != 0:
                        self.logger.error(f"Piper failed: {result.stderr}")
                        return
                        
                    # Play the audio
                    self._play_audio(audio_file_path)
                    
                finally:
                    # Clean up temporary files
                    try:
                        os.unlink(text_file_path)
                        os.unlink(audio_file_path)
                    except Exception as e:
                        self.logger.warn(f"Failed to clean up temporary files: {str(e)}")
            except Exception as e:
                self.logger.error(f"Error in TTS: {str(e)}")
                
    def _play_audio(self, audio_file_path: str) -> None:
        """Play an audio file."""
        try:
            # Try to use platform-specific commands for better performance
            if os.name == 'posix':  # Linux/Mac
                # Try aplay first (Linux)
                try:
                    subprocess.run(["aplay", audio_file_path], check=False)
                    return
                except Exception:
                    pass
                    
                # Try afplay (Mac)
                try:
                    subprocess.run(["afplay", audio_file_path], check=False)
                    return
                except Exception:
                    pass
                    
            # Fallback to python's audio playback
            self._play_audio_python(audio_file_path)
            
        except Exception as e:
            self.logger.error(f"Failed to play audio: {str(e)}")
            
    def _play_audio_python(self, audio_file_path: str) -> None:
        """Play audio using Python libraries."""
        try:
            import sounddevice as sd
            import soundfile as sf
            
            data, samplerate = sf.read(audio_file_path)
            sd.play(data, samplerate)
            sd.wait()  # Wait until audio is finished playing
        except ImportError:
            self.logger.error("sounddevice or soundfile not installed, cannot play audio")
            self.logger.info("Install with: pip install sounddevice soundfile")
        except Exception as e:
            self.logger.error(f"Error playing audio with Python: {str(e)}")
            
    def get_available_voices(self) -> List[str]:
        """Get a list of available voices."""
        return self.voices
```

## Adaptateur d'Analyse de Code (Tree-sitter)

Cet adaptateur implémente le port de sortie `CodeAnalysisOutputPort` en utilisant Tree-sitter et Ruff pour l'analyse de code.

```python
# src/peer/infrastructure/adapters/code_analysis/tree_sitter_adapter.py

import os
import subprocess
import tempfile
from typing import Dict, List, Any, Optional
import json

from peer.domain.ports.output_ports import CodeAnalysisOutputPort

class TreeSitterAdapter(CodeAnalysisOutputPort):
    """Adapter for code analysis using Tree-sitter and Ruff."""
    
    def __init__(self, config_manager, logger):
        self.config_manager = config_manager
        self.logger = logger
        self.use_tree_sitter = None
        self.use_ruff = None
        self.use_mypy = None
        self.max_file_size = None
        self.ignore_patterns = None
        self.parsers = {}
        
    def initialize(self) -> None:
        """Initialize the code analysis adapter."""
        config = self.config_manager.get_config("code_analysis")
        
        self.use_tree_sitter = config.get("use_tree_sitter", True)
        self.use_ruff = config.get("use_ruff", True)
        self.use_mypy = config.get("use_mypy", False)
        self.max_file_size = config.get("max_file_size_kb", 1024) * 1024  # Convert to bytes
        self.ignore_patterns = config.get("ignore_patterns", [])
        
        # Initialize Tree-sitter if enabled
        if self.use_tree_sitter:
            self._initialize_tree_sitter()
            
        # Check for Ruff if enabled
        if self.use_ruff:
            self._check_ruff()
            
        # Check for mypy if enabled
        if self.use_mypy:
            self._check_mypy()
            
        self.logger.info("Code analysis adapter initialized")
        
    def _initialize_tree_sitter(self) -> None:
        """Initialize Tree-sitter and load language parsers."""
        try:
            from tree_sitter import Language, Parser
            
            # Define language parsers to load
            languages = {
                "python": "https://github.com/tree-sitter/tree-sitter-python",
                "javascript": "https://github.com/tree-sitter/tree-sitter-javascript",
                "typescript": "https://github.com/tree-sitter/tree-sitter-typescript",
                "go": "https://github.com/tree-sitter/tree-sitter-go",
                "rust": "https://github.com/tree-sitter/tree-sitter-rust",
                "java": "https://github.com/tree-sitter/tree-sitter-java",
                "c": "https://github.com/tree-sitter/tree-sitter-c",
                "cpp": "https://github.com/tree-sitter/tree-sitter-cpp"
            }
            
            # Create directory for language definitions
            languages_dir = os.path.expanduser("~/.local/share/peer/tree-sitter-languages")
            os.makedirs(languages_dir, exist_ok=True)
            
            # Build language file path
            language_file = os.path.join(languages_dir, "languages.so")
            
            # Check if we need to build the languages
            build_languages = not os.path.exists(language_file)
            
            if build_languages:
                self.logger.info("Building Tree-sitter language parsers...")
                
                # Create temporary directory for cloning repositories
                with tempfile.TemporaryDirectory() as tmp_dir:
                    # Clone and build each language
                    for lang_name, repo_url in languages.items():
                        try:
                            # Clone repository
                            clone_cmd = ["git", "clone", repo_url, os.path.join(tmp_dir, lang_name)]
                            subprocess.run(clone_cmd, check=True, capture_output=True)
                            
                            self.logger.debug(f"Cloned {lang_name} parser repository")
                        except subprocess.CalledProcessError as e:
                            self.logger.error(f"Failed to clone {lang_name} parser: {e.stderr.decode()}")
                            
                    # Build languages
                    try:
                        Language.build_library(
                            language_file,
                            [os.path.join(tmp_dir, lang) for lang in languages.keys()]
                        )
                        self.logger.info("Successfully built Tree-sitter language parsers")
                    except Exception as e:
                        self.logger.error(f"Failed to build language library: {str(e)}")
                        return
                        
            # Load languages
            for lang_name in languages.keys():
                try:
                    lang = Language(language_file, lang_name)
                    parser = Parser()
                    parser.set_language(lang)
                    self.parsers[lang_name] = parser
                    self.logger.debug(f"Loaded {lang_name} parser")
                except Exception as e:
                    self.logger.error(f"Failed to load {lang_name} parser: {str(e)}")
                    
            self.logger.info(f"Initialized Tree-sitter with {len(self.parsers)} language parsers")
            
        except ImportError:
            self.logger.error("tree-sitter package not installed, disabling Tree-sitter analysis")
            self.use_tree_sitter = False
        except Exception as e:
            self.logger.error(f"Failed to initialize Tree-sitter: {str(e)}")
            self.use_tree_sitter = False
            
    def _check_ruff(self) -> None:
        """Check if Ruff is installed and available."""
        try:
            result = subprocess.run(
                ["ruff", "--version"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                self.logger.info(f"Ruff is available: {result.stdout.strip()}")
            else:
                self.logger.warn("Ruff command failed, attempting to install")
                self._install_ruff()
        except Exception:
            self.logger.warn("Ruff not found, attempting to install")
            self._install_ruff()
            
    def _install_ruff(self) -> None:
        """Install Ruff using pip."""
        try:
            self.logger.info("Installing Ruff...")
            result = subprocess.run(
                ["pip", "install", "ruff"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                self.logger.info("Successfully installed Ruff")
            else:
                self.logger.error(f"Failed to install Ruff: {result.stderr}")
                self.use_ruff = False
        except Exception as e:
            self.logger.error(f"Error installing Ruff: {str(e)}")
            self.use_ruff = False
            
    def _check_mypy(self) -> None:
        """Check if mypy is installed and available."""
        try:
            result = subprocess.run(
                ["mypy", "--version"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                self.logger.info(f"mypy is available: {result.stdout.strip()}")
            else:
                self.logger.warn("mypy command failed, attempting to install")
                self._install_mypy()
        except Exception:
            self.logger.warn("mypy not found, attempting to install")
            self._install_mypy()
            
    def _install_mypy(self) -> None:
        """Install mypy using pip."""
        try:
            self.logger.info("Installing mypy...")
            result = subprocess.run(
                ["pip", "install", "mypy"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                self.logger.info("Successfully installed mypy")
            else:
                self.logger.error(f"Failed to install mypy: {result.stderr}")
                self.use_mypy = False
        except Exception as e:
            self.logger.error(f"Error installing mypy: {str(e)}")
            self.use_mypy = False
            
    def _detect_language(self, file_path: str) -> Optional[str]:
        """Detect the programming language of a file based on its extension."""
        ext = os.path.splitext(file_path)[1].lower()
        
        # Map file extensions to language names
        extension_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
            ".c": "c",
            ".h": "c",
            ".cpp": "cpp",
            ".hpp": "cpp",
            ".cc": "cpp"
        }
        
        return extension_map.get(ext)
        
    def _should_ignore_file(self, file_path: str) -> bool:
        """Check if a file should be ignored based on patterns."""
        from fnmatch import fnmatch
        
        # Check file size
        try:
            if os.path.getsize(file_path) > self.max_file_size:
                self.logger.debug(f"Ignoring {file_path} due to size")
                return True
        except Exception:
            pass
            
        # Check ignore patterns
        for pattern in self.ignore_patterns:
            if fnmatch(file_path, pattern):
                self.logger.debug(f"Ignoring {file_path} due to pattern match: {pattern}")
                return True
                
        return False
        
    def parse_code(self, file_path: str, content: str) -> Dict[str, Any]:
        """Parse code to generate an Abstract Syntax Tree (AST) or similar structure."""
        if not self.use_tree_sitter:
            return {"error": "Tree-sitter analysis is disabled"}
            
        if self._should_ignore_file(file_path):
            return {"error": "File ignored based on configuration"}
            
        language = self._detect_language(file_path)
        if not language or language not in self.parsers:
            return {"error": f"Unsupported language for file: {file_path}"}
            
        try:
            # Parse the code
            parser = self.parsers[language]
            tree = parser.parse(content.encode('utf-8'))
            
            # Convert to a simplified representation
            root_node = tree.root_node
            
            # Create a simplified AST representation
            ast = self._node_to_dict(root_node)
            
            return {
                "language": language,
                "ast": ast
            }
        except Exception as e:
            self.logger.error(f"Error parsing {file_path}: {str(e)}")
            return {"error": f"Parsing error: {str(e)}"}
            
    def _node_to_dict(self, node) -> Dict[str, Any]:
        """Convert a Tree-sitter node to a dictionary representation."""
        result = {
            "type": node.type,
            "start_point": {"row": node.start_point[0], "column": node.start_point[1]},
            "end_point": {"row": node.end_point[0], "column": node.end_point[1]},
        }
        
        # Add children if any
        if node.child_count > 0:
            result["children"] = [self._node_to_dict(node.children[i]) for i in range(node.child_count)]
            
        return result
        
    def lint_code(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Lint code to find style issues and potential errors."""
        if not self.use_ruff:
            return []
            
        if self._should_ignore_file(file_path):
            return []
            
        language = self._detect_language(file_path)
        if language != "python":
            self.logger.debug(f"Ruff linting only supports Python, skipping {file_path}")
            return []
            
        try:
            # Create temporary file with content
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.py', delete=False) as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
                
            try:
                # Run Ruff with JSON output
                cmd = [
                    "ruff",
                    "check",
                    "--output-format=json",
                    temp_file_path
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode > 1:  # 1 means issues found, >1 means error
                    self.logger.error(f"Ruff error: {result.stderr}")
                    return []
                    
                # Parse JSON output
                if result.stdout:
                    try:
                        issues = json.loads(result.stdout)
                        
                        # Convert to standard format
                        return [
                            {
                                "line": issue.get("location", {}).get("row", 0),
                                "column": issue.get("location", {}).get("column", 0),
                                "code": issue.get("code", ""),
                                "message": issue.get("message", ""),
                                "severity": self._map_ruff_severity(issue.get("code", ""))
                            }
                            for issue in issues
                        ]
                    except json.JSONDecodeError:
                        self.logger.error("Failed to parse Ruff JSON output")
                        return []
                        
                return []
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file_path)
                except Exception:
                    pass
                    
        except Exception as e:
            self.logger.error(f"Error linting {file_path}: {str(e)}")
            return []
            
    def _map_ruff_severity(self, code: str) -> str:
        """Map Ruff error codes to severity levels."""
        # Simplified mapping
        if code.startswith("E"):
            return "error"
        elif code.startswith("W"):
            return "warning"
        elif code.startswith("F"):
            return "error"  # Flake8 errors
        elif code.startswith("I"):
            return "info"  # Import related
        elif code.startswith("N"):
            return "info"  # Naming
        elif code.startswith("S"):
            return "error"  # Security
        else:
            return "info"
            
    def check_types(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Perform static type checking on code."""
        if not self.use_mypy:
            return []
            
        if self._should_ignore_file(file_path):
            return []
            
        language = self._detect_language(file_path)
        if language != "python":
            self.logger.debug(f"mypy type checking only supports Python, skipping {file_path}")
            return []
            
        try:
            # Create temporary file with content
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.py', delete=False) as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
                
            try:
                # Run mypy
                cmd = [
                    "mypy",
                    "--no-error-summary",
                    "--no-pretty",
                    "--show-column-numbers",
                    temp_file_path
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                # Parse output
                issues = []
                if result.stdout:
                    for line in result.stdout.splitlines():
                        try:
                            # Parse mypy output format: file:line:column: severity: message
                            parts = line.split(":", 4)
                            if len(parts) >= 5:
                                _, line_num, col_num, severity, message = parts
                                
                                issues.append({
                                    "line": int(line_num),
                                    "column": int(col_num),
                                    "code": "mypy",
                                    "message": message.strip(),
                                    "severity": severity.strip().lower()
                                })
                        except Exception as e:
                            self.logger.debug(f"Failed to parse mypy output line: {line}, error: {str(e)}")
                            
                return issues
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file_path)
                except Exception:
                    pass
                    
        except Exception as e:
            self.logger.error(f"Error type checking {file_path}: {str(e)}")
            return []
```

## Adaptateur de Persistance (SQLite)

Cet adaptateur implémente le port de sortie `PersistenceOutputPort` en utilisant SQLite pour la persistance locale.

```python
# src/peer/infrastructure/adapters/persistence/sqlite_adapter.py

import os
import json
import sqlite3
from typing import Dict, List, Any, Optional
from datetime import datetime

from peer.domain.ports.output_ports import PersistenceOutputPort

class SQLiteAdapter(PersistenceOutputPort):
    """Adapter for SQLite persistence."""
    
    def __init__(self, config_manager, logger):
        self.config_manager = config_manager
        self.logger = logger
        self.db_path = None
        self.conn = None
        
    def initialize(self) -> None:
        """Initialize the SQLite adapter."""
        config = self.config_manager.get_config("session").get("sqlite_config", {})
        
        self.db_path = os.path.expanduser(config.get("db_path", "~/.local/share/peer/data/sessions.db"))
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        try:
            # Connect to database
            self.conn = sqlite3.connect(self.db_path)
            
            # Enable foreign keys
            self.conn.execute("PRAGMA foreign_keys = ON")
            
            # Create tables if they don't exist
            self._create_tables()
            
            self.logger.info(f"SQLite adapter initialized with database at {self.db_path}")
        except Exception as e:
            self.logger.error(f"Failed to initialize SQLite adapter: {str(e)}")
            
    def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # Sessions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            project_root TEXT NOT NULL,
            start_time TEXT NOT NULL,
            last_activity TEXT NOT NULL,
            current_mode TEXT NOT NULL,
            context TEXT,
            created_at TEXT NOT NULL
        )
        ''')
        
        # File contexts table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS file_contexts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            file_path TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            context TEXT,
            last_analyzed TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
            UNIQUE(session_id, file_path)
        )
        ''')
        
        # History events table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS history_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_data TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        )
        ''')
        
        # Analysis results table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            result TEXT,
            analyzed_at TEXT NOT NULL,
            UNIQUE(file_path, content_hash)
        )
        ''')
        
        self.conn.commit()
        
    def save_session(self, session_id: str, session_data: Dict[str, Any]) -> None:
        """Save session data."""
        try:
            cursor = self.conn.cursor()
            
            # Extract basic session data
            project_root = session_data.get("project_root", "")
            start_time = session_data.get("start_time", datetime.now().isoformat())
            last_activity = session_data.get("last_activity", datetime.now().isoformat())
            current_mode = session_data.get("current_mode", "developer")
            
            # Convert datetime objects to ISO format strings if needed
            if isinstance(start_time, datetime):
                start_time = start_time.isoformat()
            if isinstance(last_activity, datetime):
                last_activity = last_activity.isoformat()
                
            # Extract context, file_contexts, and history
            context = session_data.get("context", {})
            file_contexts = session_data.get("file_contexts", {})
            history = session_data.get("history", [])
            
            # Insert or update session
            cursor.execute('''
            INSERT INTO sessions (id, project_root, start_time, last_activity, current_mode, context, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                project_root = excluded.project_root,
                start_time = excluded.start_time,
                last_activity = excluded.last_activity,
                current_mode = excluded.current_mode,
                context = excluded.context
            ''', (
                session_id,
                project_root,
                start_time,
                last_activity,
                current_mode,
                json.dumps(context),
                datetime.now().isoformat()
            ))
            
            # Save file contexts
            for file_path, file_context in file_contexts.items():
                if not file_context:
                    continue
                    
                # Convert file context to serializable format
                file_context_dict = {}
                for key, value in file_context.__dict__.items():
                    if key == "last_analyzed" and isinstance(value, datetime):
                        file_context_dict[key] = value.isoformat()
                    elif key == "issues" or key == "suggestions":
                        file_context_dict[key] = [item.__dict__ for item in value]
                    else:
                        file_context_dict[key] = value
                        
                # Calculate content hash
                content_hash = self._calculate_hash(file_context_dict.get("content", ""))
                
                cursor.execute('''
                INSERT INTO file_contexts (session_id, file_path, content_hash, context, last_analyzed, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, file_path) DO UPDATE SET
                    content_hash = excluded.content_hash,
                    context = excluded.context,
                    last_analyzed = excluded.last_analyzed
                ''', (
                    session_id,
                    file_path,
                    content_hash,
                    json.dumps(file_context_dict),
                    file_context_dict.get("last_analyzed", datetime.now().isoformat()),
                    datetime.now().isoformat()
                ))
                
            # Save history events
            for event in history:
                event_type = event.get("type", "unknown")
                event_data = event.get("data", {})
                timestamp = event.get("timestamp", datetime.now().isoformat())
                
                if isinstance(timestamp, datetime):
                    timestamp = timestamp.isoformat()
                    
                cursor.execute('''
                INSERT INTO history_events (session_id, event_type, event_data, timestamp)
                VALUES (?, ?, ?, ?)
                ''', (
                    session_id,
                    event_type,
                    json.dumps(event_data),
                    timestamp
                ))
                
            self.conn.commit()
            self.logger.debug(f"Saved session {session_id}")
            
        except Exception as e:
            self.logger.error(f"Error saving session {session_id}: {str(e)}")
            self.conn.rollback()
            
    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session data."""
        try:
            cursor = self.conn.cursor()
            
            # Load session
            cursor.execute('''
            SELECT id, project_root, start_time, last_activity, current_mode, context
            FROM sessions
            WHERE id = ?
            ''', (session_id,))
            
            session_row = cursor.fetchone()
            if not session_row:
                self.logger.warn(f"Session {session_id} not found")
                return None
                
            # Parse session data
            session_data = {
                "id": session_row[0],
                "project_root": session_row[1],
                "start_time": session_row[2],
                "last_activity": session_row[3],
                "current_mode": session_row[4],
                "context": json.loads(session_row[5]) if session_row[5] else {},
                "file_contexts": {},
                "history": []
            }
            
            # Load file contexts
            cursor.execute('''
            SELECT file_path, context
            FROM file_contexts
            WHERE session_id = ?
            ''', (session_id,))
            
            for file_row in cursor.fetchall():
                file_path = file_row[0]
                file_context = json.loads(file_row[1]) if file_row[1] else {}
                session_data["file_contexts"][file_path] = file_context
                
            # Load history events
            cursor.execute('''
            SELECT event_type, event_data, timestamp
            FROM history_events
            WHERE session_id = ?
            ORDER BY timestamp ASC
            ''', (session_id,))
            
            for event_row in cursor.fetchall():
                event_type = event_row[0]
                event_data = json.loads(event_row[1]) if event_row[1] else {}
                timestamp = event_row[2]
                
                session_data["history"].append({
                    "type": event_type,
                    "data": event_data,
                    "timestamp": timestamp
                })
                
            self.logger.debug(f"Loaded session {session_id}")
            return session_data
            
        except Exception as e:
            self.logger.error(f"Error loading session {session_id}: {str(e)}")
            return None
            
    def delete_session(self, session_id: str) -> None:
        """Delete session data."""
        try:
            cursor = self.conn.cursor()
            
            # Delete session (will cascade to file_contexts and history_events)
            cursor.execute('''
            DELETE FROM sessions
            WHERE id = ?
            ''', (session_id,))
            
            self.conn.commit()
            self.logger.info(f"Deleted session {session_id}")
            
        except Exception as e:
            self.logger.error(f"Error deleting session {session_id}: {str(e)}")
            self.conn.rollback()
            
    def save_analysis_result(self, file_path: str, result: Dict[str, Any]) -> None:
        """Save code analysis results."""
        try:
            # Calculate content hash
            content = result.get("content", "")
            content_hash = self._calculate_hash(content)
            
            cursor = self.conn.cursor()
            
            # Insert or update analysis result
            cursor.execute('''
            INSERT INTO analysis_results (file_path, content_hash, result, analyzed_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(file_path, content_hash) DO UPDATE SET
                result = excluded.result,
                analyzed_at = excluded.analyzed_at
            ''', (
                file_path,
                content_hash,
                json.dumps(result),
                datetime.now().isoformat()
            ))
            
            self.conn.commit()
            self.logger.debug(f"Saved analysis result for {file_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving analysis result for {file_path}: {str(e)}")
            self.conn.rollback()
            
    def load_analysis_result(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Load code analysis results."""
        try:
            cursor = self.conn.cursor()
            
            # Load latest analysis result
            cursor.execute('''
            SELECT result
            FROM analysis_results
            WHERE file_path = ?
            ORDER BY analyzed_at DESC
            LIMIT 1
            ''', (file_path,))
            
            result_row = cursor.fetchone()
            if not result_row:
                self.logger.debug(f"No analysis result found for {file_path}")
                return None
                
            result = json.loads(result_row[0]) if result_row[0] else {}
            self.logger.debug(f"Loaded analysis result for {file_path}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error loading analysis result for {file_path}: {str(e)}")
            return None
            
    def _calculate_hash(self, content: str) -> str:
        """Calculate a hash for content."""
        import hashlib
        return hashlib.md5(content.encode('utf-8')).hexdigest()
        
    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.logger.debug("Closed SQLite connection")
```

## Adaptateur de Système de Fichiers

Cet adaptateur implémente le port de sortie `FileSystemOutputPort` pour interagir avec le système de fichiers.

```python
# src/peer/infrastructure/adapters/file_system/file_system_adapter.py

import os
from typing import Dict, List, Any, Optional

from peer.domain.ports.output_ports import FileSystemOutputPort

class FileSystemAdapter(FileSystemOutputPort):
    """Adapter for file system operations."""
    
    def __init__(self, logger):
        self.logger = logger
        
    def read_file(self, file_path: str) -> str:
        """Read the content of a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except UnicodeDecodeError:
            self.logger.warn(f"Failed to read {file_path} as UTF-8, trying with error handling")
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                return content
            except Exception as e:
                self.logger.error(f"Failed to read {file_path} with error handling: {str(e)}")
                raise
        except Exception as e:
            self.logger.error(f"Failed to read {file_path}: {str(e)}")
            raise
            
    def write_file(self, file_path: str, content: str) -> None:
        """Write content to a file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            self.logger.error(f"Failed to write to {file_path}: {str(e)}")
            raise
            
    def file_exists(self, file_path: str) -> bool:
        """Check if a file exists."""
        return os.path.isfile(file_path)
        
    def list_directory(self, dir_path: str) -> List[str]:
        """List the contents of a directory."""
        try:
            return os.listdir(dir_path)
        except Exception as e:
            self.logger.error(f"Failed to list directory {dir_path}: {str(e)}")
            raise
```

## Adaptateur de Contrôle de Version (Git)

Cet adaptateur implémente le port de sortie `VCSOutputPort` en utilisant GitPython pour interagir avec Git.

```python
# src/peer/infrastructure/adapters/vcs/git_adapter.py

import os
from typing import Dict, List, Any, Optional

from peer.domain.ports.output_ports import VCSOutputPort

class GitAdapter(VCSOutputPort):
    """Adapter for Git version control system."""
    
    def __init__(self, config_manager, logger):
        self.config_manager = config_manager
        self.logger = logger
        self.git_module = None
        
    def initialize(self) -> None:
        """Initialize the Git adapter."""
        try:
            import git
            self.git_module = git
            self.logger.info("Git adapter initialized")
        except ImportError:
            self.logger.error("gitpython package not installed, attempting to install")
            self._install_gitpython()
            
    def _install_gitpython(self) -> None:
        """Install gitpython using pip."""
        import subprocess
        
        try:
            self.logger.info("Installing gitpython...")
            result = subprocess.run(
                ["pip", "install", "gitpython"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                self.logger.info("Successfully installed gitpython")
                import git
                self.git_module = git
            else:
                self.logger.error(f"Failed to install gitpython: {result.stderr}")
        except Exception as e:
            self.logger.error(f"Error installing gitpython: {str(e)}")
            
    def _get_repo(self, repo_path: str):
        """Get a Git repository object."""
        if not self.git_module:
            raise Exception("Git module not initialized")
            
        try:
            return self.git_module.Repo(repo_path)
        except Exception as e:
            self.logger.error(f"Failed to open Git repository at {repo_path}: {str(e)}")
            raise
            
    def get_changed_files(self, repo_path: str) -> List[Dict[str, Any]]:
        """Get a list of changed files in the repository."""
        try:
            repo = self._get_repo(repo_path)
            changed_files = []
            
            # Get modified files
            for item in repo.index.diff(None):
                changed_files.append({
                    "path": item.a_path,
                    "status": self._get_change_type(item),
                    "staged": False
                })
                
            # Get staged files
            for item in repo.index.diff("HEAD"):
                changed_files.append({
                    "path": item.a_path,
                    "status": self._get_change_type(item),
                    "staged": True
                })
                
            # Get untracked files
            for path in repo.untracked_files:
                changed_files.append({
                    "path": path,
                    "status": "untracked",
                    "staged": False
                })
                
            return changed_files
        except Exception as e:
            self.logger.error(f"Failed to get changed files for {repo_path}: {str(e)}")
            return []
            
    def _get_change_type(self, diff_item) -> str:
        """Get the type of change for a diff item."""
        if diff_item.new_file:
            return "added"
        elif diff_item.deleted_file:
            return "deleted"
        elif diff_item.renamed:
            return "renamed"
        else:
            return "modified"
            
    def get_file_diff(self, repo_path: str, file_path: str) -> str:
        """Get the diff for a specific file."""
        try:
            repo = self._get_repo(repo_path)
            
            # Get diff for the file
            diff = repo.git.diff(file_path)
            return diff
        except Exception as e:
            self.logger.error(f"Failed to get diff for {file_path} in {repo_path}: {str(e)}")
            return ""
            
    def get_current_branch(self, repo_path: str) -> str:
        """Get the current branch name."""
        try:
            repo = self._get_repo(repo_path)
            return repo.active_branch.name
        except Exception as e:
            self.logger.error(f"Failed to get current branch for {repo_path}: {str(e)}")
            return ""
```

## Conclusion

Cette implémentation des adaptateurs d'infrastructure fournit les connexions concrètes entre la couche Domaine et les services externes. Chaque adaptateur implémente un port de sortie défini dans la couche Domaine, respectant ainsi le principe d'inversion de dépendance de l'architecture hexagonale.

Les adaptateurs implémentés couvrent :
- L'interaction avec les modèles de langage via Ollama
- La synthèse vocale via Piper
- L'analyse de code via Tree-sitter et Ruff
- La persistance des données via SQLite
- Les opérations sur le système de fichiers
- L'interaction avec Git pour le contrôle de version

Ces adaptateurs permettent à Peer de fonctionner entièrement en local, sans dépendances cloud, tout en offrant des fonctionnalités avancées comme l'analyse de code, la synthèse vocale et l'utilisation de modèles de langage.

Les prochaines étapes consisteront à implémenter les interfaces utilisateur (CLI, TUI, API) et à connecter tous ces composants ensemble pour former le système complet.
