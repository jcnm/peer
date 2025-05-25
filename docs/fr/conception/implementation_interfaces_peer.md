# Implémentation des Interfaces Utilisateur de Peer

Ce document détaille l'implémentation des interfaces utilisateur pour le projet Peer, conformément à l'architecture hexagonale et aux spécifications.

## Interface en Ligne de Commande (CLI)

Cette interface utilise Typer pour fournir une expérience en ligne de commande moderne et intuitive.

```python
# src/peer/interfaces/cli/commands.py

import os
import sys
import typer
from typing import Dict, List, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
import uuid

from peer.domain.ports.input_ports import PeerInputPort

app = typer.Typer(
    name="peer",
    help="Peer - AI Assistant for Development",
    add_completion=True
)

console = Console()

class CLIInterface:
    """CLI interface for Peer."""
    
    def __init__(self, peer_input_port: PeerInputPort, config_manager, logger):
        self.peer_input_port = peer_input_port
        self.config_manager = config_manager
        self.logger = logger
        self.current_session_id = None
        
    def initialize(self) -> None:
        """Initialize the CLI interface."""
        self.logger.info("CLI interface initialized")
        
        # Register commands
        self._register_commands()
        
    def _register_commands(self) -> None:
        """Register CLI commands."""
        # Main command groups
        self._register_analyze_commands()
        self._register_suggest_commands()
        self._register_explain_commands()
        self._register_session_commands()
        self._register_config_commands()
        self._register_plugin_commands()
        
    def _register_analyze_commands(self) -> None:
        """Register analyze commands."""
        
        @app.command("analyze")
        def analyze(
            path: str = typer.Argument(..., help="Path to file or directory to analyze"),
            recursive: bool = typer.Option(False, "--recursive", "-r", help="Analyze directory recursively"),
            verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed analysis")
        ):
            """Analyze code for issues and suggestions."""
            try:
                # Ensure session exists
                session_id = self._ensure_session()
                
                # Determine if path is file or directory
                if os.path.isfile(path):
                    self._analyze_file(session_id, path, verbose)
                elif os.path.isdir(path):
                    self._analyze_directory(session_id, path, recursive, verbose)
                else:
                    console.print(f"[bold red]Error:[/] Path not found: {path}")
                    sys.exit(1)
            except Exception as e:
                console.print(f"[bold red]Error:[/] {str(e)}")
                self.logger.error(f"Error in analyze command: {str(e)}")
                sys.exit(1)
                
        @app.command("lint")
        def lint(
            path: str = typer.Argument(..., help="Path to file or directory to lint"),
            fix: bool = typer.Option(False, "--fix", "-f", help="Automatically fix issues where possible")
        ):
            """Lint code for style and formatting issues."""
            try:
                # Ensure session exists
                session_id = self._ensure_session()
                
                # TODO: Implement linting logic
                console.print(f"Linting {path}...")
                
                # Placeholder for actual implementation
                if fix:
                    console.print("Fixing issues...")
                
                console.print("[bold green]Linting complete![/]")
            except Exception as e:
                console.print(f"[bold red]Error:[/] {str(e)}")
                self.logger.error(f"Error in lint command: {str(e)}")
                sys.exit(1)
                
    def _register_suggest_commands(self) -> None:
        """Register suggest commands."""
        
        @app.command("suggest")
        def suggest(
            path: str = typer.Argument(..., help="Path to file to suggest improvements for"),
            type: str = typer.Option(None, "--type", "-t", help="Type of suggestion (refactor, performance, security, style)"),
            apply: bool = typer.Option(False, "--apply", "-a", help="Apply suggestions automatically")
        ):
            """Suggest improvements for code."""
            try:
                # Ensure session exists
                session_id = self._ensure_session()
                
                # Read file
                if not os.path.isfile(path):
                    console.print(f"[bold red]Error:[/] File not found: {path}")
                    sys.exit(1)
                    
                with open(path, 'r') as f:
                    content = f.read()
                    
                # Get suggestions
                suggestions = self.peer_input_port.suggest_improvements(session_id, path, content)
                
                # Filter by type if specified
                if type:
                    suggestions = [s for s in suggestions if s.get("suggestion_type") == type]
                    
                # Display suggestions
                if not suggestions:
                    console.print("No suggestions found.")
                    return
                    
                console.print(f"[bold green]Found {len(suggestions)} suggestions:[/]")
                
                table = Table(show_header=True, header_style="bold")
                table.add_column("Line")
                table.add_column("Type")
                table.add_column("Description")
                
                for i, suggestion in enumerate(suggestions):
                    table.add_row(
                        f"{suggestion.get('line_start')}-{suggestion.get('line_end')}",
                        suggestion.get("suggestion_type", ""),
                        suggestion.get("description", "")
                    )
                    
                console.print(table)
                
                # Apply suggestions if requested
                if apply and suggestions:
                    console.print("Applying suggestions...")
                    # TODO: Implement suggestion application
                    console.print("[bold green]Suggestions applied![/]")
            except Exception as e:
                console.print(f"[bold red]Error:[/] {str(e)}")
                self.logger.error(f"Error in suggest command: {str(e)}")
                sys.exit(1)
                
    def _register_explain_commands(self) -> None:
        """Register explain commands."""
        
        @app.command("explain")
        def explain(
            path: str = typer.Argument(..., help="Path to file to explain"),
            line: int = typer.Option(None, "--line", "-l", help="Line number to explain"),
            verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed explanation")
        ):
            """Explain code and concepts."""
            try:
                # Ensure session exists
                session_id = self._ensure_session()
                
                # Read file
                if not os.path.isfile(path):
                    console.print(f"[bold red]Error:[/] File not found: {path}")
                    sys.exit(1)
                    
                with open(path, 'r') as f:
                    content = f.read()
                    
                # Prepare context
                context = {
                    "file_path": path,
                    "line": line,
                    "verbose": verbose
                }
                
                # Execute explain command
                result = self.peer_input_port.execute_command(
                    session_id,
                    "explain",
                    [path, f"--line={line}" if line else "", "--verbose" if verbose else ""]
                )
                
                # Display explanation
                if isinstance(result, str):
                    console.print(Markdown(result))
                else:
                    console.print(result)
            except Exception as e:
                console.print(f"[bold red]Error:[/] {str(e)}")
                self.logger.error(f"Error in explain command: {str(e)}")
                sys.exit(1)
                
    def _register_session_commands(self) -> None:
        """Register session commands."""
        
        @app.command("init")
        def init(
            project_root: str = typer.Argument(None, help="Root directory of the project"),
            mode: str = typer.Option("developer", "--mode", "-m", help="Initial mode (developer, architect, reviewer, tester)")
        ):
            """Initialize a new Peer session."""
            try:
                # Use current directory if no project root specified
                if not project_root:
                    project_root = os.getcwd()
                    
                # Ensure project root exists
                if not os.path.isdir(project_root):
                    console.print(f"[bold red]Error:[/] Project root not found: {project_root}")
                    sys.exit(1)
                    
                # Initialize session
                session_data = self.peer_input_port.initialize_session(project_root)
                
                if not session_data:
                    console.print("[bold red]Error:[/] Failed to initialize session")
                    sys.exit(1)
                    
                session_id = session_data.get("id")
                
                # Save session ID
                self.current_session_id = session_id
                
                # Set mode
                self.peer_input_port.update_configuration(session_id, "core", "current_mode", mode)
                
                console.print(f"[bold green]Session initialized:[/] {session_id}")
                console.print(f"Project root: {project_root}")
                console.print(f"Mode: {mode}")
            except Exception as e:
                console.print(f"[bold red]Error:[/] {str(e)}")
                self.logger.error(f"Error in init command: {str(e)}")
                sys.exit(1)
                
        @app.command("status")
        def status():
            """Show current session status."""
            try:
                # Get current session
                session_id = self._get_current_session()
                
                if not session_id:
                    console.print("[bold yellow]No active session.[/] Use 'peer init' to create one.")
                    return
                    
                # Get session status
                session_status = self.peer_input_port.get_session_status(session_id)
                
                if not session_status:
                    console.print(f"[bold red]Error:[/] Failed to get session status")
                    return
                    
                # Display status
                console.print(Panel.fit(
                    f"[bold green]Session ID:[/] {session_id}\n"
                    f"[bold green]Project Root:[/] {session_status.get('project_root', 'Unknown')}\n"
                    f"[bold green]Mode:[/] {session_status.get('current_mode', 'developer')}\n"
                    f"[bold green]Start Time:[/] {session_status.get('start_time', 'Unknown')}\n"
                    f"[bold green]Last Activity:[/] {session_status.get('last_activity', 'Unknown')}\n"
                    f"[bold green]Files Analyzed:[/] {len(session_status.get('file_contexts', {}))}\n"
                    f"[bold green]History Events:[/] {len(session_status.get('history', []))}",
                    title="Peer Session Status",
                    border_style="green"
                ))
            except Exception as e:
                console.print(f"[bold red]Error:[/] {str(e)}")
                self.logger.error(f"Error in status command: {str(e)}")
                
    def _register_config_commands(self) -> None:
        """Register configuration commands."""
        
        config_app = typer.Typer(help="Manage configuration")
        app.add_typer(config_app, name="config")
        
        @config_app.command("get")
        def config_get(
            section: str = typer.Argument(..., help="Configuration section"),
            key: str = typer.Argument(None, help="Configuration key")
        ):
            """Get configuration value."""
            try:
                # Get configuration
                config = self.config_manager.get_config(section)
                
                if key:
                    # Get specific key
                    if key in config:
                        value = config[key]
                        console.print(f"{section}.{key} = {value}")
                    else:
                        console.print(f"[bold yellow]Key not found:[/] {section}.{key}")
                else:
                    # Show entire section
                    table = Table(show_header=True, header_style="bold")
                    table.add_column("Key")
                    table.add_column("Value")
                    
                    for k, v in config.items():
                        table.add_row(k, str(v))
                        
                    console.print(f"[bold green]Configuration section:[/] {section}")
                    console.print(table)
            except Exception as e:
                console.print(f"[bold red]Error:[/] {str(e)}")
                self.logger.error(f"Error in config get command: {str(e)}")
                
        @config_app.command("set")
        def config_set(
            section: str = typer.Argument(..., help="Configuration section"),
            key: str = typer.Argument(..., help="Configuration key"),
            value: str = typer.Argument(..., help="Configuration value")
        ):
            """Set configuration value."""
            try:
                # Convert value to appropriate type
                typed_value = self._convert_value(value)
                
                # Set configuration
                self.config_manager.set_config(section, key, typed_value)
                
                # Save configuration
                self.config_manager.save_config()
                
                console.print(f"[bold green]Configuration updated:[/] {section}.{key} = {typed_value}")
            except Exception as e:
                console.print(f"[bold red]Error:[/] {str(e)}")
                self.logger.error(f"Error in config set command: {str(e)}")
                
        @config_app.command("list")
        def config_list():
            """List configuration sections."""
            try:
                # Get sections
                sections = self.config_manager.get_sections()
                
                console.print("[bold green]Configuration sections:[/]")
                for section in sections:
                    console.print(f"- {section}")
            except Exception as e:
                console.print(f"[bold red]Error:[/] {str(e)}")
                self.logger.error(f"Error in config list command: {str(e)}")
                
        @config_app.command("reset")
        def config_reset(
            confirm: bool = typer.Option(False, "--confirm", help="Confirm reset")
        ):
            """Reset configuration to defaults."""
            try:
                if not confirm:
                    console.print("[bold yellow]Warning:[/] This will reset all configuration to defaults.")
                    console.print("Use --confirm to proceed.")
                    return
                    
                # Reset configuration
                self.config_manager.reset_to_defaults()
                
                console.print("[bold green]Configuration reset to defaults.[/]")
            except Exception as e:
                console.print(f"[bold red]Error:[/] {str(e)}")
                self.logger.error(f"Error in config reset command: {str(e)}")
                
    def _register_plugin_commands(self) -> None:
        """Register plugin commands."""
        
        plugin_app = typer.Typer(help="Manage plugins")
        app.add_typer(plugin_app, name="plugin")
        
        @plugin_app.command("list")
        def plugin_list():
            """List installed plugins."""
            try:
                # Get plugin manager
                plugin_manager = self.config_manager.get_service("plugin_manager")
                
                if not plugin_manager:
                    console.print("[bold red]Error:[/] Plugin manager not available")
                    return
                    
                # Get plugins
                plugins = plugin_manager.get_plugins()
                
                if not plugins:
                    console.print("No plugins installed.")
                    return
                    
                # Display plugins
                table = Table(show_header=True, header_style="bold")
                table.add_column("Name")
                table.add_column("Type")
                table.add_column("Path")
                
                for name, plugin in plugins.items():
                    table.add_row(
                        name,
                        plugin.get("type", "unknown"),
                        plugin.get("path", "")
                    )
                    
                console.print("[bold green]Installed plugins:[/]")
                console.print(table)
            except Exception as e:
                console.print(f"[bold red]Error:[/] {str(e)}")
                self.logger.error(f"Error in plugin list command: {str(e)}")
                
        @plugin_app.command("enable")
        def plugin_enable(
            name: str = typer.Argument(..., help="Plugin name")
        ):
            """Enable a plugin."""
            try:
                # Get configuration
                config = self.config_manager.get_config("plugins")
                
                # Get disabled plugins
                disabled_plugins = config.get("disabled_plugins", [])
                
                if name not in disabled_plugins:
                    console.print(f"[bold yellow]Plugin {name} is already enabled.[/]")
                    return
                    
                # Enable plugin
                disabled_plugins.remove(name)
                
                # Update configuration
                self.config_manager.set_config("plugins", "disabled_plugins", disabled_plugins)
                
                # Save configuration
                self.config_manager.save_config()
                
                console.print(f"[bold green]Plugin {name} enabled.[/]")
                console.print("Restart Peer for changes to take effect.")
            except Exception as e:
                console.print(f"[bold red]Error:[/] {str(e)}")
                self.logger.error(f"Error in plugin enable command: {str(e)}")
                
        @plugin_app.command("disable")
        def plugin_disable(
            name: str = typer.Argument(..., help="Plugin name")
        ):
            """Disable a plugin."""
            try:
                # Get configuration
                config = self.config_manager.get_config("plugins")
                
                # Get disabled plugins
                disabled_plugins = config.get("disabled_plugins", [])
                
                if name in disabled_plugins:
                    console.print(f"[bold yellow]Plugin {name} is already disabled.[/]")
                    return
                    
                # Disable plugin
                disabled_plugins.append(name)
                
                # Update configuration
                self.config_manager.set_config("plugins", "disabled_plugins", disabled_plugins)
                
                # Save configuration
                self.config_manager.save_config()
                
                console.print(f"[bold green]Plugin {name} disabled.[/]")
                console.print("Restart Peer for changes to take effect.")
            except Exception as e:
                console.print(f"[bold red]Error:[/] {str(e)}")
                self.logger.error(f"Error in plugin disable command: {str(e)}")
                
    def _analyze_file(self, session_id: str, file_path: str, verbose: bool) -> None:
        """Analyze a single file."""
        console.print(f"Analyzing {file_path}...")
        
        try:
            # Read file
            with open(file_path, 'r') as f:
                content = f.read()
                
            # Analyze file
            results = self.peer_input_port.analyze_code_snippet(session_id, file_path, content)
            
            # Display results
            if not results:
                console.print(f"[bold green]No issues found in {file_path}[/]")
                return
                
            console.print(f"[bold yellow]Found {len(results)} issues in {file_path}:[/]")
            
            table = Table(show_header=True, header_style="bold")
            table.add_column("Line")
            table.add_column("Col")
            table.add_column("Severity")
            table.add_column("Code")
            table.add_column("Message")
            
            for issue in results:
                table.add_row(
                    str(issue.get("line", 0)),
                    str(issue.get("column", 0)),
                    issue.get("severity", ""),
                    issue.get("code", ""),
                    issue.get("message", "")
                )
                
            console.print(table)
            
            # Show file content with issues if verbose
            if verbose:
                lines = content.splitlines()
                issue_lines = set(issue.get("line", 0) for issue in results)
                
                for i, line in enumerate(lines, 1):
                    if i in issue_lines:
                        console.print(f"[bold red]{i}:[/] {line}")
                    else:
                        console.print(f"{i}: {line}")
        except Exception as e:
            console.print(f"[bold red]Error analyzing {file_path}:[/] {str(e)}")
            
    def _analyze_directory(self, session_id: str, dir_path: str, recursive: bool, verbose: bool) -> None:
        """Analyze a directory."""
        console.print(f"Analyzing directory {dir_path}...")
        
        # Get files to analyze
        files = []
        
        if recursive:
            for root, _, filenames in os.walk(dir_path):
                for filename in filenames:
                    files.append(os.path.join(root, filename))
        else:
            for filename in os.listdir(dir_path):
                file_path = os.path.join(dir_path, filename)
                if os.path.isfile(file_path):
                    files.append(file_path)
                    
        # Filter files by extension
        supported_extensions = [".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".java", ".c", ".cpp", ".h", ".hpp"]
        files = [f for f in files if os.path.splitext(f)[1] in supported_extensions]
        
        if not files:
            console.print("[bold yellow]No supported files found.[/]")
            return
            
        console.print(f"Found {len(files)} files to analyze.")
        
        # Analyze each file
        issues_count = 0
        for file_path in files:
            try:
                # Read file
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                # Analyze file
                results = self.peer_input_port.analyze_code_snippet(session_id, file_path, content)
                
                if results:
                    issues_count += len(results)
                    rel_path = os.path.relpath(file_path, dir_path)
                    console.print(f"[bold yellow]{rel_path}:[/] {len(results)} issues")
                    
                    if verbose:
                        table = Table(show_header=True, header_style="bold")
                        table.add_column("Line")
                        table.add_column("Severity")
                        table.add_column("Message")
                        
                        for issue in results:
                            table.add_row(
                                str(issue.get("line", 0)),
                                issue.get("severity", ""),
                                issue.get("message", "")
                            )
                            
                        console.print(table)
            except Exception as e:
                console.print(f"[bold red]Error analyzing {file_path}:[/] {str(e)}")
                
        console.print(f"[bold green]Analysis complete.[/] Found {issues_count} issues in {len(files)} files.")
        
    def _ensure_session(self) -> str:
        """Ensure a session exists and return its ID."""
        session_id = self._get_current_session()
        
        if not session_id:
            # Create new session
            console.print("[bold yellow]No active session.[/] Creating new session...")
            
            project_root = os.getcwd()
            session_data = self.peer_input_port.initialize_session(project_root)
            
            if not session_data:
                console.print("[bold red]Error:[/] Failed to initialize session")
                sys.exit(1)
                
            session_id = session_data.get("id")
            self.current_session_id = session_id
            
            console.print(f"[bold green]Session initialized:[/] {session_id}")
            
        return session_id
        
    def _get_current_session(self) -> Optional[str]:
        """Get the current session ID."""
        return self.current_session_id
        
    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate type."""
        # Try to convert to int
        try:
            return int(value)
        except ValueError:
            pass
            
        # Try to convert to float
        try:
            return float(value)
        except ValueError:
            pass
            
        # Try to convert to bool
        if value.lower() in ["true", "yes", "1"]:
            return True
        if value.lower() in ["false", "no", "0"]:
            return False
            
        # Return as string
        return value
        
    def run(self) -> None:
        """Run the CLI interface."""
        app()
```

