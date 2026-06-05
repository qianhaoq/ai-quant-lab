import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { TradingConsole } from "@/components/TradingConsole";
import type { TradingStatus } from "@/lib/types";

const symbols = [
  { symbol: "SPY", name: "SPDR S&P 500 ETF Trust", asset_class: "us_etf" as const },
  { symbol: "AAPL", name: "Apple Inc.", asset_class: "us_equity" as const }
];

const status: TradingStatus = {
  provider: "internal_sandbox",
  mode: "sandbox",
  broker_connected: true,
  trading_enabled: true,
  live_trading_enabled: false,
  requires_confirmation: true,
  allowed_symbols: ["SPY", "AAPL"],
  max_order_notional: 25000,
  max_order_quantity: 100,
  message: "内部沙箱已就绪；订单不会发送到真实券商。"
};

describe("TradingConsole", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("previews risk checks and submits a confirmed sandbox order", async () => {
    const user = userEvent.setup();
    const onPreviewChange = vi.fn();
    const onReceiptChange = vi.fn();
    vi.spyOn(global, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          accepted: true,
          broker_provider: "internal_sandbox",
          broker_mode: "sandbox",
          symbol: "SPY",
          side: "buy",
          quantity: 2,
          order_type: "market",
          time_in_force: "day",
          estimated_price: 499.95,
          estimated_notional: 999.9,
          risk_checks: [{ name: "标的白名单", passed: true, severity: "blocker", message: "SPY 可交易。" }],
          confirmation_required: true,
          confirmation_phrase: "确认提交 买入 2 SPY",
          message: "预检通过，等待人工确认。"
        })
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          id: "sandbox_123",
          status: "accepted_sandbox",
          broker_provider: "internal_sandbox",
          broker_mode: "sandbox",
          symbol: "SPY",
          side: "buy",
          quantity: 2,
          order_type: "market",
          time_in_force: "day",
          submitted_at: "2026-06-05T00:00:00Z",
          estimated_notional: 999.9,
          broker_order_id: null,
          message: "订单已进入内部沙箱；未发送到真实券商。"
        })
      } as Response);

    render(
      <TradingConsole
        symbols={symbols}
        status={status}
        onPreviewChange={onPreviewChange}
        onReceiptChange={onReceiptChange}
      />
    );

    await user.click(screen.getByRole("button", { name: /风控预检/i }));

    await waitFor(() => {
      expect(screen.getByText("预检通过")).toBeInTheDocument();
    });
    expect(screen.getByText("确认提交 买入 2 SPY")).toBeInTheDocument();
    expect(onPreviewChange).toHaveBeenCalledWith(expect.objectContaining({ accepted: true }));

    await user.click(screen.getByRole("button", { name: /确认提交到沙箱/i }));

    await waitFor(() => {
      expect(onReceiptChange).toHaveBeenCalledWith(expect.objectContaining({ status: "accepted_sandbox" }));
    });
  });
});
