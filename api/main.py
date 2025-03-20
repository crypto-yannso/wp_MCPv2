import logging
import sys
import time
import asyncio
import json
import uuid
from fastapi import FastAPI, HTTPException, Depends, Request, Form, Response, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
import uvicorn
from sse_starlette.sse import EventSourceResponse
from nlp.command_processor import CommandProcessor
from utils.config import HOST, PORT
from api.auth import router as auth_router, get_current_user
from api.database import Database
from api.payments import router as payments_router
from api.wordpress import router as wordpress_router  # Ajout du nouveau router
from api.events import register_client, remove_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('mcp.log')
    ]
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="WordPress MCP API",
    description="Middleware Control Panel API for WordPress",
    version="1.0.0"
)

# Include the auth router
app.include_router(auth_router)
app.include_router(payments_router)
app.include_router(wordpress_router)  # Ajout du router WordPress

# Mount static files
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Add CORS middleware with explicit headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Specify allowed origins in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "HEAD"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
    expose_headers=["Content-Type", "Content-Length"],
)

# Add middleware to add custom headers to all responses
@app.middleware("http")
async def add_custom_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["X-MCP-Server"] = "wordpress_mcp_server"
    
    # Ne pas écraser le Content-Type pour les réponses SSE
    if "text/event-stream" not in response.headers.get("Content-Type", ""):
        response.headers["Content-Type"] = "application/json"
    
    return response

# Security
security = HTTPBasic()

# Initialize command processor (lazy initialization to avoid immediate WordPress connection)
command_processor = None

def get_command_processor():
    global command_processor
    if command_processor is None:
        try:
            command_processor = CommandProcessor()
        except Exception as e:
            logger.error(f"Error initializing command processor: {str(e)}")
            return None
    return command_processor

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Process the request
    response = await call_next(request)
    
    # Log request details
    process_time = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.2f}s")
    
    return response

# Models
class CommandRequest(BaseModel):
    command: str = None
    client_id: str = None  # Optional client ID for SSE
    tool_name: str = None  # For direct tool calls (MCP protocol)
    parameters: dict = None  # Parameters for direct tool calls

class CommandResponse(BaseModel):
    success: bool
    message: str
    operation: str = None
    results: dict = None

# SSE Event types
EVENT_RECEIVED = "command_received"
EVENT_PROCESSING = "processing"
EVENT_RESULT = "result"
EVENT_ERROR = "error"
EVENT_COMPLETE = "complete"

# Store client connections for SSE
sse_clients = {}

async def sse_event_generator(client_id):
    """Generate SSE events for a given client ID"""
    try:
        queue = asyncio.Queue()
        sse_clients[client_id] = queue
        
        # Log registration of client
        logger.info(f"Registering client {client_id} in sse_clients dictionary")
        
        # Envoyer un commentaire vide d'abord pour initialiser la connexion
        # Le format sse-starlette pour les commentaires est différent
        yield {"comment": "connection initialized"}
        
        # Petit délai pour s'assurer que la connexion est établie
        await asyncio.sleep(0.1)
        
        # Send initial connection established event
        yield {
            "event": "connected",
            "data": json.dumps({"client_id": client_id, "message": "Connection established"})
        }
        
        # Un autre petit délai
        await asyncio.sleep(0.1)
        
        # Send test event for debugging
        yield {
            "event": "ping",
            "data": json.dumps({"time": time.time(), "message": "Server ping"})
        }
        
        # Keep connection alive with ping events
        ping_task = asyncio.create_task(send_ping_events(client_id))
        
        # Listen for events on the queue
        while True:
            try:
                # Wait for events with timeout to allow cancellation
                event = await asyncio.wait_for(queue.get(), timeout=15)  # Timeout réduit
                if event.get("event") == "close":
                    break
                # Assurez-vous que l'événement est correctement formaté
                if "event" not in event:
                    event["event"] = "message"
                if "data" not in event:
                    event["data"] = "{}"
                logger.debug(f"Sending event to client {client_id}: {event}")
                yield event
            except asyncio.TimeoutError:
                # Send keep-alive comment plus fréquemment - en utilisant le format comment
                yield {"comment": "keepalive"}
                continue
            
    except asyncio.CancelledError:
        # Clean up if client disconnects
        logger.info(f"Client {client_id} disconnected - connection cancelled")
    except Exception as e:
        logger.error(f"Error in SSE generator for client {client_id}: {str(e)}")
    finally:
        if client_id in sse_clients:
            logger.info(f"Removing client {client_id} from sse_clients dictionary")
            del sse_clients[client_id]
        # Cancel ping task if it exists
        try:
            ping_task.cancel()
        except UnboundLocalError:
            pass

