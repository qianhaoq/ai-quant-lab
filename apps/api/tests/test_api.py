from fastapi.testclient import TestClient
import httpx
import pytest

from app.config import Settings
from app.main import app
from app.models import OrderIntent
from app.trading import TradingGatewayError, build_status, get_account, get_positions, submit_order


client = TestClient(app)


class FakeAlpacaResponse:
    def __init__(self, payload: dict | list | None, status_code: int = 200, text: str = "") -> None:
        self.payload = payload
        self.status_code = status_code
        self.text = text
        self.content = b"1" if payload is not None or text else b""

    def json(self):
        if self.payload is None:
            raise ValueError("No JSON body")
        return self.payload


def alpaca_paper_settings() -> Settings:
    return Settings(
        broker_provider="alpaca",
        broker_mode="alpaca_paper",
        alpaca_api_key_id="paper-key",
        alpaca_api_secret_key="paper-secret",
    )


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ai-quant-lab-api"}


def test_symbols() -> None:
    response = client.get("/symbols")
    assert response.status_code == 200
    symbols = [item["symbol"] for item in response.json()]
    assert symbols == ["SPY", "QQQ", "AAPL"]


def test_get_sample_bars() -> None:
    response = client.get("/data/bars?symbol=SPY&start=2024-01-02&end=2024-01-10&timeframe=1d")
    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["symbol"] == "SPY"
    assert len(payload) == 7


def test_invalid_symbol_returns_400() -> None:
    response = client.get("/data/bars?symbol=NOPE&start=2024-01-02&end=2024-01-10&timeframe=1d")
    assert response.status_code == 400
    assert "Unsupported symbol" in response.json()["detail"]


def test_backtest_strategies_return_required_metrics() -> None:
    for strategy in ["buy_and_hold", "moving_average_crossover", "rsi_mean_reversion"]:
        response = client.post(
            "/backtests",
            json={
                "symbols": ["SPY"],
                "start": "2023-01-03",
                "end": "2024-12-31",
                "initial_cash": 100000,
                "strategy": strategy,
                "params": {},
            },
        )
        assert response.status_code == 201
        metrics = response.json()["metrics"]
        assert set(metrics) == {
            "total_return",
            "cagr",
            "volatility",
            "sharpe",
            "max_drawdown",
            "win_rate",
            "trade_count",
        }
        assert isinstance(metrics["trade_count"], int)


