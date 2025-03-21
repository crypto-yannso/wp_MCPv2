# WordPress Middleware Control Panel (MCP)

Un système qui permet de contrôler WordPress via des commandes en langage naturel avec mises à jour en temps réel (SSE).

## 🔍 Aperçu

Le WordPress MCP (Middleware Control Panel) est un middleware qui permet de contrôler WordPress par des commandes en langage naturel, sans nécessiter de connaissances techniques en HTML ou WordPress. Il transforme des commandes comme "Ajoute une section avec un titre 'Nos services' et un paragraphe décrivant nos offres" en actions concrètes sur votre site WordPress, avec des notifications en temps réel grâce aux SSE (Server-Sent Events).

## ✨ Fonctionnalités

- **Contrôle par langage naturel** : Modifiez votre site WordPress avec des commandes en français simple
- **Mises à jour en temps réel** : Recevez des notifications en temps réel grâce aux SSE (Server-Sent Events)
- **Gestion intelligente du contenu** : Ajoutez, modifiez ou supprimez des sections de page
- **Sécurité intégrée** : Restriction configurable des opérations sensibles
- **API RESTful et SSE** : Intégration facile dans d'autres applications avec support du temps réel
- **Mode démo** : Possibilité de fonctionner sans connexion WordPress pour les tests
- **Historique des opérations** : Journalisation complète des actions effectuées

## 📋 Prérequis

- Python 3.8+
- WordPress avec XML-RPC activé
- OpenAI API key

## 🚀 Installation

1. Clonez le dépôt :
   ```bash
   git clone https://github.com/votre-username/wordpress-mcp.git
   cd wordpress-mcp
   ```

2. Installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```

3. Téléchargez le modèle spaCy (optionnel) :
   ```bash
   python -m spacy download fr_core_news_md
   ```

4. Créez votre fichier .env à partir du modèle :
   ```bash
   cp .env.example .env
   ```
   
5. Modifiez le fichier .env avec vos informations WordPress et OpenAI

## 🎮 Utilisation

### Démarrer le serveur

```bash
uvicorn api.main:app --reload
```

Ordre de test recommandé :
Register
Login
Voir profil
Mettre à jour profil
Créer une page
Voir les pages
Mettre à jour une page
Voir l'historique des commandes

#Création d'un compte (si pas déjà fait)

POST http://localhost:8000/auth/register
Content-Type: application/json

{
    "email": "test@example.com",
    "password": "votre_mot_de_passe",
    "first_name": "John",
    "last_name": "Doe"
}

###Connexion (pour obtenir le token)

POST http://localhost:8000/auth/login
Content-Type: application/json

{
    "username": "test@example.com",
    "password": "votre_mot_de_passe"
}

#Voir son profil

GET http://localhost:8000/auth/profile
Authorization: Bearer votre_token_jwt

###Mettre à jour son profil
PUT http://localhost:8000/auth/profile
Authorization: Bearer votre_token_jwt
Content-Type: application/json

{
    "first_name": "John Updated",
    "last_name": "Doe Updated",
    "avatar_url": "https://example.com/avatar.jpg"
}


### Utilisation avec Server-Sent Events (SSE)

1. **Établir une connexion SSE et obtenir un client_id** :
   ```bash
   2025-03-16 12:49:31 INFO:     172.18.0.1:48218 - "GET /sse/connect HTTP/1.1" 200 OK
