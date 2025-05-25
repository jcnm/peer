# Système de Plugins et Intégration des Modes dans Peer

Ce document détaille l'implémentation du système de plugins et l'intégration des différents modes dans Peer, permettant une extensibilité et une adaptabilité maximales.

## Système de Plugins

Le système de plugins utilise Pluggy pour fournir une architecture extensible et modulaire.

```python
# src/peer/application/plugins/plugin_manager.py

import os
import sys
import importlib
import importlib.util
from typing import Dict, List, Any, Optional, Callable
import pluggy
import inspect

class PluginManager:
    """Plugin manager for Peer."""
    
    def __init__(self, config_manager, logger):
        self.config_manager = config_manager
        self.logger = logger
        self.plugin_hook_spec = pluggy.HookspecMarker("peer")
        self.plugin_hook_impl = pluggy.HookimplMarker("peer")
        self.plugin_manager = pluggy.PluginManager("peer")
        self.plugins = {}
        
    def initialize(self) -> None:
        """Initialize the plugin manager."""
        # Define hook specifications
        self._define_hook_specs()
        
        # Register hook specifications
        self.plugin_manager.add_hookspecs(self)
        
        # Load plugins
        self._load_plugins()
        
        self.logger.info(f"Plugin manager initialized with {len(self.plugins)} plugins")
        
    def _define_hook_specs(self) -> None:
        """Define hook specifications."""
        
        @self.plugin_hook_spec
        def peer_initialize(config: Dict[str, Any]) -> None:
            """Initialize the plugin."""
            pass
            
        @self.plugin_hook_spec
        def peer_shutdown() -> None:
            """Shutdown the plugin."""
            pass
            
        @self.plugin_hook_spec
        def peer_handle_command(command: str, args: List[str]) -> Any:
            """Handle a command."""
            pass
            
        @self.plugin_hook_spec
        def peer_analyze_code(file_path: str, content: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
            """Analyze code."""
            pass
            
        @self.plugin_hook_spec
        def peer_suggest_improvements(file_path: str, content: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
            """Suggest improvements for code."""
            pass
            
        @self.plugin_hook_spec
        def peer_handle_file_change(file_path: str, content: Optional[str], context: Dict[str, Any]) -> None:
            """Handle a file change event."""
            pass
            
        @self.plugin_hook_spec
        def peer_handle_vcs_change(changed_files: List[Dict[str, Any]], context: Dict[str, Any]) -> None:
            """Handle a VCS change event."""
            pass
            
        @self.plugin_hook_spec
        def peer_provide_feedback(feedback_type: str, details: Dict[str, Any], context: Dict[str, Any]) -> None:
            """Provide feedback to the plugin."""
            pass
            
        @self.plugin_hook_spec
        def peer_get_mode_handlers() -> Dict[str, Callable]:
            """Get mode handlers."""
            pass
            
    def _load_plugins(self) -> None:
        """Load plugins from the plugins directory."""
        try:
            # Get configuration
            config = self.config_manager.get_config("plugins")
            
            # Get plugin directories
            plugin_dirs = config.get("plugin_dirs", [])
            
            if not plugin_dirs:
                # Use default plugin directory
                plugin_dirs = [os.path.join(os.path.dirname(__file__), "..", "..", "plugins")]
                
            # Get disabled plugins
            disabled_plugins = config.get("disabled_plugins", [])
            
            # Load plugins from each directory
            for plugin_dir in plugin_dirs:
                if not os.path.isdir(plugin_dir):
                    self.logger.warning(f"Plugin directory not found: {plugin_dir}")
                    continue
                    
                # Get plugin files
                for filename in os.listdir(plugin_dir):
                    if not filename.endswith(".py") or filename.startswith("_"):
                        continue
                        
                    plugin_name = os.path.splitext(filename)[0]
                    
                    # Skip disabled plugins
                    if plugin_name in disabled_plugins:
                        self.logger.info(f"Skipping disabled plugin: {plugin_name}")
                        continue
                        
                    # Load plugin
                    plugin_path = os.path.join(plugin_dir, filename)
                    self._load_plugin(plugin_name, plugin_path)
        except Exception as e:
            self.logger.error(f"Error loading plugins: {str(e)}")
            
    def _load_plugin(self, plugin_name: str, plugin_path: str) -> None:
        """Load a plugin from a file."""
        try:
            # Import module
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Register plugin
            self.plugin_manager.register(module)
            
            # Store plugin info
            self.plugins[plugin_name] = {
                "name": plugin_name,
                "path": plugin_path,
                "module": module,
                "type": getattr(module, "PLUGIN_TYPE", "unknown")
            }
            
            self.logger.info(f"Loaded plugin: {plugin_name}")
        except Exception as e:
            self.logger.error(f"Error loading plugin {plugin_name}: {str(e)}")
            
    def call_hook(self, hook_name: str, *args, **kwargs) -> Any:
        """Call a hook."""
        try:
            # Get hook caller
            hook_caller = getattr(self.plugin_manager.hook, hook_name)
            
            # Call hook
            return hook_caller(*args, **kwargs)
        except Exception as e:
            self.logger.error(f"Error calling hook {hook_name}: {str(e)}")
            return None
            
    def get_plugins(self) -> Dict[str, Dict[str, Any]]:
        """Get all plugins."""
        return self.plugins
        
    def get_plugin(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Get a plugin by name."""
        return self.plugins.get(plugin_name)
        
    def get_plugins_by_type(self, plugin_type: str) -> Dict[str, Dict[str, Any]]:
        """Get plugins by type."""
        return {name: plugin for name, plugin in self.plugins.items() if plugin.get("type") == plugin_type}
        
    def initialize_plugins(self) -> None:
        """Initialize all plugins."""
        # Get configuration
        config = self.config_manager.get_config("plugins")
        
        # Call initialize hook
        self.call_hook("peer_initialize", config=config)
        
    def shutdown_plugins(self) -> None:
        """Shutdown all plugins."""
        # Call shutdown hook
        self.call_hook("peer_shutdown")
```