async def send_ping_events(client_id):
    """Send periodic ping events to keep the connection alive"""
    try:
        # Première ping après 5 secondes pour s'assurer que la connexion fonctionne
        await asyncio.sleep(5)
        await send_sse_event(client_id, "ping", {"time": time.time(), "message": "Initial ping"})
        
        counter = 0
        while client_id in sse_clients:
            # Ping plus fréquent
            await asyncio.sleep(10)  # Ping toutes les 10 secondes
            counter += 1
            await send_sse_event(client_id, "ping", {
                "time": time.time(),
                "counter": counter,
                "message": "Keepalive ping"
            })
    except asyncio.CancelledError:
        # Task was cancelled, do nothing
        logger.info(f"Ping task cancelled for client {client_id}")
        pass
    except Exception as e:
        logger.error(f"Error in ping task for client {client_id}: {str(e)}")
            
async def send_sse_event(client_id, event_type, data):
    """Send an SSE event to a specific client"""
    if client_id in sse_clients:
        try:
            # S'assurer que les données sont du JSON valide
            json_data = json.dumps(data) if isinstance(data, (dict, list)) else str(data)
            
            queue = sse_clients[client_id]
            await queue.put({
                "event": event_type,
                "data": json_data
            })
            logger.debug(f"Event queued for client {client_id}: {event_type} - {json_data[:100]}")
        except Exception as e:
            logger.error(f"Error sending event to client {client_id}: {e}")
            # Envoyer un événement d'erreur à la place
            try:
                queue = sse_clients[client_id]
                await queue.put({
                    "event": "error",
                    "data": json.dumps({"message": f"Error sending event: {str(e)}"})
                })
            except Exception:
                pass  # Ignorer les erreurs lors de l'envoi de l'erreur

# Routes
@app.get("/")
async def root(request: Request):
    """
    Racine de l'API, retourne les informations de base et les points d'entrée
    """
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    
    return {
        "message": "WordPress Middleware Control Panel API",
        "status": "running",
        "endpoints": {
            "mcp_info": f"{base_url}/mcp/info",
            "sse_connect": f"{base_url}/sse/connect",
            "command": f"{base_url}/command/sse",
            "openapi": f"{base_url}/openapi.json",
            "manifest": f"{base_url}/manifest.json",
            "health": f"{base_url}/health"
        },
        # Inclure les outils directement à la racine pour une découverte facile
        "tools": [
            "add_wordpress_page",
            "update_wordpress_content",
            "add_wordpress_section",
            "get_wordpress_content"
        ]
    }

@app.get("/.well-known/ai-plugin.json")
@app.get("/manifest.json")  # Ajout d'un alias pour une meilleure compatibilité
async def plugin_manifest(request: Request):
    """
    Endpoint standardisé pour la découverte des outils AI/MCP
    """
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    return {
        "schema_version": "1.0",
        "name_for_human": "WordPress MCP",
        "name_for_model": "wordpress_mcp",
        "description_for_human": "Contrôlez WordPress par des commandes en langage naturel",
        "description_for_model": "Plugin permettant de contrôler WordPress via des commandes textuelles",
        "auth": {
            "type": "none"
        },
        "api": {
            "type": "openapi",
            "url": f"{base_url}/openapi.json"
        },
        "logo_url": f"{base_url}/static/logo.png",
        "contact_email": "contact@example.com",
        "legal_info_url": "https://example.com/legal",
        # Ajout des outils directement dans le manifeste pour meilleure compatibilité
        "tools": [
            {
                "name": "add_wordpress_page",
                "description": "Ajouter une nouvelle page WordPress",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Titre de la page"
                        },
                        "content": {
                            "type": "string",
                            "description": "Contenu HTML de la page"
                        },
                        "status": {
                            "type": "string",
                            "description": "Statut de la page (draft, publish, etc.)",
                            "default": "draft"
                        }
                    },
                    "required": ["title", "content"]
                }
            },
            {
                "name": "update_wordpress_content",
                "description": "Mettre à jour le contenu d'une page WordPress",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "post_id": {
                            "type": "integer", 
                            "description": "ID de la page à modifier"
                        },
                        "title": {
                            "type": "string",
                            "description": "Nouveau titre (optionnel)"
                        },
                        "content": {
                            "type": "string",
                            "description": "Nouveau contenu HTML (optionnel)"
                        }
                    },
                    "required": ["post_id"]
                }
            },
            {
                "name": "add_wordpress_section",
                "description": "Ajouter une nouvelle section à une page WordPress",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "post_id": {
                            "type": "integer",
                            "description": "ID de la page"
                        },
                        "title": {
                            "type": "string",
                            "description": "Titre de la section"
                        },
                        "content": {
                            "type": "string",
                            "description": "Contenu HTML de la section"
                        },
                        "position": {
                            "type": "integer",
                            "description": "Position de la section (optionnel)"
                        }
                    },
                    "required": ["post_id", "title", "content"]
                }
            },
            {
                "name": "get_wordpress_content",
                "description": "Obtenir le contenu d'une page WordPress",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "post_id": {
                            "type": "integer",
                            "description": "ID de la page"
                        }
                    },
                    "required": ["post_id"]
                }
            }
        ]
    }

