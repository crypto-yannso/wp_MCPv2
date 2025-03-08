import logging
from .intent_parser import IntentParser
from wordpress.content_manager import WordPressContentManager

logger = logging.getLogger(__name__)

class CommandProcessor:
    """
    Process natural language commands and execute the appropriate WordPress operations
    """
    def __init__(self):
        """Initialize the command processor with an intent parser and WordPress content manager"""
        self.parser = IntentParser()
        # Initialize WordPress content manager (may raise exception if WordPress is unavailable)
        self.wp_manager = WordPressContentManager()
        logger.info("Command processor initialized")
    
    def is_demo_mode(self):
        """Check if we're in demo mode (no WordPress connection)"""
        return hasattr(self, 'wp_manager') and self.wp_manager is None
    
    def process_command(self, command):
        """
        Process a natural language command:
        1. Parse the command to extract operation and parameters
        2. Execute the operation with the extracted parameters
        3. Return the result
        """
        try:
            # Parse the command
            parsed = self.parser.parse(command)
            if not parsed["success"]:
                return parsed
            
            operation = parsed["operation"]
            parameters = parsed["parameters"]
            
            # Execute the operation
            if operation == "get_content":
                result = self.wp_manager.get_content(**parameters)
            elif operation == "add_content":
                result = self.wp_manager.add_content(**parameters)
            elif operation == "update_content":
                result = self.wp_manager.update_content(**parameters)
            elif operation == "delete_content":
                result = self.wp_manager.delete_content(**parameters)
            elif operation == "add_section":
                result = self.wp_manager.add_section(**parameters)
            elif operation == "update_section":
                result = self.wp_manager.update_section(**parameters)
            elif operation == "delete_section":
                result = self.wp_manager.delete_section(**parameters)
            elif operation == "reorder_sections":
                result = self.wp_manager.reorder_sections(**parameters)
            else:
                return {
                    "success": False,
                    "message": f"Operation {operation} is not implemented"
                }
            
            # Add operation and original command to the result
            if isinstance(result, dict):
                result["operation"] = operation
                result["command"] = command
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing command: {str(e)}")
            return {
                "success": False,
                "message": f"Error processing command: {str(e)}"
            }