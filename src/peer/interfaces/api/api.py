"""
Module contenant l'interface API de Peer.
"""

import sys
import logging
from typing import Dict, Any, Optional, List

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Importation des dépendances
try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
except ImportError as e:
    print(f"Erreur lors du chargement des dépendances: {e}")
    print("Veuillez installer les dépendances requises:")
    print("  pip install fastapi uvicorn")
    sys.exit(1)

# Importation des services
from peer.domain.services.message_service import MessageService
from peer.domain.services.system_check_service import SystemCheckService
from peer.domain.services.command_service import CommandService
from peer.infrastructure.adapters.simple_system_check_adapter import SimpleSystemCheckAdapter

# Modèles de données
class CommandRequest(BaseModel):
    """Modèle pour les requêtes de commande."""
    command: str
    args: Optional[List[str]] = None

class CommandResponse(BaseModel):
    """Modèle pour les réponses de commande."""
    result: str
    success: bool
    timestamp: str

# Création de l'application FastAPI
app = FastAPI(
    title="Peer API",
    description="API REST pour Peer",
    version="0.2.0"
)

# Initialisation des services
message_service = MessageService()
system_check_service = SystemCheckService(SimpleSystemCheckAdapter())
command_service = CommandService()  # Service centralisé de commandes

@app.get("/")
async def root():
    """Route racine de l'API."""
    return {
        "name": "Peer API",
        "version": "0.2.0",
        "status": "running"
    }

@app.get("/health")
async def health():
    """Vérifie l'état de santé de l'API."""
    return {
        "status": "healthy",
        "services": {
            "message_service": "ok",
            "system_check_service": "ok",
            "command_service": "ok"
        }
    }

@app.post("/command", response_model=CommandResponse)
async def execute_command(request: CommandRequest):
    """
    Exécute une commande.
    
    Args:
        request: Requête de commande
        
    Returns:
        CommandResponse: Réponse de la commande
    """
    try:
        # Exécuter la commande via le service centralisé
        result = command_service.execute_command(request.command, request.args or [])
        
        # Créer la réponse
        response = CommandResponse(
            result=result,
            success=True,
            timestamp=logging.Formatter.formatTime(logging.Formatter(), logging.LogRecord("", 0, "", 0, None, None, None))
        )
        
        return response
    except Exception as e:
        logging.error(f"Erreur lors de l'exécution de la commande: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/commands")
async def list_commands():
    """Liste les commandes disponibles."""
    # Obtenir la liste des commandes via le service centralisé
    help_text = command_service.execute_command("aide")
    
    # Extraire les commandes du texte d'aide
    commands = []
    for line in help_text.split("\n"):
        if line.strip().startswith("  "):
            cmd_parts = line.strip().split(" - ", 1)
            if len(cmd_parts) == 2:
                cmd_name = cmd_parts[0].strip()
                cmd_desc = cmd_parts[1].strip()
                commands.append({
                    "name": cmd_name,
                    "description": cmd_desc
                })
    
    return {
        "commands": commands
    }

def start_api(host: str = "0.0.0.0", port: int = 8000):
    """
    Démarre l'API.
    
    Args:
        host: Hôte d'écoute
        port: Port d'écoute
    """
    import uvicorn
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    start_api()