2025-03-16 12:50:00 2025-03-16 11:50:00,554 - api.main - INFO - GET /sse/46d9a76f-70d1-4e96-beb7-a46b1796e3ab - 404 - 0.00s
2025-03-16 12:50:00 INFO:     172.18.0.1:55618 - "GET /sse/46d9a76f-70d1-4e96-beb7-a46b1796e3ab HTTP/1.1" 404 Not Found
   ```
   Le serveur répondra avec un événement "connected" contenant votre client_id :
   ```
   event: connected
   data: {"client_id": "votre-client-id", "message": "Connection established"}
   ```

2. **Envoyer des commandes avec le client_id** :
   ```bash
   curl -N -X POST http://localhost:8000/command/sse \
     -H "Content-Type: application/json" \
     -d "{\"command\": \"Ajoute une nouvelle page avec le titre \\\"test\\\" et le contenu \\\"Notre équipe est composée d'experts passionnés.\\\"\", \"client_id\": \"92fd97a6-050c-4737-82af-f901aa34bb17\"}"
   ```

   curl -X POST  http://localhost:8000/command/sse \
   -H "Content-Type: application/json" \
   -d '{
     "tool_name": "add_wordpress_page",
     "parameters": {
       "title": "Nouvelle Page",
       "content": "Contenu de la page",
       "status": "publish"
     },
     "client_id": "378286b0-cc16-402a-8a06-da03a82aa0e2"
   }'

3. **Observer les résultats** :
   Les résultats seront envoyés en temps réel via la connexion SSE établie à l'étape 1. Vous recevrez des événements pour :
   - La réception de la commande (`command_received`)
   - Le début du traitement (`processing`)
   - Les résultats (`result`)
   - Les erreurs éventuelles (`error`)
   - La fin du traitement (`complete`)

### Utilisation via l'interface web

Vous pouvez également utiliser l'interface web fournie :
1. Ouvrez `examples/sse_interface.html` dans votre navigateur
2. Cliquez sur "Se connecter"
3. Entrez vos commandes dans la zone de texte
4. Observez les résultats en temps réel dans la section "Événements"

## 📝 Exemples de commandes

- "Ajoute une nouvelle page avec le titre 'À propos' et un paragraphe de présentation"
- "Mets à jour le titre de la section 'Nos services' pour qu'il soit 'Nos prestations'"
- "Supprime la section 'Ancienne offre' de la page d'accueil"
- "Réorganise les sections de la page 'Services' pour mettre 'Tarifs' en premier"

## 🔧 Configuration

- **Opérations restreintes** : Configurez les opérations qui nécessitent une confirmation dans utils/config.py
- **Niveau de logs** : Modifiez le niveau de logging dans main.py

## 🏗️ Structure du projet

```
wordpress-mcp/
├── api/                # API REST FastAPI
├── nlp/                # Traitement du langage naturel
├── wordpress/          # Interaction avec WordPress
├── utils/              # Utilitaires (config, logging, etc.)
├── examples/           # Exemples d'utilisation et interfaces
├── .env.example        # Modèle de fichier de configuration
├── main.py             # Point d'entrée principal
├── requirements.txt    # Dépendances Python
└── README.md           # Documentation
```

## 📊 Perspectives et améliorations

- **Extension à Gutenberg et Elementor** : Ajouter la gestion des blocs et widgets
- **Contrôle vocal** : Piloter WordPress par la voix avec GPT-4
- **Historique des modifications** : Permettre d'annuler un changement
- **Prise en charge des styles CSS** : Modifier les couleurs et polices avec des commandes en langage naturel

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier LICENSE pour plus d'informations.

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.

---

Avec cette approche, on obtient un CMS intelligent contrôlé uniquement par des commandes textuelles ! 🚀💡



rm /etc/nginx/sites-enabled/wp_mcpv2  # Supprimer la configuration par défaut


curl -N -X POST http://87.106.247.230/command/sse -H "Content-Type: application/json" -d '{
  "tool_name": "add_wordpress_page",
  "parameters": {
    "title": "herby-vps",
    "content": "<h1>Nos Services</h1><p>Decouvrez nos services professionnels.</p>",
    "status": "publish"
  },
  "client_id": "e3c937a1-a062-4868-be63-ccca26609f1e"
}'

$ curl -N http://87.106.247.230/sse/connect -H "Accept: text/event-stream"


//UPDATE

curl -X POST http://localhost:8000/command/sse \
   -H "Content-Type: application/json" \
   -d '{
     "tool_name": "update_wordpress_content",
     "parameters": {
       "post_id": 966,
       "title": "Nouveau Titre",
       "content": "Nouveau contenu"
     },
     "client_id": "bd95db41-fc52-4877-9ca9-42cc38cebad3"
   }'
{"message":"Command processing started","client_id":"bd95db41-fc52-4877-9ca9-42cc38cebad3"}



curl -X POST http://localhost:8000/command/sse    -H "Content-Type: application/json"    -d '{
     "tool_name": "update_wordpress_content",
     "parameters": {
       "post_id": 966,
       "content": "Nouveau sans titre contenu"
     },
     "client_id": "bd95db41-fc52-4877-9ca9-42cc38cebad3"
   }'
{"message":"Command processing started","client_id":"bd95db41-fc52-4877-9ca9-42cc38cebad3"}


curl -X POST http://localhost:8000/command/sse \
   -H "Content-Type: application/json" \
   -d '{
     "tool_name": "update_wordpress_content",
     "parameters": {
       "post_id": 966,
       "position": 0,
       "content": "CONTENU_EXISTANT2 <h2>Nouvelle Sec2tion</h2><p>Mon nouveau2 contenu</p>"
     },
     "client_id": "bd95db41-fc52-4877-9ca9-42cc38cebad3"
   }'


   curl -X POST http://localhost:8000/command/sse \
   -H "Content-Type: application/json" \
   -d '{
     "tool_name": "get_wordpress_content",
     "parameters": {
       "post_id": 5
     },
     "client_id": "bd95db41-fc52-4877-9ca9-42cc38cebad3"
   }'

   100 18949    0 18949    0     0     17      0 --:--:--  0:17:52 --:--:--    34event: processing
data: {"message": "Ex\u00e9cution de l'outil get_wordpress_content en cours..."}

event: result
data: {"success": true, "message": "Contenu de la page 966 r\u00e9cup\u00e9r\u00e9", "results": {"id": 966, "title": "Nouveau Titre", "content": "CONTENU_EXISTANT2 <h2>Nouvelle Sec2tion</h2><p>Mon nouveau2 contenu</p>", "sections": [{"id": "section-0", "title": "Nouvelle Sec2tion", "content": "<p>Mon nouveau2 contenu</p>"}]}}


   curl -X POST http://localhost:8000/command/sse \
   -H "Content-Type: application/json" \
   -d '{
     "tool_name": "update_wordpress_content",
     "parameters": {
       "post_id": 966,
       "content": "CONTENU_EXISTANT2 <h2>Nouvelle Sec2tion</h2><p>Mon nouveau2 contenu</p><h2>Section Additionnelle</h2><p>Voici le nouveau contenu que je ajoute a la page existante</p>"
     },
     "client_id": "bd95db41-fc52-4877-9ca9-42cc38cebad3"
   }'
{"message":"Command processing started","client_id":"bd95db41-fc52-4877-9ca9-42cc38cebad3"}



curl -X POST http://localhost:8000/command/sse \
   -H "Content-Type: application/json" \
   -d '{
     "tool_name": "get_meta_description",
     "parameters": {
       "post_id": 966
     },
     "client_id": "96ca8c84-86e9-4082-8ffc-2b2ed476871c"
   }'


curl -X POST http://localhost:8000/command/sse \
   -H "Content-Type: application/json" \
   -d '{
     "tool_name": "update_meta_description",
     "parameters": {
       "post_id": 966,
       "meta_description": "Ceci est la nouvelle meta description de ma page"
     },
     "client_id": "38ddcca4-6365-41b7-b6c1-4ea221dc633a"
   }'

Pour obtenir les informations SEO de tout le site :
   curl -X POST http://localhost:8000/command/sse \
   -H "Content-Type: application/json" \
   -d '{
     "tool_name": "get_seo_info",
     "parameters": {
       "post_id": 966
     },
     "client_id": "001010cd-7728-4238-8813-58aaa66dd77a"
   }'

// ajoute des conteny via template
curl -X POST http://localhost:8000/command/sse \
-H "Content-Type: application/json" \
-d '{
  "tool_name": "add_content_from_template",
  "client_id": "c3ade929-e6bb-4a1c-9a6b-61b33f80de02",
  "parameters": {
    "template_name": "page_standard",
    "variables": {
      "name": "A propos",
      "introduction": "Bienvenue sur notre page A propos",
      "services_description": "Nous proposons les services suivants",
      "services_list": "<li>Service 1</li><li>Service 2</li><li>Service 3</li>",
      "contact_info": "Contactez-nous au 01 23 45 67 89"
    }
  }
}'



curl -X POST http://localhost:8000/command/sse \
   -H "Content-Type: application/json" \
   -d '{
     "tool_name": "update_meta_description",
     "parameters": {
       "post_id": 966,
       "meta_description": "Ceci est la nouvelle meta description de ma page"
     },
     "client_id": "votre_client_id"
   }'


   curl -X POST http://localhost:8000/command/sse \
   -H "Content-Type: application/json" \
   -d '{
     "tool_name": "update_meta_description",
     "parameters": {
       "post_id": 966,
       "meta_description": "Ceci est la nouvelle meta description de ma page"
     },
     "client_id": "a4d44941-8e2c-44db-a8a5-50824feb6050"
   }'


   curl -X POST http://localhost:8000/command/sse \
   -H "Content-Type: application/json" \
   -d '{
     "tool_name": "update_meta_description",
     "parameters": {
       "post_id": 966,
       "meta_description": "Ceci est la chatte a thierry breton"
     },
     "client_id": "76fa0c70-b1be-422c-ad53-487bc0c9f82b"
   }'