## Interface Utilisateur Textuelle (TUI)

Cette interface utilise Textual pour fournir une interface utilisateur textuelle riche et interactive.

```python
# src/peer/interfaces/tui/app.py

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Input, Button, Tree, DataTable, Markdown, Log
from textual.binding import Binding
from textual.reactive import reactive
from textual import events
from textual.message import Message
from textual.css.query import NoMatches

import os
import sys
import time
from typing import Dict, List, Any, Optional
import asyncio
import uuid

from peer.domain.ports.input_ports import PeerInputPort

class PeerTUI(App):
    """Textual UI for Peer."""
    
    TITLE = "Peer - AI Assistant for Development"
    SUB_TITLE = "Omniscient Development Assistant"
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    #sidebar {
        width: 25%;
        background: $panel;
        border-right: solid $primary;
    }
    
    #main {
        width: 75%;
    }
    
    #input-container {
        height: 3;
        margin: 1 0;
        background: $surface;
    }
    
    #status-bar {
        height: 1;
        background: $primary;
        color: $text;
    }
    
    #file-tree {
        height: 100%;
        overflow: auto;
    }
    
    #output-container {
        height: 1fr;
        overflow: auto;
    }
    
    #log-container {
        height: 30%;
        border-top: solid $primary;
    }
    
    Input {
        padding: 0 1;
        background: $surface-darken-1;
        color: $text;
        border: solid $primary;
    }
    
    Button {
        margin: 0 1;
    }
    
    .mode-indicator {
        background: $primary;
        color: $text;
        padding: 0 1;
        text-align: center;
    }
    
    .file-info {
        background: $panel;
        padding: 1;
        border-bottom: solid $primary;
    }
    
    .issue {
        color: $error;
    }
    
    .suggestion {
        color: $success;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+s", "save", "Save"),
        Binding("f5", "refresh", "Refresh"),
        Binding("f1", "help", "Help"),
    ]
    
    current_mode = reactive("developer")
    current_file = reactive("")
    current_session_id = reactive("")
    
    def __init__(self, peer_input_port: PeerInputPort, config_manager, logger):
        super().__init__()
        self.peer_input_port = peer_input_port
        self.config_manager = config_manager
        self.logger = logger
        self.project_root = os.getcwd()
        self.file_contents = {}
        self.analysis_results = {}
        
    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        yield Header()
        
        with Horizontal():
            with Container(id="sidebar"):
                yield Static(f"Mode: {self.current_mode}", classes="mode-indicator")
                yield Tree(id="file-tree", label="Project Files")
                
            with Vertical(id="main"):
                with Container(classes="file-info"):
                    yield Static(id="file-path", markup=True)
                    
                with Container(id="output-container"):
                    yield Markdown(id="file-content")
                    
                with Horizontal(id="input-container"):
                    yield Input(placeholder="Enter a command or question...", id="command-input")
                    yield Button("Send", id="send-button")
                    
                with Container(id="log-container"):
                    yield Log(id="log", highlight=True, markup=True)
                    
                with Container(id="status-bar"):
                    yield Static(id="status", markup=True)
                    
        yield Footer()
        
    def on_mount(self) -> None:
        """Event handler called when the app is mounted."""
        self.initialize_session()
        self.populate_file_tree()
        self.update_status_bar()
        
    def initialize_session(self) -> None:
        """Initialize a Peer session."""
        try:
            # Initialize session
            session_data = self.peer_input_port.initialize_session(self.project_root)
            
            if not session_data:
                self.log("Failed to initialize session", level="error")
                return
                
            session_id = session_data.get("id")
            self.current_session_id = session_id
            
            # Set mode from config
            config = self.config_manager.get_config("core")
            self.current_mode = config.get("default_mode", "developer")
            
            self.log(f"Session initialized: {session_id}", level="info")
            self.log(f"Project root: {self.project_root}", level="info")
            self.log(f"Mode: {self.current_mode}", level="info")
        except Exception as e:
            self.log(f"Error initializing session: {str(e)}", level="error")
            
    def populate_file_tree(self) -> None:
        """Populate the file tree with project files."""
        try:
            tree = self.query_one("#file-tree", Tree)
            tree.root.expand()
            
            # Clear existing nodes
            tree.root.remove_children()
            
            # Add project files
            self._add_directory_to_tree(tree.root, self.project_root)
            
            self.log("File tree populated", level="info")
        except Exception as e:
            self.log(f"Error populating file tree: {str(e)}", level="error")
            
    def _add_directory_to_tree(self, parent, directory) -> None:
        """Add a directory and its contents to the file tree."""
        try:
            # Skip hidden directories
            if os.path.basename(directory).startswith("."):
                return
                
            # Skip common directories to ignore
            ignore_dirs = ["node_modules", "__pycache__", "venv", ".git", ".idea", ".vscode"]
            if os.path.basename(directory) in ignore_dirs:
                return
                
            # Get directory contents
            items = os.listdir(directory)
            
            # Sort items (directories first, then files)
            dirs = [item for item in items if os.path.isdir(os.path.join(directory, item)) and not item.startswith(".")]
            files = [item for item in items if os.path.isfile(os.path.join(directory, item)) and not item.startswith(".")]
            
            dirs.sort()
            files.sort()
            
            # Add directories
            for dir_name in dirs:
                dir_path = os.path.join(directory, dir_name)
                dir_node = parent.add(dir_name, data={"path": dir_path, "type": "directory"})
                self._add_directory_to_tree(dir_node, dir_path)
                
            # Add files
            for file_name in files:
                file_path = os.path.join(directory, file_name)
                parent.add(file_name, data={"path": file_path, "type": "file"})
        except Exception as e:
            self.log(f"Error adding directory to tree: {str(e)}", level="error")
            
    def update_status_bar(self) -> None:
        """Update the status bar."""
        try:
            status = self.query_one("#status", Static)
            status.update(f"Session: {self.current_session_id} | Mode: {self.current_mode} | File: {self.current_file or 'None'}")
        except Exception as e:
            self.log(f"Error updating status bar: {str(e)}", level="error")
            
    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Event handler called when a tree node is selected."""
        node = event.node
        data = node.data
        
        if not data:
            return
            
        path = data.get("path", "")
        type = data.get("type", "")
        
        if type == "file":
            self.open_file(path)
            
    def open_file(self, path: str) -> None:
        """Open a file and display its content."""
        try:
            # Update current file
            self.current_file = path
            
            # Update file path display
            file_path = self.query_one("#file-path", Static)
            rel_path = os.path.relpath(path, self.project_root)
            file_path.update(f"File: [bold]{rel_path}[/bold]")
            
            # Read file content
            with open(path, 'r') as f:
                content = f.read()
                
            # Store content
            self.file_contents[path] = content
            
            # Display content
            file_content = self.query_one("#file-content", Markdown)
            
            # Determine language for syntax highlighting
            ext = os.path.splitext(path)[1].lower()
            language = self._get_language_for_extension(ext)
            
            # Format content as markdown code block
            formatted_content = f"```{language}\n{content}\n```"
            file_content.update(formatted_content)
            
            # Analyze file
            self.analyze_file(path, content)
            
            self.update_status_bar()
        except Exception as e:
            self.log(f"Error opening file: {str(e)}", level="error")
            
    def analyze_file(self, path: str, content: str) -> None:
        """Analyze a file and display results."""
        try:
            # Skip analysis for large files
            if len(content) > 100000:  # ~100KB
                self.log(f"File too large for analysis: {path}", level="warning")
                return
                
            # Analyze file
            results = self.peer_input_port.analyze_code_snippet(self.current_session_id, path, content)
            
            # Store results
            self.analysis_results[path] = results
            
            # Display results
            if not results:
                self.log(f"No issues found in {os.path.basename(path)}", level="info")
                return
                
            self.log(f"Found {len(results)} issues in {os.path.basename(path)}", level="warning")
            
            for issue in results:
                line = issue.get("line", 0)
                message = issue.get("message", "")
                code = issue.get("code", "")
                severity = issue.get("severity", "")
                
                self.log(f"L{line}: [{severity}] {code} - {message}", level=severity, highlight=True)
        except Exception as e:
            self.log(f"Error analyzing file: {str(e)}", level="error")
            
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""
        button_id = event.button.id
        
        if button_id == "send-button":
            self.send_command()
            
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Event handler called when input is submitted."""
        self.send_command()
        
    def send_command(self) -> None:
        """Send the command from the input field."""
        try:
            # Get command
            input = self.query_one("#command-input", Input)
            command = input.value.strip()
            
            if not command:
                return
                
            # Log command
            self.log(f"> {command}", level="command")
            
            # Clear input
            input.value = ""
            
            # Process command
            self.process_command(command)
        except Exception as e:
            self.log(f"Error sending command: {str(e)}", level="error")
            
    def process_command(self, command: str) -> None:
        """Process a command."""
        try:
            # Check for built-in commands
            if command.startswith("/"):
                self.process_builtin_command(command[1:])
                return
                
            # Send command to Peer
            result = self.peer_input_port.execute_command(
                self.current_session_id,
                "query",
                [command]
            )
            
            # Display result
            if isinstance(result, str):
                self.log(result, level="response")
            else:
                self.log(str(result), level="response")
        except Exception as e:
            self.log(f"Error processing command: {str(e)}", level="error")
            
    def process_builtin_command(self, command: str) -> None:
        """Process a built-in command."""
        parts = command.split()
        cmd = parts[0].lower()
        args = parts[1:]
        
        if cmd == "mode":
            # Change mode
            if args:
                self.change_mode(args[0])
            else:
                self.log(f"Current mode: {self.current_mode}", level="info")
        elif cmd == "refresh":
            # Refresh file tree
            self.populate_file_tree()
            self.log("File tree refreshed", level="info")
        elif cmd == "analyze":
            # Analyze current file
            if self.current_file:
                content = self.file_contents.get(self.current_file, "")
                self.analyze_file(self.current_file, content)
            else:
                self.log("No file selected", level="warning")
        elif cmd == "suggest":
            # Suggest improvements for current file
            if self.current_file:
                self.suggest_improvements()
            else:
                self.log("No file selected", level="warning")
        elif cmd == "help":
            # Show help
            self.show_help()
        else:
            self.log(f"Unknown command: {cmd}", level="error")
            
    def change_mode(self, mode: str) -> None:
        """Change the current mode."""
        try:
            # Validate mode
            valid_modes = ["developer", "architect", "reviewer", "tester"]
            
            if mode.lower() not in valid_modes:
                self.log(f"Invalid mode: {mode}. Valid modes: {', '.join(valid_modes)}", level="error")
                return
                
            # Update mode
            self.current_mode = mode.lower()
            
            # Update mode indicator
            try:
                mode_indicator = self.query_one(".mode-indicator", Static)
                mode_indicator.update(f"Mode: {self.current_mode}")
            except NoMatches:
                pass
                
            # Update configuration
            self.peer_input_port.update_configuration(self.current_session_id, "core", "current_mode", self.current_mode)
            
            self.log(f"Mode changed to: {self.current_mode}", level="info")
            self.update_status_bar()
        except Exception as e:
            self.log(f"Error changing mode: {str(e)}", level="error")
            
    def suggest_improvements(self) -> None:
        """Suggest improvements for the current file."""
        try:
            if not self.current_file:
                self.log("No file selected", level="warning")
                return
                
            content = self.file_contents.get(self.current_file, "")
            
            if not content:
                self.log("No content to analyze", level="warning")
                return
                
            # Get suggestions
            suggestions = self.peer_input_port.suggest_improvements(self.current_session_id, self.current_file, content)
            
            # Display suggestions
            if not suggestions:
                self.log("No suggestions found", level="info")
                return
                
            self.log(f"Found {len(suggestions)} suggestions:", level="info")
            
            for suggestion in suggestions:
                line_start = suggestion.get("line_start", 0)
                line_end = suggestion.get("line_end", line_start)
                suggestion_type = suggestion.get("suggestion_type", "")
                description = suggestion.get("description", "")
                
                self.log(f"L{line_start}-{line_end}: [{suggestion_type}] {description}", level="suggestion", highlight=True)
        except Exception as e:
            self.log(f"Error suggesting improvements: {str(e)}", level="error")
            
    def show_help(self) -> None:
        """Show help information."""
        help_text = """
        # Peer TUI Help
        
        ## Built-in Commands
        - `/mode <mode>` - Change mode (developer, architect, reviewer, tester)
        - `/refresh` - Refresh file tree
        - `/analyze` - Analyze current file
        - `/suggest` - Suggest improvements for current file
        - `/help` - Show this help
        
        ## Keyboard Shortcuts
        - `Q` - Quit
        - `Ctrl+S` - Save
        - `F5` - Refresh
        - `F1` - Help
        
        ## Modes
        - `developer` - Focus on writing code
        - `architect` - Focus on architecture and design
        - `reviewer` - Focus on code review
        - `tester` - Focus on testing
        """
        
        self.log(help_text, level="info")
        
    def log(self, message: str, level: str = "info", highlight: bool = False) -> None:
        """Add a message to the log."""
        try:
            log = self.query_one("#log", Log)
            
            # Format message based on level
            if level == "error":
                formatted_message = f"[red]{message}[/red]"
            elif level == "warning":
                formatted_message = f"[yellow]{message}[/yellow]"
            elif level == "info":
                formatted_message = f"[blue]{message}[/blue]"
            elif level == "success":
                formatted_message = f"[green]{message}[/green]"
            elif level == "command":
                formatted_message = f"[bold cyan]{message}[/bold cyan]"
            elif level == "response":
                formatted_message = f"[bold white]{message}[/bold white]"
            elif level == "suggestion":
                formatted_message = f"[green]{message}[/green]"
            else:
                formatted_message = message
                
            log.write(formatted_message, highlight=highlight)
        except Exception as e:
            print(f"Error logging message: {str(e)}")
            
    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()
        
    def action_save(self) -> None:
        """Save the current file."""
        if not self.current_file:
            self.log("No file selected", level="warning")
            return
            
        # TODO: Implement file saving
        self.log("Save functionality not implemented yet", level="warning")
        
    def action_refresh(self) -> None:
        """Refresh the file tree."""
        self.populate_file_tree()
        self.log("File tree refreshed", level="info")
        
    def action_help(self) -> None:
        """Show help."""
        self.show_help()
        
    def _get_language_for_extension(self, ext: str) -> str:
        """Get the language name for a file extension."""
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
            ".cc": "cpp",
            ".md": "markdown",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".html": "html",
            ".css": "css",
            ".scss": "scss",
            ".sql": "sql",
            ".sh": "bash",
            ".bat": "batch",
            ".ps1": "powershell",
            ".xml": "xml",
            ".toml": "toml",
            ".ini": "ini",
            ".conf": "conf"
        }
        
        return extension_map.get(ext, "")
```

