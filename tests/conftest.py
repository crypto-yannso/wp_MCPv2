import pytest
import os
import sys
from unittest.mock import MagicMock

# Ajouter le répertoire racine au PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock Supabase avant l'importation
mock_supabase = MagicMock()
sys.modules['supabase'] = mock_supabase

# Fixtures globales
@pytest.fixture(autouse=True)
def env_setup():
    """Configure les variables d'environnement pour les tests"""
    os.environ['TESTING'] = 'true'
    os.environ.setdefault('SUPABASE_URL', 'https://test.supabase.co')
    os.environ.setdefault('SUPABASE_KEY', 'test-key')
    os.environ.setdefault('SUPABASE_SERVICE_ROLE_KEY', 'test-service-key')
    os.environ.setdefault('STRIPE_SECRET_KEY', 'test-stripe-key')
    os.environ.setdefault('STRIPE_WEBHOOK_SECRET', 'test-webhook-secret') 