import type { EquityPoint } from "@/lib/types";

type Props = {
  data: EquityPoint[];
};

export function EquityChart({ data }: Props) {
  const width = 760;
  const height = 360;
  const padding = { top: 24, right: 28, bottom: 38, left: 76 };
  const values = data.map((point) => point.equity);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = Math.max(max - min, 1);
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const points = data
    .map((point, index) => {
      const x = padding.left + (index / Math.max(data.length - 1, 1)) * plotWidth;
      const y = padding.top + (1 - (point.equity - min) / span) * plotHeight;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
  const startLabel = data[0]?.date ?? "";
  const endLabel = data[data.length - 1]?.date ?? "";

  return (
    <svg className="chart-frame" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="资金曲线">
      <line className="chart-axis" x1={padding.left} y1={padding.top} x2={padding.left} y2={height - padding.bottom} />
      <line
        className="chart-axis"
        x1={padding.left}
        y1={height - padding.bottom}
        x2={width - padding.right}
        y2={height - padding.bottom}
      />
      <text className="chart-label" x={padding.left - 10} y={padding.top + 4} textAnchor="end">
        {formatCurrency(max)}
      </text>
      <text className="chart-label" x={padding.left - 10} y={height - padding.bottom} textAnchor="end">
        {formatCurrency(min)}
      </text>
      <text className="chart-label" x={padding.left} y={height - 10}>
        {startLabel}
      </text>
      <text className="chart-label" x={width - padding.right} y={height - 10} textAnchor="end">
        {endLabel}
      </text>
      <polyline className="chart-line" points={points} fill="none" />
    </svg>
  );
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: "compact",
    maximumFractionDigits: 1
  }).format(value);
}
