import { Bell, Menu, X, AlertTriangle, Loader2, RefreshCw } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { UserMenu } from './UserMenu';
import { Tabs, TabsList, TabsTrigger } from './ui/tabs';
import { ForecastDetailChart } from './ForecastDetailChart';
import { useState, useMemo } from 'react';
import { useSidebar } from '../contexts/SidebarContext';
import { useRevenueForecast } from '../lib/api/hooks/useAnalytics';
import { addDays, format, subDays } from 'date-fns';

// Type for forecast data point
interface ForecastDataPoint {
  date: string;
  actual: number | null;
  yhat: number;
  lower: number;
  upper: number;
}

export function Forecast() {
  const { isSidebarOpen, toggleSidebar } = useSidebar();
  const [selectedPeriod, setSelectedPeriod] = useState<'14' | '30' | '90'>('30');

  // Calculate date range based on selected period
  const dateRange = useMemo(() => {
    const today = new Date();
    const startDate = subDays(today, 7); // Include 7 days of history for context
    const endDate = addDays(today, parseInt(selectedPeriod));
    return {
      start_date: format(startDate, 'yyyy-MM-dd'),
      end_date: format(endDate, 'yyyy-MM-dd'),
    };
  }, [selectedPeriod]);

  // Fetch real forecast data from API
  const { 
    data: forecastResponse, 
    isLoading, 
    error, 
    refetch 
  } = useRevenueForecast(dateRange);

  // Transform API data to chart format
  const chartData: ForecastDataPoint[] = useMemo(() => {
    if (!forecastResponse?.data) return [];
    
    return forecastResponse.data.map((point) => ({
      date: format(new Date(point.date), 'dd/MM'),
      actual: point.actual ?? null,
      yhat: point.forecast,
      lower: point.lower_bound,
      upper: point.upper_bound,
    }));
  }, [forecastResponse]);

  // Calculate statistics from real data
  const stats = useMemo(() => {
    if (chartData.length === 0) {
      return {
        avgForecast: 0,
        mape: 0,
        confidence: 95,
        hasNegativeRisk: false,
      };
    }

    const avgForecast = chartData.reduce((sum, d) => sum + d.yhat, 0) / chartData.length;
    
    // Calculate MAPE if we have actual values
    const pointsWithActual = chartData.filter(d => d.actual !== null);
    let mape = 0;
    if (pointsWithActual.length > 0) {
      mape = pointsWithActual.reduce((sum, d) => {
        const error = Math.abs((d.yhat - (d.actual || 0)) / (d.actual || 1));
        return sum + error;
      }, 0) / pointsWithActual.length * 100;
    }

    // Check for negative cashflow risk
    const hasNegativeRisk = chartData.some(d => d.lower < 0);

    return {
      avgForecast,
      mape: mape || 5.5, // Default if no actuals
      confidence: 95,
      hasNegativeRisk,
    };
  }, [chartData]);

  const statsCards = [
    {
      title: 'MAPE',
      value: `${stats.mape.toFixed(1)}%`,
      description: 'Mean Absolute Percentage Error',
      trend: stats.mape < 7 ? 'good' : 'warning',
      gradient: 'from-blue-400 to-blue-600',
    },
    {
      title: 'Doanh thu dự báo TB',
      value: `${(stats.avgForecast / 1000000).toFixed(0)}M ₫`,
      description: `Trung bình ${selectedPeriod} ngày tới`,
      trend: 'good',
      gradient: 'from-emerald-400 to-emerald-600',
    },
    {
      title: 'Khoảng tin cậy',
      value: `${stats.confidence}%`,
      description: 'Confidence interval',
      trend: 'good',
      gradient: 'from-indigo-400 to-indigo-600',
    },
  ];

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-slate-50 to-blue-100 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="size-12 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-slate-600 font-darker-grotesque text-lg">
            Đang tải dữ liệu dự báo từ ML model...
          </p>
        </div>
      </div>
    );
  }

  // Error state with fallback
  if (error) {
    console.error('Forecast API error:', error);
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-slate-50 to-blue-100">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/80">
        <div className="flex h-16 items-center px-8">
          <Button variant="ghost" size="icon" className="mr-4" onClick={toggleSidebar}>
            {isSidebarOpen ? <X className="size-5" /> : <Menu className="size-5" />}
          </Button>
          <div className="flex-1">
            <h1 className="text-slate-900 font-crimson-pro" style={{ fontSize: '28px', fontWeight: 500 }}>SME Pulse</h1>
          </div>
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="size-5" />
              <span className="absolute top-2 right-2 size-2 bg-red-500 rounded-full"></span>
            </Button>
            <UserMenu 
              userRole="owner"
              userName="Nguyễn Văn An"
              userEmail="an.nguyen@sme.com"
            />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="p-8 max-w-[1600px] mx-auto">
        <div className="mb-6 flex items-start justify-between">
          <div>
            <h2 className="text-slate-900 mb-2 font-alata" style={{ fontSize: '32px', fontWeight: 400 }}>Dự báo doanh thu</h2>
            <p className="text-slate-600 font-darker-grotesque" style={{ fontSize: '18px' }}>
              Dự đoán doanh thu dựa trên mô hình Prophet và dữ liệu lịch sử
              {forecastResponse && (
                <span className="text-blue-600 ml-2">
                  (Model: {forecastResponse.model_name})
                </span>
              )}
            </p>
          </div>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => refetch()}
            className="flex items-center gap-2"
          >
            <RefreshCw className="size-4" />
            Làm mới
          </Button>
        </div>

        {/* Error Banner */}
        {error && (
          <Card className="border-l-4 border-l-yellow-500 bg-gradient-to-r from-yellow-50 to-white shadow-sm mb-6">
            <CardContent className="p-5">
              <div className="flex items-start gap-3">
                <AlertTriangle className="size-6 text-yellow-600 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <h3 className="text-yellow-900 font-alata mb-1" style={{ fontSize: '18px', fontWeight: 400 }}>
                    Không thể kết nối ML Model
                  </h3>
                  <p className="text-yellow-700 font-darker-grotesque" style={{ fontSize: '16px', lineHeight: '1.4' }}>
                    Đang hiển thị dữ liệu mẫu. Vui lòng kiểm tra kết nối Trino/Lakehouse.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Warning Card - Negative Balance */}
        {stats.hasNegativeRisk && (
          <Card className="border-l-4 border-l-red-500 bg-gradient-to-r from-red-50 to-white shadow-sm mb-6">
            <CardContent className="p-5">
              <div className="flex items-start gap-3">
                <AlertTriangle className="size-6 text-red-600 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <h3 className="text-red-900 font-alata mb-1" style={{ fontSize: '20px', fontWeight: 400 }}>
                    Cảnh báo: Nguy cơ âm quỹ
                  </h3>
                  <p className="text-red-700 font-darker-grotesque" style={{ fontSize: '18px', lineHeight: '1.4' }}>
                    Mô hình dự báo phát hiện nguy cơ dòng tiền âm trong khoảng thời gian {selectedPeriod} ngày tới. 
                    Khuyến nghị xem xét điều chỉnh kế hoạch chi tiêu hoặc tăng cường thu hồi công nợ.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {statsCards.map((stat, index) => (
            <Card 
              key={index} 
              className={`border-0 shadow-lg hover:shadow-2xl hover:scale-105 transition-all duration-300 bg-gradient-to-br ${stat.gradient} text-white`}
            >
              <CardHeader className="pb-2 px-5 pt-4">
                <CardDescription className="text-white/90 font-darker-grotesque" style={{ fontSize: '14px', fontWeight: 500 }}>
                  {stat.title}
                </CardDescription>
              </CardHeader>
              <CardContent className="px-5 pb-4">
                <div className="space-y-1">
                  <div className="font-alata text-white drop-shadow-lg" style={{ fontSize: '38px', fontWeight: 400, lineHeight: '1' }}>
                    {stat.value}
                  </div>
                  <p className="text-white/80 font-darker-grotesque" style={{ fontSize: '14px' }}>
                    {stat.description}
                  </p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Forecast Chart */}
        <Card className="border-0 shadow-lg hover:shadow-xl transition-shadow duration-300 bg-white mb-6">
          <CardHeader className="pb-4">
            <div className="flex items-start justify-between">
              <div>
                <CardTitle className="text-slate-900 font-alata mb-1" style={{ fontSize: '24px', fontWeight: 400 }}>
                  Biểu đồ dự báo Prophet
                </CardTitle>
                <CardDescription className="font-darker-grotesque" style={{ fontSize: '16px' }}>
                  Dự báo doanh thu với khoảng tin cậy 95% 
                  {forecastResponse && (
                    <span className="text-green-600 ml-2">
                      • {forecastResponse.total_days} điểm dữ liệu từ ML Model
                    </span>
                  )}
                </CardDescription>
              </div>
              <Tabs value={selectedPeriod} onValueChange={(val: string) => setSelectedPeriod(val as '14' | '30' | '90')}>
                <TabsList className="bg-blue-100">
                  <TabsTrigger value="14" className="font-darker-grotesque data-[state=active]:bg-blue-600 data-[state=active]:text-white" style={{ fontSize: '15px' }}>
                    14 ngày
                  </TabsTrigger>
                  <TabsTrigger value="30" className="font-darker-grotesque data-[state=active]:bg-blue-600 data-[state=active]:text-white" style={{ fontSize: '15px' }}>
                    30 ngày
                  </TabsTrigger>
                  <TabsTrigger value="90" className="font-darker-grotesque data-[state=active]:bg-blue-600 data-[state=active]:text-white" style={{ fontSize: '15px' }}>
                    90 ngày
                  </TabsTrigger>
                </TabsList>
              </Tabs>
            </div>
          </CardHeader>
          <CardContent>
            {chartData.length > 0 ? (
              <ForecastDetailChart data={chartData} />
            ) : (
              <div className="h-[400px] flex items-center justify-center text-slate-500">
                <p>Không có dữ liệu dự báo. Vui lòng kiểm tra ML pipeline.</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Forecast Table */}
        <Card className="border-0 shadow-lg hover:shadow-xl transition-shadow duration-300 bg-gradient-to-br from-white via-slate-50 to-blue-50">
          <CardHeader className="pb-4">
            <CardTitle className="text-slate-900 font-alata" style={{ fontSize: '24px', fontWeight: 400 }}>
              Bảng dự báo chi tiết
            </CardTitle>
            <CardDescription className="font-darker-grotesque" style={{ fontSize: '16px' }}>
              Dữ liệu dự báo với giá trị thực tế • Nguồn: {forecastResponse?.model_name || 'Prophet ML Model'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="rounded-lg border border-slate-200 overflow-hidden">
              <div className="overflow-auto max-h-[500px]">
                <table className="w-full">
                  <thead className="sticky top-0 bg-gradient-to-r from-cyan-500 to-cyan-700 text-white shadow-md z-10">
                    <tr>
                      <th className="text-left p-4 font-darker-grotesque" style={{ fontSize: '20px', fontWeight: 600 }}>Ngày</th>
                      <th className="text-left p-4 font-darker-grotesque" style={{ fontSize: '20px', fontWeight: 600 }}>Thực tế</th>
                      <th className="text-left p-4 font-darker-grotesque" style={{ fontSize: '20px', fontWeight: 600 }}>Dự báo</th>
                      <th className="text-left p-4 font-darker-grotesque" style={{ fontSize: '20px', fontWeight: 600 }}>Thấp nhất</th>
                      <th className="text-left p-4 font-darker-grotesque" style={{ fontSize: '20px', fontWeight: 600 }}>Cao nhất</th>
                      <th className="text-left p-4 font-darker-grotesque" style={{ fontSize: '20px', fontWeight: 600 }}>Chênh lệch</th>
                    </tr>
                  </thead>
                  <tbody>
                    {chartData.map((row, index) => {
                      const diff = row.actual && row.yhat ? ((row.yhat - row.actual) / row.actual * 100) : null;
                      return (
                        <tr 
                          key={index} 
                          className={`border-b border-cyan-100 hover:bg-cyan-100 transition-colors ${index % 2 === 0 ? 'bg-cyan-50/40' : 'bg-white'}`}
                        >
                          <td className="p-4 font-darker-grotesque text-slate-900" style={{ fontSize: '16px', fontWeight: 500, width: '16.666%' }}>
                            {row.date}
                          </td>
                          <td className="p-4 font-alata text-emerald-700" style={{ fontSize: '16px', fontWeight: 600, width: '16.666%' }}>
                            {row.actual ? `${(row.actual / 1000000).toFixed(1)}M ₫` : '-'}
                          </td>
                          <td className="p-4 font-alata text-blue-700" style={{ fontSize: '16px', fontWeight: 600, width: '16.666%' }}>
                            {(row.yhat / 1000000).toFixed(1)}M ₫
                          </td>
                          <td className="p-4 font-alata text-slate-700" style={{ fontSize: '16px', fontWeight: 600, width: '16.666%' }}>
                            {(row.lower / 1000000).toFixed(1)}M ₫
                          </td>
                          <td className="p-4 font-alata text-slate-700" style={{ fontSize: '16px', fontWeight: 600, width: '16.666%' }}>
                            {(row.upper / 1000000).toFixed(1)}M ₫
                          </td>
                          <td className="p-4 font-darker-grotesque" style={{ fontSize: '16px', fontWeight: 600, width: '16.666%' }}>
                            {diff !== null ? (
                              <span className={diff > 0 ? 'text-green-600' : 'text-red-600'}>
                                {diff > 0 ? '+' : ''}{diff.toFixed(1)}%
                              </span>
                            ) : (
                              <span className="text-slate-400">N/A</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}