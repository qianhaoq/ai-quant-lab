import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { StrategyForm } from "@/components/StrategyForm";

const symbols = [
  { symbol: "SPY", name: "SPDR S&P 500 ETF Trust", asset_class: "us_etf" as const },
  { symbol: "AAPL", name: "Apple Inc.", asset_class: "us_equity" as const }
];

describe("StrategyForm", () => {
  it("submits the selected strategy payload", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<StrategyForm symbols={symbols} loading={false} onSubmit={onSubmit} />);

    await user.selectOptions(screen.getByLabelText("标的"), "AAPL");
    await user.selectOptions(screen.getByLabelText("策略"), "buy_and_hold");
    await user.click(screen.getByRole("button", { name: /运行回测/i }));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        symbols: ["AAPL"],
        strategy: "buy_and_hold",
        timeframe: "1d",
        initial_cash: 100000,
        params: {}
      })
    );
  });
});