## Interface API REST

Cette interface utilise FastAPI pour fournir une API REST moderne et documentée.

```python
# src/peer/interfaces/api/routes.py

from fastapi import FastAPI, HTTPException, Depends, Body, Query, Path, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
import os
import uuid
from datetime import datetime

from peer.domain.ports.input_ports import PeerInputPort

# Define models
class SessionRequest(BaseModel):
    project_root: str = Field(..., description="Root directory of the project")
    mode: str = Field("developer", description="Initial mode (developer, architect, reviewer, tester)")

class SessionResponse(BaseModel):
    id: str = Field(..., description="Session ID")
    project_root: str = Field(..., description="Root directory of the project")
    start_time: str = Field(..., description="Session start time")
    current_mode: str = Field(..., description="Current mode")

class CodeAnalysisRequest(BaseModel):
    file_path: str = Field(..., description="Path to the file to analyze")
    content: str = Field(..., description="Content of the file")

class CodeAnalysisIssue(BaseModel):
    line: int = Field(..., description="Line number")
    column: int = Field(..., description="Column number")
    code: str = Field(..., description="Issue code")
    message: str = Field(..., description="Issue message")
    severity: str = Field(..., description="Issue severity")

class CodeSuggestion(BaseModel):
    line_start: int = Field(..., description="Start line number")
    line_end: int = Field(..., description="End line number")
    suggestion_type: str = Field(..., description="Type of suggestion")
    description: str = Field(..., description="Suggestion description")
    suggested_code: Optional[str] = Field(None, description="Suggested code")
    confidence: Optional[float] = Field(None, description="Confidence level")

class CommandRequest(BaseModel):
    command: str = Field(..., description="Command to execute")
    args: List[str] = Field([], description="Command arguments")

class ConfigUpdateRequest(BaseModel):
    section: str = Field(..., description="Configuration section")
    key: str = Field(..., description="Configuration key")
    value: Any = Field(..., description="Configuration value")

class APIInterface:
    """API interface for Peer."""
    
    def __init__(self, peer_input_port: PeerInputPort, config_manager, logger):
        self.peer_input_port = peer_input_port
        self.config_manager = config_manager
        self.logger = logger
        self.app = FastAPI(
            title="Peer API",
            description="API for Peer - AI Assistant for Development",
            version="0.1.0"
        )
        
    def initialize(self) -> None:
        """Initialize the API interface."""
        # Configure CORS
        config = self.config_manager.get_config("api")
        origins = config.get("cors_origins", ["*"])
        
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Register routes
        self._register_routes()
        
        self.logger.info("API interface initialized")
        
    def _register_routes(self) -> None:
        """Register API routes."""
        app = self.app
        
        # Session routes
        @app.post("/sessions", response_model=SessionResponse, tags=["Sessions"])
        async def create_session(request: SessionRequest):
            """Create a new session."""
            try:
                # Validate project root
                if not os.path.isdir(request.project_root):
                    raise HTTPException(status_code=400, detail="Project root not found")
                    
                # Initialize session
                session_data = self.peer_input_port.initialize_session(request.project_root)
                
                if not session_data:
                    raise HTTPException(status_code=500, detail="Failed to initialize session")
                    
                session_id = session_data.get("id")
                
                # Set mode
                self.peer_input_port.update_configuration(session_id, "core", "current_mode", request.mode)
                
                # Get updated session
                session_status = self.peer_input_port.get_session_status(session_id)
                
                return {
                    "id": session_id,
                    "project_root": session_status.get("project_root", request.project_root),
                    "start_time": session_status.get("start_time", datetime.now().isoformat()),
                    "current_mode": session_status.get("current_mode", request.mode)
                }
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Error creating session: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @app.get("/sessions/{session_id}", response_model=Dict[str, Any], tags=["Sessions"])
        async def get_session(session_id: str):
            """Get session status."""
            try:
                # Get session status
                session_status = self.peer_input_port.get_session_status(session_id)
                
                if not session_status:
                    raise HTTPException(status_code=404, detail="Session not found")
                    
                return session_status
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Error getting session: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
                
        # Code analysis routes
        @app.post("/sessions/{session_id}/analyze", response_model=List[CodeAnalysisIssue], tags=["Code Analysis"])
        async def analyze_code(session_id: str, request: CodeAnalysisRequest):
            """Analyze code for issues."""
            try:
                # Analyze code
                results = self.peer_input_port.analyze_code_snippet(session_id, request.file_path, request.content)
                
                if not results:
                    return []
                    
                return results
            except Exception as e:
                self.logger.error(f"Error analyzing code: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @app.post("/sessions/{session_id}/suggest", response_model=List[CodeSuggestion], tags=["Code Analysis"])
        async def suggest_improvements(session_id: str, request: CodeAnalysisRequest):
            """Suggest improvements for code."""
            try:
                # Get suggestions
                suggestions = self.peer_input_port.suggest_improvements(session_id, request.file_path, request.content)
                
                if not suggestions:
                    return []
                    
                return suggestions
            except Exception as e:
                self.logger.error(f"Error suggesting improvements: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
                
        # Command routes
        @app.post("/sessions/{session_id}/commands", response_model=Any, tags=["Commands"])
        async def execute_command(session_id: str, request: CommandRequest):
            """Execute a command."""
            try:
                # Execute command
                result = self.peer_input_port.execute_command(session_id, request.command, request.args)
                
                return {"result": result}
            except Exception as e:
                self.logger.error(f"Error executing command: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
                
        # Configuration routes
        @app.get("/sessions/{session_id}/config", response_model=Dict[str, Any], tags=["Configuration"])
        async def get_config(session_id: str, section: Optional[str] = None):
            """Get configuration."""
            try:
                # Get configuration
                config = self.peer_input_port.get_configuration(session_id, section)
                
                return config
            except Exception as e:
                self.logger.error(f"Error getting configuration: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @app.put("/sessions/{session_id}/config", response_model=Dict[str, Any], tags=["Configuration"])
        async def update_config(session_id: str, request: ConfigUpdateRequest):
            """Update configuration."""
            try:
                # Update configuration
                self.peer_input_port.update_configuration(session_id, request.section, request.key, request.value)
                
                # Get updated configuration
                config = self.peer_input_port.get_configuration(session_id, request.section)
                
                return config
            except Exception as e:
                self.logger.error(f"Error updating configuration: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
                
        # File change routes
        @app.post("/sessions/{session_id}/file-changes", tags=["File Changes"])
        async def handle_file_change(
            session_id: str,
            file_path: str = Body(..., embed=True),
            content: Optional[str] = Body(None, embed=True)
        ):
            """Handle a file change event."""
            try:
                # Handle file change
                self.peer_input_port.handle_file_change(session_id, file_path, content)
                
                return {"status": "ok"}
            except Exception as e:
                self.logger.error(f"Error handling file change: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
                
        # VCS change routes
        @app.post("/sessions/{session_id}/vcs-changes", tags=["VCS Changes"])
        async def handle_vcs_change(
            session_id: str,
            changed_files: List[Dict[str, Any]] = Body(..., embed=True)
        ):
            """Handle a VCS change event."""
            try:
                # Handle VCS change
                self.peer_input_port.handle_vcs_change(session_id, changed_files)
                
                return {"status": "ok"}
            except Exception as e:
                self.logger.error(f"Error handling VCS change: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
                
        # Feedback routes
        @app.post("/sessions/{session_id}/feedback", tags=["Feedback"])
        async def provide_feedback(
            session_id: str,
            feedback_type: str = Body(..., embed=True),
            details: Dict[str, Any] = Body(..., embed=True)
        ):
            """Provide feedback to the Peer assistant."""
            try:
                # Provide feedback
                self.peer_input_port.provide_feedback(session_id, feedback_type, details)
                
                return {"status": "ok"}
            except Exception as e:
                self.logger.error(f"Error providing feedback: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
                
    def get_app(self) -> FastAPI:
        """Get the FastAPI application."""
        return self.app
```

