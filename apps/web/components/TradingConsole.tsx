"use client";

import { FormEvent, useState } from "react";
import { ArrowDownRight, ArrowUpRight, ShieldCheck, Send } from "lucide-react";
import { previewOrder, submitOrder } from "@/lib/api";
import type {
  OrderIntent,
  OrderPreview,
  OrderReceipt,
  OrderSide,
  OrderType,
  SymbolInfo,
  TimeInForce,
  TradingStatus
} from "@/lib/types";

type Props = {
  symbols: SymbolInfo[];
  status: TradingStatus | null;
  onPreviewChange: (preview: OrderPreview | null) => void;
  onReceiptChange: (receipt: OrderReceipt | null) => void;
};

export function TradingConsole({ symbols, status, onPreviewChange, onReceiptChange }: Props) {
  const listedSymbols = symbols.map((item) => item.symbol);
  const allowedSymbols = status?.allowed_symbols.length ? status.allowed_symbols : ["SPY", "QQQ", "AAPL"];
  const availableSymbols = allowedSymbols.filter((item) => listedSymbols.length === 0 || listedSymbols.includes(item));

  const [symbol, setSymbol] = useState("SPY");
  const [side, setSide] = useState<OrderSide>("buy");
  const [quantity, setQuantity] = useState("2");
  const [orderType, setOrderType] = useState<OrderType>("market");
  const [timeInForce, setTimeInForce] = useState<TimeInForce>("day");
  const [limitPrice, setLimitPrice] = useState("");
  const [rationale, setRationale] = useState("AI 信号待验证，先用小额订单意图检查风控。");
  const [preview, setPreview] = useState<OrderPreview | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [loadingSubmit, setLoadingSubmit] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedSymbol = availableSymbols.includes(symbol) ? symbol : availableSymbols[0] ?? "SPY";

  function updatePreview(nextPreview: OrderPreview | null) {
    setPreview(nextPreview);
    onPreviewChange(nextPreview);
    onReceiptChange(null);
  }

  function buildIntent(): OrderIntent {
    return {
      symbol: selectedSymbol,
      side,
      quantity: Number(quantity),
      order_type: orderType,
      time_in_force: timeInForce,
      ...(orderType === "limit" ? { limit_price: Number(limitPrice) } : {}),
      ...(rationale.trim() ? { rationale: rationale.trim() } : {})
    };
  }

  async function submitPreview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoadingPreview(true);
    setError(null);
    try {
      const nextPreview = await previewOrder(buildIntent());
      updatePreview(nextPreview);
    } catch (err) {
      updatePreview(null);
      setError(err instanceof Error ? err.message : "风控预检失败");
    } finally {
      setLoadingPreview(false);
    }
  }

  async function submitConfirmedOrder() {
    if (!preview) {
      return;
    }
    setLoadingSubmit(true);
    setError(null);
    try {
      const receipt = await submitOrder({ ...buildIntent(), confirmation_phrase: preview.confirmation_phrase });
      onReceiptChange(receipt);
    } catch (err) {
      setError(err instanceof Error ? err.message : "订单提交失败");
    } finally {
      setLoadingSubmit(false);
    }
  }

  const canPreview =
    Number(quantity) > 0 && (orderType === "market" || Number(limitPrice) > 0) && availableSymbols.length > 0;
  const submitLabel = status?.provider === "internal_sandbox" ? "确认提交到沙箱" : "确认提交订单";

  return (
    <form className="trade-form" onSubmit={submitPreview}>
      <label>
        标的
        <select
          value={selectedSymbol}
          onChange={(event) => {
            setSymbol(event.target.value);
            updatePreview(null);
          }}
        >
          {availableSymbols.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </label>

      <div className="field-group">
        <span className="field-label">方向</span>
        <div className="segmented" role="group" aria-label="方向">
          <button
            type="button"
            className={side === "buy" ? "segment active" : "segment"}
            onClick={() => {
              setSide("buy");
              updatePreview(null);
            }}
          >
            <ArrowUpRight size={16} /> 买入
          </button>
          <button
            type="button"
            className={side === "sell" ? "segment active" : "segment"}
            onClick={() => {
              setSide("sell");
              updatePreview(null);
            }}
          >
            <ArrowDownRight size={16} /> 卖出
          </button>
        </div>
      </div>

      <div className="form-row">
        <label>
          数量
          <input
            min="0.0001"
            step="0.0001"
            type="number"
            value={quantity}
            onChange={(event) => {
              setQuantity(event.target.value);
              updatePreview(null);
            }}
          />
        </label>
        <label>
          有效期
          <select
            value={timeInForce}
            onChange={(event) => {
              setTimeInForce(event.target.value as TimeInForce);
              updatePreview(null);
            }}
          >
            <option value="day">DAY</option>
            <option value="gtc">GTC</option>
          </select>
        </label>
      </div>

      <div className="form-row">
        <label>
          订单类型
          <select
            value={orderType}
            onChange={(event) => {
              setOrderType(event.target.value as OrderType);
              updatePreview(null);
            }}
          >
            <option value="market">市价</option>
            <option value="limit">限价</option>
          </select>
        </label>
        <label>
          限价
          <input
            disabled={orderType === "market"}
            min="0.01"
            step="0.01"
            type="number"
            value={limitPrice}
            onChange={(event) => {
              setLimitPrice(event.target.value);
              updatePreview(null);
            }}
            placeholder={orderType === "market" ? "市价单不填" : "例如 472.5"}
          />
        </label>
      </div>

      <label>
        交易理由
        <textarea value={rationale} onChange={(event) => setRationale(event.target.value)} />
      </label>

      <button type="submit" disabled={!canPreview || loadingPreview}>
        <ShieldCheck size={16} />
        {loadingPreview ? "预检中" : "风控预检"}
      </button>

      {preview ? (
        <div className={preview.accepted ? "preview-banner accepted" : "preview-banner blocked"}>
          <strong>{preview.accepted ? "预检通过" : "预检拦截"}</strong>
          <span>{preview.message}</span>
          <code>{preview.confirmation_phrase}</code>
        </div>
      ) : null}

      <button
        className="secondary-button"
        type="button"
        disabled={!preview?.accepted || loadingSubmit}
        onClick={submitConfirmedOrder}
      >
        <Send size={16} />
        {loadingSubmit ? "提交中" : submitLabel}
      </button>

      {error ? (
        <p className="error" role="alert">
          {error}
        </p>
      ) : null}
    </form>
  );
}
