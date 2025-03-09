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
     -d "{\"command\": \"Ajoute une nouvelle page avec le titre \\\"Notre équipe\\\" et le contenu \\\"Notre équipe est composée d'experts passionnés.\\\"\", \"client_id\": \"12def2ee-da84-4c6a-9a7f-c81786e69737\"}"
   ```

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