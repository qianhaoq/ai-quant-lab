import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MetricsGrid } from "@/components/MetricsGrid";

describe("MetricsGrid", () => {
  it("renders core backtest metrics", () => {
    render(
      <MetricsGrid
        metrics={{
          total_return: 0.1234,
          cagr: 0.061,
          volatility: 0.18,
          sharpe: 1.42,
          max_drawdown: -0.087,
          win_rate: 0.6,
          trade_count: 5
        }}
      />
    );

    expect(screen.getByText("Total Return")).toBeInTheDocument();
    expect(screen.getByText("12.34%")).toBeInTheDocument();
    expect(screen.getByText("Sharpe")).toBeInTheDocument();
    expect(screen.getByText("1.42")).toBeInTheDocument();
  });
});
