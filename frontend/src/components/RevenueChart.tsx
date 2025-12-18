import { AreaChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceDot } from 'recharts';
import { useDailyRevenue, useRevenueAnomalies } from '../lib/api/hooks';

export function RevenueChart() {
  // Get last 14 days
  const endDate = new Date();
  const startDate = new Date();
  startDate.setDate(startDate.getDate() - 14);
  
  const { data: revenueData, isLoading } = useDailyRevenue({
    start_date: startDate.toISOString().split('T')[0],
    end_date: endDate.toISOString().split('T')[0],
  });
  
  const { data: anomalyData } = useRevenueAnomalies({
    start_date: startDate.toISOString().split('T')[0],
    end_date: endDate.toISOString().split('T')[0],
  });

  // Merge revenue data with anomalies
  const anomalyDates = new Set(anomalyData?.data.map(a => a.date) || []);
  const avgRevenue = (revenueData?.data && revenueData.data.length > 0)
    ? revenueData.data.reduce((sum, d) => sum + d.revenue, 0) / revenueData.data.length
    : 50000000;
  
  const data = revenueData?.data.map(point => ({
    date: new Date(point.date).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' }),
    revenue: point.revenue,
    target: avgRevenue,
    anomaly: anomalyDates.has(point.date),
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
            <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
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
            formatter={(value: number) => [`${formatCurrency(value)} ₫`, 'Doanh thu']}
          />
          <Area
            type="monotone"
            dataKey="revenue"
            stroke="#3b82f6"
            strokeWidth={2}
            fill="url(#colorRevenue)"
          />
          <Line
            type="monotone"
            dataKey="target"
            stroke="#94a3b8"
            strokeWidth={1}
            strokeDasharray="5 5"
            dot={false}
          />
          {data.map((entry, index) => 
            entry.anomaly ? (
              <ReferenceDot
                key={index}
                x={entry.date}
                y={entry.revenue}
                r={6}
                fill="#ef4444"
                stroke="white"
                strokeWidth={2}
              />
            ) : null
          )}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
