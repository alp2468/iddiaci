"""
Pytest configuration and fixtures
"""
import pytest
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Set environment variable for tests
os.environ.setdefault('REACT_APP_BACKEND_URL', 'https://coupon-bot.preview.emergentagent.com')

@pytest.fixture
def base_url():
    """Return base URL for API tests"""
    return os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
