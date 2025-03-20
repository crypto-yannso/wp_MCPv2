import os
import logging
from dotenv import load_dotenv
from utils.logger import setup_logger
from api.main import start as start_api


# Initialize logger
logger = setup_logger(
    name="mcp", 
    log_file="logs/mcp.log", 
    level=logging.INFO
)

def main():
    """Main entry point for the WordPress Middleware Control Panel"""
    try:
        # Load environment variables
        load_dotenv()
        
        # Check for demo mode
        demo_mode = os.getenv("MCP_DEMO_MODE", "false").lower() == "true"
        allow_demo_mode = os.getenv("MCP_ALLOW_DEMO_MODE", "false").lower() == "true"
        
        # Check required environment variables if not in demo mode
        if not demo_mode:
            required_vars = ["WP_URL", "WP_USERNAME", "WP_PASSWORD", "OPENAI_API_KEY"]
            missing_vars = [var for var in required_vars if not os.getenv(var)]
            
            if missing_vars and not allow_demo_mode:
                logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
                logger.error("Please check your .env file or environment variables or enable MCP_ALLOW_DEMO_MODE")
                return
            elif missing_vars:
                logger.warning(f"Missing environment variables: {', '.join(missing_vars)}. Continuing in demo mode.")
                os.environ["MCP_DEMO_MODE"] = "true"
        
        # Create logs directory if it doesn't exist
        if not os.path.exists("logs"):
            os.makedirs("logs")
            
        # Start the API server
        if demo_mode:
            logger.info("Starting WordPress Middleware Control Panel in DEMO MODE")
        else:
            logger.info("Starting WordPress Middleware Control Panel")
            
        start_api()
        
    except Exception as e:
        logger.error(f"Error starting WordPress MCP: {str(e)}")
        raise

if __name__ == "__main__":
    main()