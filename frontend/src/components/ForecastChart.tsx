import { AreaChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useCashflowForecast } from '../lib/api/hooks';
import { useMemo } from 'react';

export function ForecastChart() {
  const { data: forecastData, isLoading } = useCashflowForecast();

  // Process data for next 7 days
  const chartData = useMemo(() => {
    if (!forecastData?.data) return [];
    
    let dataPoints = Array.isArray(forecastData.data) ? forecastData.data : forecastData.data?.rows || [];
    
    return dataPoints.slice(0, 7).map((point: any) => {
      // Metabase format: [ds, yhat, yhat_lower, yhat_upper]
      const date = point[0];
      const yhat = point[1];
      const lower = point[2];
      const upper = point[3];
      
      let formattedDate = 'N/A';
      try {
        if (date) {
          const dateObj = new Date(date);
          if (!isNaN(dateObj.getTime())) {
            formattedDate = dateObj.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });
          }
        }
      } catch (e) {
        console.warn('Invalid date:', date);
      }
      
      return {
        date: formattedDate,
        forecast: yhat || 0,
        lower: lower || 0,
        upper: upper || 0,
      };
    }).sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
  }, [forecastData]);

  const formatCurrency = (value: number) => {
    return `${(value / 1000000).toFixed(1)}M`;
  };

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload || payload.length === 0) return null;
    
    const data = payload[0].payload;
    
    return (
      <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-lg">
        <p className="font-alata text-slate-900" style={{ fontSize: '16px', fontWeight: 600, marginBottom: '8px' }}>
          {data.date}
        </p>
        <p className="text-emerald-600 font-darker-grotesque" style={{ fontSize: '14px', marginBottom: '4px' }}>
          Dự báo: {formatCurrency(data.forecast)} ₫
        </p>
        <p className="text-orange-600 font-darker-grotesque" style={{ fontSize: '14px', marginBottom: '4px' }}>
          Cao nhất: {formatCurrency(data.upper)} ₫
        </p>
        <p className="text-blue-600 font-darker-grotesque" style={{ fontSize: '14px' }}>
          Thấp nhất: {formatCurrency(data.lower)} ₫
        </p>
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="h-[300px] w-full flex items-center justify-center">
        <div className="text-slate-500">Đang tải dữ liệu...</div>
      </div>
    );
  }

  return (
    <div className="h-[400px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            {/* Confidence band gradient */}
            <linearGradient id="colorConfidence" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#6366f1" stopOpacity={0.15} />
              <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
            </linearGradient>
            {/* Main forecast gradient */}
            <linearGradient id="colorForecast" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
          <XAxis 
            dataKey="date" 
            stroke="#64748b"
            tick={{ fontSize: 14, fontFamily: 'Darker Grotesque' }}
            tickLine={false}
          />
          <YAxis 
            stroke="#64748b"
            tick={{ fontSize: 14, fontFamily: 'Darker Grotesque' }}
            tickLine={false}
            tickFormatter={formatCurrency}
          />
          <Tooltip content={<CustomTooltip />} />
          
          {/* Confidence band (area between lower and upper) */}
          <Area
            type="monotone"
            dataKey="lower"
            stackId="confidence"
            stroke="none"
            fill="#e0e7ff"
            fillOpacity={0.3}
            isAnimationActive={false}
          />
          <Area
            type="monotone"
            dataKey="upper"
            stackId="confidence"
            stroke="none"
            fill="#e0e7ff"
            fillOpacity={0}
            isAnimationActive={false}
          />
          
          {/* Main forecast line with area */}
          <Area
            type="monotone"
            dataKey="forecast"
            stroke="#10b981"
            strokeWidth={3}
            fill="url(#colorForecast)"
            dot={{ fill: '#10b981', r: 5, strokeWidth: 2, stroke: 'white' }}
            activeDot={{ r: 7, strokeWidth: 2, stroke: 'white' }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
