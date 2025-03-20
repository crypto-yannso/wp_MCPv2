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
   curl -N http://localhost:8000/sse/connect -H "Accept: text/event-stream"
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

   curl -X POST http://87.106.247.230:8000/command/sse \
   -H "Content-Type: application/json" \
   -d '{
     "tool_name": "add_wordpress_page",
     "parameters": {
       "title": "Nouvelle Page",
       "content": "Contenu de la page",
       "status": "publish"
     },
     "client_id": "92fd97a6-050c-4737-82af-f901aa34bb17"
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


# 1. Ajouter une authentification JWT
- Implémenter un système de tokens JWT
- Ajouter un endpoint de login/register
- Protéger les routes sensibles

# 2. Rate Limiting
- Limiter le nombre de requêtes par IP/utilisateur
- Ajouter des délais entre les requêtes

# 3. Validation des entrées
- Ajouter des validateurs pour le contenu HTML
- Filtrer les scripts malveillants


# 1. Ajouter des métriques
- Temps de réponse
- Nombre de requêtes
- Taux de succès/échec

# 2. Améliorer les logs
- Logs structurés (JSON)
- Rotation des logs
- Niveau de log configurable


# 1. Mise en cache
- Cacher les réponses fréquentes
- Utiliser Redis pour le cache

# 2. Optimisation des requêtes
- Pagination des résultats
- Compression des réponses

# 1. Gestion des médias
- Upload d'images
- Gestion de la bibliothèque média

# 2. Gestion des versions
- Historique des modifications
- Restauration de versions

# 3. Templates
- Système de templates pour les pages
- Composants réutilisables


# 1. Dashboard d'administration
- Interface web pour gérer les pages
- Visualisation des métriques

# 2. Éditeur visuel
- Éditeur WYSIWYG
- Prévisualisation en direct


 # Base de données :

# 1. Migration vers une base de données
- PostgreSQL pour les données structurées
- MongoDB pour les contenus
- Gestion des migrations

# 2. Backup automatique
- Sauvegarde périodique
- Restauration simplifiée


Déploiement :
# 1. CI/CD
- GitHub Actions
- Tests automatisés
- Déploiement automatique

# 2. Containerisation
- Docker multi-stage builds
- Docker Compose pour dev/prod
- Kubernetes pour le scaling




Pour toutes les autres requêtes, dans l'onglet "Authorization" :
Type : Bearer Token
Token : {{token}}
Les routes protégées sont maintenant :
/command - Pour les commandes simples
/command/sse - Pour les commandes avec Server-Sent Events
/wordpress/{tool_name} - Pour l'accès direct aux outils WordPress
Les routes non protégées sont :
/health - Pour vérifier l'état de l'API
/auth/login - Pour se connecter
/auth/register - Pour s'inscrire
/auth/verify - Pour vérifier l'email
/auth/forgot-password - Pour réinitialiser le mot de passe
Si une requête est faite sans token valide, l'API retournera une erreur 401 Unauthorized.
Voulez-vous que je vous montre comment tester une route protégée spécifique ou comment gérer les erreurs d'authentification côté client ?