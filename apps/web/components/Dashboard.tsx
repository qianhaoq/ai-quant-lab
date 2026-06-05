"use client";

import { useEffect, useState } from "react";
import { Activity, Bot, Landmark, ReceiptText, ShieldCheck, WalletCards } from "lucide-react";
import { fetchSymbols, fetchTradingAccount, fetchTradingPositions, fetchTradingStatus } from "@/lib/api";
import type { AccountSnapshot, OrderPreview, OrderReceipt, PositionSnapshot, SymbolInfo, TradingStatus } from "@/lib/types";
import { ResearchCopilot } from "@/components/ResearchCopilot";
import { TradingConsole } from "@/components/TradingConsole";

export function Dashboard() {
  const [symbols, setSymbols] = useState<SymbolInfo[]>([]);
  const [status, setStatus] = useState<TradingStatus | null>(null);
  const [account, setAccount] = useState<AccountSnapshot | null>(null);
  const [positions, setPositions] = useState<PositionSnapshot[]>([]);
  const [preview, setPreview] = useState<OrderPreview | null>(null);
  const [receipt, setReceipt] = useState<OrderReceipt | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadTradingState() {
      try {
        const [nextSymbols, nextStatus] = await Promise.all([fetchSymbols(), fetchTradingStatus()]);
        if (!active) {
          return;
        }
        setSymbols(nextSymbols);
        setStatus(nextStatus);
        const [nextAccount, nextPositions] = await Promise.all([fetchTradingAccount(), fetchTradingPositions()]);
        if (!active) {
          return;
        }
        setAccount(nextAccount);
        setPositions(nextPositions);
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "交易状态加载失败");
        }
      }
    }

    loadTradingState();
    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            <Activity size={22} />
          </div>
          <div>
            <h1>AI 量化交易平台</h1>
            <p>受控交易网关、风控预检和 AI 信号研究</p>
          </div>
        </div>
        <div className="status-strip" aria-label="Platform status">
          <span className="status-pill">
            <Landmark size={16} /> {status ? providerLabel(status.provider) : "交易网关"}
          </span>
          <span className="status-pill">
            <ShieldCheck size={16} /> 风控预检
          </span>
          <span className="status-pill">
            <Bot size={16} /> 人工确认
          </span>
        </div>
      </header>

      <div className="grid">
        <aside className="panel">
          <div className="panel-header">
            <h2>订单意图</h2>
            <ShieldCheck size={18} aria-hidden="true" />
          </div>
          <div className="panel-body">
            <TradingConsole symbols={symbols} status={status} onPreviewChange={setPreview} onReceiptChange={setReceipt} />
            {error ? <p className="error" role="alert">{error}</p> : null}
          </div>
        </aside>

        <section className="panel" aria-label="账户与风控">
          <div className="panel-header">
            <h2>账户与风控</h2>
            <p className="risk-note">{status ? modeLabel(status.mode) : "正在连接"}</p>
          </div>
          <div className="panel-body">
            {status ? (
              <div className="gateway-summary">
                <div>
                  <span>网关</span>
                  <strong>{providerLabel(status.provider)}</strong>
                </div>
                <div>
                  <span>状态</span>
                  <strong>{status.trading_enabled ? "可提交" : "已锁定"}</strong>
                </div>
                <div>
                  <span>Live</span>
                  <strong>{status.live_trading_enabled ? "已开启" : "关闭"}</strong>
                </div>
              </div>
            ) : (
              <p className="empty-state">正在读取交易网关状态。</p>
            )}

            <div className="account-grid" aria-label="账户快照">
              <div className="metric">
                <p className="metric-label">组合市值</p>
                <p className="metric-value">{account ? formatCurrency(account.portfolio_value) : "--"}</p>
              </div>
              <div className="metric">
                <p className="metric-label">现金</p>
                <p className="metric-value">{account ? formatCurrency(account.cash) : "--"}</p>
              </div>
              <div className="metric">
                <p className="metric-label">购买力</p>
                <p className="metric-value">{account ? formatCurrency(account.buying_power) : "--"}</p>
              </div>
            </div>

            <div className="section-title">
              <WalletCards size={16} aria-hidden="true" />
              <h3>当前持仓</h3>
            </div>
            {positions.length > 0 ? (
              <table className="positions-table">
                <thead>
                  <tr>
                    <th>标的</th>
                    <th>数量</th>
                    <th>市值</th>
                    <th>未实现盈亏</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.map((position) => (
                    <tr key={position.symbol}>
                      <td>{position.symbol}</td>
                      <td>{formatNumber(position.quantity)}</td>
                      <td>{formatCurrency(position.market_value)}</td>
                      <td className={position.unrealized_pl >= 0 ? "gain" : "loss"}>
                        {formatCurrency(position.unrealized_pl)} / {formatPercent(position.unrealized_pl_pct)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="empty-state">暂无持仓。</p>
            )}

            <div className="section-title">
              <ShieldCheck size={16} aria-hidden="true" />
              <h3>风控预检</h3>
            </div>
            {preview ? (
              <ul className="risk-checks" aria-label="风控检查">
                {preview.risk_checks.map((check) => (
                  <li key={check.name} className={check.passed ? "passed" : "blocked"}>
                    <strong>{check.name}</strong>
                    <span>{check.message}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="empty-state">先提交一个订单意图。</p>
            )}

            {receipt ? (
              <div className="receipt-box" role="status">
                <ReceiptText size={16} aria-hidden="true" />
                <div>
                  <strong>订单已进入内部沙箱</strong>
                  <span>
                    {receipt.symbol} {receipt.side === "buy" ? "买入" : "卖出"} {formatNumber(receipt.quantity)}，
                    {formatCurrency(receipt.estimated_notional)}
                  </span>
                </div>
              </div>
            ) : null}
          </div>
        </section>

        <aside className="panel">
          <div className="panel-header">
            <h2>AI 交易研究员</h2>
            <Bot size={18} aria-hidden="true" />
          </div>
          <div className="panel-body">
            <ResearchCopilot />
          </div>
        </aside>
      </div>
    </main>
  );
}

function providerLabel(provider: string) {
  if (provider === "internal_sandbox") {
    return "内部沙箱";
  }
  if (provider === "alpaca") {
    return "Alpaca";
  }
  return provider;
}

function modeLabel(mode: TradingStatus["mode"]) {
  if (mode === "alpaca_live") {
    return "Alpaca Live";
  }
  if (mode === "alpaca_paper") {
    return "Alpaca Paper";
  }
  return "内部沙箱";
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("zh-CN", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 4 }).format(value);
}

function formatPercent(value: number) {
  return new Intl.NumberFormat("zh-CN", { style: "percent", maximumFractionDigits: 2 }).format(value);
}
