#!/usr/bin/env python3
"""
Script de test simple pour la connexion SSE au MCP WordPress.
Utilise le module sseclient-py pour établir une connexion SSE et
afficher les événements reçus.
"""
import json
import sys
import requests
import time
import uuid
from sseclient import SSEClient

def simple_sse_test(base_url="http://localhost:8000"):
    """Test simple de connexion SSE"""
    print(f"Connexion au serveur: {base_url}")
    
    # 1. Vérifier que le serveur est disponible
    try:
        response = requests.get(f"{base_url}")
        print(f"Serveur disponible: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Erreur lors de la vérification du serveur: {e}")
        return
    
    # 2. Récupérer les informations du serveur MCP
    try:
        response = requests.get(f"{base_url}/mcp/info")
        print(f"Informations MCP: {response.status_code}")
        info = response.json()
        
        # Afficher les outils disponibles
        if "tools" in info:
            print(f"Outils disponibles: {len(info['tools'])}")
            for tool in info["tools"]:
                print(f"- {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}")
        else:
            print("Aucun outil trouvé dans la réponse MCP")
            print(json.dumps(info, indent=2))
    except Exception as e:
        print(f"Erreur lors de la récupération des informations MCP: {e}")
    
    # 3. Établir une connexion SSE
    try:
        print("\nÉtablissement de la connexion SSE...")
        client = SSEClient(f"{base_url}/sse/connect")
        
        # Attendre et afficher les événements
        client_id = None
        event_count = 0
        
        # Utiliser client.events() au lieu d'itérer directement
        for msg in client.events():
            event_count += 1
            event_type = msg.event if msg.event else "message"
            print(f"Event #{event_count}: {event_type}, Data: {msg.data}")
            
            if msg.event == "connected":
                try:
                    data = json.loads(msg.data)
                    client_id = data.get("client_id")
                    print(f"Client ID reçu: {client_id}")
                    
                    # Une fois connecté, envoyer une commande de test
                    if client_id:
                        send_test_command(base_url, client_id)
                except Exception as e:
                    print(f"Erreur lors du traitement de l'événement connected: {e}")
            
            # Après avoir reçu quelques événements, quitter
            if event_count > 5 or (msg.event == "ping" and client_id):
                print("Plusieurs événements reçus, connexion SSE fonctionnelle")
                break
                
    except KeyboardInterrupt:
        print("\nInterruption utilisateur, fermeture de la connexion...")
    except Exception as e:
        print(f"Erreur lors de la connexion SSE: {e}")

def send_test_command(base_url, client_id):
    """Envoyer une commande de test au serveur"""
    print(f"\nEnvoi d'une commande de test avec client_id: {client_id}")
    
    # Commande directe
    try:
        command_data = {
            "client_id": client_id,
            "command": "Montre-moi le contenu de la page avec l'ID 1"
        }
        
        response = requests.post(
            f"{base_url}/command/sse",
            json=command_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Résultat de la commande: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Erreur lors de l'envoi de la commande: {e}")
    
    # Après une pause, envoyer un appel d'outil direct
    time.sleep(2)
    
    try:
        tool_data = {
            "client_id": client_id,
            "tool_name": "get_wordpress_content",
            "parameters": {
                "post_id": 1
            }
        }
        
        response = requests.post(
            f"{base_url}/command/sse",
            json=tool_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Résultat de l'appel d'outil: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'appel d'outil: {e}")

if __name__ == "__main__":
    # Si un argument est fourni, utiliser comme URL de base
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    simple_sse_test(base_url)