from datetime import date, datetime, timezone
from uuid import uuid4

import httpx

from app.config import Settings
from app.data_provider import DataProviderError, get_sample_bars, symbol_exists
from app.models import (
    AccountSnapshot,
    BrokerMode,
    OrderIntent,
    OrderPreview,
    OrderReceipt,
    PositionSnapshot,
    RiskCheck,
    TradingStatusResponse,
)


class TradingGatewayError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


ORDERS: dict[str, OrderReceipt] = {}


def build_status(settings: Settings) -> TradingStatusResponse:
    provider = _broker_provider(settings)
    mode = _broker_mode(settings)
    broker_connected = provider == "internal_sandbox" or _alpaca_credentials_present(settings)
    trading_enabled = provider == "internal_sandbox" or (
        provider == "alpaca" and broker_connected and (mode != "alpaca_live" or settings.enable_live_trading)
    )
    if provider == "alpaca" and mode == "alpaca_live" and not settings.enable_live_trading:
        message = "Alpaca live 已配置为目标模式，但真实交易开关未开启。"
    elif provider == "alpaca" and not broker_connected:
        message = "Alpaca 交易网关未连接：缺少 API key。"
    elif provider == "internal_sandbox":
        message = "内部沙箱已就绪；订单不会发送到真实券商。"
    else:
        message = "交易网关已就绪；订单仍需风控预检和人工确认。"
    return TradingStatusResponse(
        provider=provider,
        mode=mode,
        broker_connected=broker_connected,
        trading_enabled=trading_enabled,
        live_trading_enabled=settings.enable_live_trading and mode == "alpaca_live",
        requires_confirmation=True,
        allowed_symbols=settings.trade_symbols,
        max_order_notional=settings.max_order_notional,
        max_order_quantity=settings.max_order_quantity,
        message=message,
    )


def get_account(settings: Settings) -> AccountSnapshot:
    provider = _broker_provider(settings)
    if provider == "alpaca":
        return _get_alpaca_account(settings)
    positions_value = sum(position.market_value for position in _internal_positions())
    cash = 92_500.0
    return AccountSnapshot(
        account_id="internal-sandbox",
        cash=round(cash, 2),
        buying_power=round(cash * 2, 2),
        portfolio_value=round(cash + positions_value, 2),
        status="sandbox",
    )


def get_positions(settings: Settings) -> list[PositionSnapshot]:
    provider = _broker_provider(settings)
    if provider == "alpaca":
        return _get_alpaca_positions(settings)
    return _internal_positions()


def preview_order(intent: OrderIntent, settings: Settings) -> OrderPreview:
    normalized_intent = intent.model_copy(update={"symbol": intent.symbol.upper()})
    provider = _broker_provider(settings)
    mode = _broker_mode(settings)
    estimated_price = _estimated_price(normalized_intent)
    estimated_notional = round(estimated_price * normalized_intent.quantity, 2)
    checks = _risk_checks(
        intent=normalized_intent,
        settings=settings,
        provider=provider,
        mode=mode,
        estimated_notional=estimated_notional,
    )
    accepted = all(check.passed for check in checks)
    side_text = "买入" if normalized_intent.side == "buy" else "卖出"
    confirmation_phrase = f"确认提交 {side_text} {normalized_intent.quantity:g} {normalized_intent.symbol}"
    message = "预检通过，等待人工确认。" if accepted else "预检未通过，订单不会提交。"
    return OrderPreview(
        accepted=accepted,
        broker_provider=provider,
        broker_mode=mode,
        symbol=normalized_intent.symbol,
        side=normalized_intent.side,
        quantity=normalized_intent.quantity,
        order_type=normalized_intent.order_type,
        time_in_force=normalized_intent.time_in_force,
        estimated_price=estimated_price,
        estimated_notional=estimated_notional,
        risk_checks=checks,
        confirmation_required=True,
        confirmation_phrase=confirmation_phrase,
        message=message,
    )


def submit_order(intent: OrderIntent, settings: Settings) -> OrderReceipt:
    preview = preview_order(intent, settings)
    if not preview.accepted:
        raise TradingGatewayError(preview.message, status_code=400)
    if intent.confirmation_phrase != preview.confirmation_phrase:
        raise TradingGatewayError("确认短语不匹配，订单未提交。", status_code=400)
    if preview.broker_provider == "alpaca":
        return _submit_alpaca_order(intent.model_copy(update={"symbol": preview.symbol}), preview, settings)
    return _submit_internal_sandbox_order(preview)


