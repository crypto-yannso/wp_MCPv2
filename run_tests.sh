#!/bin/bash

# Nettoyer les conteneurs et images existants
docker-compose down
docker-compose rm -f test

# Reconstruire l'image de test
docker-compose build test

# Exécuter tous les tests
docker-compose run --rm test pytest -v

# Exécuter uniquement les tests unitaires
# docker-compose run --rm test pytest -v -m unit

# Exécuter avec couverture de code
# docker-compose run --rm test pytest -v --cov=api --cov-report=term-missing

# Exécuter un fichier de test spécifique
# docker-compose run --rm test pytest tests/unit/test_database.py -v

# Exécuter avec debug
# docker-compose run --rm test pytest -v --pdb 