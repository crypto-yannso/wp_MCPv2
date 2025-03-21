import os
import requests
import shutil

def download_file(url, filename):
    """Download a file from URL"""
    print(f"Downloading {filename}...")
    response = requests.get(url, stream=True)
    with open(filename, 'wb') as f:
        shutil.copyfileobj(response.raw, f)
    print(f"Downloaded {filename}")

def setup_swagger():
    """Download and setup Swagger UI files"""
    # Create static directory if it doesn't exist
    static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
    os.makedirs(static_dir, exist_ok=True)
    
    # Swagger UI files
    files = {
        "swagger-ui-bundle.js": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.11.0/swagger-ui-bundle.js",
        "swagger-ui.css": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.11.0/swagger-ui.css",
        "redoc.standalone.js": "https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js"
    }
    
    # Download each file
    for filename, url in files.items():
        filepath = os.path.join(static_dir, filename)
        if not os.path.exists(filepath):
            download_file(url, filepath)
        else:
            print(f"File {filename} already exists")

if __name__ == "__main__":
    setup_swagger() 