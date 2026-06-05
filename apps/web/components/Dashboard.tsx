"use client";

import { useEffect, useState } from "react";
import { Activity, Bot, Database, FlaskConical, ShieldCheck } from "lucide-react";
import { createBacktest, fetchSymbols } from "@/lib/api";
import type { BacktestRequest, BacktestResult, SymbolInfo } from "@/lib/types";
import { EquityChart } from "@/components/EquityChart";
import { MetricsGrid } from "@/components/MetricsGrid";
import { ResearchCopilot } from "@/components/ResearchCopilot";
import { StrategyForm } from "@/components/StrategyForm";

export function Dashboard() {
  const [symbols, setSymbols] = useState<SymbolInfo[]>([]);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSymbols()
      .then(setSymbols)
      .catch((err: Error) => setError(err.message));
  }, []);

  async function runBacktest(payload: BacktestRequest) {
    setLoading(true);
    setError(null);
    try {
      const nextResult = await createBacktest(payload);
      setResult(nextResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : "回测失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            <Activity size={22} />
          </div>
          <div>
            <h1>AI 量化实验室</h1>
            <p>美股与 ETF 的研究型回测工作台</p>
          </div>
        </div>
        <div className="status-strip" aria-label="Platform status">
          <span className="status-pill">
            <ShieldCheck size={16} /> 研究模式
          </span>
          <span className="status-pill">
            <Database size={16} /> 样例数据
          </span>
          <span className="status-pill">
            <Bot size={16} /> Mock AI 兜底
          </span>
        </div>
      </header>

      <div className="grid">
        <aside className="panel">
          <div className="panel-header">
            <h2>策略实验室</h2>
            <FlaskConical size={18} aria-hidden="true" />
          </div>
          <div className="panel-body">
            <StrategyForm symbols={symbols} loading={loading} onSubmit={runBacktest} />
            {error ? <p className="error" role="alert">{error}</p> : null}
          </div>
        </aside>

        <section className="panel" aria-label="回测结果">
          <div className="panel-header">
            <h2>{result ? `${result.symbol} 回测` : "回测结果"}</h2>
            <p className="risk-note">不连接券商，不产生订单</p>
          </div>
          <div className="panel-body">
            {result ? (
              <>
                <MetricsGrid metrics={result.metrics} />
                <EquityChart data={result.equity_curve} />
              </>
            ) : (
              <p className="empty-state">运行一个样例策略，查看指标和资金曲线。</p>
            )}
          </div>
        </section>

        <aside className="panel">
          <div className="panel-header">
            <h2>AI 研究助手</h2>
            <Bot size={18} aria-hidden="true" />
          </div>
          <div className="panel-body">
            <ResearchCopilot backtestId={result?.id} />
          </div>
        </aside>
      </div>
    </main>
  );
}
