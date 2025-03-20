FROM python:3.11-slim

WORKDIR /app

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copie des fichiers de dépendances
COPY requirements.txt .

# Installation des dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Variables d'environnement
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV HOST=0.0.0.0
ENV PYTHONDONTWRITEBYTECODE=1

# Exposition du port
EXPOSE 8000

# Le code source sera monté comme volume
# La commande est définie dans docker-compose.yml