## Implémentation des Modes

Les modes sont implémentés comme des plugins spécialisés qui définissent des comportements spécifiques pour différents contextes.

```python
# src/peer/plugins/developer_mode.py

from typing import Dict, List, Any, Optional, Callable

# Plugin metadata
PLUGIN_NAME = "developer_mode"
PLUGIN_TYPE = "mode"

# Hook implementation marker (will be set by plugin manager)
plugin_hook_impl = None

def peer_initialize(config: Dict[str, Any]) -> None:
    """Initialize the plugin."""
    global plugin_hook_impl
    from peer.application.plugins.plugin_manager import PluginManager
    plugin_manager = config.get("plugin_manager")
    if plugin_manager:
        plugin_hook_impl = plugin_manager.plugin_hook_impl
    
@plugin_hook_impl
def peer_get_mode_handlers() -> Dict[str, Callable]:
    """Get mode handlers."""
    return {
        "developer": handle_developer_mode
    }
    
def handle_developer_mode(context: Dict[str, Any]) -> Dict[str, Any]:
    """Handle developer mode."""
    # Set developer-specific context
    context["focus_areas"] = ["code_quality", "performance", "readability"]
    context["suggestion_types"] = ["refactoring", "optimization", "documentation"]
    context["analysis_depth"] = "deep"
    
    # Set developer-specific prompts
    context["system_prompt"] = """
    You are a senior developer assistant. Focus on helping the user write high-quality, 
    maintainable code. Provide specific, actionable suggestions for improving code quality, 
    performance, and readability. When analyzing code, look for:
    
    1. Code smells and anti-patterns
    2. Performance bottlenecks
    3. Readability and maintainability issues
    4. Missing documentation
    5. Potential bugs and edge cases
    
    Provide concrete examples and explanations for your suggestions.
    """
    
    return context
    
@plugin_hook_impl
def peer_analyze_code(file_path: str, content: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Analyze code with developer focus."""
    # Only handle if in developer mode
    if context.get("current_mode") != "developer":
        return []
        
    # Developer-specific analysis would go here
    # This is a simplified example
    issues = []
    
    # Check for long functions (simplified example)
    lines = content.splitlines()
    in_function = False
    function_start = 0
    function_name = ""
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Very simplified function detection (for demonstration)
        if line.startswith("def ") and "(" in line:
            in_function = True
            function_start = i
            function_name = line.split("def ")[1].split("(")[0].strip()
        elif in_function and line.startswith("return "):
            function_length = i - function_start
            
            # Flag long functions
            if function_length > 30:  # Arbitrary threshold
                issues.append({
                    "line": function_start + 1,
                    "column": 0,
                    "code": "DEV001",
                    "message": f"Function '{function_name}' is too long ({function_length} lines). Consider breaking it down.",
                    "severity": "warning"
                })
                
            in_function = False
            
    return issues
    
@plugin_hook_impl
def peer_suggest_improvements(file_path: str, content: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Suggest improvements with developer focus."""
    # Only handle if in developer mode
    if context.get("current_mode") != "developer":
        return []
        
    # Developer-specific suggestions would go here
    # This is a simplified example
    suggestions = []
    
    # Check for missing docstrings (simplified example)
    lines = content.splitlines()
    in_function = False
    function_start = 0
    function_name = ""
    has_docstring = False
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Very simplified function detection (for demonstration)
        if line.startswith("def ") and "(" in line:
            in_function = True
            function_start = i
            function_name = line.split("def ")[1].split("(")[0].strip()
            has_docstring = False
        elif in_function and line.startswith('"""'):
            has_docstring = True
        elif in_function and line.startswith("return "):
            if not has_docstring:
                suggestions.append({
                    "line_start": function_start + 1,
                    "line_end": function_start + 1,
                    "suggestion_type": "documentation",
                    "description": f"Add docstring to function '{function_name}'",
                    "suggested_code": f'    """\n    Description of {function_name}.\n    \n    Args:\n        # Add parameters here\n    \n    Returns:\n        # Add return value here\n    """\n',
                    "confidence": 0.9
                })
                
            in_function = False
            
    return suggestions
```

