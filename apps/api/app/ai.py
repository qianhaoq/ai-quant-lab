from app.config import Settings
from app.models import BacktestResult, ResearchRequest, ResearchResponse


def mock_research_response(request: ResearchRequest, backtest: BacktestResult | None) -> ResearchResponse:
    if backtest:
        metrics = backtest.metrics
        answer = (
            "交易研究摘要：这次结果只能用于形成信号假设，不构成投资建议。"
            f"{backtest.symbol} 的当前策略总收益为 {metrics.total_return:.2%}，"
            f"夏普比率为 {metrics.sharpe:.2f}，最大回撤为 {metrics.max_drawdown:.2%}。"
            "任何订单意图都必须先进入风控预检，并由人工确认后才能提交。"
        )
    else:
        answer = (
            "交易研究摘要：AI 可以帮助生成信号假设、解释账户风险和建议下一组实验，"
            "但不能直接下单。所有订单都必须经过风控预检、确认短语和人工复核。"
        )
    return ResearchResponse(
        answer=answer,
        suggested_experiments=[
            "先用 SPY、QQQ、AAPL 小额订单意图验证风控规则。",
            "把 AI 信号拆成入场理由、风险预算、退出条件，再分别验证。",
            "真实券商接入前，先在 paper 模式核对订单生命周期和错误处理。",
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
                        "你是一个 AI 量化交易平台里的交易研究助手。请使用中文回答。"
                        "不要提供投资建议，不要承诺收益，不要绕过风控生成可执行券商指令。"
                        "可以提出信号假设、风险检查、订单意图字段建议和验证步骤。"
                        "所有真实订单都必须经过风控预检、确认短语和人工复核。"
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
                "先在 paper 或内部沙箱中验证订单生命周期。",
                "把信号假设和仓位上限拆开评估。",
                "提交前复核最大名义金额、标的白名单和持仓约束。",
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
