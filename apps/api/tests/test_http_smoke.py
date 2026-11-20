"""Real TCP HTTP smoke; no broker credentials, only the internal fake gateway."""
import socket
import threading
import time

import httpx
import uvicorn

from app.main import app, settings


def test_loopback_http_auth_and_authorized_sandbox(monkeypatch, loopback_connector):
    monkeypatch.setattr(settings, 'api_tokens', {'synthetic-http-token': 'local-operator'})
    monkeypatch.setattr(settings, 'broker_provider', 'internal_sandbox')
    monkeypatch.setattr(settings, 'broker_mode', 'sandbox')
    monkeypatch.setattr(settings, 'enable_paid_models', False)
    # Fail immediately if an unexpected provider path is reached.
    def forbidden(*args, **kwargs):
        raise AssertionError('Smoke must not call an external provider')
    monkeypatch.setattr('app.trading._alpaca_request', forbidden)
    monkeypatch.setattr('openai.AsyncOpenAI', forbidden)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(('127.0.0.1', 0))
        listener.listen(16)
        permitted_address = listener.getsockname()
        def smoke_connect(sock, address):
            assert address == permitted_address, 'Only this smoke listener is permitted'
            return loopback_connector(sock, address)
        monkeypatch.setattr(socket.socket, 'connect', smoke_connect)
        server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', log_level='warning'))
        thread = threading.Thread(target=server.run, kwargs={'sockets': [listener]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 5
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.01)
            assert server.started
            with httpx.Client(base_url=f'http://127.0.0.1:{listener.getsockname()[1]}', trust_env=False) as client:
                assert client.get('/health').status_code == 200
                assert client.get('/trading/status').status_code == 401
                client.headers['Authorization'] = 'Bearer synthetic-http-token'
                assert client.get('/trading/status').json()['provider'] == 'internal_sandbox'
                body = {'symbol': 'SPY', 'side': 'buy', 'quantity': 1}
                preview = client.post('/trading/orders/preview', json=body)
                assert preview.status_code == 200
                approved = preview.json()
                assert approved['accepted']
                body.update(approval_token=approved['approval_token'], confirmation_phrase=approved['confirmation_phrase'])
                receipt = client.post('/trading/orders', json=body)
                assert receipt.status_code == 201
                assert receipt.json()['status'] == 'accepted_sandbox'
        finally:
            server.should_exit = True
            thread.join(timeout=5)
            assert not thread.is_alive()
