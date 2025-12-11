import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface AnomalyChartProps {
  data: Array<{
    date: string;
    revenue: number;
    isAnomaly: boolean;
    severity?: 'high' | 'medium' | 'low';
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

  return (
    <div className="h-[400px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
          <XAxis 
            dataKey="date" 
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
          
          <Line
            type="monotone"
            dataKey="revenue"
            stroke="#3b82f6"
            strokeWidth={2.5}
            dot={(props: any) => {
              const { cx, cy, payload, index } = props;
              if (payload.isAnomaly) {
                return (
                  <circle
                    key={`anomaly-dot-${index}`}
                    cx={cx}
                    cy={cy}
                    r={8}
                    fill={getSeverityColor(payload.severity)}
                    stroke="white"
                    strokeWidth={3}
                  />
                );
              }
              return <circle key={`normal-dot-${index}`} cx={cx} cy={cy} r={4} fill="#3b82f6" />;
            }}
            activeDot={{ r: 6, fill: '#3b82f6', stroke: 'white', strokeWidth: 2 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
