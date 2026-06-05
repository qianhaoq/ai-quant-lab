from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


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
