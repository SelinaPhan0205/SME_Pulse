import { Bell, Menu, X, TrendingDown, TrendingUp, AlertTriangle, DollarSign, Calendar, Percent } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { UserMenu } from './UserMenu';
import { RevenueChart } from './RevenueChart';
import { ForecastChart } from './ForecastChart';
import { AnomalyChart } from './AnomalyChart';
import { useSidebar } from '../contexts/SidebarContext';
import { useDashboardSummary, usePaymentSuccessRate, useAlerts, useCashflowForecast, useAnomalyResult, useDailyRevenue } from '../lib/api/hooks';
import { useMemo } from 'react';

export function Dashboard() {
  const navigate = useNavigate();
  const { isSidebarOpen, toggleSidebar } = useSidebar();
  
  // Fetch data from API
  const { data: summary, isLoading: loadingSummary } = useDashboardSummary();
  const { data: paymentRate } = usePaymentSuccessRate();
  const { data: dailyRevenueData } = useDailyRevenue();
  const { data: alertsData, isLoading: loadingAlerts } = useAlerts({ 
    status: 'new', 
    severity: 'warning,error,critical',
    limit: 5 
  });
  
  // Fetch forecast and anomaly data for dashboard charts
  const { data: forecastData } = useCashflowForecast();
  const { data: anomalyData } = useAnomalyResult();

  // Process forecast data for 7-day forecast chart
  const forecastChartData = useMemo(() => {
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
        console.warn('Invalid forecast date:', date);
      }
      
      return {
        date: formattedDate,
        forecast: yhat || 0,
        lower: lower || 0,
        upper: upper || 0,
      };
    }).sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
  }, [forecastData]);

  // Process anomaly data for 14-day anomaly chart
  const anomalyChartData = useMemo(() => {
    if (!anomalyData?.data) return [];
    
    let dataPoints = Array.isArray(anomalyData.data) ? anomalyData.data : anomalyData.data?.rows || [];
    
    // Group transactions by date
    const groupedByDate = new Map<string, any[]>();
    dataPoints.forEach((point: any) => {
      const date = point[1];
      if (!groupedByDate.has(date)) {
        groupedByDate.set(date, []);
      }
      groupedByDate.get(date)!.push(point);
    });
    
    // Convert to chart data - 1 point per day
    return Array.from(groupedByDate.entries()).map(([date, transactions]) => {
      // Check if any transaction on this day is anomaly
      const anomalyTransactions = transactions.filter((t: any) => t[3] === 1);
      
      let formattedDate = 'N/A';
      try {
        if (date) {
          const dateObj = new Date(date);
          if (!isNaN(dateObj.getTime())) {
            formattedDate = dateObj.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });
          }
        }
      } catch (e) {
        console.warn('Invalid anomaly date:', date);
      }
      
      if (anomalyTransactions.length > 0) {
        // Has anomaly - use highest amount and determine severity
        const anomalyAmount = Math.max(...anomalyTransactions.map((t: any) => t[2]));
        
        // Determine severity based on amount
        // HIGH: > 80M, MEDIUM: 40-80M, LOW: 20-40M
        let severity: 'high' | 'medium' | 'low' = 'low';
        if (anomalyAmount > 80_000_000) {
          severity = 'high';
        } else if (anomalyAmount > 40_000_000) {
          severity = 'medium';
        }
        
        return {
          date: formattedDate,
          revenue: anomalyAmount,
          isAnomaly: true,
          severity: severity,
          rawDate: date,
          timestamp: new Date(date).getTime(),
        };
      } else {
        // No anomaly - calculate average amount for the day
        const avgAmount = transactions.reduce((sum: number, t: any) => sum + t[2], 0) / transactions.length;
        
        return {
          date: formattedDate,
          revenue: avgAmount,
          isAnomaly: false,
          severity: 'low',
          rawDate: date,
          timestamp: new Date(date).getTime(),
        };
      }
    }).slice(0, 14).sort((a, b) => {
      // Sort by timestamp to ensure correct chronological order
      return a.timestamp - b.timestamp;
    });
  }, [anomalyData]);

  // Calculate metrics from API data
  const totalRevenue = dailyRevenueData?.total_revenue || 0;
  const metrics = summary ? [
    {
      title: 'Tỉ lệ thanh toán thành công',
      value: `${Math.round((paymentRate?.success_rate || 0) * 100)}%`,
      change: '+9.8%',
      changeLabel: 'so với tháng qua',
      trend: 'up' as const,
      icon: Percent,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
    },
    {
      title: 'Doanh thu tháng này',
      value: totalRevenue > 0 ? `${Math.round(totalRevenue / 1000000)}` : '0',
      unit: 'triệu ₫',
      change: '+12%',
      changeLabel: 'so với tháng trước',
      trend: 'up' as const,
      icon: DollarSign,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
    },
    {
      title: 'Công nợ phải thu',
      value: `${Math.round((summary.total_ar || 0) / 1000000)}`,
      unit: 'triệu ₫',
      change: `${summary.overdue_ar_count || 0} quá hạn`,
      changeLabel: 'cần xử lý',
      trend: 'down' as const,
      icon: Calendar,
      color: 'text-orange-600',
      bgColor: 'bg-orange-50',
    },
  ] : [];

  // Map API alerts to anomaly format
  const anomalies = alertsData?.items.map(alert => ({
    id: alert.id,
    description: alert.message || alert.title || 'Cảnh báo hệ thống',
    severity: alert.severity === 'critical' || alert.severity === 'error' 
      ? 'high' as const
      : alert.severity === 'warning' 
      ? 'medium' as const 
      : 'low' as const,
    time: new Date(alert.created_at).toLocaleString('vi-VN', { 
      day: '2-digit', 
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    }),
  })) || [];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-slate-100">
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
        <div className="mb-6">
          <h2 className="text-slate-900 mb-2 font-alata" style={{ fontSize: '32px', fontWeight: 400 }}>Dashboard</h2>
          <p className="text-slate-600 font-darker-grotesque" style={{ fontSize: '18px' }}>Tổng quan về tình hình tài chính doanh nghiệp</p>
        </div>

        {/* Metrics Grid - Compact at top */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {loadingSummary ? (
            // Loading skeleton for metrics
            Array.from({ length: 3 }).map((_, index) => (
              <Card 
                key={index} 
                className="border-0 shadow-sm bg-gradient-to-br from-white to-slate-50/50 backdrop-blur"
              >
                <CardHeader className="pb-0 px-5 pt-3.5">
                  <div className="flex items-start justify-between">
                    <div className="h-4 w-24 bg-slate-200 rounded animate-pulse"></div>
                    <div className="h-8 w-8 bg-slate-200 rounded-lg animate-pulse"></div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-1 px-5 pb-3.5">
                  <div className="h-10 w-32 bg-slate-200 rounded animate-pulse mb-2"></div>
                  <div className="h-4 w-20 bg-slate-200 rounded animate-pulse"></div>
                </CardContent>
              </Card>
            ))
          ) : (
            metrics.map((metric, index) => {
              const Icon = metric.icon;
              return (
                <Card 
                  key={index} 
                  className="border-0 shadow-sm hover:shadow-md transition-shadow bg-gradient-to-br from-white to-slate-50/50 backdrop-blur"
                >
                  <CardHeader className="pb-0 px-5 pt-3.5">
                    <div className="flex items-start justify-between">
                      <CardDescription className="text-slate-600 font-darker-grotesque" style={{ fontSize: '13px' }}>
                        {metric.title}
                      </CardDescription>
                      <div className={`p-1.5 rounded-lg ${metric.bgColor}`}>
                        <Icon className={`size-4 ${metric.color}`} />
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-1 px-5 pb-3.5">
                    <div className="flex items-baseline gap-2">
                      <span className="text-slate-900 font-alata" style={{ fontSize: '38px', fontWeight: 400, lineHeight: '1' }}>
                        {metric.value}
                      </span>
                      {metric.unit && (
                        <span className="text-slate-600 font-darker-grotesque" style={{ fontSize: '14px' }}>
                          {metric.unit}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-1.5">
                      {metric.trend === 'up' ? (
                        <TrendingUp className="size-3.5 text-green-600" />
                      ) : (
                        <TrendingDown className="size-3.5 text-orange-600" />
                      )}
                      <span className={`font-alata ${metric.trend === 'up' ? 'text-green-600' : 'text-orange-600'}`} style={{ fontSize: '13px' }}>
                        {metric.change}
                      </span>
                      <span className="text-slate-500 font-darker-grotesque" style={{ fontSize: '12px' }}>
                        {metric.changeLabel}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              );
            })
          )}
        </div>

        {/* Main Grid - Anomalies and Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          {/* Charts - 2 columns */}
          <div className="lg:col-span-2 space-y-6">
            <Card className="border-0 shadow-lg hover:shadow-xl transition-shadow bg-gradient-to-br from-white via-slate-50 to-blue-50/20">
              <CardHeader className="pb-4">
                <CardTitle className="text-slate-900 font-alata" style={{ fontSize: '22px', fontWeight: 400 }}>
                  Doanh thu 14 ngày
                </CardTitle>
                <CardDescription className="font-darker-grotesque text-slate-600" style={{ fontSize: '15px' }}>
                  Xu hướng doanh thu hàng ngày với cảnh báo bất thường
                </CardDescription>
              </CardHeader>
              <CardContent>
                <AnomalyChart data={anomalyChartData} />
              </CardContent>
            </Card>

            <Card className="border-0 shadow-lg hover:shadow-xl transition-shadow bg-gradient-to-br from-white via-slate-50 to-emerald-50/20">
              <CardHeader className="pb-4">
                <CardTitle className="text-slate-900 font-alata" style={{ fontSize: '22px', fontWeight: 400 }}>
                  Dự báo dòng tiền 7 ngày
                </CardTitle>
                <CardDescription className="font-darker-grotesque text-slate-600" style={{ fontSize: '15px' }}>
                  Dự đoán dòng tiền hàng ngày với phạm vi tin cậy 95%
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ForecastChart />
              </CardContent>
            </Card>
          </div>

          {/* Anomaly Detection - Full height, 1 column on right */}
          <div>
            <Card className="border-0 shadow-sm bg-gradient-to-br from-white to-orange-50/20 h-full flex flex-col">
              <CardHeader className="pb-4">
                <div className="flex items-center justify-between mb-1">
                  <CardTitle className="text-slate-900 font-alata" style={{ fontSize: '24px', fontWeight: 400 }}>
                    Cảnh báo AI
                  </CardTitle>
                  <Badge variant="destructive" className="rounded-full font-alata px-3 py-1" style={{ fontSize: '14px' }}>
                    {anomalies.length}
                  </Badge>
                </div>
                <CardDescription className="font-darker-grotesque" style={{ fontSize: '16px' }}>
                  Phát hiện bất thường
                </CardDescription>
              </CardHeader>
              <CardContent className="flex-1">
                <div className="space-y-3.5">
                  {loadingAlerts ? (
                    // Loading skeleton
                    Array.from({ length: 3 }).map((_, index) => (
                      <div key={index} className="p-4 rounded-lg bg-slate-100 animate-pulse">
                        <div className="flex gap-3">
                          <div className="h-5 w-5 bg-slate-300 rounded"></div>
                          <div className="flex-1 space-y-2">
                            <div className="h-5 w-full bg-slate-300 rounded"></div>
                            <div className="h-4 w-24 bg-slate-300 rounded"></div>
                          </div>
                        </div>
                      </div>
                    ))
                  ) : anomalies.length === 0 ? (
                    <p className="text-slate-500 text-center py-8 font-darker-grotesque" style={{ fontSize: '16px' }}>
                      Không có cảnh báo mới
                    </p>
                  ) : (
                    anomalies.map((anomaly) => (
                    <div
                      key={anomaly.id}
                      className={`p-4 rounded-lg border-l-4 ${
                        anomaly.severity === 'high'
                          ? 'border-l-red-500 bg-red-50/70'
                          : anomaly.severity === 'medium'
                          ? 'border-l-orange-500 bg-orange-50/70'
                          : 'border-l-yellow-500 bg-yellow-50/70'
                      }`}
                    >
                      <div className="flex gap-3">
                        <div className="shrink-0 mt-1">
                          <AlertTriangle
                            className={`size-5 ${
                              anomaly.severity === 'high'
                                ? 'text-red-600'
                                : anomaly.severity === 'medium'
                                ? 'text-orange-600'
                                : 'text-yellow-600'
                            }`}
                          />
                        </div>
                        <div className="flex-1 space-y-1">
                          <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '22px', lineHeight: '1.3', fontWeight: 500 }}>
                            {anomaly.description}
                          </p>
                          <p className="text-slate-500 font-darker-grotesque" style={{ fontSize: '15px' }}>
                            {anomaly.time}
                          </p>
                        </div>
                      </div>
                    </div>
                    ))
                  )}
                </div>
              </CardContent>
              <div className="mt-auto px-6 pb-5 flex justify-end border-t border-slate-100 pt-4">
                <button
                  onClick={() => navigate('/dashboard/anomaly')}
                  className="text-orange-600 hover:text-orange-700 font-darker-grotesque underline decoration-2 underline-offset-4 transition-colors"
                  style={{ fontSize: '22px', fontWeight: 500 }}
                >
                  Xem chi tiết →
                </button>
              </div>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}