import { Bell, Menu, X, AlertTriangle, TrendingDown, Filter, Loader2, RefreshCw } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { UserMenu } from './UserMenu';
import { AnomalyChart } from './AnomalyChart';
import { useState, useMemo } from 'react';
import { useSidebar } from '../contexts/SidebarContext';
import { useAnomalyResult } from '../lib/api/hooks';
import { format } from 'date-fns';

// Types
interface AnomalyItem {
  id: string;
  date: string;
  amount: number;
  customer: string;
  score: number;
  severity: 'high' | 'medium' | 'low';
  category?: string;
  reasons: Array<{ feature: string; importance: number }>;
}

interface ChartDataPoint {
  date: string;
  revenue: number;
  isAnomaly: boolean;
  severity?: 'high' | 'medium' | 'low';
  rawDate?: string;
  timestamp: number; // Use numeric timestamp for accurate sorting
}

export function AnomalyDetection() {
  const { isSidebarOpen, toggleSidebar } = useSidebar();
  const [selectedSeverity, setSelectedSeverity] = useState<'all' | 'high' | 'medium' | 'low'>('all');

  // Fetch real anomaly data from Metabase
  const { 
    data: anomalyData, 
    isLoading, 
    error, 
    refetch 
  } = useAnomalyResult();

  // Transform Metabase data to display format
  const anomalies: AnomalyItem[] = useMemo(() => {
    if (!anomalyData?.data) {
      console.warn('No anomalyData:', anomalyData);
      return [];
    }
    
    // Handle both array of objects and Metabase API response format
    let dataPoints = Array.isArray(anomalyData.data) ? anomalyData.data : anomalyData.data?.rows || [];
    
    // Also try nested structure if data is an object with rows
    if (!Array.isArray(dataPoints) && anomalyData.data?.rows) {
      dataPoints = anomalyData.data.rows;
    }
    
    console.log('AnomalyDetection dataPoints:', dataPoints);
    
    // Only return actual anomalies (where anomaly = 1)
    return dataPoints.filter((point: any) => point[3] === 1).map((point: any, index: number) => {
      // Metabase returns array format: [txn_id, txn_date, amount_vnd, anomaly]
      const txnId = point[0] || `TXN${index}`;
      const date = point[1];
      const amount = point[2];
      
      // Safe date formatting
      let formattedDate = 'Chưa xác định';
      try {
        if (date) {
          const dateObj = new Date(date);
          if (!isNaN(dateObj.getTime())) {
            formattedDate = format(dateObj, 'dd/MM/yyyy');
          }
        }
      } catch (e) {
        console.warn('Invalid date:', date);
      }
      
      // Determine severity based on amount (not random)
      // HIGH: > 80M, MEDIUM: 40-80M, LOW: 20-40M
      let severity: 'high' | 'medium' | 'low' = 'low';
      if (amount > 80_000_000) {
        severity = 'high';
      } else if (amount > 40_000_000) {
        severity = 'medium';
      }
      
      // Calculate anomaly score based on severity (not random)
      const score = severity === 'high' ? 0.95 : severity === 'medium' ? 0.70 : 0.50;
      
      return {
        id: `TXN${String(index + 1).padStart(3, '0')}`,
        date: formattedDate,
        amount: amount || 0,
        customer: `Transaction #${txnId}`,
        score: score,
        severity: severity as 'high' | 'medium' | 'low',
        category: 'Unusual Activity',
        reasons: [
          { feature: `Mức độ: ${(score * 100).toFixed(0)}%`, importance: score },
          { feature: `Số tiền: ${(amount / 1000000).toFixed(1)}M ₫`, importance: 0.5 },
        ],
      };
    });
  }, [anomalyData]);

  // Generate chart data from anomalies
  const chartData: ChartDataPoint[] = useMemo(() => {
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
        const dateObj = new Date(date);
        if (!isNaN(dateObj.getTime())) {
          formattedDate = format(dateObj, 'dd/MM/yyyy');
        }
      } catch (e) {
        console.warn('Invalid date:', date);
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
        } as ChartDataPoint;
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
        } as ChartDataPoint;
      }
    }).sort((a, b) => {
      // Sort by timestamp to ensure correct chronological order
      return a.timestamp - b.timestamp;
    });
  }, [anomalyData]);

  const filteredAnomalies = selectedSeverity === 'all' 
    ? anomalies 
    : anomalies.filter(a => a.severity === selectedSeverity);

  // Calculate stats from real data - only count actual anomalies
  const stats = useMemo(() => {
    if (anomalies.length === 0) {
      return [
        { title: 'Tổng bất thường', value: '0', description: 'Giao dịch được đánh dấu bởi ML', gradient: 'from-red-400 to-red-600', icon: AlertTriangle },
        { title: 'Mức độ cao', value: '0', description: 'Cần xem xét ngay', gradient: 'from-orange-400 to-orange-600', icon: TrendingDown },
        { title: 'Điểm TB', value: '0.00', description: 'Anomaly score trung bình', gradient: 'from-amber-400 to-amber-600', icon: Filter },
      ];
    }

    const totalAnomalies = anomalies.length;
    
    // Count high severity
    const highCount = anomalies.filter(a => a.severity === 'high').length;
    
    // Calculate average score from anomalies list
    const avgScore = anomalies.reduce((sum, a) => sum + a.score, 0) / totalAnomalies;

    return [
      {
        title: 'Tổng bất thường',
        value: totalAnomalies.toString(),
        description: 'Giao dịch được đánh dấu bởi ML',
        gradient: 'from-red-400 to-red-600',
        icon: AlertTriangle,
      },
      {
        title: 'Mức độ cao',
        value: highCount.toString(),
        description: 'Cần xem xét ngay',
        gradient: 'from-orange-400 to-orange-600',
        icon: TrendingDown,
      },
      {
        title: 'Điểm TB',
        value: avgScore.toFixed(2),
        description: 'Anomaly score trung bình',
        gradient: 'from-amber-400 to-amber-600',
        icon: Filter,
      },
    ];
  }, [anomalies]);

  const getSeverityBadge = (severity: 'high' | 'medium' | 'low') => {
    const config = {
      high: { label: 'Cao', className: 'bg-red-100 text-red-700 border-red-300' },
      medium: { label: 'TB', className: 'bg-orange-100 text-orange-700 border-orange-300' },
      low: { label: 'Thấp', className: 'bg-yellow-100 text-yellow-700 border-yellow-300' },
    };
    return config[severity];
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-50 via-slate-50 to-red-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="size-12 animate-spin text-orange-600 mx-auto mb-4" />
          <p className="text-slate-600 font-darker-grotesque text-lg">
            Đang tải dữ liệu phát hiện bất thường từ ML model...
          </p>
        </div>
      </div>
    );
  }

  // Error state with fallback
  if (error) {
    console.error('Anomaly API error:', error);
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 via-slate-50 to-red-50">
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
              <span className="absolute right-2 top-2 size-2 rounded-full bg-red-500"></span>
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
            <h2 className="text-slate-900 mb-2 font-alata" style={{ fontSize: '32px', fontWeight: 400 }}>Cảnh báo bất thường</h2>
            <p className="text-slate-600 font-darker-grotesque" style={{ fontSize: '18px' }}>
              Phát hiện giao dịch bất thường bằng Machine Learning (Isolation Forest)
              {anomalyData && (
                <span className="text-orange-600 ml-2">
                  • {anomalies.length} cảnh báo từ ML Model
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

        {/* Error Banner - Only show if error AND no data loaded */}
        {error && !anomalyData?.data?.length && (
          <Card className="border-l-4 border-l-yellow-500 bg-gradient-to-r from-yellow-50 to-white shadow-sm mb-6">
            <CardContent className="p-5">
              <div className="flex items-start gap-3">
                <AlertTriangle className="size-6 text-yellow-600 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <h3 className="text-yellow-900 font-alata mb-1" style={{ fontSize: '18px', fontWeight: 400 }}>
                    Không thể kết nối ML Model
                  </h3>
                  <p className="text-yellow-700 font-darker-grotesque" style={{ fontSize: '16px', lineHeight: '1.4' }}>
                    Vui lòng kiểm tra kết nối Trino/Lakehouse. Đảm bảo ML pipeline đã chạy.
                    {error instanceof Error && <span className="block text-sm mt-1">Chi tiết: {error.message}</span>}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {stats.map((stat, index) => {
            const Icon = stat.icon;
            return (
              <Card 
                key={index} 
                className={`border-0 shadow-lg hover:shadow-2xl hover:scale-105 transition-all duration-300 bg-gradient-to-br ${stat.gradient} text-white`}
              >
                <CardHeader className="pb-2 px-5 pt-4">
                  <div className="flex items-center justify-between">
                    <CardDescription className="text-white/90 font-darker-grotesque" style={{ fontSize: '14px', fontWeight: 500 }}>
                      {stat.title}
                    </CardDescription>
                    <Icon className="size-5 text-white/80" />
                  </div>
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
            );
          })}
        </div>

        {/* Chart */}
        <Card className="border-0 shadow-lg hover:shadow-xl transition-shadow duration-300 bg-white mb-6">
          <CardHeader className="pb-4">
            <CardTitle className="text-slate-900 font-alata" style={{ fontSize: '24px', fontWeight: 400 }}>
              Biểu đồ doanh thu với điểm bất thường
            </CardTitle>
            <CardDescription className="font-darker-grotesque" style={{ fontSize: '16px' }}>
              Các điểm màu đỏ/cam/vàng đánh dấu giao dịch bất thường được phát hiện
            </CardDescription>
          </CardHeader>
          <CardContent>
            <AnomalyChart data={chartData} />
            <div className="flex items-center justify-center gap-6 mt-4 font-darker-grotesque" style={{ fontSize: '16px' }}>
              <div className="flex items-center gap-2">
                <div className="size-4 rounded-full bg-red-600"></div>
                <span className="text-slate-700">Mức độ cao</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="size-4 rounded-full bg-orange-500"></div>
                <span className="text-slate-700">Mức độ trung bình</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="size-4 rounded-full bg-yellow-400"></div>
                <span className="text-slate-700">Mức độ thấp</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Anomaly Table */}
        <Card className="border-0 shadow-lg hover:shadow-xl transition-shadow duration-300 bg-gradient-to-br from-white via-slate-50 to-orange-50">
          <CardHeader className="pb-4">
            <div className="flex items-start justify-between">
              <div>
                <CardTitle className="text-slate-900 font-alata" style={{ fontSize: '24px', fontWeight: 400 }}>
                  Danh sách giao dịch bất thường
                </CardTitle>
                <CardDescription className="font-darker-grotesque" style={{ fontSize: '16px' }}>
                  Chi tiết điểm anomaly và lý do phát hiện
                </CardDescription>
              </div>
              <div className="flex gap-2">
                <Button
                  variant={selectedSeverity === 'all' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSelectedSeverity('all')}
                  className="font-darker-grotesque"
                  style={{ fontSize: '15px' }}
                >
                  Tất cả
                </Button>
                <Button
                  variant={selectedSeverity === 'high' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSelectedSeverity('high')}
                  className={`font-darker-grotesque ${selectedSeverity === 'high' ? 'bg-red-600 hover:bg-red-700' : ''}`}
                  style={{ fontSize: '15px' }}
                >
                  Cao
                </Button>
                <Button
                  variant={selectedSeverity === 'medium' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSelectedSeverity('medium')}
                  className={`font-darker-grotesque ${selectedSeverity === 'medium' ? 'bg-orange-600 hover:bg-orange-700' : ''}`}
                  style={{ fontSize: '15px' }}
                >
                  TB
                </Button>
                <Button
                  variant={selectedSeverity === 'low' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSelectedSeverity('low')}
                  className={`font-darker-grotesque ${selectedSeverity === 'low' ? 'bg-yellow-600 hover:bg-yellow-700' : ''}`}
                  style={{ fontSize: '15px' }}
                >
                  Thấp
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {filteredAnomalies.map((anomaly) => {
                const severityConfig = getSeverityBadge(anomaly.severity);
                return (
                  <Card key={anomaly.id} className="border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
                    <CardContent className="p-5">
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <h3 className="font-darker-grotesque text-slate-900" style={{ fontSize: '20px', fontWeight: 600 }}>
                              {anomaly.id}
                            </h3>
                            <Badge className={`${severityConfig.className} font-darker-grotesque border`} style={{ fontSize: '14px' }}>
                              {severityConfig.label}
                            </Badge>
                          </div>
                          <div className="grid grid-cols-3 gap-4">
                            <div>
                              <p className="text-slate-500 font-darker-grotesque" style={{ fontSize: '14px' }}>Khách hàng</p>
                              <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '17px', fontWeight: 500 }}>
                                {anomaly.customer}
                              </p>
                            </div>
                            <div>
                              <p className="text-slate-500 font-darker-grotesque" style={{ fontSize: '14px' }}>Số tiền</p>
                              <p className="text-slate-900 font-alata" style={{ fontSize: '17px', fontWeight: 600 }}>
                                {(anomaly.amount / 1000000).toFixed(1)}M ₫
                              </p>
                            </div>
                            <div>
                              <p className="text-slate-500 font-darker-grotesque" style={{ fontSize: '14px' }}>Ngày giao dịch</p>
                              <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '17px', fontWeight: 500 }}>
                                {anomaly.date}
                              </p>
                            </div>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '14px' }}>Anomaly Score</p>
                          <p className="font-alata text-red-600" style={{ fontSize: '32px', fontWeight: 600, lineHeight: '1' }}>
                            {(anomaly.score * 100).toFixed(0)}
                          </p>
                        </div>
                      </div>

                      {/* Feature Importance */}
                      <div className="border-t border-slate-200 pt-4">
                        <h4 className="text-slate-700 font-darker-grotesque mb-3" style={{ fontSize: '16px', fontWeight: 600 }}>
                          Lý do bất thường:
                        </h4>
                        <div className="space-y-2">
                          {anomaly.reasons.map((reason, idx) => (
                            <div key={idx} className="flex items-center gap-3">
                              <div className="flex-1">
                                <div className="flex items-center justify-between mb-1">
                                  <span className="text-slate-700 font-darker-grotesque" style={{ fontSize: '16px' }}>
                                    {reason.feature}
                                  </span>
                                  <span className="text-slate-500 font-darker-grotesque" style={{ fontSize: '15px' }}>
                                    {(reason.importance * 100).toFixed(0)}%
                                  </span>
                                </div>
                                <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-gradient-to-r from-red-400 to-orange-500 rounded-full transition-all duration-500"
                                    style={{ width: `${reason.importance * 100}%` }}
                                  ></div>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>

            {filteredAnomalies.length === 0 && (
              <div className="text-center py-12">
                <AlertTriangle className="size-12 text-slate-300 mx-auto mb-3" />
                <p className="text-slate-500 font-darker-grotesque" style={{ fontSize: '18px' }}>
                  Không có giao dịch bất thường với bộ lọc này
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}