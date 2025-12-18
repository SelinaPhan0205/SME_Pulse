import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface AnomalyChartProps {
  data: Array<{
    date: string;
    revenue: number;
    isAnomaly: boolean;
    severity?: 'high' | 'medium' | 'low';
    rawDate?: string; // YYYY-MM-DD format for proper sorting
  }>;
}

export function AnomalyChart({ data }: AnomalyChartProps) {
  const formatCurrency = (value: number) => {
    return `${(value / 1000000).toFixed(0)}M`;
  };

  const getSeverityColor = (severity?: string) => {
    switch (severity) {
      case 'high': return '#dc2626';
      case 'medium': return '#f97316';
      case 'low': return '#facc15';
      default: return '#3b82f6';
    }
  };

  const getDotSize = (isAnomaly: boolean) => {
    return isAnomaly ? 8 : 4;  // Larger for anomaly, smaller for normal
  };

  return (
    <div className="h-[400px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            {/* Gradient cho area fill màu xanh dương */}
            <linearGradient id="colorRevenueAnomaly" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
          <XAxis 
            dataKey="timestamp"
            type="number"
            scale="time"
            domain={['auto', 'auto']}
            tickFormatter={(ts) => {
              const d = new Date(ts);
              return `${String(d.getDate()).padStart(2,'0')}/${String(d.getMonth()+1).padStart(2,'0')}/${d.getFullYear()}`;
            }}
            stroke="#64748b"
            tick={{ fontSize: 16, fontFamily: 'Darker Grotesque' }}
            tickLine={false}
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
            formatter={(value: number) => {
              return [`${formatCurrency(value)} ₫`, 'Doanh thu'];
            }}
          />
          
          {/* Area với gradient fill */}
          <Area
            type="monotone"
            dataKey="revenue"
            stroke="#3b82f6"
            strokeWidth={2.5}
            fill="url(#colorRevenueAnomaly)"
            dot={(props: any) => {
              const { cx, cy, payload, index } = props;
              const size = getDotSize(payload.isAnomaly);
              const color = payload.isAnomaly 
                ? getSeverityColor(payload.severity)
                : '#3b82f6';  // Blue for normal days
              
              return (
                <circle
                  key={`dot-${index}`}
                  cx={cx}
                  cy={cy}
                  r={size}
                  fill={color}
                  stroke="white"
                  strokeWidth={2}
                />
              );
            }}
            activeDot={(props: any) => {
              const { cx, cy, payload } = props;
              return (
                <circle
                  cx={cx}
                  cy={cy}
                  r={getDotSize(payload.isAnomaly) + 2}
                  fill={payload.isAnomaly ? getSeverityColor(payload.severity) : '#3b82f6'}
                  stroke="white"
                  strokeWidth={2}
                />
              );
            }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
