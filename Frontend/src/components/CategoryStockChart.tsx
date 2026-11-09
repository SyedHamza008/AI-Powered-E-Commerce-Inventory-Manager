import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
  Label,
} from 'recharts';

interface CategoryMetric {
  category: string;
  product_count: number;
  total_stock: number;
}

interface CategoryStockChartProps {
  data?: CategoryMetric[];
  /** Optional custom threshold value. Defaults to the calculated average safety benchmark */
  safetyThreshold?: number;
}

const BAR_COLORS = ['#6366f1', '#818cf8', '#a5b4fc', '#4f46e5', '#4338ca'];

export function CategoryStockChart({ data = [], safetyThreshold }: CategoryStockChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="h-48 flex items-center justify-center text-xs text-slate-500 italic">
        No category distribution data available
      </div>
    );
  }

  // Calculate default baseline threshold if none explicitly provided
  // (e.g., benchmark average: 15 units per category target)
  const computedThreshold =
    safetyThreshold !== undefined
      ? safetyThreshold
      : Math.round(
          data.reduce((acc, curr) => acc + curr.total_stock, 0) / (data.length || 1) * 0.4
        ) || 10;

  return (
    <div className="w-full h-52 pt-2">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{ top: 16, right: 24, left: -20, bottom: 4 }}
        >
          <XAxis
            dataKey="category"
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            axisLine={{ stroke: '#334155' }}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            axisLine={{ stroke: '#334155' }}
            tickLine={false}
            allowDecimals={false}
          />
          <Tooltip content={<CustomTooltip />} />

          {/* Target Safety Stock Baseline Watermark */}
          <ReferenceLine
            y={computedThreshold}
            stroke="#f59e0b"
            strokeDasharray="4 4"
            strokeWidth={1.5}
          >
            <Label
              value={`Safety Benchmark (${computedThreshold})`}
              position="top"
              fill="#fbbf24"
              fontSize={10}
              fontWeight={600}
              offset={4}
            />
          </ReferenceLine>

          <Bar
            dataKey="total_stock"
            radius={[6, 6, 0, 0]}
            maxBarSize={48}
            animationDuration={800}
          >
            {data.map((entry, index) => {
              // Highlight bars beneath the threshold in warm rose/coral
              const isBelowSafety = entry.total_stock < computedThreshold;
              return (
                <Cell
                  key={`cell-${index}`}
                  fill={isBelowSafety ? '#f43f5e' : BAR_COLORS[index % BAR_COLORS.length]}
                />
              );
            })}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function CustomTooltip({ active, payload, label }: any) {
  if (active && payload && payload.length) {
    const item: CategoryMetric = payload[0].payload;
    return (
      <div className="p-2.5 rounded-lg bg-slate-900 border border-indigo-500/30 text-white shadow-xl text-xs space-y-1">
        <p className="font-semibold text-indigo-300">{label}</p>
        <p className="text-slate-300">
          Units in Stock: <span className="font-bold text-white">{item.total_stock}</span>
        </p>
        <p className="text-slate-400 text-[11px]">
          Product Lines: <span className="text-slate-200">{item.product_count}</span>
        </p>
      </div>
    );
  }
  return null;
}