"""
Module contenant l'interface API REST.
"""

import logging
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from peer.domain.services.message_service import MessageService
from peer.domain.services.system_check_service import SystemCheckService
from peer.infrastructure.adapters.simple_tts_adapter import SimpleTTSAdapter
from peer.infrastructure.adapters.simple_system_check_adapter import SimpleSystemCheckAdapter

logger = logging.getLogger(__name__)

# Initialiser les adaptateurs
tts_adapter = SimpleTTSAdapter()
tts_adapter.initialize()

system_check_adapter = SimpleSystemCheckAdapter()

# Initialiser les services
message_service = MessageService(tts_adapter)
system_check_service = SystemCheckService(system_check_adapter)

# Créer l'application FastAPI
app = FastAPI(
    title="Peer API",
    description="API REST pour l'application Peer",
    version="0.1.0"
)


@app.get("/")
async def root() -> Dict[str, str]:
    """
    Point d'entrée principal de l'API.
    
    Returns:
        Message de bienvenue
    """
    welcome_message = message_service.get_welcome_message()
    message_service.vocalize_message(welcome_message)
    return {"message": welcome_message.content}


@app.get("/check")
async def check_system() -> Dict[str, Any]:
    """
    Vérifie l'état du système.
    
    Returns:
        État du système
    """
    status = system_check_service.check_system()
    message = system_check_service.get_status_message()
    
    return {
        "status": "ok" if status.is_online else "error",
        "message": message,
        "components": status.components_status
    }


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Vérifie l'état de santé de l'API.
    
    Returns:
        État de santé
    """
    return {"status": "ok"}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Gestionnaire d'exceptions global."""
    logger.error(f"Erreur non gérée: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"message": "Une erreur interne s'est produite"}
    )


def start_api():
    """
    Démarre l'API avec uvicorn.
    
    Cette fonction est utilisée comme point d'entrée pour démarrer l'API
    via la ligne de commande ou un script.
    """
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    start_api()