def _risk_checks(
    intent: OrderIntent,
    settings: Settings,
    provider: str,
    mode: BrokerMode,
    estimated_notional: float,
) -> list[RiskCheck]:
    checks = [
        RiskCheck(
            name="标的白名单",
            passed=intent.symbol in settings.trade_symbols and symbol_exists(intent.symbol),
            severity="blocker",
            message=f"{intent.symbol} 必须在允许交易标的内，且当前数据源可以识别。",
        ),
        RiskCheck(
            name="订单数量上限",
            passed=intent.quantity <= settings.max_order_quantity,
            severity="blocker",
            message=f"数量 {intent.quantity:g} 不能超过单笔上限 {settings.max_order_quantity:g}。",
        ),
        RiskCheck(
            name="名义金额上限",
            passed=estimated_notional <= settings.max_order_notional,
            severity="blocker",
            message=f"预估名义金额 ${estimated_notional:,.2f} 不能超过 ${settings.max_order_notional:,.2f}。",
        ),
        RiskCheck(
            name="交易网关状态",
            passed=provider in {"internal_sandbox", "alpaca"},
            severity="blocker",
            message=f"当前交易网关：{provider}。",
        ),
        RiskCheck(
            name="人工确认",
            passed=True,
            severity="info",
            message="提交订单前必须输入预检返回的确认短语；AI 不能绕过此步骤。",
        ),
    ]
    if provider == "alpaca":
        checks.append(
            RiskCheck(
                name="券商凭证",
                passed=_alpaca_credentials_present(settings),
                severity="blocker",
                message="Alpaca 模式需要 ALPACA_API_KEY_ID 和 ALPACA_API_SECRET_KEY。",
            )
        )
    if mode == "alpaca_live":
        checks.append(
            RiskCheck(
                name="Live 交易开关",
                passed=settings.enable_live_trading,
                severity="blocker",
                message="真实交易必须显式设置 ENABLE_LIVE_TRADING=true。",
            )
        )
    if provider == "internal_sandbox" and intent.side == "sell":
        held_quantity = _held_quantity(intent.symbol)
        checks.append(
            RiskCheck(
                name="沙箱持仓校验",
                passed=intent.quantity <= held_quantity,
                severity="blocker",
                message=f"内部沙箱当前持有 {held_quantity:g} 股 {intent.symbol}。",
            )
        )
    return checks


def _submit_internal_sandbox_order(preview: OrderPreview) -> OrderReceipt:
    receipt = OrderReceipt(
        id=f"sandbox_{uuid4().hex[:12]}",
        status="accepted_sandbox",
        broker_provider=preview.broker_provider,
        broker_mode=preview.broker_mode,
        symbol=preview.symbol,
        side=preview.side,
        quantity=preview.quantity,
        order_type=preview.order_type,
        time_in_force=preview.time_in_force,
        submitted_at=datetime.now(timezone.utc).isoformat(),
        estimated_notional=preview.estimated_notional,
        message="订单已进入内部沙箱；未发送到真实券商。",
    )
    ORDERS[receipt.id] = receipt
    return receipt


def _submit_alpaca_order(intent: OrderIntent, preview: OrderPreview, settings: Settings) -> OrderReceipt:
    base_url = _alpaca_base_url(preview.broker_mode)
    body: dict[str, str | float] = {
        "symbol": intent.symbol,
        "qty": intent.quantity,
        "side": intent.side,
        "type": intent.order_type,
        "time_in_force": intent.time_in_force,
    }
    if intent.order_type == "limit" and intent.limit_price is not None:
        body["limit_price"] = intent.limit_price
    response = _alpaca_request(
        "post",
        f"{base_url}/v2/orders",
        settings=settings,
        error_prefix="Alpaca 订单提交失败",
        json=body,
    )
    payload = response.json()
    receipt = OrderReceipt(
        id=f"alpaca_{uuid4().hex[:12]}",
        status=str(payload.get("status", "submitted")),
        broker_provider=preview.broker_provider,
        broker_mode=preview.broker_mode,
        symbol=preview.symbol,
        side=preview.side,
        quantity=preview.quantity,
        order_type=preview.order_type,
        time_in_force=preview.time_in_force,
        submitted_at=datetime.now(timezone.utc).isoformat(),
        estimated_notional=preview.estimated_notional,
        broker_order_id=str(payload.get("id")) if payload.get("id") else None,
        message="订单已提交到 Alpaca；请在券商后台复核状态。",
    )
    ORDERS[receipt.id] = receipt
    return receipt


def _get_alpaca_account(settings: Settings) -> AccountSnapshot:
    _require_alpaca_credentials(settings)
    response = _alpaca_request(
        "get",
        f"{_alpaca_base_url(_broker_mode(settings))}/v2/account",
        settings=settings,
        error_prefix="无法读取 Alpaca 账户快照",
    )
    payload = response.json()
    return AccountSnapshot(
        account_id=str(payload.get("id", "alpaca")),
        cash=float(payload.get("cash", 0)),
        buying_power=float(payload.get("buying_power", 0)),
        portfolio_value=float(payload.get("portfolio_value", 0)),
        status=str(payload.get("status", "unknown")),
    )