@app.get("/logo.png")
async def get_logo():
    """
    Serve logo image for MCP
    """
    logo_path = os.path.join(static_dir, "logo.png")
    if not os.path.exists(logo_path):
        # Create a default logo if it doesn't exist
        return FileResponse(os.path.join(os.path.dirname(os.path.abspath(__file__)), "default_logo.png"))
    return FileResponse(logo_path)

@app.get("/openapi.json")
async def openapi_spec(request: Request):
    """
    Spécification OpenAPI pour les outils
    """
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    return {
        "openapi": "3.0.1",
        "info": {
            "title": "WordPress MCP API",
            "description": "API pour contrôler WordPress via des commandes en langage naturel",
            "version": "1.0.0"
        },
        "servers": [
            {
                "url": base_url
            }
        ],
        "paths": {
            "/command/sse": {
                "post": {
                    "summary": "Exécuter une commande ou un outil",
                    "operationId": "executeCommand",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "client_id": {
                                            "type": "string",
                                            "description": "Identifiant du client pour la connexion SSE"
                                        },
                                        "command": {
                                            "type": "string",
                                            "description": "Commande en langage naturel à exécuter"
                                        },
                                        "tool_name": {
                                            "type": "string",
                                            "description": "Nom de l'outil à exécuter directement"
                                        },
                                        "parameters": {
                                            "type": "object",
                                            "description": "Paramètres pour l'exécution de l'outil"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "202": {
                            "description": "Commande acceptée pour traitement"
                        }
                    }
                }
            },
            "/sse/connect": {
                "get": {
                    "summary": "Établir une connexion SSE",
                    "operationId": "connectSSE",
                    "responses": {
                        "200": {
                            "description": "Connexion SSE établie"
                        }
                    }
                }
            }
        }
    }

@app.post("/command")
async def process_command(
    request: CommandRequest,
    current_user = Depends(get_current_user)
):
    try:
        logger.info(f"Received command from user {current_user.email}: {request.command}")
        
        # Sauvegarder la commande dans la base de données
        command_record = await Database.save_command(
            user_id=current_user.id,
            command=request.command,
            command_type="direct",
            status="processing"
        )
        
        # Get command processor
        processor = get_command_processor()
        if processor is None:
            await Database.update_command_status(
                command_record["id"],
                "error",
                {"error": "WordPressConnectionError"}
            )
            return CommandResponse(
                success=False,
                message="Erreur de connexion à WordPress. Vérifiez vos paramètres de configuration (.env).",
                operation=None,
                results={"error": "WordPressConnectionError"}
            )
        
        # Process the command
        result = processor.process_command(request.command)
        
        if isinstance(result, dict) and "success" in result:
            success = result.get("success", False)
            message = result.get("message", "Command processed")
            
            # Remove some fields from the response
            if "success" in result:
                del result["success"]
            if "message" in result:
                del result["message"]
            if "command" in result:
                del result["command"]
            
            # Mettre à jour le statut dans la base de données
            await Database.update_command_status(
                command_record["id"],
                "completed" if success else "error",
                result
            )
                
            return CommandResponse(
                success=success,
                message=message,
                operation=result.get("operation"),
                results=result
            )
        else:
            # Mettre à jour le statut dans la base de données
            await Database.update_command_status(
                command_record["id"],
                "completed",
                result
            )
            
            return CommandResponse(
                success=True,
                message="Command processed",
                results=result
            )
    except Exception as e:
        logger.error(f"Error processing command: {str(e)}")
        
        # Mettre à jour le statut dans la base de données
        if 'command_record' in locals():
            await Database.update_command_status(
                command_record["id"],
                "error",
                {"error": str(e)}
            )
            
        return CommandResponse(
            success=False,
            message=f"Erreur lors du traitement de la commande: {str(e)}",
            operation=None,
            results={"error": str(e)}
        )