def test_buy_and_hold_snapshot() -> None:
    response = client.post(
        "/backtests",
        json={
            "symbols": ["SPY"],
            "start": "2023-01-03",
            "end": "2024-12-31",
            "initial_cash": 100000,
            "strategy": "buy_and_hold",
            "params": {},
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["metrics"]["total_return"] == 0.294872
    assert payload["metrics"]["trade_count"] == 1
    assert payload["equity_curve"][0]["equity"] == 100000


def test_unknown_strategy_is_rejected() -> None:
    response = client.post(
        "/backtests",
        json={
            "symbols": ["SPY"],
            "start": "2024-01-02",
            "end": "2024-01-10",
            "initial_cash": 100000,
            "strategy": "magic",
            "params": {},
        },
    )
    assert response.status_code == 422


def test_research_chat_uses_mock_without_openai_key() -> None:
    backtest = client.post(
        "/backtests",
        json={
            "symbols": ["SPY"],
            "start": "2024-01-02",
            "end": "2024-03-29",
            "initial_cash": 100000,
            "strategy": "buy_and_hold",
            "params": {},
        },
    ).json()
    response = client.post(
        "/research/chat",
        json={"question": "What should I inspect next?", "backtest_id": backtest["id"]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["used_mock"] is True
    assert "交易研究摘要" in payload["answer"]


def test_trading_status_defaults_to_internal_sandbox() -> None:
    response = client.get("/trading/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "internal_sandbox"
    assert payload["mode"] == "sandbox"
    assert payload["broker_connected"] is True
    assert payload["trading_enabled"] is True
    assert payload["requires_confirmation"] is True
    assert payload["allowed_symbols"] == ["SPY", "QQQ", "AAPL"]


def test_trading_account_and_positions_use_sandbox_snapshots() -> None:
    account = client.get("/trading/account")
    positions = client.get("/trading/positions")
    assert account.status_code == 200
    assert positions.status_code == 200
    assert account.json()["account_id"] == "internal-sandbox"
    assert [item["symbol"] for item in positions.json()] == ["SPY", "QQQ"]


def test_order_preview_accepts_valid_sandbox_order() -> None:
    response = client.post(
        "/trading/orders/preview",
        json={"symbol": "SPY", "side": "buy", "quantity": 2, "order_type": "market", "time_in_force": "day"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["broker_provider"] == "internal_sandbox"
    assert payload["confirmation_phrase"] == "确认提交 买入 2 SPY"
    assert payload["estimated_notional"] > 0


def test_order_preview_rejects_unknown_symbol() -> None:
    response = client.post(
        "/trading/orders/preview",
        json={"symbol": "NOPE", "side": "buy", "quantity": 1, "order_type": "market", "time_in_force": "day"},
    )
    assert response.status_code == 400
    assert "Unsupported symbol" in response.json()["detail"]


def test_order_submit_requires_confirmation_phrase() -> None:
    response = client.post(
        "/trading/orders",
        json={
            "symbol": "SPY",
            "side": "buy",
            "quantity": 2,
            "order_type": "market",
            "time_in_force": "day",
            "confirmation_phrase": "确认提交 买入 3 SPY",
        },
    )
    assert response.status_code == 400
    assert "确认短语不匹配" in response.json()["detail"]


def test_order_submit_accepts_internal_sandbox_order() -> None:
    response = client.post(
        "/trading/orders",
        json={
            "symbol": "SPY",
            "side": "buy",
            "quantity": 2,
            "order_type": "market",
            "time_in_force": "day",
            "confirmation_phrase": "确认提交 买入 2 SPY",
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "accepted_sandbox"
    assert payload["broker_order_id"] is None
    assert "未发送到真实券商" in payload["message"]


def test_alpaca_paper_status_is_enabled_with_credentials() -> None:
    payload = build_status(alpaca_paper_settings())
    assert payload.provider == "alpaca"
    assert payload.mode == "alpaca_paper"
    assert payload.broker_connected is True
    assert payload.trading_enabled is True
    assert payload.live_trading_enabled is False


def test_alpaca_paper_account_and_positions_use_mocked_http(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict] = []

    def fake_get(url: str, headers: dict, timeout: int):
        calls.append({"url": url, "headers": headers, "timeout": timeout})
        if url.endswith("/v2/account"):
            return FakeAlpacaResponse(
                {
                    "id": "paper-account",
                    "cash": "100000.50",
                    "buying_power": "200001.00",
                    "portfolio_value": "125000.75",
                    "status": "ACTIVE",
                }
            )
        if url.endswith("/v2/positions"):
            return FakeAlpacaResponse(
                [
                    {
                        "symbol": "SPY",
                        "qty": "3",
                        "market_value": "1500",
                        "avg_entry_price": "480",
                        "unrealized_pl": "60",
                        "unrealized_plpc": "0.041667",
                    }
                ]
            )
        return FakeAlpacaResponse({"message": "not found"}, status_code=404)

    monkeypatch.setattr("app.trading.httpx.get", fake_get)

    account = get_account(alpaca_paper_settings())
    positions = get_positions(alpaca_paper_settings())

    assert account.account_id == "paper-account"
    assert account.cash == 100000.50
    assert positions[0].symbol == "SPY"
    assert positions[0].quantity == 3
    assert positions[0].last_price == 500
    assert calls[0]["url"] == "https://paper-api.alpaca.markets/v2/account"
    assert calls[0]["headers"]["APCA-API-KEY-ID"] == "paper-key"
    assert calls[0]["headers"]["APCA-API-SECRET-KEY"] == "paper-secret"


def test_alpaca_paper_order_submission_uses_risk_and_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict] = []

    def fake_post(url: str, headers: dict, json: dict, timeout: int):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeAlpacaResponse({"id": "alpaca-order-1", "status": "accepted"})

    monkeypatch.setattr("app.trading.httpx.post", fake_post)

    receipt = submit_order(
        OrderIntent(
            symbol="SPY",
            side="buy",
            quantity=1,
            order_type="market",
            time_in_force="day",
            confirmation_phrase="确认提交 买入 1 SPY",
        ),
        alpaca_paper_settings(),
    )

    assert receipt.status == "accepted"
    assert receipt.broker_provider == "alpaca"
    assert receipt.broker_mode == "alpaca_paper"
    assert receipt.broker_order_id == "alpaca-order-1"
    assert calls == [
        {
            "url": "https://paper-api.alpaca.markets/v2/orders",
            "headers": {
                "APCA-API-KEY-ID": "paper-key",
                "APCA-API-SECRET-KEY": "paper-secret",
            },
            "json": {
                "symbol": "SPY",
                "qty": 1.0,
                "side": "buy",
                "type": "market",
                "time_in_force": "day",
            },
            "timeout": 10,
        }
    ]


def test_alpaca_submit_still_requires_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(url: str, headers: dict, json: dict, timeout: int):
        return FakeAlpacaResponse({"id": "should-not-submit", "status": "accepted"})

    monkeypatch.setattr("app.trading.httpx.post", fake_post)

    with pytest.raises(TradingGatewayError, match="确认短语不匹配"):
        submit_order(
            OrderIntent(
                symbol="SPY",
                side="buy",
                quantity=1,
                order_type="market",
                time_in_force="day",
                confirmation_phrase="确认提交 买入 2 SPY",
            ),
            alpaca_paper_settings(),
        )


def test_alpaca_http_errors_are_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, headers: dict, timeout: int):
        raise httpx.RequestError("paper endpoint unavailable")

    monkeypatch.setattr("app.trading.httpx.get", fake_get)

    with pytest.raises(TradingGatewayError, match="无法读取 Alpaca 账户快照：paper endpoint unavailable") as error:
        get_account(alpaca_paper_settings())
    assert error.value.status_code == 502


def test_alpaca_rejected_order_returns_broker_message(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(url: str, headers: dict, json: dict, timeout: int):
        return FakeAlpacaResponse({"message": "insufficient buying power"}, status_code=403)

    monkeypatch.setattr("app.trading.httpx.post", fake_post)

    with pytest.raises(TradingGatewayError, match="Alpaca 订单提交失败：insufficient buying power") as error:
        submit_order(
            OrderIntent(
                symbol="SPY",
                side="buy",
                quantity=1,
                order_type="market",
                time_in_force="day",
                confirmation_phrase="确认提交 买入 1 SPY",
            ),
            alpaca_paper_settings(),
        )
    assert error.value.status_code == 502
