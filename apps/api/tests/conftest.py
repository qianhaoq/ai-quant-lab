"""No inherited credentials or external network in tests."""
import os
import socket
import pytest

_SOCKET_CONNECT = socket.socket.connect

@pytest.fixture
def loopback_connector():
    """Original connector for the explicitly loopback-bound HTTP smoke only."""
    return _SOCKET_CONNECT

os.environ.clear()
os.environ.update({'API_TOKENS': '{"test-operator-token":"local-operator","test-other-token":"other"}', 'OPENAI_API_KEY': '', 'ALPACA_API_KEY_ID': '', 'ALPACA_API_SECRET_KEY': '', 'ENABLE_PAID_MODELS': 'false', 'BROKER_PROVIDER': 'internal_sandbox', 'BROKER_MODE': 'sandbox', 'ENABLE_LIVE_TRADING': 'false'})

from app.config import Settings
Settings.model_config["env_file"] = None

@pytest.fixture(autouse=True)
def isolated_safety(monkeypatch, tmp_path):
    from app.main import settings
    from app.config import Settings
    monkeypatch.setitem(Settings.model_config, 'env_file', None)
    for field in ('openai_api_key', 'alpaca_api_key_id', 'alpaca_api_secret_key'):
        monkeypatch.setattr(settings, field, None)
    monkeypatch.setattr(settings, 'safety_db_path', str(tmp_path / 'safety.sqlite3'))
    def blocked(*args, **kwargs):
        raise AssertionError('External network forbidden in tests')
    monkeypatch.setattr(socket.socket, 'connect', blocked)
