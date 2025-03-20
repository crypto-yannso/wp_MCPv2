from typing import Dict, Any
import asyncio
import logging
import json

logger = logging.getLogger(__name__)

# Stockage des connexions clients
client_connections: Dict[str, asyncio.Queue] = {}

async def send_sse_event(client_id: str, event_type: str, data: Any):
    """
    Envoie un événement SSE à un client spécifique
    """
    if client_id not in client_connections:
        logger.warning(f"Client {client_id} not found in active connections")
        return

    try:
        event_data = {
            "event": event_type,
            "data": data
        }
        await client_connections[client_id].put(json.dumps(event_data))
    except Exception as e:
        logger.error(f"Error sending SSE event: {str(e)}")

def register_client(client_id: str) -> asyncio.Queue:
    """
    Enregistre un nouveau client SSE
    """
    if client_id in client_connections:
        return client_connections[client_id]
    
    queue = asyncio.Queue()
    client_connections[client_id] = queue
    return queue

def remove_client(client_id: str):
    """
    Supprime un client SSE
    """
    if client_id in client_connections:
        del client_connections[client_id] 