def _get_alpaca_positions(settings: Settings) -> list[PositionSnapshot]:
    _require_alpaca_credentials(settings)
    response = _alpaca_request(
        "get",
        f"{_alpaca_base_url(_broker_mode(settings))}/v2/positions",
        settings=settings,
        error_prefix="无法读取 Alpaca 持仓",
    )
    positions = []
    for item in response.json():
        quantity = float(item.get("qty", 0))
        market_value = float(item.get("market_value", 0))
        average_entry_price = float(item.get("avg_entry_price", 0))
        last_price = market_value / quantity if quantity else average_entry_price
        positions.append(
            PositionSnapshot(
                symbol=str(item.get("symbol", "")),
                quantity=quantity,
                market_value=market_value,
                average_entry_price=average_entry_price,
                last_price=round(last_price, 2),
                unrealized_pl=float(item.get("unrealized_pl", 0)),
                unrealized_pl_pct=float(item.get("unrealized_plpc", 0)),
            )
        )
    return positions


def _internal_positions() -> list[PositionSnapshot]:
    holdings = {"SPY": (25.0, 438.0), "QQQ": (12.0, 350.0)}
    positions = []
    for symbol, (quantity, average_entry_price) in holdings.items():
        last_price = _sample_last_close(symbol)
        market_value = round(quantity * last_price, 2)
        unrealized_pl = round((last_price - average_entry_price) * quantity, 2)
        positions.append(
            PositionSnapshot(
                symbol=symbol,
                quantity=quantity,
                market_value=market_value,
                average_entry_price=average_entry_price,
                last_price=last_price,
                unrealized_pl=unrealized_pl,
                unrealized_pl_pct=round((last_price / average_entry_price) - 1, 6),
            )
        )
    return positions


def _estimated_price(intent: OrderIntent) -> float:
    if intent.order_type == "limit" and intent.limit_price is not None:
        return round(intent.limit_price, 2)
    return _sample_last_close(intent.symbol)


def _sample_last_close(symbol: str) -> float:
    try:
        frame = get_sample_bars(symbol=symbol, start=date(2024, 12, 20), end=date(2024, 12, 31), timeframe="1d")
    except DataProviderError as error:
        raise TradingGatewayError(str(error), status_code=400) from error
    return float(frame.iloc[-1].close)


def _held_quantity(symbol: str) -> float:
    for position in _internal_positions():
        if position.symbol == symbol:
            return position.quantity
    return 0.0


def _broker_provider(settings: Settings) -> str:
    provider = settings.broker_provider.strip().lower()
    if provider in {"alpaca_paper", "alpaca_live"}:
        return "alpaca"
    if provider == "alpaca":
        return provider
    return "internal_sandbox"


def _broker_mode(settings: Settings) -> BrokerMode:
    raw_mode = settings.broker_mode.strip().lower()
    provider = settings.broker_provider.strip().lower()
    if _broker_provider(settings) == "internal_sandbox":
        return "sandbox"
    if provider == "alpaca_paper":
        return "alpaca_paper"
    if provider == "alpaca_live":
        return "alpaca_live"
    if raw_mode in {"alpaca_paper", "paper"}:
        return "alpaca_paper"
    if raw_mode in {"alpaca_live", "live"}:
        return "alpaca_live"
    return "sandbox"


def _alpaca_base_url(mode: BrokerMode) -> str:
    if mode == "alpaca_live":
        return "https://api.alpaca.markets"
    return "https://paper-api.alpaca.markets"


def _alpaca_credentials_present(settings: Settings) -> bool:
    return bool(settings.alpaca_api_key_id and settings.alpaca_api_secret_key)


def _require_alpaca_credentials(settings: Settings) -> None:
    if not _alpaca_credentials_present(settings):
        raise TradingGatewayError("缺少 Alpaca API key，无法连接券商网关。", status_code=400)


def _alpaca_headers(settings: Settings) -> dict[str, str]:
    _require_alpaca_credentials(settings)
    return {
        "APCA-API-KEY-ID": settings.alpaca_api_key_id or "",
        "APCA-API-SECRET-KEY": settings.alpaca_api_secret_key or "",
    }


def _alpaca_request(method: str, url: str, settings: Settings, error_prefix: str, **kwargs) -> httpx.Response:
    try:
        if method == "get":
            response = httpx.get(url, headers=_alpaca_headers(settings), timeout=10, **kwargs)
        elif method == "post":
            response = httpx.post(url, headers=_alpaca_headers(settings), timeout=10, **kwargs)
        else:
            raise TradingGatewayError(f"Unsupported Alpaca method: {method}", status_code=500)
    except httpx.HTTPError as error:
        raise TradingGatewayError(f"{error_prefix}：{error}", status_code=502) from error

    if response.status_code >= 400:
        raise TradingGatewayError(f"{error_prefix}：{_response_error_detail(response)}", status_code=502)
    return response


def _response_error_detail(response: httpx.Response) -> str:
    if response.content:
        try:
            payload = response.json()
        except ValueError:
            return response.text
        if isinstance(payload, dict):
            detail = payload.get("message") or payload.get("detail") or payload.get("error")
            if detail:
                return str(detail)
        return str(payload)
    return response.text or f"HTTP {response.status_code}"