## Implémentation de l'Application Principale

Cette implémentation connecte toutes les interfaces et les adaptateurs à la couche Domaine.

```python
# src/peer/__init__.py

import os
import sys
import argparse
from typing import Dict, List, Any, Optional

from peer.application.config.config_manager import ConfigManager
from peer.infrastructure.services.logging_service import LoggingService
from peer.application.event.event_bus import EventBus
from peer.application.services.core_service import CoreService
from peer.application.plugins.plugin_manager import PluginManager

# Import domain services
from peer.domain.services.workflow_service import WorkflowService
from peer.domain.services.code_analysis_service import CodeAnalysisService
from peer.domain.services.session_management_service import SessionManagementService
from peer.domain.services.context_detection_service import ContextDetectionService
from peer.domain.services.peer_assistant_service import PeerAssistantService

# Import adapters
from peer.infrastructure.adapters.llm.ollama_adapter import OllamaAdapter
from peer.infrastructure.adapters.tts.piper_adapter import PiperAdapter
from peer.infrastructure.adapters.code_analysis.tree_sitter_adapter import TreeSitterAdapter
from peer.infrastructure.adapters.persistence.sqlite_adapter import SQLiteAdapter
from peer.infrastructure.adapters.file_system.file_system_adapter import FileSystemAdapter
from peer.infrastructure.adapters.vcs.git_adapter import GitAdapter

# Import interfaces
from peer.interfaces.cli.commands import CLIInterface
from peer.interfaces.tui.app import PeerTUI
from peer.interfaces.api.routes import APIInterface

# Import application layer
from peer.application.peer_application import PeerApplication

def main():
    """Main entry point for Peer."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Peer - AI Assistant for Development")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--tui", action="store_true", help="Start the TUI interface")
    parser.add_argument("--api", action="store_true", help="Start the API interface")
    
    # Add subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Parse arguments
    args, unknown = parser.parse_known_args()
    
    # Initialize core components
    config_manager = ConfigManager()
    config_manager.initialize()
    
    # Load configuration from file if specified
    if args.config:
        config_manager.load_config(args.config)
        
    # Initialize logging service
    logging_service = LoggingService()
    logging_service.initialize(config_manager.get_config("logging"))
    logger = logging_service.get_logger("peer")
    
    # Initialize event bus
    event_bus = EventBus()
    
    # Initialize core service
    core_service = CoreService(config_manager, logger, event_bus)
    core_service.initialize()
    
    # Register core services
    core_service.register_service("config_manager", config_manager)
    core_service.register_service("logging_service", logging_service)
    core_service.register_service("event_bus", event_bus)
    
    # Initialize infrastructure adapters
    llm_adapter = OllamaAdapter(config_manager, logger)
    llm_adapter.initialize()
    
    tts_adapter = PiperAdapter(config_manager, logger)
    tts_adapter.initialize()
    
    code_analysis_adapter = TreeSitterAdapter(config_manager, logger)
    code_analysis_adapter.initialize()
    
    persistence_adapter = SQLiteAdapter(config_manager, logger)
    persistence_adapter.initialize()
    
    file_system_adapter = FileSystemAdapter(logger)
    
    vcs_adapter = GitAdapter(config_manager, logger)
    vcs_adapter.initialize()
    
    # Register adapters
    core_service.register_service("llm_adapter", llm_adapter)
    core_service.register_service("tts_adapter", tts_adapter)
    core_service.register_service("code_analysis_adapter", code_analysis_adapter)
    core_service.register_service("persistence_adapter", persistence_adapter)
    core_service.register_service("file_system_adapter", file_system_adapter)
    core_service.register_service("vcs_adapter", vcs_adapter)
    
    # Initialize domain services
    code_analysis_service = CodeAnalysisService(code_analysis_adapter, persistence_adapter, logger)
    session_management_service = SessionManagementService(persistence_adapter, logger)
    context_detection_service = ContextDetectionService(logger)
    workflow_service = WorkflowService(llm_adapter, None, logger)  # UI adapter will be set later
    peer_assistant_service = PeerAssistantService(llm_adapter, tts_adapter, code_analysis_service, None, vcs_adapter, logger)  # UI adapter will be set later
    
    # Register domain services
    core_service.register_service("code_analysis_service", code_analysis_service)
    core_service.register_service("session_management_service", session_management_service)
    core_service.register_service("context_detection_service", context_detection_service)
    core_service.register_service("workflow_service", workflow_service)
    core_service.register_service("peer_assistant_service", peer_assistant_service)
    
    # Initialize plugin manager
    plugin_manager = PluginManager(config_manager, logger)
    plugin_manager.initialize()
    core_service.register_service("plugin_manager", plugin_manager)
    
    # Initialize application layer
    peer_application = PeerApplication(
        config_manager,
        logger,
        event_bus,
        session_management_service,
        code_analysis_service,
        workflow_service,
        peer_assistant_service,
        context_detection_service
    )
    core_service.register_service("peer_application", peer_application)
    
    # Initialize interfaces
    cli_interface = CLIInterface(peer_application, config_manager, logger)
    cli_interface.initialize()
    
    # Set UI adapter for domain services
    workflow_service.ui_port = cli_interface  # Temporary, will be replaced based on active interface
    peer_assistant_service.ui_port = cli_interface  # Temporary, will be replaced based on active interface
    
    # Start the appropriate interface
    if args.tui:
        # Start TUI
        tui_interface = PeerTUI(peer_application, config_manager, logger)
        workflow_service.ui_port = tui_interface
        peer_assistant_service.ui_port = tui_interface
        tui_interface.run()
    elif args.api:
        # Start API
        import uvicorn
        api_interface = APIInterface(peer_application, config_manager, logger)
        api_interface.initialize()
        
        api_config = config_manager.get_config("api")
        host = api_config.get("host", "0.0.0.0")
        port = api_config.get("port", 8000)
        
        logger.info(f"Starting API server on {host}:{port}")
        uvicorn.run(api_interface.get_app(), host=host, port=port)
    else:
        # Use CLI by default
        if args.command:
            # Execute command
            result = cli_interface.execute_command(args.command, unknown)
            if result:
                print(result)
        else:
            # Show help
            parser.print_help()
    
    # Shutdown core service
    core_service.shutdown()

if __name__ == "__main__":
    main()
```

