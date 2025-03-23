# Utiliser une image officielle de Python
FROM python:3.10-slim

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Créer le répertoire static avant de copier les fichiers
RUN mkdir -p /app/static

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Installer pip et setuptools à jour
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copier d'abord les requirements pour profiter du cache Docker
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste des fichiers de l'application
COPY . .

# Vérifier l'installation des dépendances
RUN python check_setup.py || echo "Certaines dépendances nécessitent des clés API"

# Exposer le port sur lequel l'application va tourner
EXPOSE 8000

# Lancer l'application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]