@app.post("/command/sse")
async def process_command_sse(
    request: Request, 
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user)
):
    """
    Process a natural language command with SSE updates
    """
    try:
        body = await request.json()
        logger.info(f"Received command from user {current_user.email}: {body}")
    except Exception as e:
        logger.error(f"Error parsing request body: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    
    # Get client ID from request body
    client_id = body.get("client_id")
    if not client_id:
        raise HTTPException(status_code=400, detail="Client ID is required for SSE")
    
    # Associer le client_id avec l'utilisateur
    client_id = f"{current_user.id}_{client_id}"
    
    if client_id not in sse_clients:
        logger.warning(f"Client {client_id} not found in sse_clients. Auto-registering.")
        sse_clients[client_id] = asyncio.Queue()
    
    # Check if there's a tool_name in the request
    command = body.get("command")
    tool_name = body.get("tool_name")
    tool_params = body.get("parameters")
    
    # Process command in background task
    if tool_name and tool_params:
        # Handle direct tool call (MCP protocol)
        logger.info(f"Direct tool call: {tool_name} with params: {tool_params}")
        background_tasks.add_task(process_tool_background, tool_name, tool_params, client_id)
    elif command:
        # Handle natural language command
        logger.info(f"Natural language command: {command}")
        background_tasks.add_task(process_command_background, command, client_id)
    else:
        raise HTTPException(status_code=400, detail="Either 'command' or 'tool_name' and 'parameters' must be provided")
    
    return JSONResponse(
        status_code=202,
        content={"message": "Command processing started", "client_id": client_id}
    )

async def process_command_background(command: str, client_id: str):
    """Process natural language command in background and send SSE events with progress"""
    try:
        # Notify that command was received
        await send_sse_event(client_id, EVENT_RECEIVED, {
            "message": "Command received",
            "command": command
        })
        
        # Get command processor
        processor = get_command_processor()
        if processor is None:
            await send_sse_event(client_id, EVENT_ERROR, {
                "message": "Erreur de connexion à WordPress. Vérifiez vos paramètres de configuration (.env).",
                "error": "WordPressConnectionError"
            })
            return
        
        # Notify that processing started
        await send_sse_event(client_id, EVENT_PROCESSING, {
            "message": "Traitement de la commande en cours..."
        })
        
        # Process the command (with artificial delay to show progress)
        await asyncio.sleep(0.5)  # Simulate processing time
        result = processor.process_command(command)
        
        # Send result
        if isinstance(result, dict) and "success" in result:
            success = result.get("success", False)
            message = result.get("message", "Command processed")
            
            # Remove some fields from the response
            if "success" in result:
                del result["success"]
            if "message" in result:
                del result["message"]
            if "command" in result:
                del result["command"]
                
            await send_sse_event(client_id, EVENT_RESULT, {
                "success": success,
                "message": message,
                "operation": result.get("operation"),
                "results": result
            })
        else:
            await send_sse_event(client_id, EVENT_RESULT, {
                "success": True,
                "message": "Command processed",
                "results": result
            })
        
        # Notify that processing is complete
        await send_sse_event(client_id, EVENT_COMPLETE, {
            "message": "Traitement terminé"
        })
    except Exception as e:
        logger.error(f"Error processing command: {str(e)}")
        await send_sse_event(client_id, EVENT_ERROR, {
            "message": f"Erreur lors du traitement de la commande: {str(e)}",
            "error": str(e)
        })

async def process_tool_background(tool_name: str, tool_params: dict, client_id: str):
    """Process direct tool call in background and send SSE events with progress"""
    try:
        # Notify that tool call was received
        await send_sse_event(client_id, EVENT_RECEIVED, {
            "message": f"Tool call received: {tool_name}",
            "tool": tool_name,
            "parameters": tool_params
        })
        
        # Get command processor
        processor = get_command_processor()
        if processor is None:
            await send_sse_event(client_id, EVENT_ERROR, {
                "message": "Erreur de connexion à WordPress. Vérifiez vos paramètres de configuration (.env).",
                "error": "WordPressConnectionError"
            })
            return
        
        # Notify that processing started
        await send_sse_event(client_id, EVENT_PROCESSING, {
            "message": f"Exécution de l'outil {tool_name} en cours..."
        })
        
        # Execute the tool based on the tool name
        if tool_name == "add_wordpress_page":
            # Handle add_wordpress_page tool
            title = tool_params.get("title", "")
            content = tool_params.get("content", "")
            status = tool_params.get("status", "draft")
            
            # Process the command with artificial delay
            await asyncio.sleep(0.5)
            result = processor.wp_manager.add_content(title, content, status)
            
            await send_sse_event(client_id, EVENT_RESULT, {
                "success": True,
                "message": f"Page créée avec succès: {title}",
                "results": result
            })
            
        elif tool_name == "update_wordpress_content":
            # Handle update_wordpress_content tool
            post_id = tool_params.get("post_id")
            title = tool_params.get("title")
            content = tool_params.get("content")
            
            # Process the command with artificial delay
            await asyncio.sleep(0.5)
            result = processor.wp_manager.update_content(post_id, title, content)
            
            await send_sse_event(client_id, EVENT_RESULT, {
                "success": result.get("success", False),
                "message": result.get("message", "Contenu mis à jour"),
                "results": result
            })
            
        elif tool_name == "add_wordpress_section":
            # Handle add_wordpress_section tool
            post_id = tool_params.get("post_id")
            title = tool_params.get("title")
            content = tool_params.get("content")
            position = tool_params.get("position")
            
            # Process the command with artificial delay
            await asyncio.sleep(0.5)
            result = processor.wp_manager.add_section(post_id, title, content, position)
            
            await send_sse_event(client_id, EVENT_RESULT, {
                "success": result.get("success", False),
                "message": result.get("message", "Section ajoutée"),
                "results": result
            })
            
        elif tool_name == "get_wordpress_content":
            # Handle get_wordpress_content tool
            post_id = tool_params.get("post_id")
            
            # Process the command with artificial delay
            await asyncio.sleep(0.5)
            result = processor.wp_manager.get_content(post_id)
            
            await send_sse_event(client_id, EVENT_RESULT, {
                "success": True,
                "message": f"Contenu de la page {post_id} récupéré",
                "results": result
            })
            
        else:
            # Unknown tool
            await send_sse_event(client_id, EVENT_ERROR, {
                "message": f"Outil inconnu: {tool_name}",
                "error": "UnknownToolError"
            })
            return
        
        # Notify that processing is complete
        await send_sse_event(client_id, EVENT_COMPLETE, {
            "message": "Traitement terminé"
        })
    except Exception as e:
        logger.error(f"Error processing tool call: {str(e)}")
        await send_sse_event(client_id, EVENT_ERROR, {
            "message": f"Erreur lors de l'exécution de l'outil {tool_name}: {str(e)}",
            "error": str(e)
        })

@app.post("/command/form")
async def process_command_form(command: str = Form(...)):
    """
    Process a natural language command from a form submission
    """
    request = CommandRequest(command=command)
    return await process_command(request)

@app.get("/sse/{client_id}")
async def sse_endpoint(client_id: str, request: Request):
    """
    Point d'entrée pour les connexions SSE
    """
    logger.info(f"New SSE connection request with client ID: {client_id}")
    
    # Créer la réponse SSE avec des en-têtes explicites
    response = EventSourceResponse(sse_event_generator(client_id))
    
    # Configurer les en-têtes explicitement
    response.headers["Content-Type"] = "text/event-stream"
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"
    
    # Activer CORS pour cette réponse
    origin = request.headers.get("Origin", "*")
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    
    return response

@app.get("/mcp/info")
@app.get("/api/mcp")
async def get_mcp_info(request: Request):
    """
    Returns MCP compatibility information
    """
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    
    # Define MCP tools
    mcp_tools = [
        {
            "name": "add_wordpress_page",
            "description": "Ajouter une nouvelle page WordPress",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Titre de la page"
                    },
                    "content": {
                        "type": "string",
                        "description": "Contenu HTML de la page"
                    },
                    "status": {
                        "type": "string",
                        "description": "Statut de la page (draft, publish, etc.)",
                        "default": "draft"
                    }
                },
                "required": ["title", "content"]
            }
        },
        {
            "name": "update_wordpress_content",
            "description": "Mettre à jour le contenu d'une page WordPress",
            "parameters": {
                "type": "object",
                "properties": {
                    "post_id": {
                        "type": "integer",
                        "description": "ID de la page à modifier"
                    },
                    "title": {
                        "type": "string",
                        "description": "Nouveau titre (optionnel)"
                    },
                    "content": {
                        "type": "string",
                        "description": "Nouveau contenu HTML (optionnel)"
                    }
                },
                "required": ["post_id"]
            }
        },
        {
            "name": "add_wordpress_section",
            "description": "Ajouter une nouvelle section à une page WordPress",
            "parameters": {
                "type": "object",
                "properties": {
                    "post_id": {
                        "type": "integer",
                        "description": "ID de la page"
                    },
                    "title": {
                        "type": "string",
                        "description": "Titre de la section"
                    },
                    "content": {
                        "type": "string",
                        "description": "Contenu HTML de la section"
                    },
                    "position": {
                        "type": "integer",
                        "description": "Position de la section (optionnel)"
                    }
                },
                "required": ["post_id", "title", "content"]
            }
        },
        {
            "name": "get_wordpress_content",
            "description": "Obtenir le contenu d'une page WordPress",
            "parameters": {
                "type": "object",
                "properties": {
                    "post_id": {
                        "type": "integer",
                        "description": "ID de la page"
                    }
                },
                "required": ["post_id"]
            }
        }
    ]
    
    return {
        "schema_version": "1.0",
        "id": "wordpress_mcp_server",
        "name": "WordPress MCP Server",
        "description": "Middleware Control Panel pour WordPress via commandes en langage naturel",
        "auth": {
            "type": "none"
        },
        "api": {
            "url": f"{base_url}/command/sse",
            "type": "rest"
        },
        "tools": mcp_tools,
        "streaming": {
            "url": f"{base_url}/sse",
            "type": "sse"
        },
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint (non protégé)
    """
    return {"status": "ok"}

# Protéger la route des outils WordPress
@app.post("/wordpress/{tool_name}")
async def execute_wordpress_tool(
    tool_name: str,
    params: dict,
    current_user = Depends(get_current_user)
):
    """
    Execute a WordPress tool with authentication
    """
    try:
        logger.info(f"User {current_user.email} executing tool: {tool_name}")
        processor = get_command_processor()
        if processor is None:
            raise HTTPException(status_code=500, detail="WordPress connection error")
            
        # Vérifier si l'outil existe
        if not hasattr(processor.wp_manager, tool_name):
            raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")
            
        # Exécuter l'outil
        tool = getattr(processor.wp_manager, tool_name)
        result = tool(**params)
        
        return {
            "success": True,
            "tool": tool_name,
            "result": result
        }
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Ajouter une nouvelle route pour récupérer l'historique des commandes
@app.get("/commands/history")
async def get_commands_history(current_user = Depends(get_current_user)):
    """
    Récupérer l'historique des commandes de l'utilisateur
    """
    try:
        commands = await Database.get_user_commands(current_user.id)
        return {
            "success": True,
            "commands": commands
        }
    except Exception as e:
        logger.error(f"Error fetching commands history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Ajouter une route pour récupérer les pages WordPress
@app.get("/wordpress/pages")
async def get_wordpress_pages(current_user = Depends(get_current_user)):
    """
    Récupérer toutes les pages WordPress de l'utilisateur
    """
    try:
        pages = await Database.get_wordpress_pages(current_user.id)
        return {
            "success": True,
            "pages": pages
        }
    except Exception as e:
        logger.error(f"Error fetching WordPress pages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def start():
    """Start the FastAPI application using uvicorn"""
    logger.info(f"Starting WordPress MCP API on http://{HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT, reload=True)

if __name__ == "__main__":
    start()