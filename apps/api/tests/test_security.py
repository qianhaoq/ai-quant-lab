from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from app.main import app, settings, BACKTEST_OWNERS
from app.config import Settings
from app.security import reserve_research, release_research

client = TestClient(app, headers={'Authorization': 'Bearer test-operator-token'})
intent = {'symbol': 'SPY', 'side': 'buy', 'quantity': 1}


def approved(body=None):
    body = dict(body or intent)
    preview = client.post('/trading/orders/preview', json=body).json()
    return {**body, 'approval_token': preview['approval_token'], 'confirmation_phrase': preview['confirmation_phrase']}


@pytest.mark.parametrize('method,path,body', [
    ('get', '/trading/status', None), ('get', '/trading/account', None),
    ('get', '/trading/positions', None), ('post', '/trading/orders/preview', intent),
    ('post', '/trading/orders', intent), ('post', '/research/chat', {'question': 'hello'}),
    ('post', '/backtests', {}), ('get', '/backtests/other', None),
])
def test_authentication_and_account_authorization(method, path, body):
    anonymous = TestClient(app)
    assert anonymous.request(method, path, json=body).status_code == 401
    assert client.request(method, path, json=body, headers={'Authorization': 'Bearer test-other-token'}).status_code == 403
    assert client.request(method, path, json=body, headers={'X-Account-ID': 'someone-else'}).status_code == 403


def test_confirmation_binding_and_replay():
    body = approved()
    assert client.post('/trading/orders', json=intent).status_code == 400
    assert client.post('/trading/orders', json={**body, 'confirmation_phrase': 'wrong'}).status_code == 400
    for change in ({'quantity': 2}, {'symbol': 'QQQ'}, {'side': 'sell'}, {'time_in_force': 'gtc'}, {'rationale': 'changed'}, {'order_type': 'limit', 'limit_price': 100}):
        assert client.post('/trading/orders', json={**body, **change}).status_code == 400
    assert client.post('/trading/orders', json=body).status_code == 201
    assert client.post('/trading/orders', json=body).status_code == 400


def test_expired_and_subject_bound_approval(monkeypatch):
    from app import security
    body = approved()
    with monkeypatch.context() as scoped:
        scoped.setattr(settings, 'api_tokens', {'second': 'second'})
        scoped.setattr(settings, 'broker_owner_subject', 'second')
        assert client.post('/trading/orders', json=body, headers={'Authorization': 'Bearer second'}).status_code == 400
    body = approved()
    now = security.time.time()
    monkeypatch.setattr(security.time, 'time', lambda: now + 301)
    assert client.post('/trading/orders', json=body).status_code == 400


def test_cumulative_order_budget_and_parallel_replay(monkeypatch):
    monkeypatch.setattr(settings, 'safety_max_orders', 1)
    body = approved()
    with ThreadPoolExecutor(4) as pool:
        codes = list(pool.map(lambda _: client.post('/trading/orders', json=body).status_code, range(4)))
    assert codes.count(201) == 1
    assert client.post('/trading/orders', json=approved()).status_code == 429


def test_notional_budget_persists(monkeypatch):
    monkeypatch.setattr(settings, 'safety_max_notional', 1)
    assert client.post('/trading/orders', json=approved()).status_code == 429
    # Fresh Settings object still uses the same persistent ledger.
    monkeypatch.setattr(settings, 'safety_model_calls', 1)
    lease = reserve_research(settings)
    release_research(settings, lease)
    fresh = Settings(safety_db_path=settings.safety_db_path, safety_model_calls=1)
    with pytest.raises(Exception) as error:
        reserve_research(fresh)
    assert error.value.status_code == 429


def test_model_call_token_concurrency_limits(monkeypatch):
    monkeypatch.setattr(settings, 'safety_model_concurrency', 1)
    lease = reserve_research(settings)
    assert client.post('/research/chat', json={'question': 'hello'}).status_code == 429
    release_research(settings, lease)
    monkeypatch.setattr(settings, 'safety_model_total_tokens', 17000)
    assert client.post('/research/chat', json={'question': 'hello'}).status_code == 429


def test_model_parallel_limit(monkeypatch):
    monkeypatch.setattr(settings, 'safety_model_calls', 1)
    def attempt(_):
        try:
            return reserve_research(settings)
        except Exception as error:
            return error.status_code
    with ThreadPoolExecutor(4) as pool:
        results = list(pool.map(attempt, range(4)))
    assert results.count(429) == 3


