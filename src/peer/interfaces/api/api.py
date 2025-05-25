"""
Module contenant l'interface API de Peer.

Refactorisé pour utiliser le daemon central et l'adaptateur API.
"""

import sys
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

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
    from fastapi import FastAPI, HTTPException, Depends
    from pydantic import BaseModel
    import uvicorn
except ImportError as e:
    print(f"Erreur lors du chargement des dépendances: {e}")
    print("Veuillez installer les dépendances requises:")
    print("  pip install fastapi uvicorn")
    sys.exit(1)

# Importation du core centralisé
from peer.core import get_daemon, APIAdapter, CoreRequest, CoreResponse, InterfaceType, CommandType
from peer.domain.services.message_service import MessageService

# Modèles de données pour l'API REST
class CommandRequest(BaseModel):
    """Modèle pour les requêtes de commande via API REST."""
    command: str
    parameters: Optional[Dict[str, Any]] = {}
    context: Optional[Dict[str, Any]] = {}
    session_id: Optional[str] = None

class CommandResponse(BaseModel):
    """Modèle pour les réponses de commande via API REST."""
    type: str
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    instance_id: int
    request_id: Optional[str] = None
    response_id: str
    timestamp: str

class SessionRequest(BaseModel):
    """Modèle pour les requêtes de session."""
    interface_type: str = "api"

class SessionResponse(BaseModel):
    """Modèle pour les réponses de session."""
    session_id: str
    interface_type: str
    created_at: str

# Instance globale du daemon et de l'adaptateur
_daemon = None
_adapter = None

def get_api_daemon():
    """Obtenir l'instance du daemon pour l'API"""
    global _daemon, _adapter
    if _daemon is None:
        _daemon = get_daemon()
        _adapter = APIAdapter()
    return _daemon, _adapter

# Création de l'application FastAPI
app = FastAPI(
    title="Peer API",
    description="API REST pour Peer - Interface standardisée avec le daemon central",
    version="0.3.0"
)

@app.get("/")
async def root():
    """Point d'entrée racine de l'API"""
    daemon, _ = get_api_daemon()
    return {
        "message": "Peer API - Interface REST pour le daemon central",
        "version": daemon.get_version(),
        "endpoints": {
            "commands": "/command",
            "sessions": "/session",
            "status": "/status",
            "capabilities": "/capabilities",
            "help": "/help"
        }
    }

@app.post("/command", response_model=CommandResponse)
async def execute_command(request: CommandRequest):
    """
    Exécuter une commande via l'API REST.
    """
    daemon, adapter = get_api_daemon()
    
    try:
        # Convertir la requête API en format interface
        interface_input = {
            'command': request.command,
            'parameters': request.parameters,
            'context': request.context
        }
        
        # Traduire via l'adaptateur API
        if request.session_id:
            adapter.set_session_id(request.session_id)
        
        core_request = adapter.translate_to_core(interface_input)
        
        # Exécuter via le daemon
        core_response = daemon.execute_command(core_request)
        
        # Traduire la réponse
        api_response_dict = adapter.translate_from_core(core_response)
        
        return CommandResponse(**api_response_dict)
        
    except Exception as e:
        logging.error(f"Erreur lors de l'exécution de la commande API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/session", response_model=SessionResponse)
async def create_session(request: SessionRequest):
    """
    Créer une nouvelle session.
    """
    daemon, _ = get_api_daemon()
    
    try:
        session_id = daemon.create_session(InterfaceType.API)
        
        return SessionResponse(
            session_id=session_id,
            interface_type="api",
            created_at=datetime.now().isoformat()
        )
        
    except Exception as e:
        logging.error(f"Erreur lors de la création de session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/session/{session_id}")
async def end_session(session_id: str):
    """
    Terminer une session.
    """
    daemon, _ = get_api_daemon()
    
    try:
        success = daemon.end_session(session_id)
        
        if success:
            return {"message": "Session terminée avec succès", "session_id": session_id}
        else:
            raise HTTPException(status_code=404, detail="Session non trouvée")
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Erreur lors de la suppression de session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
async def get_status():
    """
    Obtenir le statut du système.
    """
    daemon, adapter = get_api_daemon()
    
    try:
        # Créer une requête de statut
        core_request = CoreRequest(
            command=CommandType.STATUS,
            interface_type=InterfaceType.API
        )
        
        core_response = daemon.execute_command(core_request)
        api_response = adapter.translate_from_core(core_response)
        
        return api_response
        
    except Exception as e:
        logging.error(f"Erreur lors de la récupération du statut: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/capabilities")
async def get_capabilities():
    """
    Obtenir les capacités disponibles.
    """
    daemon, adapter = get_api_daemon()
    
    try:
        # Créer une requête de capacités
        core_request = CoreRequest(
            command=CommandType.CAPABILITIES,
            interface_type=InterfaceType.API
        )
        
        core_response = daemon.execute_command(core_request)
        api_response = adapter.translate_from_core(core_response)
        
        return api_response
        
    except Exception as e:
        logging.error(f"Erreur lors de la récupération des capacités: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/help")
async def get_help(command: Optional[str] = None):
    """
    Obtenir l'aide.
    """
    daemon, adapter = get_api_daemon()
    
    try:
        # Créer une requête d'aide
        parameters = {}
        if command:
            parameters['command'] = command
            
        core_request = CoreRequest(
            command=CommandType.HELP,
            parameters=parameters,
            interface_type=InterfaceType.API
        )
        
        core_response = daemon.execute_command(core_request)
        api_response = adapter.translate_from_core(core_response)
        
        return api_response
        
    except Exception as e:
        logging.error(f"Erreur lors de la récupération de l'aide: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Fonction pour démarrer le serveur
def start_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """
    Démarre le serveur API.
    
    Args:
        host: Adresse d'écoute
        port: Port d'écoute  
        reload: Mode rechargement automatique
    """
    uvicorn.run(
        "peer.interfaces.api.api:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )

if __name__ == "__main__":
    start_server()