## Application Layer

Cette couche fait le lien entre les interfaces utilisateur et la couche Domaine.

```python
# src/peer/application/peer_application.py

from typing import Dict, List, Any, Optional
import uuid
from datetime import datetime

from peer.domain.ports.input_ports import PeerInputPort

class PeerApplication(PeerInputPort):
    """Application layer for Peer."""
    
    def __init__(self, config_manager, logger, event_bus, 
                 session_service, code_analysis_service, 
                 workflow_service, peer_assistant_service,
                 context_detection_service):
        self.config_manager = config_manager
        self.logger = logger
        self.event_bus = event_bus
        self.session_service = session_service
        self.code_analysis_service = code_analysis_service
        self.workflow_service = workflow_service
        self.peer_assistant_service = peer_assistant_service
        self.context_detection_service = context_detection_service
        
    def initialize_session(self, project_root: str) -> Dict[str, Any]:
        """Initialize a new Peer session for a project."""
        try:
            # Get configuration
            config = self.config_manager.get_config("core")
            initial_mode = config.get("default_mode", "developer")
            
            # Create session
            session = self.session_service.create_session(project_root, initial_mode)
            
            # Return session data
            return session.__dict__
        except Exception as e:
            self.logger.error(f"Error initializing session: {str(e)}")
            return None
            
    def execute_command(self, session_id: str, command: str, args: List[str]) -> Any:
        """Execute a specific command within a session."""
        try:
            # Get session
            session = self.session_service.get_session(session_id)
            
            if not session:
                self.logger.error(f"Session not found: {session_id}")
                return None
                
            # Detect mode based on command and context
            detected_mode = self.context_detection_service.detect_mode(session.context, command)
            
            if detected_mode != session.current_mode:
                self.logger.info(f"Switching mode from {session.current_mode} to {detected_mode} based on command")
                session.current_mode = detected_mode
                self.session_service.update_session_context(session_id, {"current_mode": detected_mode})
                
            # Add command to history
            self.session_service.add_history_event(session_id, {
                "type": "command",
                "data": {
                    "command": command,
                    "args": args
                },
                "timestamp": datetime.now().isoformat()
            })
            
            # Execute command
            if command == "query":
                # Natural language query
                query = " ".join(args) if args else ""
                return self._handle_query(session, query)
            elif command == "explain":
                # Explain code
                return self._handle_explain(session, args)
            else:
                # Try to handle with plugins
                plugin_manager = self.config_manager.get_service("plugin_manager")
                if plugin_manager:
                    result = plugin_manager.call_hook("peer_handle_command", command, args)
                    if result:
                        return result
                        
                self.logger.warn(f"Unknown command: {command}")
                return f"Unknown command: {command}"
        except Exception as e:
            self.logger.error(f"Error executing command: {str(e)}")
            return f"Error: {str(e)}"
            
    def analyze_code_snippet(self, session_id: str, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Analyze a given code snippet."""
        try:
            # Get session
            session = self.session_service.get_session(session_id)
            
            if not session:
                self.logger.error(f"Session not found: {session_id}")
                return []
                
            # Analyze code
            code_context = self.code_analysis_service.analyze_file(file_path, content)
            
            # Add to session
            self.session_service.add_file_context(session_id, file_path, code_context)
            
            # Return issues
            return [issue.__dict__ for issue in code_context.issues]
        except Exception as e:
            self.logger.error(f"Error analyzing code: {str(e)}")
            return []
            
    def suggest_improvements(self, session_id: str, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Suggest improvements for a given code snippet."""
        try:
            # Get session
            session = self.session_service.get_session(session_id)
            
            if not session:
                self.logger.error(f"Session not found: {session_id}")
                return []
                
            # Analyze code first
            code_context = self.code_analysis_service.analyze_file(file_path, content)
            
            # Add to session
            self.session_service.add_file_context(session_id, file_path, code_context)
            
            # Generate suggestions
            suggestions = self.peer_assistant_service._generate_suggestions(session, file_path, code_context)
            
            # Return suggestions
            return [suggestion.__dict__ for suggestion in suggestions]
        except Exception as e:
            self.logger.error(f"Error suggesting improvements: {str(e)}")
            return []
            
    def handle_file_change(self, session_id: str, file_path: str, content: Optional[str] = None) -> None:
        """Handle a file change event (create, update, delete)."""
        try:
            # Get session
            session = self.session_service.get_session(session_id)
            
            if not session:
                self.logger.error(f"Session not found: {session_id}")
                return
                
            # Add event to history
            self.session_service.add_history_event(session_id, {
                "type": "file_change",
                "data": {
                    "file_path": file_path,
                    "action": "delete" if content is None else "update"
                },
                "timestamp": datetime.now().isoformat()
            })
            
            # If content is None, file was deleted
            if content is None:
                # Remove from file contexts
                if file_path in session.file_contexts:
                    del session.file_contexts[file_path]
                    self.session_service.update_session_context(session_id, {"file_contexts": session.file_contexts})
                return
                
            # Analyze file
            code_context = self.code_analysis_service.analyze_file(file_path, content)
            
            # Add to session
            self.session_service.add_file_context(session_id, file_path, code_context)
            
            # Provide proactive assistance
            self.peer_assistant_service.provide_proactive_assistance(session)
        except Exception as e:
            self.logger.error(f"Error handling file change: {str(e)}")
            
    def handle_vcs_change(self, session_id: str, changed_files: List[Dict[str, Any]]) -> None:
        """Handle a version control system change event."""
        try:
            # Get session
            session = self.session_service.get_session(session_id)
            
            if not session:
                self.logger.error(f"Session not found: {session_id}")
                return
                
            # Add event to history
            self.session_service.add_history_event(session_id, {
                "type": "vcs_change",
                "data": {
                    "changed_files": changed_files
                },
                "timestamp": datetime.now().isoformat()
            })
            
            # TODO: Implement VCS change handling
        except Exception as e:
            self.logger.error(f"Error handling VCS change: {str(e)}")
            
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get the current status of a session."""
        try:
            # Get session
            session = self.session_service.get_session(session_id)
            
            if not session:
                self.logger.error(f"Session not found: {session_id}")
                return None
                
            # Convert to dict
            session_dict = session.__dict__.copy()
            
            # Convert file contexts to dict
            file_contexts = {}
            for file_path, context in session.file_contexts.items():
                if context:
                    file_contexts[file_path] = context.__dict__
                    
            session_dict["file_contexts"] = file_contexts
            
            return session_dict
        except Exception as e:
            self.logger.error(f"Error getting session status: {str(e)}")
            return None
            
    def provide_feedback(self, session_id: str, feedback_type: str, details: Dict[str, Any]) -> None:
        """Provide feedback to the Peer assistant."""
        try:
            # Get session
            session = self.session_service.get_session(session_id)
            
            if not session:
                self.logger.error(f"Session not found: {session_id}")
                return
                
            # Add feedback to history
            self.session_service.add_history_event(session_id, {
                "type": "feedback",
                "data": {
                    "feedback_type": feedback_type,
                    "details": details
                },
                "timestamp": datetime.now().isoformat()
            })
            
            # TODO: Use feedback to improve suggestions
        except Exception as e:
            self.logger.error(f"Error providing feedback: {str(e)}")
            
    def get_configuration(self, session_id: str, section: Optional[str] = None) -> Dict[str, Any]:
        """Get the current configuration for the session."""
        try:
            # Get session
            session = self.session_service.get_session(session_id)
            
            if not session:
                self.logger.error(f"Session not found: {session_id}")
                return {}
                
            # Get configuration
            if section:
                return self.config_manager.get_config(section)
            else:
                # Get all sections
                config = {}
                for section_name in self.config_manager.get_sections():
                    config[section_name] = self.config_manager.get_config(section_name)
                return config
        except Exception as e:
            self.logger.error(f"Error getting configuration: {str(e)}")
            return {}
            
    def update_configuration(self, session_id: str, section: str, key: str, value: Any) -> None:
        """Update the configuration for the session."""
        try:
            # Get session
            session = self.session_service.get_session(session_id)
            
            if not session:
                self.logger.error(f"Session not found: {session_id}")
                return
                
            # Update configuration
            self.config_manager.set_config(section, key, value)
            
            # Save configuration
            self.config_manager.save_config()
            
            # Update session context if needed
            if section == "core" and key == "current_mode":
                session.current_mode = value
                self.session_service.update_session_context(session_id, {"current_mode": value})
        except Exception as e:
            self.logger.error(f"Error updating configuration: {str(e)}")
            
    def _handle_query(self, session, query: str) -> str:
        """Handle a natural language query."""
        try:
            # Execute task
            results = self.workflow_service.execute_task(query, session.context)
            
            if not results:
                return "I couldn't find an answer to your query."
                
            # Return results
            if isinstance(results, list):
                return "\n\n".join(results)
            else:
                return str(results)
        except Exception as e:
            self.logger.error(f"Error handling query: {str(e)}")
            return f"Error: {str(e)}"
            
    def _handle_explain(self, session, args: List[str]) -> str:
        """Handle an explain command."""
        try:
            if not args:
                return "Please specify a file to explain."
                
            file_path = args[0]
            
            # Check if file exists in session
            if file_path not in session.file_contexts:
                return f"File not found in session: {file_path}"
                
            code_context = session.file_contexts[file_path]
            
            # Get line number if specified
            line = None
            for arg in args[1:]:
                if arg.startswith("--line="):
                    try:
                        line = int(arg.split("=")[1])
                    except ValueError:
                        pass
                        
            # Generate explanation
            prompt = f"Explain the following code from file '{file_path}'"
            if line:
                prompt += f" focusing on line {line}"
                
            prompt += ":\n\n```\n"
            
            if line:
                # Extract the specific line and context
                lines = code_context.content.splitlines()
                if 0 <= line - 1 < len(lines):
                    # Get context (5 lines before and after)
                    start = max(0, line - 6)
                    end = min(len(lines), line + 5)
                    
                    for i in range(start, end):
                        if i == line - 1:
                            prompt += f"-> {i+1}: {lines[i]}\n"
                        else:
                            prompt += f"   {i+1}: {lines[i]}\n"
                else:
                    prompt += code_context.content
            else:
                prompt += code_context.content
                
            prompt += "\n```"
            
            # Get explanation from LLM
            llm_adapter = self.config_manager.get_service("llm_adapter")
            explanation = llm_adapter.generate_text(prompt, session.context)
            
            return explanation
        except Exception as e:
            self.logger.error(f"Error handling explain command: {str(e)}")
            return f"Error: {str(e)}"
```

## Conclusion

Cette implémentation des interfaces utilisateur et de l'application principale complète l'architecture hexagonale de Peer. Les interfaces CLI, TUI et API REST fournissent différentes façons d'interagir avec le système, tandis que la couche Application fait le lien entre ces interfaces et la couche Domaine.

L'architecture est maintenant complète, avec :
- Une couche Domaine contenant la logique métier
- Des adaptateurs d'infrastructure pour interagir avec les services externes
- Des interfaces utilisateur pour interagir avec l'utilisateur
- Une couche Application pour orchestrer le tout

Cette implémentation respecte les principes de l'architecture hexagonale, avec une séparation claire des responsabilités et une inversion des dépendances. Elle permet également un fonctionnement entièrement local, sans dépendances cloud, tout en offrant des fonctionnalités avancées comme l'analyse de code, la synthèse vocale et l'utilisation de modèles de langage.

Le système Peer est maintenant prêt à être utilisé et étendu avec de nouveaux plugins et fonctionnalités.