def test_fake_llm_explicit_opt_in_output_and_failure_budget(monkeypatch):
    calls = []
    class FakeLLM:
        def __init__(self, **kwargs):
            assert kwargs['max_retries'] == 0
            self.chat = SimpleNamespace(completions=self)
        async def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='研究假设，仅供验证'))])
    monkeypatch.setattr('openai.AsyncOpenAI', FakeLLM)
    monkeypatch.setattr(settings, 'openai_api_key', 'fake-not-a-key')
    assert client.post('/research/chat', json={'question': 'hello'}).json()['used_mock']
    assert not calls
    monkeypatch.setattr(settings, 'enable_paid_models', True)
    monkeypatch.setattr(settings, 'safety_model_calls', 2)
    assert not client.post('/research/chat', json={'question': 'hello'}).json()['used_mock']
    assert calls[0]['max_tokens'] == 1000
    assert client.post('/research/chat', json={'question': 'hello'}).status_code == 429


def test_cross_subject_backtest_research():
    BACKTEST_OWNERS['foreign'] = 'other'
    assert client.get('/backtests/foreign').status_code == 403
    assert client.post('/research/chat', json={'question': 'hello', 'backtest_id': 'foreign'}).status_code == 403


def test_nonfinite_order_rejected():
    assert client.post('/trading/orders/preview', json={**intent, 'quantity': 'Infinity'}).status_code == 422


def test_fake_broker_api_authorization_and_approval(monkeypatch):
    calls = []
    from test_api import FakeAlpacaResponse
    def fake_get(url, **kwargs):
        calls.append(url)
        return FakeAlpacaResponse({'id': 'fake-account', 'cash': '1', 'buying_power': '1', 'portfolio_value': '1'})
    def fake_post(url, **kwargs):
        calls.append(url)
        return FakeAlpacaResponse({'id': 'fake-order', 'status': 'accepted'})
    monkeypatch.setattr('app.trading.httpx.get', fake_get)
    monkeypatch.setattr('app.trading.httpx.post', fake_post)
    monkeypatch.setattr(settings, 'broker_provider', 'alpaca')
    monkeypatch.setattr(settings, 'broker_mode', 'alpaca_paper')
    monkeypatch.setattr(settings, 'alpaca_api_key_id', 'fake-key')
    monkeypatch.setattr(settings, 'alpaca_api_secret_key', 'fake-secret')
    assert TestClient(app).get('/trading/account').status_code == 401
    assert client.get('/trading/account', headers={'Authorization': 'Bearer test-other-token'}).status_code == 403
    assert not calls
    assert client.get('/trading/account').json()['account_id'] == 'fake-account'
    body = approved({**intent, 'order_type': 'limit', 'limit_price': 100})
    assert client.post('/trading/orders', json=body).status_code == 201
    assert client.post('/trading/orders', json=body).status_code == 400
    assert len(calls) == 2
    monkeypatch.setattr(settings, 'broker_mode', 'alpaca_live')
    assert client.post('/trading/orders/preview', json=intent).json()['accepted'] is False


def test_failed_llm_is_not_retried_and_consumes_budget(monkeypatch):
    calls = []
    class FailingLLM:
        def __init__(self, **kwargs):
            assert kwargs['max_retries'] == 0
            self.chat = SimpleNamespace(completions=self)
        async def create(self, **kwargs):
            calls.append(kwargs)
            raise RuntimeError('fake provider failed')
    monkeypatch.setattr('openai.AsyncOpenAI', FailingLLM)
    monkeypatch.setattr(settings, 'openai_api_key', 'fake-key')
    monkeypatch.setattr(settings, 'enable_paid_models', True)
    monkeypatch.setattr(settings, 'safety_model_calls', 1)
    assert client.post('/research/chat', json={'question': 'hello'}).json()['used_mock']
    assert client.post('/research/chat', json={'question': 'hello'}).status_code == 429
    assert len(calls) == 1


def test_notional_accumulates_across_tokens_and_new_approvals(monkeypatch):
    monkeypatch.setattr(settings, 'safety_max_notional', 150)
    body = {**intent, 'order_type': 'limit', 'limit_price': 100}
    first = approved(body)
    assert client.post('/trading/orders', json=first).status_code == 201
    monkeypatch.setattr(settings, 'api_tokens', {'rotated': 'local-operator', 'test-operator-token': 'local-operator'})
    second = approved(body)
    assert client.post('/trading/orders', json=second, headers={'Authorization': 'Bearer rotated'}).status_code == 429


def test_new_preview_invalidates_old_and_mode_is_bound(monkeypatch):
    first = approved()
    second = approved()
    assert client.post('/trading/orders', json=first).status_code == 400
    monkeypatch.setattr(settings, 'broker_mode', 'alpaca_paper')
    assert client.post('/trading/orders', json=second).status_code == 400
