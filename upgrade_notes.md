# Notes de mise à jour pour WordPress MCP

## Mise à jour vers OpenAI v1.x

Le système a été mis à jour pour utiliser la dernière version de l'API OpenAI (v1.x). Les changements suivants ont été apportés :

### Modifications apportées

1. **Utilisation exclusive du client moderne**
   - Le code utilise désormais uniquement la nouvelle interface client OpenAI
   - Suppression de l'ancien code utilisant `openai.Completion.create`
   - Remplacement par `client.completions.create` (client moderne)

2. **Meilleure gestion des erreurs**
   - Ajout d'un système de fallback robuste vers l'extraction basée sur des règles
   - Messages de journalisation détaillés pour faciliter le débogage

3. **Mode sans API**
   - Le système peut fonctionner entièrement sans API OpenAI
   - L'extraction d'intention et de paramètres est faite par des règles simples

### Comment mettre à jour

1. **Mettre à jour les dépendances** :
   ```bash
   pip install -r requirements.txt
   ```

2. **Configurer votre API OpenAI** :
   - Assurez-vous que votre fichier `.env` contient une clé API OpenAI valide
   - Ou activez le mode démo si vous ne voulez pas utiliser d'API OpenAI

3. **Tester le système** :
   ```bash
   python main.py
   ```

### Nouvelles fonctionnalités

- **Mode sans connexion SSE** :
  Les clients peuvent maintenant appeler directement les outils via API REST
  sans nécessiter de connexion SSE préalable.

- **Meilleure compatibilité client** :
  L'API expose désormais ses endpoints sous plusieurs formats
  pour une meilleure compatibilité avec différents clients MCP.

### Problèmes connus

- Certains clients peuvent avoir des problèmes avec les connexions SSE.
  Si c'est le cas, utilisez l'approche directe via l'endpoint `/command/sse`
  avec un client ID arbitraire.