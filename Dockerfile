FROM python:3.11-slim as builder

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

# Stage final
FROM python:3.11-slim

WORKDIR /app

# Copie des dépendances du builder
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/

# Copie du code source
COPY . .

# Variables d'environnement
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV HOST=0.0.0.0

# Exposition du port
EXPOSE 8000

# Commande de démarrage
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]