```python
# src/peer/plugins/architect_mode.py

from typing import Dict, List, Any, Optional, Callable

# Plugin metadata
PLUGIN_NAME = "architect_mode"
PLUGIN_TYPE = "mode"

# Hook implementation marker (will be set by plugin manager)
plugin_hook_impl = None

def peer_initialize(config: Dict[str, Any]) -> None:
    """Initialize the plugin."""
    global plugin_hook_impl
    from peer.application.plugins.plugin_manager import PluginManager
    plugin_manager = config.get("plugin_manager")
    if plugin_manager:
        plugin_hook_impl = plugin_manager.plugin_hook_impl
    
@plugin_hook_impl
def peer_get_mode_handlers() -> Dict[str, Callable]:
    """Get mode handlers."""
    return {
        "architect": handle_architect_mode
    }
    
def handle_architect_mode(context: Dict[str, Any]) -> Dict[str, Any]:
    """Handle architect mode."""
    # Set architect-specific context
    context["focus_areas"] = ["architecture", "design_patterns", "system_structure"]
    context["suggestion_types"] = ["architecture", "design", "structure"]
    context["analysis_depth"] = "system"
    
    # Set architect-specific prompts
    context["system_prompt"] = """
    You are a software architect assistant. Focus on helping the user design and implement 
    robust, scalable, and maintainable software architectures. When analyzing code, look for:
    
    1. Architectural patterns and anti-patterns
    2. Component coupling and cohesion
    3. Dependency management
    4. System boundaries and interfaces
    5. Scalability and performance considerations
    
    Provide high-level architectural guidance and concrete implementation suggestions.
    """
    
    return context
    
@plugin_hook_impl
def peer_analyze_code(file_path: str, content: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Analyze code with architect focus."""
    # Only handle if in architect mode
    if context.get("current_mode") != "architect":
        return []
        
    # Architect-specific analysis would go here
    # This is a simplified example
    issues = []
    
    # Check for circular dependencies (simplified example)
    import_lines = [line.strip() for line in content.splitlines() if line.strip().startswith("import ") or line.strip().startswith("from ")]
    
    # Get current module name from file path
    import os
    module_name = os.path.splitext(os.path.basename(file_path))[0]
    
    # Check if module imports itself (simplified circular dependency check)
    for line in import_lines:
        if f"import {module_name}" in line or f"from {module_name} import" in line:
            issues.append({
                "line": content.splitlines().index(line) + 1,
                "column": 0,
                "code": "ARCH001",
                "message": f"Potential circular dependency: module imports itself",
                "severity": "error"
            })
            
    return issues
    
@plugin_hook_impl
def peer_suggest_improvements(file_path: str, content: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Suggest improvements with architect focus."""
    # Only handle if in architect mode
    if context.get("current_mode") != "architect":
        return []
        
    # Architect-specific suggestions would go here
    # This is a simplified example
    suggestions = []
    
    # Check for dependency injection opportunities (simplified example)
    lines = content.splitlines()
    class_definitions = []
    
    # Find class definitions
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith("class ") and ":" in line:
            class_name = line.split("class ")[1].split("(")[0].strip()
            class_definitions.append((i, class_name))
            
    # Check for hardcoded dependencies
    for class_start, class_name in class_definitions:
        # Look for direct instantiations in __init__
        in_init = False
        init_start = -1
        
        for i in range(class_start, len(lines)):
            line = lines[i].strip()
            
            if line.startswith("def __init__(") and "self" in line:
                in_init = True
                init_start = i
            elif in_init and line.startswith("def "):
                # End of __init__
                break
            elif in_init and " = " in line and "(" in line and ")" in line:
                # Potential direct instantiation
                var_name = line.split(" = ")[0].strip()
                class_instantiated = line.split(" = ")[1].split("(")[0].strip()
                
                # Skip self assignments and built-ins
                if var_name.startswith("self.") and class_instantiated not in ["str", "int", "list", "dict", "set", "tuple"]:
                    suggestions.append({
                        "line_start": i + 1,
                        "line_end": i + 1,
                        "suggestion_type": "architecture",
                        "description": f"Consider using dependency injection for '{class_instantiated}'",
                        "suggested_code": f"# Add {class_instantiated} as a parameter to __init__ instead of instantiating it directly\n",
                        "confidence": 0.7
                    })
                    
    return suggestions
```

```python
# src/peer/plugins/reviewer_mode.py

from typing import Dict, List, Any, Optional, Callable

# Plugin metadata
PLUGIN_NAME = "reviewer_mode"
PLUGIN_TYPE = "mode"

# Hook implementation marker (will be set by plugin manager)
plugin_hook_impl = None

def peer_initialize(config: Dict[str, Any]) -> None:
    """Initialize the plugin."""
    global plugin_hook_impl
    from peer.application.plugins.plugin_manager import PluginManager
    plugin_manager = config.get("plugin_manager")
    if plugin_manager:
        plugin_hook_impl = plugin_manager.plugin_hook_impl
    
@plugin_hook_impl
def peer_get_mode_handlers() -> Dict[str, Callable]:
    """Get mode handlers."""
    return {
        "reviewer": handle_reviewer_mode
    }
    
def handle_reviewer_mode(context: Dict[str, Any]) -> Dict[str, Any]:
    """Handle reviewer mode."""
    # Set reviewer-specific context
    context["focus_areas"] = ["code_quality", "best_practices", "security", "standards"]
    context["suggestion_types"] = ["improvement", "security", "style", "standards"]
    context["analysis_depth"] = "thorough"
    
    # Set reviewer-specific prompts
    context["system_prompt"] = """
    You are a code reviewer assistant. Focus on helping the user identify issues, 
    improvements, and best practices in their code. When reviewing code, look for:
    
    1. Code quality issues
    2. Security vulnerabilities
    3. Compliance with coding standards
    4. Test coverage and quality
    5. Documentation completeness
    
    Provide specific, actionable feedback with clear explanations of the issues and how to fix them.
    """
    
    return context
    
@plugin_hook_impl
def peer_analyze_code(file_path: str, content: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Analyze code with reviewer focus."""
    # Only handle if in reviewer mode
    if context.get("current_mode") != "reviewer":
        return []
        
    # Reviewer-specific analysis would go here
    # This is a simplified example
    issues = []
    
    # Check for security issues (simplified example)
    lines = content.splitlines()
    
    for i, line in enumerate(lines):
        line = line.strip().lower()
        
        # Check for hardcoded credentials (simplified)
        if "password" in line and "=" in line and ("\"" in line or "'" in line):
            issues.append({
                "line": i + 1,
                "column": 0,
                "code": "SEC001",
                "message": "Potential hardcoded credential detected",
                "severity": "critical"
            })
            
        # Check for SQL injection vulnerabilities (simplified)
        if "execute(" in line and "+" in line and "query" in line:
            issues.append({
                "line": i + 1,
                "column": 0,
                "code": "SEC002",
                "message": "Potential SQL injection vulnerability",
                "severity": "critical"
            })
            
    return issues
    
@plugin_hook_impl
def peer_suggest_improvements(file_path: str, content: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Suggest improvements with reviewer focus."""
    # Only handle if in reviewer mode
    if context.get("current_mode") != "reviewer":
        return []
        
    # Reviewer-specific suggestions would go here
    # This is a simplified example
    suggestions = []
    
    # Check for test coverage (simplified example)
    import os
    filename = os.path.basename(file_path)
    
    # Skip test files
    if filename.startswith("test_") or filename.endswith("_test.py"):
        return suggestions
        
    # Check if there's a corresponding test file
    test_filename = f"test_{filename}"
    test_filepath = os.path.join(os.path.dirname(file_path), test_filename)
    
    if not os.path.exists(test_filepath):
        suggestions.append({
            "line_start": 1,
            "line_end": 1,
            "suggestion_type": "testing",
            "description": f"No test file found for {filename}. Consider creating {test_filename}",
            "confidence": 0.8
        })
        
    # Check for error handling (simplified example)
    lines = content.splitlines()
    
    for i, line in enumerate(lines):
        if "except:" in line and i + 1 < len(lines) and "pass" in lines[i + 1].strip():
            suggestions.append({
                "line_start": i + 1,
                "line_end": i + 2,
                "suggestion_type": "error_handling",
                "description": "Avoid using bare except with pass. Handle exceptions explicitly or at least log them.",
                "suggested_code": "except Exception as e:\n    logger.error(f\"Error: {str(e)}\")",
                "confidence": 0.9
            })
            
    return suggestions
```

