import os
import sys
import pkg_resources
from dotenv import load_dotenv

def check_dependencies():
    """Vérifie que toutes les dépendances sont installées"""
    required = {
        'openai': 'Pour GPT-4 et OpenAI Mini',
        'google-generativeai': 'Pour Gemini',
        'anthropic': 'Pour Claude',
        'python-dotenv': 'Pour la configuration',
        'requests': 'Pour les requêtes HTTP',
        'fastapi': 'Pour l\'API',
        'uvicorn': 'Pour le serveur'
    }
    
    missing = []
    for package in required:
        try:
            pkg_resources.require(package)
        except pkg_resources.DistributionNotFound:
            missing.append(f"{package} ({required[package]})")
            
    return missing

def check_api_keys():
    """Vérifie que toutes les clés API sont configurées"""
    load_dotenv()
    
    required_keys = {
        'OPENAI_API_KEY': 'Pour GPT-4 et OpenAI Mini',
        'GOOGLE_API_KEY': 'Pour Gemini',
        'ANTHROPIC_API_KEY': 'Pour Claude'
    }
    
    missing = []
    for key, description in required_keys.items():
        if not os.getenv(key):
            missing.append(f"{key} ({description})")
            
    return missing

def main():
    """Vérifie l'installation et la configuration"""
    print("🔍 Vérification de l'installation...\n")
    
    # Vérifier les dépendances
    missing_deps = check_dependencies()
    if missing_deps:
        print("❌ Dépendances manquantes :")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\nInstallation des dépendances manquantes :")
        print("pip install -r requirements.txt\n")
    else:
        print("✅ Toutes les dépendances sont installées\n")
    
    # Vérifier les clés API
    missing_keys = check_api_keys()
    if missing_keys:
        print("❌ Clés API manquantes :")
        for key in missing_keys:
            print(f"  - {key}")
        print("\nAjoutez ces clés dans votre fichier .env\n")
    else:
        print("✅ Toutes les clés API sont configurées\n")
    
    # Résumé
    if not missing_deps and not missing_keys:
        print("🎉 Tout est correctement configuré !")
        sys.exit(0)
    else:
        print("⚠️  Certaines configurations sont manquantes")
        sys.exit(1)

if __name__ == "__main__":
    main() 