import logging
import re
import json
from utils.config import OPENAI_API_KEY, ALLOWED_OPERATIONS

logger = logging.getLogger(__name__)

# Vérifier si l'API OpenAI est configurée
HAS_OPENAI = False
client = None
try:
    if OPENAI_API_KEY:
        # Import the modern OpenAI client (v1.x)
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        HAS_OPENAI = True
        logger.info("Using OpenAI API v1.x (modern client)")
    else:
        logger.warning("OpenAI API key not found in environment variables")
except Exception as e:
    logger.error(f"Failed to initialize OpenAI client: {str(e)}")
    logger.info("Will use rule-based processing instead of OpenAI")

class IntentParser:
    """
    Class to parse natural language commands into structured operations
    """
    def __init__(self):
        """Initialize intent parser"""
        logger.info("Intent parser initialized")
    
    def extract_intent(self, command):
        """
        Extract the intent (operation type) from a natural language command
        using OpenAI to classify the intent
        """
        try:
            prompt = f"""
            Analyze the following command and determine the WordPress operation intended.
            Return only one of these operations without explanation: {', '.join(ALLOWED_OPERATIONS)}
            
            Command: "{command}"
            
            Operation:
            """
            
            # Check if we're in demo mode (no OpenAI API)
            if not HAS_OPENAI:
                logger.info("DEMO MODE: Simulating OpenAI call for intent extraction")
                # Règles simples basées sur des mots-clés
                command = command.lower()
                if "seo" in command or "référencement" in command:
                    return "get_seo_info"
                elif "meta description" in command:
                    if "modifie" in command or "change" in command or "mets à jour" in command:
                        return "update_meta_description"
                    else:
                        return "get_meta_description"
                elif "ajoute" in command or "crée" in command:
                    return "add_content" if "page" in command else "add_section"
                elif "mets à jour" in command or "modifie" in command:
                    return "update_content" if "page" in command else "update_section"
                elif "supprime" in command:
                    return "delete_content" if "page" in command else "delete_section"
                elif "réorganise" in command:
                    return "reorder_sections"
                elif "montre" in command or "affiche" in command:
                    return "get_content"
                else:
                    return None
            
            # Use modern OpenAI API
            try:
                if client:
                    response = client.completions.create(
                        model="gpt-3.5-turbo-instruct",
                        prompt=prompt,
                        max_tokens=20,
                        temperature=0.1
                    )
                    operation = response.choices[0].text.strip().lower()
                else:
                    raise ValueError("OpenAI client not initialized")
            except Exception as e:
                logger.error(f"OpenAI API error: {str(e)}")
                # Fallback to rule-based intent extraction
                logger.info("Falling back to rule-based intent extraction")
                if "ajoute" in command.lower() or "crée" in command.lower() or "créer" in command.lower():
                    return "add_content" if "page" in command.lower() else "add_section"
                elif "mets à jour" in command.lower() or "modifie" in command.lower() or "modifier" in command.lower():
                    return "update_content" if "page" in command.lower() else "update_section"
                elif "supprime" in command.lower() or "supprimer" in command.lower():
                    return "delete_content" if "page" in command.lower() else "delete_section"
                elif "réorganise" in command.lower() or "réorganiser" in command.lower():
                    return "reorder_sections"
                elif "montre" in command.lower() or "affiche" in command.lower() or "obtenir" in command.lower():
                    return "get_content"
                else:
                    return None
            
            # Validate that the operation is allowed
            if operation not in ALLOWED_OPERATIONS:
                logger.warning(f"Unrecognized operation: {operation}")
                return None
                
            return operation
        except Exception as e:
            logger.error(f"Failed to extract intent: {str(e)}")
            return None
            
    def extract_parameters(self, command, operation):
        """
        Extract parameters for the operation from a natural language command
        using OpenAI to parse the details
        """
        try:
            parameter_schema = self._get_parameter_schema(operation)
            
            prompt = f"""
            Extract parameters from the following command for a WordPress {operation} operation.
            Return a valid JSON object with these parameters: {', '.join(parameter_schema.keys())}
            
            Command: "{command}"
            
            JSON parameters:
            """
            
            # Fonction utilitaire pour l'extraction de paramètres basée sur des règles
            def rule_based_extraction():
                logger.info("Using rule-based parameter extraction")
                params = {}
                
                # Extract post_id
                if "page" in command.lower() and "id" in command.lower():
                    post_id_match = re.search(r'id\s*:?\s*(\d+)', command.lower())
                    if post_id_match:
                        params["post_id"] = int(post_id_match.group(1))
                    else:
                        params["post_id"] = 5  # Default ID for demo
                
                # Extract titles (sauf pour get_content)
                if operation != "get_content":
                    title_match = re.search(r"titre\s*['\"]([^'\"]+)['\"]", command)
                    if title_match:
                        params["title"] = title_match.group(1)
                    elif "titre" in command.lower():
                        params["title"] = "Titre d'exemple"
                    
                    # Extract content (sauf pour get_content)
                    content_match = re.search(r"contenu\s*['\"]([^'\"]+)['\"]", command)
                    if content_match:
                        params["content"] = content_match.group(1)
                    elif "contenu" in command.lower():
                        params["content"] = "<p>Contenu d'exemple pour la démonstration.</p>"
                
                # Extract section_id
                if "section" in command.lower():
                    section_match = re.search(r'section\s*[\'"]([^\'"]+)[\'"]', command)
                    if section_match:
                        params["section_id"] = "section-0"  # Use first section
                    else:
                        params["section_id"] = "section-0"
                
                # Extract position
                if "position" in command.lower():
                    params["position"] = 0
                
                # Extract section_order
                if "réorganise" in command.lower():
                    params["section_order"] = ["section-0", "section-1", "section-2"]
                
                return params
            
            # Check if we're in demo mode (no OpenAI API)
            if not HAS_OPENAI:
                logger.info("DEMO MODE: Simulating OpenAI call for parameter extraction")
                return rule_based_extraction()
            
            # Use modern OpenAI API
            try:
                if client:
                    response = client.completions.create(
                        model="gpt-3.5-turbo-instruct",
                        prompt=prompt,
                        max_tokens=200,
                        temperature=0.1
                    )
                    json_text = response.choices[0].text.strip()
                else:
                    raise ValueError("OpenAI client not initialized")
            except Exception as e:
                logger.error(f"OpenAI API error in parameter extraction: {str(e)}")
                # Fallback to rule-based parameter extraction
                return rule_based_extraction()
            
            try:
                parameters = json.loads(json_text)
                # Validate parameters against schema
                for key, required in parameter_schema.items():
                    if required and key not in parameters:
                        logger.warning(f"Missing required parameter: {key}")
                        # Fall back to rule-based extraction if missing required parameters
                        return rule_based_extraction()
                return parameters
            except json.JSONDecodeError:
                logger.error("Failed to parse parameters JSON")
                # Fall back to rule-based extraction if JSON parsing fails
                return rule_based_extraction()
                
        except Exception as e:
            logger.error(f"Failed to extract parameters: {str(e)}")
            return None
    
    def _get_parameter_schema(self, operation):
        """
        Return the parameter schema for a given operation
        Each value indicates if the parameter is required
        """
        schemas = {
            "get_content": {
                "post_id": True
            },
            "add_content": {
                "title": True,
                "content": True,
                "status": False
            },
            "update_content": {
                "post_id": True,
                "title": False,
                "content": False,
                "status": False
            },
            "delete_content": {
                "post_id": True,
                "force": False
            },
            "add_section": {
                "post_id": True,
                "title": True,
                "content": True,
                "position": False
            },
            "update_section": {
                "post_id": True,
                "section_id": True,
                "title": False,
                "content": False
            },
            "delete_section": {
                "post_id": True,
                "section_id": True,
                "force": False
            },
            "reorder_sections": {
                "post_id": True,
                "section_order": True
            },
            "get_meta_description": {
                "post_id": True
            },
            "update_meta_description": {
                "post_id": True,
                "meta_description": True
            },
            "get_seo_info": {
                "post_id": False
            }
        }
        
        return schemas.get(operation, {})
        
    def parse(self, command):
        """
        Parse a natural language command into a structured operation
        with parameters
        """
        operation = self.extract_intent(command)
        if not operation:
            return {
                "success": False,
                "message": "Could not determine the operation from your command"
            }
            
        parameters = self.extract_parameters(command, operation)
        if not parameters:
            return {
                "success": False,
                "message": "Could not extract the necessary parameters from your command"
            }
            
        return {
            "success": True,
            "operation": operation,
            "parameters": parameters
        }