```python
# src/peer/plugins/tester_mode.py

from typing import Dict, List, Any, Optional, Callable

# Plugin metadata
PLUGIN_NAME = "tester_mode"
PLUGIN_TYPE = "mode"

# Hook implementation marker (will be set by plugin manager)
plugin_hook_impl = None

def peer_initialize(config: Dict[str, Any]) -> None:
    """Initialize the plugin."""
    global plugin_hook_impl
    from peer.application.plugins.plugin_manager import PluginManager
    plugin_manager = config.get("plugin_manager")
    if plugin_manager:
        plugin_hook_impl = plugin_manager.plugin_hook_impl
    
@plugin_hook_impl
def peer_get_mode_handlers() -> Dict[str, Callable]:
    """Get mode handlers."""
    return {
        "tester": handle_tester_mode
    }
    
def handle_tester_mode(context: Dict[str, Any]) -> Dict[str, Any]:
    """Handle tester mode."""
    # Set tester-specific context
    context["focus_areas"] = ["testing", "edge_cases", "coverage", "quality"]
    context["suggestion_types"] = ["test", "coverage", "edge_case"]
    context["analysis_depth"] = "testing"
    
    # Set tester-specific prompts
    context["system_prompt"] = """
    You are a testing assistant. Focus on helping the user write comprehensive, 
    effective tests for their code. When analyzing code, look for:
    
    1. Missing test cases
    2. Edge cases that aren't covered
    3. Opportunities for property-based testing
    4. Mocking and test isolation needs
    5. Test quality and maintainability
    
    Provide specific, actionable suggestions for improving test coverage and quality.
    """
    
    return context
    
@plugin_hook_impl
def peer_analyze_code(file_path: str, content: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Analyze code with tester focus."""
    # Only handle if in tester mode
    if context.get("current_mode") != "tester":
        return []
        
    # Tester-specific analysis would go here
    # This is a simplified example
    issues = []
    
    # Check if this is a test file
    import os
    filename = os.path.basename(file_path)
    is_test_file = filename.startswith("test_") or filename.endswith("_test.py")
    
    if is_test_file:
        # Analyze test file
        lines = content.splitlines()
        
        # Check for assertions
        has_assertions = False
        for line in lines:
            if "assert" in line or ".assert" in line or "self.assert" in line:
                has_assertions = True
                break
                
        if not has_assertions:
            issues.append({
                "line": 1,
                "column": 0,
                "code": "TEST001",
                "message": "Test file contains no assertions",
                "severity": "error"
            })
    else:
        # Analyze implementation file
        # Check for testability issues
        lines = content.splitlines()
        
        for i, line in enumerate(lines):
            # Check for global state (simplified)
            if line.strip().startswith("global "):
                issues.append({
                    "line": i + 1,
                    "column": 0,
                    "code": "TEST002",
                    "message": "Global state can make testing difficult",
                    "severity": "warning"
                })
                
            # Check for direct calls to external services (simplified)
            if "requests." in line or "urllib" in line:
                issues.append({
                    "line": i + 1,
                    "column": 0,
                    "code": "TEST003",
                    "message": "Direct external service call may need mocking for tests",
                    "severity": "info"
                })
                
    return issues
    
@plugin_hook_impl
def peer_suggest_improvements(file_path: str, content: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Suggest improvements with tester focus."""
    # Only handle if in tester mode
    if context.get("current_mode") != "tester":
        return []
        
    # Tester-specific suggestions would go here
    # This is a simplified example
    suggestions = []
    
    # Check if this is a test file
    import os
    filename = os.path.basename(file_path)
    is_test_file = filename.startswith("test_") or filename.endswith("_test.py")
    
    if is_test_file:
        # Suggest improvements for test file
        lines = content.splitlines()
        
        # Check for parameterized tests
        has_parameterized = False
        for line in lines:
            if "@parameterized" in line or "@pytest.mark.parametrize" in line:
                has_parameterized = True
                break
                
        if not has_parameterized and len(lines) > 30:  # Arbitrary threshold
            suggestions.append({
                "line_start": 1,
                "line_end": 1,
                "suggestion_type": "test",
                "description": "Consider using parameterized tests to reduce duplication",
                "suggested_code": "# Example with pytest:\n@pytest.mark.parametrize(\"input, expected\", [\n    (\"input1\", \"expected1\"),\n    (\"input2\", \"expected2\"),\n])\ndef test_function(input, expected):\n    assert function(input) == expected",
                "confidence": 0.7
            })
    else:
        # Suggest test cases for implementation file
        # Extract function definitions (simplified)
        functions = []
        lines = content.splitlines()
        
        for i, line in enumerate(lines):
            if line.strip().startswith("def ") and "(" in line and ")" in line and ":" in line:
                function_name = line.strip().split("def ")[1].split("(")[0].strip()
                functions.append((i, function_name))
                
        # Suggest test cases for each function
        for line_num, function_name in functions:
            if not function_name.startswith("_"):  # Skip private functions
                suggestions.append({
                    "line_start": line_num + 1,
                    "line_end": line_num + 1,
                    "suggestion_type": "test",
                    "description": f"Create test cases for function '{function_name}'",
                    "suggested_code": f"# Example test case:\ndef test_{function_name}():\n    # Arrange\n    # Act\n    result = {function_name}()\n    # Assert\n    assert result == expected_value",
                    "confidence": 0.8
                })
                
    return suggestions
```

