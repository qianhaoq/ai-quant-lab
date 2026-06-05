from app.config import Settings
from app.models import BacktestResult, ResearchRequest, ResearchResponse


def mock_research_response(request: ResearchRequest, backtest: BacktestResult | None) -> ResearchResponse:
    if backtest:
        metrics = backtest.metrics
        answer = (
            "研究模式摘要：这次回测只能用于形成研究假设，不构成投资建议。"
            f"{backtest.symbol} 的当前策略总收益为 {metrics.total_return:.2%}，"
            f"夏普比率为 {metrics.sharpe:.2f}，最大回撤为 {metrics.max_drawdown:.2%}。"
            "下一步建议先和买入并持有基准对比，再在不同时间窗口测试相邻参数。"
        )
    else:
        answer = (
            "研究模式摘要：先从买入并持有这类简单基准开始，再在同一标的和时间范围内对比规则策略。"
            "任何 AI 生成的想法都应视为待验证假设，必须经过样本外测试。"
        )
    return ResearchResponse(
        answer=answer,
        suggested_experiments=[
            "在 SPY、QQQ、AAPL 上用同一时间窗口运行相同策略。",
            "调整策略参数前，先和买入并持有基准对比。",
            "平移开始和结束日期，检查结果是否依赖特定市场阶段。",
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
                        "你是一个研究模式量化应用里的 AI 研究助手。请使用中文回答。"
                        "不要提供投资建议，不要推荐下单，不要生成可执行的券商指令。"
                        "所有输出都必须表述为研究假设和验证步骤。"
                    ),
                },
                {
                    "role": "user",
                    "content": f"问题：{request.question}\n\n回测上下文：\n{context}",
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
                "在不同市场阶段重新运行策略。",
                "和买入并持有、空仓基准同时对比。",
                "在继续实验前先检查最大回撤和交易次数。",
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
