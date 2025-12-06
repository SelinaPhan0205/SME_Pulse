import { Bell, Menu, X, AlertTriangle, TrendingDown, Filter } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { UserMenu } from './UserMenu';
import { AnomalyChart } from './AnomalyChart';
import { useState } from 'react';
import { useSidebar } from '../contexts/SidebarContext';

export function AnomalyDetection() {
  const { isSidebarOpen, toggleSidebar } = useSidebar();
  const [selectedSeverity, setSelectedSeverity] = useState<'all' | 'high' | 'medium' | 'low'>('all');

  const chartData = [
    { date: '01/11', revenue: 52000000, isAnomaly: false },
    { date: '02/11', revenue: 54000000, isAnomaly: false },
    { date: '03/11', revenue: 51000000, isAnomaly: false },
    { date: '04/11', revenue: 53000000, isAnomaly: false },
    { date: '05/11', revenue: 28000000, isAnomaly: true, severity: 'high' as const },
    { date: '06/11', revenue: 55000000, isAnomaly: false },
    { date: '07/11', revenue: 56000000, isAnomaly: false },
    { date: '08/11', revenue: 54000000, isAnomaly: false },
    { date: '09/11', revenue: 42000000, isAnomaly: true, severity: 'medium' as const },
    { date: '10/11', revenue: 57000000, isAnomaly: false },
    { date: '11/11', revenue: 58000000, isAnomaly: false },
    { date: '12/11', revenue: 59000000, isAnomaly: false },
    { date: '13/11', revenue: 56000000, isAnomaly: false },
    { date: '14/11', revenue: 60000000, isAnomaly: false },
    { date: '15/11', revenue: 85000000, isAnomaly: true, severity: 'high' as const },
    { date: '16/11', revenue: 58000000, isAnomaly: false },
    { date: '17/11', revenue: 57000000, isAnomaly: false },
    { date: '18/11', revenue: 59000000, isAnomaly: false },
    { date: '19/11', revenue: 46000000, isAnomaly: true, severity: 'low' as const },
    { date: '20/11', revenue: 61000000, isAnomaly: false },
    { date: '21/11', revenue: 62000000, isAnomaly: false },
    { date: '22/11', revenue: 63000000, isAnomaly: false },
  ];

  const anomalies = [
    {
      id: 'TXN001',
      date: '05/11/2024',
      amount: 28000000,
      customer: 'Công ty TNHH ABC',
      score: 0.92,
      severity: 'high' as const,
      reasons: [
        { feature: 'Giá trị thấp bất thường', importance: 0.45 },
        { feature: 'Thời gian thanh toán lạ', importance: 0.32 },
        { feature: 'Khác biệt với pattern', importance: 0.15 },
      ],
    },
    {
      id: 'TXN002',
      date: '15/11/2024',
      amount: 85000000,
      customer: 'Công ty CP XYZ',
      score: 0.88,
      severity: 'high' as const,
      reasons: [
        { feature: 'Giá trị cao bất thường', importance: 0.52 },
        { feature: 'Khách hàng mới', importance: 0.28 },
        { feature: 'Vượt ngưỡng trung bình', importance: 0.08 },
      ],
    },
    {
      id: 'TXN003',
      date: '09/11/2024',
      amount: 42000000,
      customer: 'Doanh nghiệp DEF',
      score: 0.68,
      severity: 'medium' as const,
      reasons: [
        { feature: 'Giảm 22% so với TB', importance: 0.38 },
        { feature: 'Thanh toán trễ', importance: 0.20 },
        { feature: 'Phương thức thanh toán lạ', importance: 0.10 },
      ],
    },
    {
      id: 'TXN004',
      date: '19/11/2024',
      amount: 46000000,
      customer: 'Công ty GHI',
      score: 0.55,
      severity: 'low' as const,
      reasons: [
        { feature: 'Giảm nhẹ so với TB', importance: 0.25 },
        { feature: 'Ngày trong tuần bất thường', importance: 0.18 },
        { feature: 'Danh mục sản phẩm khác', importance: 0.12 },
      ],
    },
  ];

  const filteredAnomalies = selectedSeverity === 'all' 
    ? anomalies 
    : anomalies.filter(a => a.severity === selectedSeverity);

  const stats = [
    {
      title: 'Tổng bất thường',
      value: anomalies.length.toString(),
      description: 'Giao dịch được đánh dấu',
      gradient: 'from-red-400 to-red-600',
      icon: AlertTriangle,
    },
    {
      title: 'Mức độ cao',
      value: anomalies.filter(a => a.severity === 'high').length.toString(),
      description: 'Cần xem xét ngay',
      gradient: 'from-orange-400 to-orange-600',
      icon: TrendingDown,
    },
    {
      title: 'Điểm TB',
      value: (anomalies.reduce((sum, a) => sum + a.score, 0) / anomalies.length).toFixed(2),
      description: 'Anomaly score trung bình',
      gradient: 'from-amber-400 to-amber-600',
      icon: Filter,
    },
  ];

  const getSeverityBadge = (severity: 'high' | 'medium' | 'low') => {
    const config = {
      high: { label: 'Cao', className: 'bg-red-100 text-red-700 border-red-300' },
      medium: { label: 'TB', className: 'bg-orange-100 text-orange-700 border-orange-300' },
      low: { label: 'Thấp', className: 'bg-yellow-100 text-yellow-700 border-yellow-300' },
    };
    return config[severity];
  };

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
        <div className="mb-6">
          <h2 className="text-slate-900 mb-2 font-alata" style={{ fontSize: '32px', fontWeight: 400 }}>Cảnh báo bất thường</h2>
          <p className="text-slate-600 font-darker-grotesque" style={{ fontSize: '18px' }}>
            Phát hiện giao dịch bất thường bằng Machine Learning
          </p>
        </div>

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