## Service de Détection de Mode

Ce service détecte automatiquement le mode le plus approprié en fonction du contexte.

```python
# src/peer/domain/services/context_detection_service.py

from typing import Dict, List, Any, Optional
import re

class ContextDetectionService:
    """Service for detecting context and mode based on user input and project state."""
    
    def __init__(self, logger):
        self.logger = logger
        
    def detect_mode(self, context: Dict[str, Any], command: str) -> str:
        """Detect the most appropriate mode based on context and command."""
        # Get current mode
        current_mode = context.get("current_mode", "developer")
        
        # If command is empty, return current mode
        if not command:
            return current_mode
            
        # Convert command to lowercase for easier matching
        command_lower = command.lower()
        
        # Check for explicit mode indicators
        if any(term in command_lower for term in ["architect", "design", "structure", "pattern"]):
            return "architect"
        elif any(term in command_lower for term in ["review", "check", "analyze", "quality"]):
            return "reviewer"
        elif any(term in command_lower for term in ["test", "coverage", "assert", "mock"]):
            return "tester"
        elif any(term in command_lower for term in ["code", "implement", "function", "class"]):
            return "developer"
            
        # Check context for clues
        file_contexts = context.get("file_contexts", {})
        
        # Count file types
        test_files = 0
        implementation_files = 0
        
        for file_path in file_contexts:
            if file_path.startswith("test_") or file_path.endswith("_test.py"):
                test_files += 1
            else:
                implementation_files += 1
                
        # If mostly working with test files, suggest tester mode
        if test_files > implementation_files:
            return "tester"
            
        # Default to current mode
        return current_mode
        
    def detect_file_type(self, file_path: str, content: str) -> str:
        """Detect the type of file based on path and content."""
        # Check file extension
        if file_path.endswith(".py"):
            return "python"
        elif file_path.endswith(".js"):
            return "javascript"
        elif file_path.endswith(".ts"):
            return "typescript"
        elif file_path.endswith(".html"):
            return "html"
        elif file_path.endswith(".css"):
            return "css"
        elif file_path.endswith(".md"):
            return "markdown"
        elif file_path.endswith(".json"):
            return "json"
        elif file_path.endswith(".yaml") or file_path.endswith(".yml"):
            return "yaml"
        elif file_path.endswith(".toml"):
            return "toml"
        elif file_path.endswith(".sql"):
            return "sql"
        elif file_path.endswith(".sh"):
            return "shell"
        elif file_path.endswith(".bat"):
            return "batch"
        elif file_path.endswith(".ps1"):
            return "powershell"
        elif file_path.endswith(".c") or file_path.endswith(".h"):
            return "c"
        elif file_path.endswith(".cpp") or file_path.endswith(".hpp"):
            return "cpp"
        elif file_path.endswith(".java"):
            return "java"
        elif file_path.endswith(".go"):
            return "go"
        elif file_path.endswith(".rs"):
            return "rust"
        
        # Check content for clues
        if "#!/usr/bin/env python" in content or "import " in content or "from " in content and "import " in content:
            return "python"
        elif "function " in content or "const " in content or "let " in content or "var " in content:
            return "javascript"
        elif "<html" in content or "<!DOCTYPE html" in content:
            return "html"
        elif "@media" in content or "{" in content and ":" in content and ";" in content:
            return "css"
        
        # Default to text
        return "text"
        
    def detect_language(self, content: str) -> str:
        """Detect the programming language of the content."""
        # Count language indicators
        indicators = {
            "python": 0,
            "javascript": 0,
            "typescript": 0,
            "html": 0,
            "css": 0,
            "java": 0,
            "c": 0,
            "cpp": 0,
            "go": 0,
            "rust": 0
        }
        
        # Python indicators
        if "def " in content or "import " in content or "from " in content and "import " in content:
            indicators["python"] += 1
        if ":" in content and "    " in content:  # Indentation with 4 spaces
            indicators["python"] += 1
        if "__init__" in content or "__main__" in content:
            indicators["python"] += 1
            
        # JavaScript/TypeScript indicators
        if "function " in content or "const " in content or "let " in content or "var " in content:
            indicators["javascript"] += 1
        if "() =>" in content or "() {" in content:
            indicators["javascript"] += 1
        if "export " in content or "import " in content and "from " in content:
            indicators["javascript"] += 1
            
        # TypeScript-specific indicators
        if ": " in content and "interface " in content:
            indicators["typescript"] += 1
        if "<" in content and ">" in content and ":" in content:  # Generic types
            indicators["typescript"] += 1
            
        # HTML indicators
        if "<html" in content or "<!DOCTYPE html" in content:
            indicators["html"] += 1
        if "<div" in content or "<span" in content or "<p" in content:
            indicators["html"] += 1
            
        # CSS indicators
        if "{" in content and ":" in content and ";" in content:
            indicators["css"] += 1
        if "@media" in content or "@keyframes" in content:
            indicators["css"] += 1
            
        # Java indicators
        if "public class " in content or "private " in content or "protected " in content:
            indicators["java"] += 1
        if "System.out.println" in content or "import java." in content:
            indicators["java"] += 1
            
        # C indicators
        if "#include <" in content or "int main(" in content:
            indicators["c"] += 1
        if "printf(" in content or "scanf(" in content:
            indicators["c"] += 1
            
        # C++ indicators
        if "#include <" in content and ("std::" in content or "using namespace std" in content):
            indicators["cpp"] += 1
        if "class " in content and "::" in content:
            indicators["cpp"] += 1
            
        # Go indicators
        if "package " in content or "import (" in content:
            indicators["go"] += 1
        if "func " in content and "() {" in content:
            indicators["go"] += 1
            
        # Rust indicators
        if "fn " in content and "-> " in content:
            indicators["rust"] += 1
        if "let mut " in content or "impl " in content:
            indicators["rust"] += 1
            
        # Find language with highest score
        max_score = 0
        detected_language = "unknown"
        
        for language, score in indicators.items():
            if score > max_score:
                max_score = score
                detected_language = language
                
        return detected_language
```

