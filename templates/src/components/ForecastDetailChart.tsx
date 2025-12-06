import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceDot } from 'recharts';

interface ForecastDetailChartProps {
  data: Array<{
    date: string;
    actual: number | null;
    yhat: number;
    lower: number;
    upper: number;
  }>;
}

export function ForecastDetailChart({ data }: ForecastDetailChartProps) {
  const formatCurrency = (value: number) => {
    return `${(value / 1000000).toFixed(0)}M`;
  };

  // Find points where forecast goes below a threshold (e.g., 45M) - negative balance warning
  const warningThreshold = 45000000;
  const warningPoints = data.filter(d => d.yhat < warningThreshold);

  return (
    <div className="h-[400px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="colorYhat" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#2563eb" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#2563eb" stopOpacity={0.05} />
            </linearGradient>
            <linearGradient id="colorConfidenceInterval" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.15} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
          <XAxis 
            dataKey="date" 
            stroke="#64748b"
            tick={{ fontSize: 16, fontFamily: 'Darker Grotesque' }}
            tickLine={false}
            interval={data.length > 30 ? 'preserveStartEnd' : 0}
          />
          <YAxis 
            stroke="#64748b"
            tick={{ fontSize: 16, fontFamily: 'Darker Grotesque' }}
            tickLine={false}
            tickFormatter={formatCurrency}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              fontSize: '17px',
              fontFamily: 'Darker Grotesque',
              padding: '12px',
            }}
            labelStyle={{ fontWeight: 600, color: '#1e293b', fontSize: '18px', marginBottom: '8px' }}
            itemStyle={{ fontSize: '17px', padding: '4px 0', fontWeight: 500 }}
            formatter={(value: number, name: string) => {
              const labels: Record<string, string> = {
                actual: 'Thực tế',
                yhat: 'Dự báo',
                lower: 'Thấp nhất',
                upper: 'Cao nhất',
              };
              return [`${formatCurrency(value)} ₫`, labels[name] || name];
            }}
          />
          
          {/* Confidence interval area */}
          <Area
            type="monotone"
            dataKey="upper"
            stroke="none"
            fill="url(#colorConfidenceInterval)"
            fillOpacity={1}
            hide
          />
          <Area
            type="monotone"
            dataKey="lower"
            stroke="none"
            fill="white"
            fillOpacity={1}
            hide
          />
          
          {/* Main forecast line */}
          <Area
            type="monotone"
            dataKey="yhat"
            stroke="#2563eb"
            strokeWidth={2.5}
            fill="url(#colorYhat)"
            dot={false}
            activeDot={{ r: 6, fill: '#2563eb', stroke: 'white', strokeWidth: 2 }}
          />
          
          {/* Actual data line */}
          <Line
            type="monotone"
            dataKey="actual"
            stroke="#10b981"
            strokeWidth={2.5}
            dot={{ fill: '#10b981', r: 5, strokeWidth: 0 }}
            connectNulls={false}
          />

          {/* Upper bound dashed line */}
          <Line
            type="monotone"
            dataKey="upper"
            stroke="#93c5fd"
            strokeWidth={1.5}
            strokeDasharray="5 5"
            dot={false}
          />
          
          {/* Lower bound dashed line */}
          <Line
            type="monotone"
            dataKey="lower"
            stroke="#93c5fd"
            strokeWidth={1.5}
            strokeDasharray="5 5"
            dot={false}
          />

          {/* Warning points for negative balance */}
          {warningPoints.map((point, index) => (
            <ReferenceDot
              key={index}
              x={point.date}
              y={point.yhat}
              r={6}
              fill="#ef4444"
              stroke="white"
              strokeWidth={2}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}