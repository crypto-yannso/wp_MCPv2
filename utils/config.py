import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# WordPress Configuration
WP_URL = os.getenv("WP_URL")
WP_USERNAME = os.getenv("WP_USERNAME")
WP_PASSWORD = os.getenv("WP_PASSWORD")

# OpenAI API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Server Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Security Configuration
ALLOWED_OPERATIONS = [
    "add_content",
    "update_content",
    "delete_content",
    "get_content",
    "get_all_pages",
    "add_section",
    "update_section",
    "delete_section",
    "reorder_sections",
    "get_meta_description",
    "update_meta_description",
    "get_seo_info",
    "add_content_from_template",
    "analyze_llm"
]

# Restrict operations that can modify content
RESTRICTED_OPERATIONS = [
    "delete_content",
    "delete_section"
]


