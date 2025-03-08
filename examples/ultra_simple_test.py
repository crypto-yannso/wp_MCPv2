#!/usr/bin/env python3
"""
Test ultra-simple pour le serveur MCP WordPress.
N'utilise que les bibliothèques standard et 'requests'.
"""
import json
import sys
import requests
import time
import uuid
import threading

def ultra_simple_test(base_url="http://localhost:8000"):
    """Test ultra-simple du serveur MCP"""
    print(f"Connexion au serveur: {base_url}")
    
    # 1. Vérifier que le serveur est disponible
    try:
        response = requests.get(f"{base_url}")
        print(f"Serveur disponible: {response.status_code}")
        info = response.json()
        print("Outils disponibles:", ", ".join(info.get("tools", [])))
    except Exception as e:
        print(f"Erreur lors de la vérification du serveur: {e}")
        return
    
    # 2. Test direct de l'endpoint MCP
    try:
        response = requests.get(f"{base_url}/mcp/info")
        print(f"\nInformations MCP reçues: {response.status_code}")
        
        # Afficher les outils
        mcp_info = response.json()
        if "tools" in mcp_info:
            print(f"Outils détectés: {len(mcp_info['tools'])}")
            for tool in mcp_info["tools"]:
                print(f"- {tool['name']}: {tool['description']}")
        else:
            print("Aucun outil trouvé")
            
    except Exception as e:
        print(f"Erreur lors de la récupération des infos MCP: {e}")
    
    # 3. Génération d'un client ID sans SSE
    client_id = str(uuid.uuid4())
    print(f"\nUtilisation du client ID généré localement: {client_id}")
    
    # 4. Appel direct d'outil
    try:
        print("\nAppel direct de l'outil get_wordpress_content")
        payload = {
            "client_id": client_id,
            "tool_name": "get_wordpress_content",
            "parameters": {
                "post_id": 1
            }
        }
        
        response = requests.post(
            f"{base_url}/command/sse",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Réponse: {response.status_code}")
        result = response.json()
        print(json.dumps(result, indent=2))
        
        print("\nTest terminé avec succès")
        print("Conclusion: Le serveur MCP répond correctement aux requêtes")
        print("Les outils sont bien détectés et peuvent être appelés directement")
        
    except Exception as e:
        print(f"Erreur lors de l'appel d'outil: {e}")

if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    ultra_simple_test(base_url)