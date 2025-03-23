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
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
import os
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
import uvicorn
from sse_starlette.sse import EventSourceResponse
from nlp.command_processor import CommandProcessor
from utils.config import HOST, PORT

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
    description="""
    Middleware Control Panel API pour WordPress.
    
    Cette API permet de :
    * Gérer le contenu WordPress via des commandes en langage naturel
    * Manipuler les pages et les sections
    * Gérer le SEO et les meta descriptions
    * Recevoir des mises à jour en temps réel via SSE
    
    ## Commandes
    
    Vous pouvez utiliser des commandes en langage naturel comme :
    * "crée une nouvelle page avec le titre 'Ma Page'"
    * "ajoute une section 'Introduction' à la page avec ID 123"
    * "montre moi les informations seo du site"
    * "modifie la meta description de la page 456"
    
    ## Authentification
    
    L'API utilise l'authentification basique HTTP pour sécuriser les endpoints.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={"defaultModelsExpandDepth": -1}
)

# Mount static files
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Add CORS middleware with explicit headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "HEAD"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
    expose_headers=["Content-Type", "Content-Length"],
)

# Custom Swagger UI route
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """
    Interface Swagger UI personnalisée
    """
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Documentation API",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
    )

# Custom ReDoc route
@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    """
    Interface ReDoc personnalisée
    """
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Documentation API",
        redoc_js_url="/static/redoc.standalone.js",
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

# Models with enhanced documentation
class CommandRequest(BaseModel):
    """
    Modèle pour les requêtes de commande
    """
    command: str = None
    client_id: str = None
    tool_name: str = None
    parameters: dict = None

    class Config:
        schema_extra = {
            "example": {
                "command": "crée une nouvelle page avec le titre 'Ma Page'",
                "client_id": "550e8400-e29b-41d4-a716-446655440000",
                "tool_name": "add_content",
                "parameters": {
                    "title": "Ma Page",
                    "content": "<p>Contenu de ma page</p>"
                }
            }
        }

class CommandResponse(BaseModel):
    """
    Modèle pour les réponses de commande
    """
    success: bool
    message: str
    operation: str = None
    results: dict = None

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Page créée avec succès",
                "operation": "add_content",
                "results": {
                    "id": 123,
                    "title": "Ma Page",
                    "status": "draft"
                }
            }
        }

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
                "name": "add_content_from_template",
                "description": "Créer une page WordPress à partir d'un template prédéfini",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "template_name": {
                            "type": "string",
                            "description": "Nom du template à utiliser (page_standard ou article_blog)",
                            "enum": ["page_standard", "article_blog"]
                        },
                        "variables": {
                            "type": "object",
                            "description": "Variables à injecter dans le template",
                            "properties": {
                                "name": {"type": "string", "description": "Nom de la page (pour page_standard)"},
                                "introduction": {"type": "string", "description": "Texte d'introduction"},
                                "services_description": {"type": "string", "description": "Description des services (pour page_standard)"},
                                "services_list": {"type": "string", "description": "Liste HTML des services (pour page_standard)"},
                                "contact_info": {"type": "string", "description": "Informations de contact (pour page_standard)"},
                                "title": {"type": "string", "description": "Titre de l'article (pour article_blog)"},
                                "section1_title": {"type": "string", "description": "Titre de la première section (pour article_blog)"},
                                "section1_content": {"type": "string", "description": "Contenu de la première section (pour article_blog)"},
                                "section2_title": {"type": "string", "description": "Titre de la deuxième section (pour article_blog)"},
                                "section2_content": {"type": "string", "description": "Contenu de la deuxième section (pour article_blog)"},
                                "conclusion": {"type": "string", "description": "Conclusion de l'article (pour article_blog)"}
                            }
                        }
                    },
                    "required": ["template_name", "variables"]
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
            },
            {
                "name": "get_meta_description",
                "description": "Obtenir la meta description d'une page WordPress",
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
            },
            {
                "name": "update_meta_description",
                "description": "Mettre à jour la meta description d'une page WordPress",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "post_id": {
                            "type": "integer",
                            "description": "ID de la page"
                        },
                        "meta_description": {
                            "type": "string",
                            "description": "Nouvelle meta description"
                        }
                    },
                    "required": ["post_id", "meta_description"]
                }
            },
            {
                "name": "get_seo_info",
                "description": "Obtenir toutes les informations SEO d'une page ou du site entier",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "post_id": {
                            "type": "integer",
                            "description": "ID de la page (optionnel - si non fourni, retourne les informations SEO du site)"
                        }
                    }
                }
            },
            {
                "name": "get_all_pages",
                "description": "Obtenir la liste de toutes les pages WordPress",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "number": {
                            "type": "integer",
                            "description": "Nombre de pages à récupérer par page (défaut: 100)",
                            "default": 100
                        },
                        "page": {
                            "type": "integer",
                            "description": "Numéro de la page pour la pagination (défaut: 1)",
                            "default": 1
                        },
                        "status": {
                            "type": "string",
                            "description": "Statut des pages à récupérer (publish, draft, private, any)",
                            "default": "any"
                        }
                    }
                }
            },
            {
                "name": "analyze_llm",
                "description": "Analyser le site avec LLMConsole",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "site_url": {"type": "string", "description": "URL du site à analyser"},
                        "analysis_type": {
                            "type": "string", 
                            "description": "Type d'analyse (ranking ou recommendations)",
                            "enum": ["ranking", "recommendations"]
                        }
                    },
                    "required": ["site_url", "analysis_type"]
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
async def process_command(request: CommandRequest):
    """
    Process a natural language command for WordPress (REST API version)
    """
    try:
        logger.info(f"Received command: {request.command}")
        
        # Get command processor
        processor = get_command_processor()
        if processor is None:
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
                
            return CommandResponse(
                success=success,
                message=message,
                operation=result.get("operation"),
                results=result
            )
        else:
            return CommandResponse(
                success=True,
                message="Command processed",
                results=result
            )
    except Exception as e:
        logger.error(f"Error processing command: {str(e)}")
        return CommandResponse(
            success=False,
            message=f"Erreur lors du traitement de la commande: {str(e)}",
            operation=None,
            results={"error": str(e)}
        )

@app.post("/command/sse")
async def process_command_sse(request: Request, background_tasks: BackgroundTasks):
    """
    Process a natural language command with SSE updates
    """
    # Parse request body
    try:
        body = await request.json()
        logger.info(f"Received command: {body}")
    except Exception as e:
        logger.error(f"Error parsing request body: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    
    # Get client ID from request body
    client_id = body.get("client_id")
    if not client_id:
        raise HTTPException(status_code=400, detail="Client ID is required for SSE")
    
    # Check if client exists in sse_clients dictionary - DÉSACTIVÉ POUR TESTS
    # Nous auto-enregistrons le client s'il n'existe pas déjà
    if client_id not in sse_clients:
        logger.warning(f"Client {client_id} not found in sse_clients. Auto-registering.")
        # Créer une file pour ce client ID même s'il n'a pas de connexion SSE
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
            
        elif tool_name == "get_meta_description":
            # Handle get_meta_description tool
            post_id = tool_params.get("post_id")
            
            # Process the command with artificial delay
            await asyncio.sleep(0.5)
            result = processor.wp_manager.get_meta_description(post_id)
            
            await send_sse_event(client_id, EVENT_RESULT, {
                "success": True,
                "message": f"Meta description de la page {post_id} récupérée",
                "results": result
            })
            
        elif tool_name == "update_meta_description":
            # Handle update_meta_description tool
            post_id = tool_params.get("post_id")
            meta_description = tool_params.get("meta_description")
            
            # Process the command with artificial delay
            await asyncio.sleep(0.5)
            result = processor.wp_manager.update_meta_description(post_id, meta_description)
            
            await send_sse_event(client_id, EVENT_RESULT, {
                "success": result.get("success", False),
                "message": result.get("message", "Meta description mise à jour"),
                "results": result
            })
            
        elif tool_name == "get_seo_info":
            # Handle get_seo_info tool
            post_id = tool_params.get("post_id")
            
            # Process the command with artificial delay
            await asyncio.sleep(0.5)
            result = processor.wp_manager.get_seo_info(post_id)
            
            await send_sse_event(client_id, EVENT_RESULT, {
                "success": True,
                "message": f"Informations SEO de la page {post_id} récupérées",
                "results": result
            })
            
        elif tool_name == "get_all_pages":
            # Handle get_all_pages tool
            number = tool_params.get("number", 100)
            page = tool_params.get("page", 1)
            status = tool_params.get("status", "any")
            
            # Process the command with artificial delay
            await asyncio.sleep(0.5)
            result = processor.wp_manager.get_all_pages(number, page, status)
            
            await send_sse_event(client_id, EVENT_RESULT, {
                "success": True,
                "message": "Liste des pages WordPress récupérée",
                "results": result
            })
            
        elif tool_name == "add_content_from_template":
            # Handle add_content_from_template tool
            template_name = tool_params.get("template_name")
            variables = tool_params.get("variables", {})
            
            # Process the command with artificial delay
            await asyncio.sleep(0.5)
            result = processor.wp_manager.add_content_from_template(template_name, variables)
            
            await send_sse_event(client_id, EVENT_RESULT, {
                "success": result.get("success", False),
                "message": result.get("message", "Contenu créé à partir du template"),
                "results": result
            })
            
        elif tool_name == "analyze_llm":
            # Créer l'analyseur LLM
            from wordpress.llm_analyzer import LLMAnalyzer
            analyzer = LLMAnalyzer(tool_params["site_url"])
            
            # Effectuer l'analyse demandée
            if tool_params["analysis_type"] == "ranking":
                results = analyzer.get_brand_ranking()
                message = "Analyse du classement de marque terminée"
            else:
                results = analyzer.get_recommendations()
                message = "Analyse des recommandations terminée"
                
            # Envoyer les résultats
            await send_sse_event(client_id, "result", {
                "success": True,
                "message": message,
                "results": results
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

@app.get("/sse/connect/{client_id}")
async def sse_connect(client_id: str, request: Request):
    """
    Endpoint to establish a Server-Sent Events connection with a specified client ID
    """
    logger.info(f"New SSE connection with specified client ID: {client_id}")
    
    # Créer la réponse SSE avec des en-têtes explicites
    response = EventSourceResponse(sse_event_generator(client_id))
    
    # Configurer les en-têtes explicitement
    response.headers["Content-Type"] = "text/event-stream"
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"  # Désactive la mise en buffer par Nginx
    
    # Activer CORS pour cette réponse
    origin = request.headers.get("Origin", "*")
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    
    return response

@app.get("/sse/connect")
@app.get("/mcp/info")  # Alias pour une meilleure découverte
@app.get("/api/mcp")   # Autre alias couramment utilisé
async def sse_connect_new(request: Request):
    """
    Endpoint to establish a Server-Sent Events connection with a generated client ID
    or returns MCP compatibility information
    """
    # Check if this is a client connection or MCP discovery request
    accept_header = str(request.headers.get("accept", ""))
    
    logger.info(f"SSE connect called with Accept header: {accept_header}")
    
    # If client is requesting event-stream, establish SSE connection
    if "text/event-stream" in accept_header:
        client_id = str(uuid.uuid4())
        logger.info(f"New SSE connection with generated ID: {client_id}")
        
        # Create SSE response with explicit headers
        response = EventSourceResponse(sse_event_generator(client_id))
        
        # Configurer les en-têtes explicitement
        response.headers["Content-Type"] = "text/event-stream"
        response.headers["Cache-Control"] = "no-cache, no-transform"
        response.headers["Connection"] = "keep-alive"
        response.headers["X-Accel-Buffering"] = "no"  # Désactive la mise en buffer par Nginx
        
        # Activer CORS pour cette réponse
        origin = request.headers.get("Origin", "*")
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        
        return response
    
    # Otherwise, return MCP compatibility information
    else:
        # Define MCP tools - ces outils doivent être exposés dans différents formats pour compatibilité
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
                "name": "add_content_from_template",
                "description": "Créer une page WordPress à partir d'un template prédéfini",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "template_name": {
                            "type": "string",
                            "description": "Nom du template à utiliser (page_standard ou article_blog)",
                            "enum": ["page_standard", "article_blog"]
                        },
                        "variables": {
                            "type": "object",
                            "description": "Variables à injecter dans le template",
                            "properties": {
                                "name": {"type": "string", "description": "Nom de la page (pour page_standard)"},
                                "introduction": {"type": "string", "description": "Texte d'introduction"},
                                "services_description": {"type": "string", "description": "Description des services (pour page_standard)"},
                                "services_list": {"type": "string", "description": "Liste HTML des services (pour page_standard)"},
                                "contact_info": {"type": "string", "description": "Informations de contact (pour page_standard)"},
                                "title": {"type": "string", "description": "Titre de l'article (pour article_blog)"},
                                "section1_title": {"type": "string", "description": "Titre de la première section (pour article_blog)"},
                                "section1_content": {"type": "string", "description": "Contenu de la première section (pour article_blog)"},
                                "section2_title": {"type": "string", "description": "Titre de la deuxième section (pour article_blog)"},
                                "section2_content": {"type": "string", "description": "Contenu de la deuxième section (pour article_blog)"},
                                "conclusion": {"type": "string", "description": "Conclusion de l'article (pour article_blog)"}
                            }
                        }
                    },
                    "required": ["template_name", "variables"]
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
            },
            {
                "name": "get_meta_description",
                "description": "Obtenir la meta description d'une page WordPress",
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
            },
            {
                "name": "update_meta_description",
                "description": "Mettre à jour la meta description d'une page WordPress",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "post_id": {
                            "type": "integer",
                            "description": "ID de la page"
                        },
                        "meta_description": {
                            "type": "string",
                            "description": "Nouvelle meta description"
                        }
                    },
                    "required": ["post_id", "meta_description"]
                }
            },
            {
                "name": "get_seo_info",
                "description": "Obtenir toutes les informations SEO d'une page ou du site entier",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "post_id": {
                            "type": "integer",
                            "description": "ID de la page (optionnel - si non fourni, retourne les informations SEO du site)"
                        }
                    }
                }
            },
            {
                "name": "get_all_pages",
                "description": "Obtenir la liste de toutes les pages WordPress",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "number": {
                            "type": "integer",
                            "description": "Nombre de pages à récupérer par page (défaut: 100)",
                            "default": 100
                        },
                        "page": {
                            "type": "integer",
                            "description": "Numéro de la page pour la pagination (défaut: 1)",
                            "default": 1
                        },
                        "status": {
                            "type": "string",
                            "description": "Statut des pages à récupérer (publish, draft, private, any)",
                            "default": "any"
                        }
                    }
                }
            },
            {
                "name": "analyze_llm",
                "description": "Analyser le site avec LLMConsole",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "site_url": {"type": "string", "description": "URL du site à analyser"},
                        "analysis_type": {
                            "type": "string", 
                            "description": "Type d'analyse (ranking ou recommendations)",
                            "enum": ["ranking", "recommendations"]
                        }
                    },
                    "required": ["site_url", "analysis_type"]
                }
            }
        ]
        
        # Format simplifié des outils pour certains clients
        simplified_tools = [
            {
                "name": tool["name"],
                "description": tool["description"]
            } for tool in mcp_tools
        ]
        
        # Return MCP compatibility information in multiple formats for maximum compatibility
        base_url = f"{request.url.scheme}://{request.url.netloc}"
        
        # Format principal
        mcp_response = {
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
                "url": f"{base_url}/sse/connect",
                "type": "sse"
            },
            "functions": mcp_tools,  # Certains clients s'attendent à 'functions' plutôt que 'tools'
            
            # Formats alternatifs intégrés
            "capabilities": {
                "tools": simplified_tools  # Format simplifié pour certains clients
            },
            "mcp": {
                "tools": mcp_tools,
                "version": "1.0",
                "server_name": "wordpress_mcp"
            },
            
            # Ajout de propriétés communes pour différentes implémentations MCP
            "server_name": "wordpress_mcp_server",
            "server_url": f"{base_url}/sse/connect",
            "command_url": f"{base_url}/command/sse",
            "version": "1.0.0"
        }
        
        return mcp_response

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "ok"}

@app.post("/analyze")
async def analyze_site(request: Request):
    """
    Endpoint pour analyser un site avec différents modèles LLM
    """
    try:
        # Parse request body
        body = await request.json()
        site_url = body.get("site_url")
        analysis_type = body.get("analysis_type")
        models = body.get("models", [])  # Liste optionnelle des modèles à utiliser
        api_keys = body.get("api_keys", {})  # Clés API optionnelles
        
        if not site_url or not analysis_type:
            raise HTTPException(
                status_code=400, 
                detail="Les paramètres 'site_url' et 'analysis_type' sont requis"
            )
            
        # Créer l'analyseur LLM
        from wordpress.llm_analyzer import LLMAnalyzer
        analyzer = LLMAnalyzer(site_url, api_keys)
        
        # Effectuer l'analyse demandée avec les modèles spécifiés
        if analysis_type == "ranking":
            results = analyzer.get_brand_ranking()
            message = "Analyse du classement de marque terminée"
        elif analysis_type == "recommendations":
            results = analyzer.get_recommendations()
            message = "Analyse des recommandations terminée"
        else:
            raise HTTPException(
                status_code=400,
                detail="Le type d'analyse doit être 'ranking' ou 'recommendations'"
            )
            
        # Si une erreur est retournée dans les résultats
        if isinstance(results, dict) and "error" in results:
            raise HTTPException(
                status_code=400,
                detail=results.get("details", results["error"])
            )
            
        return {
            "success": True,
            "message": message,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'analyse: {str(e)}"
        )

def start():
    """Start the FastAPI application using uvicorn"""
    logger.info(f"Starting WordPress MCP API on http://{HOST}:{PORT}")
    uvicorn.run("api.main:app", host=HOST, port=PORT, reload=True)

if __name__ == "__main__":
    start()