import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

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
    return `${(value / 1000000).toFixed(1)}M`;
  };

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload || payload.length === 0) return null;
    
    const dataPoint = payload[0].payload;
    
    return (
      <div className="bg-white p-4 rounded-lg border-2 border-slate-200 shadow-lg">
        <p className="font-alata text-slate-900 mb-3" style={{ fontSize: '16px', fontWeight: 600 }}>
          {dataPoint.date}
        </p>
        <p className="text-blue-600 font-darker-grotesque mb-2" style={{ fontSize: '15px', fontWeight: 500 }}>
          Dự báo: {formatCurrency(dataPoint.yhat)} ₫
        </p>
        <p className="text-orange-600 font-darker-grotesque mb-2" style={{ fontSize: '15px', fontWeight: 500 }}>
          Cao nhất: {formatCurrency(dataPoint.upper)} ₫
        </p>
        <p className="text-indigo-600 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>
          Thấp nhất: {formatCurrency(dataPoint.lower)} ₫
        </p>
      </div>
    );
  };

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
            content={<CustomTooltip />}
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
            activeDot={{ r: 6, fill: '#3b82f6', stroke: 'white', strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}