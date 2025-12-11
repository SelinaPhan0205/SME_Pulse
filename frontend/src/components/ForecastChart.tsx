import { AreaChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useRevenueForecast } from '../lib/api/hooks';

export function ForecastChart() {
  // Get next 7 days forecast
  const startDate = new Date();
  const endDate = new Date();
  endDate.setDate(endDate.getDate() + 7);
  
  const { data: forecastData, isLoading } = useRevenueForecast({
    start_date: startDate.toISOString().split('T')[0],
    end_date: endDate.toISOString().split('T')[0],
  });

  const data = forecastData?.data.map(point => ({
    date: new Date(point.date).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' }),
    actual: point.actual,
    forecast: point.forecast,
    lower: point.lower_bound,
    upper: point.upper_bound,
  })) || [];

  const formatCurrency = (value: number) => {
    return `${(value / 1000000).toFixed(0)}M`;
  };

  if (isLoading) {
    return (
      <div className="h-[300px] w-full flex items-center justify-center">
        <div className="text-slate-500">Đang tải dữ liệu...</div>
      </div>
    );
  }

  return (
    <div className="h-[300px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="colorForecast" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="colorConfidence" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#6366f1" stopOpacity={0.1} />
              <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
          <XAxis 
            dataKey="date" 
            stroke="#64748b"
            tick={{ fontSize: 12 }}
            tickLine={false}
          />
          <YAxis 
            stroke="#64748b"
            tick={{ fontSize: 12 }}
            tickLine={false}
            tickFormatter={formatCurrency}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              fontSize: '12px',
            }}
            formatter={(value: number, name: string) => {
              const labels: Record<string, string> = {
                actual: 'Thực tế',
                forecast: 'Dự báo',
                lower: 'Thấp nhất',
                upper: 'Cao nhất',
              };
              return [`${formatCurrency(value)} ₫`, labels[name] || name];
            }}
          />
          <Area
            type="monotone"
            dataKey="upper"
            stroke="none"
            fill="url(#colorConfidence)"
            fillOpacity={1}
          />
          <Area
            type="monotone"
            dataKey="lower"
            stroke="none"
            fill="white"
            fillOpacity={1}
          />
          <Line
            type="monotone"
            dataKey="actual"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={{ fill: '#3b82f6', r: 4 }}
            connectNulls={false}
          />
          <Line
            type="monotone"
            dataKey="forecast"
            stroke="#10b981"
            strokeWidth={2}
            strokeDasharray="5 5"
            dot={{ fill: '#10b981', r: 4 }}
            connectNulls={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
