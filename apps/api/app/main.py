from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.security import principal, issue_approval, reserve_order, reserve_research, release_research
from app.ai import research_chat
from app.backtester import BacktestError, run_backtest
from app.config import get_settings
from app.data_provider import DataProviderError, bars_to_models, get_sample_bars, list_symbols
from app.trading import (
    TradingGatewayError,
    build_status,
    get_account,
    get_positions,
    preview_order,
    submit_order,
)
from app.models import (
    AccountSnapshot,
    BacktestRequest,
    BacktestResult,
    Bar,
    HealthResponse,
    OrderIntent,
    OrderPreview,
    OrderReceipt,
    PositionSnapshot,
    ResearchRequest,
    ResearchResponse,
    Symbol,
    TradingStatusResponse,
)

settings = get_settings()

app = FastAPI(
    title="ai-quant-lab API",
    version="0.1.0",
    description="AI quant trading API with guarded broker gateway, risk precheck, and AI research support.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BACKTESTS: dict[str, BacktestResult] = {}
BACKTEST_OWNERS: dict[str, str] = {}


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="ai-quant-lab-api")


@app.get("/symbols", response_model=list[Symbol])
def symbols() -> list[Symbol]:
    return list_symbols()


@app.get("/data/bars", response_model=list[Bar])
def bars(
    symbol: str = Query(min_length=1),
    start: str = Query(pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end: str = Query(pattern=r"^\d{4}-\d{2}-\d{2}$"),
    timeframe: str = "1d",
) -> list[Bar]:
    try:
        frame = get_sample_bars(symbol=symbol, start=_parse_date(start), end=_parse_date(end), timeframe=timeframe)
        return bars_to_models(frame)
    except DataProviderError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/backtests", response_model=BacktestResult, status_code=201)
def create_backtest(request: BacktestRequest, subject: str = Depends(principal)) -> BacktestResult:
    if settings.market_data_provider != "sample":
        raise HTTPException(
            status_code=501,
            detail="Only the sample market data provider is implemented in v1",
        )
    try:
        symbol = request.symbols[0].upper()
        frame = get_sample_bars(symbol=symbol, start=request.start, end=request.end, timeframe=request.timeframe)
        normalized_request = request.model_copy(update={"symbols": [symbol]})
        result = run_backtest(normalized_request, frame)
        BACKTESTS[result.id] = result
        BACKTEST_OWNERS[result.id] = subject
        return result
    except (DataProviderError, BacktestError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/backtests/{backtest_id}", response_model=BacktestResult)
def get_backtest(backtest_id: str, subject: str = Depends(principal)) -> BacktestResult:
    if BACKTEST_OWNERS.get(backtest_id) != subject:
        raise HTTPException(403, "Backtest not authorized")
    result = BACKTESTS.get(backtest_id)
    if not result:
        raise HTTPException(status_code=404, detail="Backtest not found")
    return result


@app.get("/trading/status", response_model=TradingStatusResponse)
def trading_status(subject: str = Depends(principal)) -> TradingStatusResponse:
    return build_status(settings)


@app.get("/trading/account", response_model=AccountSnapshot)
def trading_account(subject: str = Depends(principal)) -> AccountSnapshot:
    try:
        return get_account(settings)
    except TradingGatewayError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error


@app.get("/trading/positions", response_model=list[PositionSnapshot])
def trading_positions(subject: str = Depends(principal)) -> list[PositionSnapshot]:
    try:
        return get_positions(settings)
    except TradingGatewayError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error


@app.post("/trading/orders/preview", response_model=OrderPreview)
def trading_order_preview(request: OrderIntent, subject: str = Depends(principal)) -> OrderPreview:
    try:
        preview = preview_order(request, settings)
        if preview.accepted:
            preview.approval_token = issue_approval(request, settings, subject)
        return preview
    except TradingGatewayError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error


@app.post("/trading/orders", response_model=OrderReceipt, status_code=201)
def trading_order_submit(request: OrderIntent, subject: str = Depends(principal)) -> OrderReceipt:
    try:
        preview = preview_order(request, settings)
        if not preview.accepted or request.confirmation_phrase != preview.confirmation_phrase:
            raise HTTPException(400, "确认短语不匹配或风控未通过")
        # Shared gateway risk checks reject all broker sells and market buys.
        # This ledger reserves intent notional, not reconciled execution amounts.
        notional = max(preview.estimated_notional, (request.limit_price or 0) * request.quantity)
        reserve_order(request, settings, subject, notional)
        return submit_order(request, settings)
    except TradingGatewayError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error


@app.post("/research/chat", response_model=ResearchResponse)
async def research(request: ResearchRequest, subject: str = Depends(principal)) -> ResearchResponse:
    backtest = None
    if request.backtest_id:
        if BACKTEST_OWNERS.get(request.backtest_id) != subject:
            raise HTTPException(403, "Backtest not authorized")
        backtest = BACKTESTS.get(request.backtest_id)
        if not backtest:
            raise HTTPException(status_code=404, detail="Backtest not found")
    lease = reserve_research(settings)
    try:
        return await research_chat(request=request, settings=settings, backtest=backtest)
    finally:
        release_research(settings, lease)


def _parse_date(value: str):
    from datetime import date

    return date.fromisoformat(value)