## Intégration du Service Peer Assistant Omniscient

Le Service Peer Assistant Omniscient est implémenté comme un service transversal qui fonctionne en continu, analysant le contexte et fournissant un feedback adaptatif.

```python
# src/peer/domain/services/peer_assistant_service.py

from typing import Dict, List, Any, Optional
import threading
import time
import queue
import os
from datetime import datetime

class PeerAssistantService:
    """Omniscient Peer Assistant service that provides continuous feedback and assistance."""
    
    def __init__(self, llm_adapter, tts_adapter, code_analysis_service, ui_port, vcs_adapter, logger):
        self.llm_adapter = llm_adapter
        self.tts_adapter = tts_adapter
        self.code_analysis_service = code_analysis_service
        self.ui_port = ui_port
        self.vcs_adapter = vcs_adapter
        self.logger = logger
        self.event_queue = queue.Queue()
        self.running = False
        self.assistant_thread = None
        self.feedback_enabled = True
        self.voice_feedback_enabled = True
        self.last_feedback_time = {}  # Track last feedback time per file
        self.feedback_cooldown = 5  # Seconds between feedback for the same file
        
    def initialize(self) -> None:
        """Initialize the Peer Assistant service."""
        self.running = True
        self.assistant_thread = threading.Thread(target=self._assistant_loop, daemon=True)
        self.assistant_thread.start()
        self.logger.info("Peer Assistant service initialized")
        
    def shutdown(self) -> None:
        """Shutdown the Peer Assistant service."""
        self.running = False
        if self.assistant_thread:
            self.assistant_thread.join(timeout=2)
        self.logger.info("Peer Assistant service shutdown")
        
    def add_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Add an event to the queue."""
        self.event_queue.put({
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
        
    def provide_proactive_assistance(self, session) -> None:
        """Provide proactive assistance based on session context."""
        try:
            # Add event to queue
            self.add_event("proactive_assistance", {
                "session_id": session.id,
                "context": session.context
            })
        except Exception as e:
            self.logger.error(f"Error providing proactive assistance: {str(e)}")
            
    def _assistant_loop(self) -> None:
        """Main assistant loop that processes events and provides feedback."""
        while self.running:
            try:
                # Get event from queue with timeout
                try:
                    event = self.event_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                    
                # Process event
                event_type = event.get("type")
                data = event.get("data", {})
                
                if event_type == "file_change":
                    self._handle_file_change_event(data)
                elif event_type == "vcs_change":
                    self._handle_vcs_change_event(data)
                elif event_type == "proactive_assistance":
                    self._handle_proactive_assistance_event(data)
                elif event_type == "command":
                    self._handle_command_event(data)
                elif event_type == "feedback":
                    self._handle_feedback_event(data)
                    
                # Mark event as processed
                self.event_queue.task_done()
            except Exception as e:
                self.logger.error(f"Error in assistant loop: {str(e)}")
                time.sleep(1)  # Avoid tight loop on error
                
    def _handle_file_change_event(self, data: Dict[str, Any]) -> None:
        """Handle a file change event."""
        try:
            file_path = data.get("file_path")
            content = data.get("content")
            session_id = data.get("session_id")
            
            if not file_path or not content or not session_id:
                return
                
            # Check cooldown
            now = time.time()
            if file_path in self.last_feedback_time:
                elapsed = now - self.last_feedback_time[file_path]
                if elapsed < self.feedback_cooldown:
                    return
                    
            # Update last feedback time
            self.last_feedback_time[file_path] = now
            
            # Analyze file
            code_context = self.code_analysis_service.analyze_file(file_path, content)
            
            # Check for issues
            if code_context.issues:
                # Generate feedback
                feedback = self._generate_feedback(file_path, code_context)
                
                # Provide feedback
                if feedback and self.feedback_enabled:
                    if self.voice_feedback_enabled and self.tts_adapter:
                        self.tts_adapter.speak(feedback)
                    
                    if self.ui_port:
                        self.ui_port.display_notification(feedback, "peer_assistant")
        except Exception as e:
            self.logger.error(f"Error handling file change event: {str(e)}")
            
    def _handle_vcs_change_event(self, data: Dict[str, Any]) -> None:
        """Handle a VCS change event."""
        try:
            changed_files = data.get("changed_files", [])
            session_id = data.get("session_id")
            
            if not changed_files or not session_id:
                return
                
            # Analyze changes
            feedback = self._analyze_vcs_changes(changed_files)
            
            # Provide feedback
            if feedback and self.feedback_enabled:
                if self.voice_feedback_enabled and self.tts_adapter:
                    self.tts_adapter.speak(feedback)
                
                if self.ui_port:
                    self.ui_port.display_notification(feedback, "peer_assistant")
        except Exception as e:
            self.logger.error(f"Error handling VCS change event: {str(e)}")
            
    def _handle_proactive_assistance_event(self, data: Dict[str, Any]) -> None:
        """Handle a proactive assistance event."""
        try:
            session_id = data.get("session_id")
            context = data.get("context", {})
            
            if not session_id or not context:
                return
                
            # Generate proactive assistance
            assistance = self._generate_proactive_assistance(context)
            
            # Provide assistance
            if assistance and self.feedback_enabled:
                if self.voice_feedback_enabled and self.tts_adapter:
                    self.tts_adapter.speak(assistance)
                
                if self.ui_port:
                    self.ui_port.display_notification(assistance, "peer_assistant")
        except Exception as e:
            self.logger.error(f"Error handling proactive assistance event: {str(e)}")
            
    def _handle_command_event(self, data: Dict[str, Any]) -> None:
        """Handle a command event."""
        try:
            command = data.get("command")
            args = data.get("args", [])
            session_id = data.get("session_id")
            
            if not command or not session_id:
                return
                
            # Process command
            if command == "enable_feedback":
                self.feedback_enabled = True
                if self.ui_port:
                    self.ui_port.display_notification("Feedback enabled", "peer_assistant")
            elif command == "disable_feedback":
                self.feedback_enabled = False
                if self.ui_port:
                    self.ui_port.display_notification("Feedback disabled", "peer_assistant")
            elif command == "enable_voice":
                self.voice_feedback_enabled = True
                if self.ui_port:
                    self.ui_port.display_notification("Voice feedback enabled", "peer_assistant")
            elif command == "disable_voice":
                self.voice_feedback_enabled = False
                if self.ui_port:
                    self.ui_port.display_notification("Voice feedback disabled", "peer_assistant")
        except Exception as e:
            self.logger.error(f"Error handling command event: {str(e)}")
            
    def _handle_feedback_event(self, data: Dict[str, Any]) -> None:
        """Handle a feedback event."""
        try:
            feedback_type = data.get("feedback_type")
            details = data.get("details", {})
            session_id = data.get("session_id")
            
            if not feedback_type or not session_id:
                return
                
            # Process feedback
            if feedback_type == "helpful":
                # User found feedback helpful
                pass
            elif feedback_type == "not_helpful":
                # User did not find feedback helpful
                pass
            elif feedback_type == "too_frequent":
                # User thinks feedback is too frequent
                self.feedback_cooldown *= 2  # Double cooldown
            elif feedback_type == "too_infrequent":
                # User thinks feedback is too infrequent
                self.feedback_cooldown = max(1, self.feedback_cooldown // 2)  # Halve cooldown, min 1 second
        except Exception as e:
            self.logger.error(f"Error handling feedback event: {str(e)}")
            
    def _generate_feedback(self, file_path: str, code_context) -> str:
        """Generate feedback for a file."""
        try:
            # Get issues
            issues = code_context.issues
            
            if not issues:
                return None
                
            # Count issues by severity
            severity_counts = {}
            for issue in issues:
                severity = issue.severity
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
                
            # Generate feedback
            feedback = f"I noticed some issues in {os.path.basename(file_path)}: "
            
            for severity, count in severity_counts.items():
                feedback += f"{count} {severity} issues, "
                
            feedback = feedback.rstrip(", ") + "."
            
            # Add details for critical and error issues
            critical_errors = [issue for issue in issues if issue.severity in ["critical", "error"]]
            
            if critical_errors:
                feedback += " Critical issues include: "
                
                for i, issue in enumerate(critical_errors[:3]):  # Limit to 3 issues
                    feedback += f"{issue.message} (line {issue.line})"
                    
                    if i < len(critical_errors[:3]) - 1:
                        feedback += ", "
                        
            return feedback
        except Exception as e:
            self.logger.error(f"Error generating feedback: {str(e)}")
            return None
            
    def _analyze_vcs_changes(self, changed_files: List[Dict[str, Any]]) -> str:
        """Analyze VCS changes and generate feedback."""
        try:
            if not changed_files:
                return None
                
            # Count changes by type
            change_counts = {}
            for file_change in changed_files:
                change_type = file_change.get("change_type", "modified")
                change_counts[change_type] = change_counts.get(change_type, 0) + 1
                
            # Generate feedback
            feedback = "I noticed some changes in your repository: "
            
            for change_type, count in change_counts.items():
                feedback += f"{count} files {change_type}, "
                
            feedback = feedback.rstrip(", ") + "."
            
            # Add details for specific changes
            if len(changed_files) <= 5:  # Limit details to 5 files
                feedback += " Changes include: "
                
                for i, file_change in enumerate(changed_files):
                    file_path = file_change.get("file_path", "")
                    change_type = file_change.get("change_type", "modified")
                    
                    if file_path:
                        feedback += f"{os.path.basename(file_path)} ({change_type})"
                        
                        if i < len(changed_files) - 1:
                            feedback += ", "
                            
            return feedback
        except Exception as e:
            self.logger.error(f"Error analyzing VCS changes: {str(e)}")
            return None
            
    def _generate_proactive_assistance(self, context: Dict[str, Any]) -> str:
        """Generate proactive assistance based on context."""
        try:
            # Get current mode
            current_mode = context.get("current_mode", "developer")
            
            # Get file contexts
            file_contexts = context.get("file_contexts", {})
            
            if not file_contexts:
                return None
                
            # Count issues by severity
            total_issues = 0
            severity_counts = {}
            
            for file_path, file_context in file_contexts.items():
                if hasattr(file_context, "issues"):
                    issues = file_context.issues
                    total_issues += len(issues)
                    
                    for issue in issues:
                        severity = issue.severity
                        severity_counts[severity] = severity_counts.get(severity, 0) + 1
                        
            if total_issues == 0:
                return None
                
            # Generate assistance
            assistance = f"In {current_mode} mode, I've analyzed your project and found {total_issues} issues: "
            
            for severity, count in severity_counts.items():
                assistance += f"{count} {severity}, "
                
            assistance = assistance.rstrip(", ") + "."
            
            # Add mode-specific advice
            if current_mode == "developer":
                assistance += " Consider running a linter to fix style issues automatically."
            elif current_mode == "architect":
                assistance += " You might want to review the overall structure for architectural issues."
            elif current_mode == "reviewer":
                assistance += " I recommend addressing critical issues before submitting for review."
            elif current_mode == "tester":
                assistance += " Make sure to add tests for any new functionality."
                
            return assistance
        except Exception as e:
            self.logger.error(f"Error generating proactive assistance: {str(e)}")
            return None
            
    def _generate_suggestions(self, session, file_path: str, code_context) -> List[Dict[str, Any]]:
        """Generate suggestions for a file."""
        try:
            # Get current mode
            current_mode = session.current_mode
            
            # Get suggestions from plugins
            plugin_manager = session.context.get("plugin_manager")
            
            if plugin_manager:
                suggestions = plugin_manager.call_hook(
                    "peer_suggest_improvements",
                    file_path=file_path,
                    content=code_context.content,
                    context={"current_mode": current_mode}
                )
                
                if suggestions:
                    return suggestions
                    
            # Generate suggestions using LLM
            prompt = f"""
            Analyze the following code and suggest improvements. Focus on {current_mode} aspects.
            
            File: {file_path}
            
            ```
            {code_context.content}
            ```
            
            Provide suggestions in the following format:
            1. Line X-Y: [suggestion_type] Description
            2. Line Z: [suggestion_type] Description
            
            Where suggestion_type is one of: refactoring, optimization, documentation, architecture, testing, security, style.
            """
            
            response = self.llm_adapter.generate_text(prompt, session.context)
            
            # Parse suggestions
            suggestions = []
            
            for line in response.splitlines():
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                    
                # Try to parse suggestion
                try:
                    # Match pattern like "1. Line 10-15: [refactoring] Extract method"
                    import re
                    match = re.match(r'^\d+\.\s+Line\s+(\d+)(?:-(\d+))?\:\s+\[(\w+)\]\s+(.+)$', line)
                    
                    if match:
                        line_start = int(match.group(1))
                        line_end = int(match.group(2)) if match.group(2) else line_start
                        suggestion_type = match.group(3)
                        description = match.group(4)
                        
                        suggestions.append({
                            "line_start": line_start,
                            "line_end": line_end,
                            "suggestion_type": suggestion_type,
                            "description": description,
                            "confidence": 0.7
                        })
                except Exception:
                    # Skip lines that don't match the expected format
                    pass
                    
            return suggestions
        except Exception as e:
            self.logger.error(f"Error generating suggestions: {str(e)}")
            return []
```

## Conclusion

Cette implémentation du système de plugins et du Service Peer Assistant Omniscient complète l'architecture hexagonale de Peer. Le système de plugins permet d'étendre facilement les fonctionnalités de Peer avec de nouveaux modes et comportements, tandis que le Service Peer Assistant Omniscient fournit une assistance continue et adaptative en fonction du contexte.

L'architecture est maintenant complète, avec :
- Un système de plugins extensible basé sur Pluggy
- Des modes spécialisés (développeur, architecte, reviewer, testeur) implémentés comme des plugins
- Un service de détection de contexte pour adapter automatiquement le mode
- Un Service Peer Assistant Omniscient qui fonctionne en continu et de manière transversale
- Un système de feedback vocal pour signaler les problèmes en temps réel

Cette implémentation respecte les principes de l'architecture hexagonale, avec une séparation claire des responsabilités et une inversion des dépendances. Elle permet également un fonctionnement entièrement local, sans dépendances cloud, tout en offrant des fonctionnalités avancées comme l'analyse de code, la synthèse vocale et l'utilisation de modèles de langage.

Le système Peer est maintenant prêt à être utilisé et étendu avec de nouveaux plugins et fonctionnalités.
