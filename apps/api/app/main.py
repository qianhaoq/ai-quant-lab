from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

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
def create_backtest(request: BacktestRequest) -> BacktestResult:
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
        return result
    except (DataProviderError, BacktestError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/backtests/{backtest_id}", response_model=BacktestResult)
def get_backtest(backtest_id: str) -> BacktestResult:
    result = BACKTESTS.get(backtest_id)
    if not result:
        raise HTTPException(status_code=404, detail="Backtest not found")
    return result


@app.get("/trading/status", response_model=TradingStatusResponse)
def trading_status() -> TradingStatusResponse:
    return build_status(settings)


@app.get("/trading/account", response_model=AccountSnapshot)
def trading_account() -> AccountSnapshot:
    try:
        return get_account(settings)
    except TradingGatewayError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error


@app.get("/trading/positions", response_model=list[PositionSnapshot])
def trading_positions() -> list[PositionSnapshot]:
    try:
        return get_positions(settings)
    except TradingGatewayError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error


@app.post("/trading/orders/preview", response_model=OrderPreview)
def trading_order_preview(request: OrderIntent) -> OrderPreview:
    try:
        return preview_order(request, settings)
    except TradingGatewayError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error


@app.post("/trading/orders", response_model=OrderReceipt, status_code=201)
def trading_order_submit(request: OrderIntent) -> OrderReceipt:
    try:
        return submit_order(request, settings)
    except TradingGatewayError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error


@app.post("/research/chat", response_model=ResearchResponse)
async def research(request: ResearchRequest) -> ResearchResponse:
    backtest = None
    if request.backtest_id:
        backtest = BACKTESTS.get(request.backtest_id)
        if not backtest:
            raise HTTPException(status_code=404, detail="Backtest not found")
    return await research_chat(request=request, settings=settings, backtest=backtest)


def _parse_date(value: str):
    from datetime import date

    return date.fromisoformat(value)
