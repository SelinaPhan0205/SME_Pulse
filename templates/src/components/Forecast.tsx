import { Bell, Menu, X, TrendingDown, TrendingUp, AlertTriangle, Calendar as CalendarIcon } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { UserMenu } from './UserMenu';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { ForecastDetailChart } from './ForecastDetailChart';
import { useState } from 'react';
import { useSidebar } from '../contexts/SidebarContext';

export function Forecast() {
  const { isSidebarOpen, toggleSidebar } = useSidebar();
  const [selectedPeriod, setSelectedPeriod] = useState<'14' | '30' | '90'>('30');

  const forecastData = {
    '14': {
      data: [
        { date: '23/11', actual: 50000000, yhat: 52000000, lower: 47000000, upper: 57000000 },
        { date: '24/11', actual: null, yhat: 54000000, lower: 49000000, upper: 59000000 },
        { date: '25/11', actual: null, yhat: 53000000, lower: 48000000, upper: 58000000 },
        { date: '26/11', actual: null, yhat: 55000000, lower: 50000000, upper: 60000000 },
        { date: '27/11', actual: null, yhat: 57000000, lower: 52000000, upper: 62000000 },
        { date: '28/11', actual: null, yhat: 59000000, lower: 54000000, upper: 64000000 },
        { date: '29/11', actual: null, yhat: 56000000, lower: 51000000, upper: 61000000 },
        { date: '30/11', actual: null, yhat: 58000000, lower: 53000000, upper: 63000000 },
        { date: '01/12', actual: null, yhat: 60000000, lower: 55000000, upper: 65000000 },
        { date: '02/12', actual: null, yhat: 62000000, lower: 57000000, upper: 67000000 },
        { date: '03/12', actual: null, yhat: 61000000, lower: 56000000, upper: 66000000 },
        { date: '04/12', actual: null, yhat: 63000000, lower: 58000000, upper: 68000000 },
        { date: '05/12', actual: null, yhat: 65000000, lower: 60000000, upper: 70000000 },
        { date: '06/12', actual: null, yhat: 64000000, lower: 59000000, upper: 69000000 },
      ],
      mape: 5.2,
      negativeBalance: false,
    },
    '30': {
      data: Array.from({ length: 30 }, (_, i) => ({
        date: `${23 + i}/11`,
        actual: i === 0 ? 50000000 : null,
        yhat: 52000000 + i * 1000000 + Math.random() * 3000000,
        lower: 47000000 + i * 1000000,
        upper: 57000000 + i * 1000000 + Math.random() * 5000000,
      })),
      mape: 6.8,
      negativeBalance: false,
    },
    '90': {
      data: Array.from({ length: 90 }, (_, i) => ({
        date: `${23 + i}/11`,
        actual: i === 0 ? 50000000 : null,
        yhat: 52000000 + i * 800000 + Math.random() * 4000000,
        lower: 45000000 + i * 800000,
        upper: 59000000 + i * 800000 + Math.random() * 6000000,
      })),
      mape: 8.9,
      negativeBalance: true,
    },
  };

  const currentForecast = forecastData[selectedPeriod];

  const stats = [
    {
      title: 'MAPE',
      value: `${currentForecast.mape}%`,
      description: 'Mean Absolute Percentage Error',
      trend: currentForecast.mape < 7 ? 'good' : 'warning',
      gradient: 'from-blue-400 to-blue-600',
    },
    {
      title: 'Doanh thu dự báo TB',
      value: `${(currentForecast.data.reduce((sum, d) => sum + (d.yhat || 0), 0) / currentForecast.data.length / 1000000).toFixed(0)}M ₫`,
      description: `Trung bình ${selectedPeriod} ngày tới`,
      trend: 'good',
      gradient: 'from-emerald-400 to-emerald-600',
    },
    {
      title: 'Khoảng tin cậy',
      value: '95%',
      description: 'Confidence interval',
      trend: 'good',
      gradient: 'from-indigo-400 to-indigo-600',
    },
  ];

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
        <div className="mb-6">
          <h2 className="text-slate-900 mb-2 font-alata" style={{ fontSize: '32px', fontWeight: 400 }}>Dự báo doanh thu</h2>
          <p className="text-slate-600 font-darker-grotesque" style={{ fontSize: '18px' }}>Dự đoán doanh thu dựa trên mô hình Prophet và dữ liệu lịch sử</p>
        </div>

        {/* Warning Card - Negative Balance */}
        {currentForecast.negativeBalance && (
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
          {stats.map((stat, index) => (
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
                </CardDescription>
              </div>
              <Tabs value={selectedPeriod} onValueChange={(val: string) => setSelectedPeriod(val as any)}>
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
            <ForecastDetailChart data={currentForecast.data} />
          </CardContent>
        </Card>

        {/* Forecast Table */}
        <Card className="border-0 shadow-lg hover:shadow-xl transition-shadow duration-300 bg-gradient-to-br from-white via-slate-50 to-blue-50">
          <CardHeader className="pb-4">
            <CardTitle className="text-slate-900 font-alata" style={{ fontSize: '24px', fontWeight: 400 }}>
              Bảng dự báo chi tiết
            </CardTitle>
            <CardDescription className="font-darker-grotesque" style={{ fontSize: '16px' }}>
              Dữ liệu dự báo với giá trị thực tế
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
                    {currentForecast.data.map((row, index) => {
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