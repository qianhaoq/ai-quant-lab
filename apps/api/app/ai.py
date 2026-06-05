from app.config import Settings
from app.models import BacktestResult, ResearchRequest, ResearchResponse


def mock_research_response(request: ResearchRequest, backtest: BacktestResult | None) -> ResearchResponse:
    if backtest:
        metrics = backtest.metrics
        answer = (
            "Research-only summary: this backtest can be used to form hypotheses, not trading advice. "
            f"For {backtest.symbol}, the selected strategy produced total return "
            f"{metrics.total_return:.2%}, Sharpe {metrics.sharpe:.2f}, and max drawdown "
            f"{metrics.max_drawdown:.2%}. The next useful step is to compare the result against "
            "buy-and-hold and test nearby parameter values on a different date range."
        )
    else:
        answer = (
            "Research-only summary: start with a simple baseline such as buy-and-hold, then compare "
            "a rule-based strategy against the same symbol and date range. Treat any AI-generated idea "
            "as a hypothesis that must be validated by out-of-sample tests."
        )
    return ResearchResponse(
        answer=answer,
        suggested_experiments=[
            "Run the same strategy on SPY, QQQ, and AAPL over the same window.",
            "Compare against buy-and-hold before changing strategy parameters.",
            "Shift the start and end dates to check whether the result is regime-dependent.",
        ],
        used_mock=True,
    )


async def research_chat(
    request: ResearchRequest, settings: Settings, backtest: BacktestResult | None
) -> ResearchResponse:
    if not settings.openai_api_key:
        return mock_research_response(request, backtest)

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        context = _format_backtest_context(backtest)
        completion = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an AI research copilot for a paper-only quantitative research app. "
                        "Never provide investment advice, never recommend placing orders, and never "
                        "generate executable broker instructions. Frame all output as hypotheses and "
                        "validation steps."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Question: {request.question}\n\nBacktest context:\n{context}",
                },
            ],
            temperature=0.2,
        )
        answer = completion.choices[0].message.content or ""
        if not answer.strip():
            return mock_research_response(request, backtest)
        return ResearchResponse(
            answer=answer.strip(),
            suggested_experiments=[
                "Re-run on a different market regime.",
                "Compare to buy-and-hold and a no-trade baseline.",
                "Inspect max drawdown before considering any next experiment.",
            ],
            used_mock=False,
        )
    except Exception:
        return mock_research_response(request, backtest)


def _format_backtest_context(backtest: BacktestResult | None) -> str:
    if not backtest:
        return "No backtest result was attached."
    metrics = backtest.metrics
    return (
        f"id={backtest.id}, symbol={backtest.symbol}, strategy={backtest.request.strategy}, "
        f"total_return={metrics.total_return}, cagr={metrics.cagr}, volatility={metrics.volatility}, "
        f"sharpe={metrics.sharpe}, max_drawdown={metrics.max_drawdown}, "
        f"win_rate={metrics.win_rate}, trade_count={metrics.trade_count}"
    )
