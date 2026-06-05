import type { Metrics } from "@/lib/types";

type Props = {
  metrics: Metrics;
};

const METRICS: Array<{ key: keyof Metrics; label: string; format: "percent" | "number" | "integer" }> = [
  { key: "total_return", label: "总收益", format: "percent" },
  { key: "cagr", label: "年化收益", format: "percent" },
  { key: "volatility", label: "波动率", format: "percent" },
  { key: "sharpe", label: "夏普比率", format: "number" },
  { key: "max_drawdown", label: "最大回撤", format: "percent" },
  { key: "win_rate", label: "胜率", format: "percent" },
  { key: "trade_count", label: "交易次数", format: "integer" }
];

export function MetricsGrid({ metrics }: Props) {
  return (
    <div className="metrics-grid">
      {METRICS.map((item) => (
        <div className="metric" key={item.key}>
          <p className="metric-label">{item.label}</p>
          <p className="metric-value">{formatMetric(metrics[item.key], item.format)}</p>
        </div>
      ))}
    </div>
  );
}

function formatMetric(value: number, format: "percent" | "number" | "integer") {
  if (format === "percent") {
    return new Intl.NumberFormat("en-US", { style: "percent", maximumFractionDigits: 2 }).format(value);
  }
  if (format === "integer") {
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(value);
  }
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(value);
}
