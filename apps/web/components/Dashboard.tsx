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
      setError(err instanceof Error ? err.message : "Backtest failed");
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
            <h1>AI Quant Lab</h1>
            <p>US equity and ETF research workspace</p>
          </div>
        </div>
        <div className="status-strip" aria-label="Platform status">
          <span className="status-pill">
            <ShieldCheck size={16} /> Research only
          </span>
          <span className="status-pill">
            <Database size={16} /> Sample data
          </span>
          <span className="status-pill">
            <Bot size={16} /> Mock AI fallback
          </span>
        </div>
      </header>

      <div className="grid">
        <aside className="panel">
          <div className="panel-header">
            <h2>Strategy Lab</h2>
            <FlaskConical size={18} aria-hidden="true" />
          </div>
          <div className="panel-body">
            <StrategyForm symbols={symbols} loading={loading} onSubmit={runBacktest} />
            {error ? <p className="error" role="alert">{error}</p> : null}
          </div>
        </aside>

        <section className="panel" aria-label="Backtest results">
          <div className="panel-header">
            <h2>{result ? `${result.symbol} Backtest` : "Backtest Results"}</h2>
            <p className="risk-note">No orders or broker connections</p>
          </div>
          <div className="panel-body">
            {result ? (
              <>
                <MetricsGrid metrics={result.metrics} />
                <EquityChart data={result.equity_curve} />
              </>
            ) : (
              <p className="empty-state">Run a sample strategy to inspect metrics and equity curve.</p>
            )}
          </div>
        </section>

        <aside className="panel">
          <div className="panel-header">
            <h2>Research Copilot</h2>
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
