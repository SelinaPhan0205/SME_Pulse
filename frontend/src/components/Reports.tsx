import { Bell, Menu, X, Download, Filter, Calendar as CalendarIcon, TrendingUp, CreditCard, Users, CheckCircle, DollarSign, Activity, Clock, AlertCircle, ArrowUpRight, ArrowDownRight, Loader2 } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { UserMenu } from './UserMenu';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, Area, AreaChart } from 'recharts';
import { useState, useEffect } from 'react';
import { useSidebar } from '../contexts/SidebarContext';
import { useCreateExportJob, useExportJobStatus } from '../lib/api/hooks/useReports';
import type { ExportJobCreateRequest } from '../lib/api/services/reports';

// Map frontend report types to backend report_type
// Backend only supports: ar_aging, ap_aging, cashflow
// For unsupported types, we map to the closest available type
type BackendReportType = 'ar_aging' | 'ap_aging' | 'cashflow';

const reportTypeMapping: Record<string, BackendReportType | null> = {
  'Doanh thu': 'cashflow',       // Revenue → Cashflow report
  'Thanh toán': 'cashflow',      // Payment → Cashflow report
  'Công nợ': 'ar_aging',         // AR Aging report
  'Đối soát': 'ar_aging',        // Reconciliation → AR Aging (closest match)
};

// Map backend type to display name for notifications
const reportTypeDisplayName: Record<string, string> = {
  'ar_aging': 'Công nợ phải thu (AR Aging)',
  'ap_aging': 'Công nợ phải trả (AP Aging)',
  'cashflow': 'Dòng tiền (Cashflow)',
};

export function Reports() {
  const { isSidebarOpen, toggleSidebar } = useSidebar();
  const [periodType, setPeriodType] = useState<'month' | 'range'>('month');
  const [selectedMonth, setSelectedMonth] = useState('2024-11');
  const [showDateRangeDialog, setShowDateRangeDialog] = useState(false);
  
  // Export job state
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [exportingType, setExportingType] = useState<string | null>(null);
  
  // Export job mutation and status polling
  const createExportMutation = useCreateExportJob();
  const { data: jobStatus } = useExportJobStatus(currentJobId);
  
  // Handle job completion
  useEffect(() => {
    if (jobStatus?.status === 'completed' && jobStatus.file_url) {
      // Download the file
      window.open(jobStatus.file_url, '_blank');
      // Reset state
      setCurrentJobId(null);
      setExportingType(null);
    } else if (jobStatus?.status === 'failed') {
      alert(`Xuất báo cáo thất bại: ${jobStatus.error_message || 'Lỗi không xác định'}`);
      setCurrentJobId(null);
      setExportingType(null);
    }
  }, [jobStatus]);

  // Data for Revenue Chart
  const revenueData = [
    { date: '01/11', revenue: 52000000 },
    { date: '02/11', revenue: 54000000 },
    { date: '03/11', revenue: 51000000 },
    { date: '04/11', revenue: 53000000 },
    { date: '05/11', revenue: 55000000 },
    { date: '06/11', revenue: 56000000 },
    { date: '07/11', revenue: 54000000 },
    { date: '08/11', revenue: 57000000 },
    { date: '09/11', revenue: 58000000 },
    { date: '10/11', revenue: 59000000 },
    { date: '11/11', revenue: 60000000 },
    { date: '12/11', revenue: 58000000 },
    { date: '13/11', revenue: 61000000 },
    { date: '14/11', revenue: 62000000 },
    { date: '15/11', revenue: 63000000 },
  ];

  // Data for Payment (using actual methods from database)
  const paymentData = [
    { method: 'Chuyển khoản', success: 850, failed: 45, total: 895, amount: 450000000 },
    { method: 'VietQR', success: 620, failed: 38, total: 658, amount: 320000000 },
    { method: 'Thẻ', success: 480, failed: 22, total: 502, amount: 280000000 },
    { method: 'Tiền mặt', success: 320, failed: 15, total: 335, amount: 180000000 },
  ];

  // Data for AR Aging Chart
  const arAgingData = [
    { range: '0-30 ngày', amount: 125000000, count: 45 },
    { range: '31-60 ngày', amount: 78000000, count: 28 },
    { range: '61-90 ngày', amount: 52000000, count: 18 },
    { range: '91-120 ngày', amount: 35000000, count: 12 },
    { range: '>120 ngày', amount: 28000000, count: 8 },
  ];

  // Data for Reconciliation Chart
  const reconciliationData = [
    { date: '18/11', reconciled: 45000000, pending: 5000000 },
    { date: '19/11', reconciled: 48000000, pending: 4500000 },
    { date: '20/11', reconciled: 52000000, pending: 3000000 },
    { date: '21/11', reconciled: 50000000, pending: 6000000 },
    { date: '22/11', reconciled: 55000000, pending: 4000000 },
  ];

  // Calculate KPIs for Revenue
  const totalRevenue = revenueData.reduce((sum, d) => sum + d.revenue, 0);
  const avgRevenuePerDay = totalRevenue / revenueData.length;
  const growthPercent = 12.5; // Mock data
  const peakDay = revenueData.reduce((max, d) => d.revenue > max.revenue ? d : max, revenueData[0]);

  // Calculate KPIs for Payment
  const totalTransactions = paymentData.reduce((sum, d) => sum + d.total, 0);
  const totalSuccess = paymentData.reduce((sum, d) => sum + d.success, 0);
  const successRate = ((totalSuccess / totalTransactions) * 100).toFixed(1);
  const totalAmountPaid = paymentData.reduce((sum, d) => sum + d.amount, 0);
  const bestMethod = paymentData.reduce((max, d) => d.total > max.total ? d : max, paymentData[0]);

  // Calculate KPIs for AR Aging
  const totalAR = arAgingData.reduce((sum, d) => sum + d.amount, 0);
  const overdueAmount = arAgingData.slice(1).reduce((sum, d) => sum + d.amount, 0); // Exclude 0-30 days
  const dso = 45; // Mock DSO
  const largestBucket = arAgingData.reduce((max, d) => d.amount > max.amount ? d : max, arAgingData[0]);

  // Calculate KPIs for Reconciliation
  const totalReconciled = reconciliationData.reduce((sum, d) => sum + d.reconciled, 0);
  const totalOutstanding = reconciliationData.reduce((sum, d) => sum + d.pending, 0);
  const reconRate = ((totalReconciled / (totalReconciled + totalOutstanding)) * 100).toFixed(1);
  const bestReconDay = reconciliationData.reduce((max, d) => d.reconciled > max.reconciled ? d : max, reconciliationData[0]);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(value);
  };

  const formatCurrencyShort = (value: number) => {
    return `${(value / 1000000).toFixed(0)}M`;
  };

  /**
   * Handle report download - triggers async export job
   * Backend only supports XLSX format and specific report types
   */
  const handleDownload = async (type: 'pdf' | 'xlsx', reportType: string) => {
    // Backend currently only supports xlsx
    if (type === 'pdf') {
      alert('Định dạng PDF đang được phát triển. Vui lòng sử dụng XLSX.');
      return;
    }
    
    const backendReportType = reportTypeMapping[reportType];
    if (!backendReportType) {
      alert(`Loại báo cáo "${reportType}" không được hỗ trợ`);
      return;
    }
    
    // Prevent multiple exports at once
    if (currentJobId) {
      alert('Đang xử lý xuất báo cáo khác. Vui lòng đợi.');
      return;
    }
    
    setExportingType(reportType);
    
    try {
      console.log(`📊 Exporting report: ${reportType} → backend type: ${backendReportType}`);
      
      const result = await createExportMutation.mutateAsync({
        report_type: backendReportType as any, // Cast to expected type
        format: 'xlsx',
      });
      
      console.log(`✅ Export job created: ${result.job_id}`);
      
      // Store job_id to poll status
      setCurrentJobId(result.job_id);
    } catch (error: any) {
      console.error('Export error:', error);
      const errorMsg = error?.response?.data?.detail || error?.message || 'Lỗi không xác định';
      alert(`Không thể tạo báo cáo: ${errorMsg}`);
      setExportingType(null);
    }
  };
  
  // Check if currently exporting a specific report type
  const isExporting = (reportType: string) => {
    return exportingType === reportType && (currentJobId !== null || createExportMutation.isPending);
  };

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
        <div className="mb-6" style={{ lineHeight: 1.2 }}>
          <h2 className="text-slate-900 mb-1 font-alata" style={{ fontSize: '32px', fontWeight: 400 }}>Báo cáo</h2>
          <p className="text-slate-600 font-darker-grotesque" style={{ fontSize: '18px' }}>
            Phân tích chi tiết và xuất báo cáo theo nhu cầu
          </p>
        </div>

        {/* Filters */}
        <Card className="border-0 shadow-lg mb-6 bg-white">
          <CardContent className="pt-6">
            <div className="flex items-center gap-4 flex-wrap">
              <div className="flex items-center gap-2">
                <CalendarIcon className="size-5 text-slate-500" />
                <span className="text-slate-700 font-darker-grotesque" style={{ fontSize: '18px', fontWeight: 500 }}>
                  Chu kỳ:
                </span>
              </div>
              <Select value={selectedMonth} onValueChange={setSelectedMonth}>
                <SelectTrigger className="w-[200px] font-darker-grotesque" style={{ fontSize: '18px' }}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="2024-11" className="font-darker-grotesque" style={{ fontSize: '17px' }}>Tháng 11/2024</SelectItem>
                  <SelectItem value="2024-10" className="font-darker-grotesque" style={{ fontSize: '17px' }}>Tháng 10/2024</SelectItem>
                  <SelectItem value="2024-09" className="font-darker-grotesque" style={{ fontSize: '17px' }}>Tháng 9/2024</SelectItem>
                  <SelectItem value="2024-08" className="font-darker-grotesque" style={{ fontSize: '17px' }}>Tháng 8/2024</SelectItem>
                  <SelectItem value="2024-07" className="font-darker-grotesque" style={{ fontSize: '17px' }}>Tháng 7/2024</SelectItem>
                </SelectContent>
              </Select>
              <Button
                variant="outline"
                onClick={() => setShowDateRangeDialog(true)}
                className="font-darker-grotesque"
                style={{ fontSize: '17px' }}
              >
                <CalendarIcon className="size-4 mr-2" />
                Khoảng thời gian
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Date Range Dialog */}
        {showDateRangeDialog && (
          <>
            <div className="fixed inset-0 bg-black/50 z-50" onClick={() => setShowDateRangeDialog(false)} />
            <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 bg-white rounded-lg shadow-2xl p-6 w-[400px]">
              <h3 className="font-alata text-slate-900 mb-4" style={{ fontSize: '24px', fontWeight: 400 }}>
                Chọn khoảng thời gian
              </h3>
              <div className="space-y-4">
                <div>
                  <label className="font-darker-grotesque text-slate-700 mb-2 block" style={{ fontSize: '17px' }}>
                    Từ ngày:
                  </label>
                  <input
                    type="date"
                    className="w-full px-4 py-2 border rounded-lg font-darker-grotesque"
                    style={{ fontSize: '17px' }}
                  />
                </div>
                <div>
                  <label className="font-darker-grotesque text-slate-700 mb-2 block" style={{ fontSize: '17px' }}>
                    Đến ngày:
                  </label>
                  <input
                    type="date"
                    className="w-full px-4 py-2 border rounded-lg font-darker-grotesque"
                    style={{ fontSize: '17px' }}
                  />
                </div>
                <div className="flex gap-2 mt-6">
                  <Button
                    className="flex-1 font-darker-grotesque"
                    style={{ fontSize: '17px' }}
                    onClick={() => {
                      setShowDateRangeDialog(false);
                      alert('Áp dụng khoảng thời gian đã chọn');
                    }}
                  >
                    Áp dụng
                  </Button>
                  <Button
                    variant="outline"
                    className="flex-1 font-darker-grotesque"
                    style={{ fontSize: '17px' }}
                    onClick={() => setShowDateRangeDialog(false)}
                  >
                    Hủy
                  </Button>
                </div>
              </div>
            </div>
          </>
        )}

        {/* Tabs for different reports */}
        <Tabs defaultValue="revenue" className="space-y-6">
          <TabsList className="grid w-full grid-cols-4 h-auto p-1 bg-slate-100">
            <TabsTrigger 
              value="revenue" 
              className="font-darker-grotesque data-[state=active]:bg-gradient-to-r data-[state=active]:from-blue-500 data-[state=active]:to-blue-600 data-[state=active]:text-white"
              style={{ fontSize: '18px', padding: '12px' }}
            >
              <TrendingUp className="size-5 mr-2" />
              Doanh thu
            </TabsTrigger>
            <TabsTrigger 
              value="payment" 
              className="font-darker-grotesque data-[state=active]:bg-gradient-to-r data-[state=active]:from-green-500 data-[state=active]:to-green-600 data-[state=active]:text-white"
              style={{ fontSize: '18px', padding: '12px' }}
            >
              <CreditCard className="size-5 mr-2" />
              Thanh toán
            </TabsTrigger>
            <TabsTrigger 
              value="ar" 
              className="font-darker-grotesque data-[state=active]:bg-gradient-to-r data-[state=active]:from-orange-500 data-[state=active]:to-orange-600 data-[state=active]:text-white"
              style={{ fontSize: '18px', padding: '12px' }}
            >
              <Users className="size-5 mr-2" />
              Công nợ
            </TabsTrigger>
            <TabsTrigger 
              value="reconcile" 
              className="font-darker-grotesque data-[state=active]:bg-gradient-to-r data-[state=active]:from-purple-500 data-[state=active]:to-purple-600 data-[state=active]:text-white"
              style={{ fontSize: '18px', padding: '12px' }}
            >
              <CheckCircle className="size-5 mr-2" />
              Đối soát
            </TabsTrigger>
          </TabsList>

          {/* Revenue Tab */}
          <TabsContent value="revenue" className="space-y-6">
            {/* KPI Cards */}
            <div className="grid grid-cols-4 gap-4">
              <Card className="border-0 shadow-md bg-gradient-to-br from-blue-500 to-blue-600 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 cursor-pointer">
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-blue-100 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>Tổng doanh thu</p>
                      <p className="text-white font-alata mt-2" style={{ fontSize: '28px', fontWeight: 700 }}>
                        {formatCurrencyShort(totalRevenue)}₫
                      </p>
                    </div>
                    <DollarSign className="size-10 text-blue-200" />
                  </div>
                </CardContent>
              </Card>

              <Card className="border-0 shadow-md bg-gradient-to-br from-cyan-500 to-cyan-600 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 cursor-pointer">
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-cyan-100 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>TB/Ngày</p>
                      <p className="text-white font-alata mt-2" style={{ fontSize: '28px', fontWeight: 700 }}>
                        {formatCurrencyShort(avgRevenuePerDay)}₫
                      </p>
                    </div>
                    <Activity className="size-10 text-cyan-200" />
                  </div>
                </CardContent>
              </Card>

              <Card className="border-0 shadow-md bg-gradient-to-br from-emerald-500 to-emerald-600 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 cursor-pointer">
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-emerald-100 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>Tăng trưởng</p>
                      <p className="text-white font-alata mt-2 flex items-center gap-2" style={{ fontSize: '28px', fontWeight: 700 }}>
                        {growthPercent}%
                        <ArrowUpRight className="size-7 text-emerald-200" />
                      </p>
                    </div>
                    <TrendingUp className="size-10 text-emerald-200" />
                  </div>
                </CardContent>
              </Card>

              <Card className="border-0 shadow-md bg-gradient-to-br from-violet-500 to-violet-600 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 cursor-pointer">
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-violet-100 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>Ngày cao nhất</p>
                      <p className="text-white font-alata mt-2" style={{ fontSize: '20px', fontWeight: 700 }}>
                        {peakDay.date}
                      </p>
                      <p className="text-violet-200 font-darker-grotesque mt-1" style={{ fontSize: '14px' }}>
                        {formatCurrencyShort(peakDay.revenue)}₫
                      </p>
                    </div>
                    <CheckCircle className="size-10 text-violet-200" />
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Insight */}
            <Card className="border-0 shadow-md bg-gradient-to-r from-blue-50 to-cyan-50 border-l-4 border-blue-500">
              <CardContent className="pt-6">
                <div className="flex items-start gap-3">
                  <div className="p-2 bg-blue-100 rounded-lg">
                    <TrendingUp className="size-6 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '16px', fontWeight: 600 }}>Thông tin quan trọng</p>
                    <p className="text-slate-700 font-darker-grotesque mt-1" style={{ fontSize: '17px' }}>
                      Doanh thu tăng <span className="font-alata text-blue-600" style={{ fontWeight: 700 }}>{growthPercent}%</span> so với kỳ trước. 
                      Ngày cao nhất: <span className="font-alata text-blue-600" style={{ fontWeight: 700 }}>{peakDay.date}</span> ({formatCurrency(peakDay.revenue)}).
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Chart and Table */}
            <Card className="border-0 shadow-lg bg-white">
              <CardHeader className="flex flex-row items-center justify-between pb-4">
                <div>
                  <CardTitle className="text-slate-900 font-alata" style={{ fontSize: '24px', fontWeight: 400 }}>
                    Biểu đồ doanh thu
                  </CardTitle>
                  <CardDescription className="font-darker-grotesque mt-1" style={{ fontSize: '16px' }}>
                    Theo ngày trong tháng 11/2024
                  </CardDescription>
                </div>
                <div className="flex gap-2">
                  <Button 
                    size="sm" 
                    variant="outline"
                    onClick={() => handleDownload('pdf', 'Doanh thu')}
                    className="font-darker-grotesque border-blue-300 text-blue-600 hover:bg-blue-50 hover:text-blue-700"
                    style={{ fontSize: '16px' }}
                  >
                    <Download className="size-4 mr-2" />
                    PDF
                  </Button>
                  <Button 
                    size="sm" 
                    variant="outline"
                    onClick={() => handleDownload('xlsx', 'Doanh thu')}
                    disabled={isExporting('Doanh thu')}
                    className="font-darker-grotesque border-blue-300 text-blue-600 hover:bg-blue-50 hover:text-blue-700"
                    style={{ fontSize: '16px' }}
                  >
                    {isExporting('Doanh thu') ? (
                      <Loader2 className="size-4 mr-2 animate-spin" />
                    ) : (
                      <Download className="size-4 mr-2" />
                    )}
                    XLSX
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="h-[350px] mb-6">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={revenueData}>
                      <defs>
                        <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                      <XAxis 
                        dataKey="date" 
                        stroke="#64748b"
                        style={{ fontSize: '14px', fontFamily: 'Darker Grotesque' }}
                      />
                      <YAxis 
                        stroke="#64748b"
                        tickFormatter={formatCurrencyShort}
                        style={{ fontSize: '14px', fontFamily: 'Darker Grotesque' }}
                      />
                      <Tooltip
                        formatter={(value: number) => [formatCurrency(value), 'Doanh thu']}
                        contentStyle={{ 
                          borderRadius: '8px', 
                          border: '1px solid #e2e8f0',
                          fontFamily: 'Darker Grotesque',
                          fontSize: '15px'
                        }}
                      />
                      <Area 
                        type="monotone" 
                        dataKey="revenue" 
                        stroke="#3b82f6" 
                        strokeWidth={3}
                        fill="url(#revenueGradient)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>

                {/* Table with sticky header */}
                <div className="border rounded-lg overflow-hidden">
                  <div className="overflow-auto max-h-[400px]">
                    <table className="w-full">
                      <thead className="sticky top-0 bg-gradient-to-r from-blue-50 to-blue-100 z-10">
                        <tr>
                          <th className="text-left p-4 font-darker-grotesque text-slate-900 border-b border-slate-200" style={{ fontSize: '18px', fontWeight: 600 }}>Ngày</th>
                          <th className="text-center p-4 font-darker-grotesque text-slate-900 border-b border-slate-200" style={{ fontSize: '18px', fontWeight: 600 }}>Doanh thu</th>
                          <th className="text-right p-4 font-darker-grotesque text-slate-900 border-b border-slate-200" style={{ fontSize: '18px', fontWeight: 600 }}>So với TB</th>
                        </tr>
                      </thead>
                      <tbody>
                        {revenueData.map((item, idx) => {
                          const diff = item.revenue - avgRevenuePerDay;
                          const diffPercent = ((diff / avgRevenuePerDay) * 100).toFixed(1);
                          return (
                            <tr key={idx} className={`border-b border-slate-100 hover:bg-blue-50/30 transition-colors ${idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'}`}>
                              <td className="p-4 font-darker-grotesque text-slate-700" style={{ fontSize: '17px' }}>{item.date}</td>
                              <td className="p-4 text-center font-alata text-slate-900" style={{ fontSize: '19px', fontWeight: 600 }}>
                                {formatCurrency(item.revenue)}
                              </td>
                              <td className="p-4 text-right font-darker-grotesque" style={{ fontSize: '16px' }}>
                                <span className={diff >= 0 ? 'text-green-600' : 'text-red-600'}>
                                  {diff >= 0 ? '+' : ''}{diffPercent}%
                                </span>
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
          </TabsContent>

          {/* Payment Tab */}
          <TabsContent value="payment" className="space-y-6">
            {/* KPI Cards */}
            <div className="grid grid-cols-4 gap-4">
              <Card className="border-0 shadow-md bg-gradient-to-br from-green-500 to-green-600 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 cursor-pointer">
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-green-100 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>Tổng giao dịch</p>
                      <p className="text-white font-alata mt-2" style={{ fontSize: '28px', fontWeight: 700 }}>
                        {totalTransactions.toLocaleString()}
                      </p>
                    </div>
                    <CreditCard className="size-10 text-green-200" />
                  </div>
                </CardContent>
              </Card>

              <Card className="border-0 shadow-md bg-gradient-to-br from-emerald-500 to-emerald-600 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 cursor-pointer">
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-emerald-100 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>Tỷ lệ thành công</p>
                      <p className="text-white font-alata mt-2" style={{ fontSize: '28px', fontWeight: 700 }}>
                        {successRate}%
                      </p>
                    </div>
                    <CheckCircle className="size-10 text-emerald-200" />
                  </div>
                </CardContent>
              </Card>

              <Card className="border-0 shadow-md bg-gradient-to-br from-teal-500 to-teal-600 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 cursor-pointer">
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-teal-100 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>Tổng tiền thu</p>
                      <p className="text-white font-alata mt-2" style={{ fontSize: '28px', fontWeight: 700 }}>
                        {formatCurrencyShort(totalAmountPaid)}₫
                      </p>
                    </div>
                    <DollarSign className="size-10 text-teal-200" />
                  </div>
                </CardContent>
              </Card>

              <Card className="border-0 shadow-md bg-gradient-to-br from-cyan-500 to-cyan-600 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 cursor-pointer">
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-cyan-100 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>PT phổ biến nhất</p>
                      <p className="text-white font-alata mt-2" style={{ fontSize: '20px', fontWeight: 700 }}>
                        {bestMethod.method}
                      </p>
                      <p className="text-cyan-200 font-darker-grotesque mt-1" style={{ fontSize: '14px' }}>
                        {bestMethod.total} giao dịch
                      </p>
                    </div>
                    <TrendingUp className="size-10 text-cyan-200" />
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Insight */}
            <Card className="border-0 shadow-md bg-gradient-to-r from-green-50 to-emerald-50 border-l-4 border-green-500">
              <CardContent className="pt-6">
                <div className="flex items-start gap-3">
                  <div className="p-2 bg-green-100 rounded-lg">
                    <CheckCircle className="size-6 text-green-600" />
                  </div>
                  <div>
                    <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '16px', fontWeight: 600 }}>Thông tin quan trọng</p>
                    <p className="text-slate-700 font-darker-grotesque mt-1" style={{ fontSize: '17px' }}>
                      <span className="font-alata text-green-600" style={{ fontWeight: 700 }}>{bestMethod.method}</span> là phương thức phổ biến nhất với {bestMethod.total} giao dịch. 
                      Tỷ lệ thành công đạt <span className="font-alata text-green-600" style={{ fontWeight: 700 }}>{successRate}%</span>.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Chart and Table */}
            <Card className="border-0 shadow-lg bg-white">
              <CardHeader className="flex flex-row items-center justify-between pb-4">
                <div>
                  <CardTitle className="text-slate-900 font-alata" style={{ fontSize: '24px', fontWeight: 400 }}>
                    Thống kê thanh toán
                  </CardTitle>
                  <CardDescription className="font-darker-grotesque mt-1" style={{ fontSize: '16px' }}>
                    Theo phương thức trong tháng 11/2024
                  </CardDescription>
                </div>
                <div className="flex gap-2">
                  <Button 
                    size="sm" 
                    variant="outline"
                    onClick={() => handleDownload('pdf', 'Thanh toán')}
                    className="font-darker-grotesque border-green-300 text-green-600 hover:bg-green-50 hover:text-green-700"
                    style={{ fontSize: '16px' }}
                  >
                    <Download className="size-4 mr-2" />
                    PDF
                  </Button>
                  <Button 
                    size="sm" 
                    variant="outline"
                    onClick={() => handleDownload('xlsx', 'Thanh toán')}
                    disabled={isExporting('Thanh toán')}
                    className="font-darker-grotesque border-green-300 text-green-600 hover:bg-green-50 hover:text-green-700"
                    style={{ fontSize: '16px' }}
                  >
                    {isExporting('Thanh toán') ? (
                      <Loader2 className="size-4 mr-2 animate-spin" />
                    ) : (
                      <Download className="size-4 mr-2" />
                    )}
                    XLSX
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="h-[350px] mb-6">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={paymentData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                      <XAxis 
                        dataKey="method" 
                        stroke="#64748b"
                        style={{ fontSize: '14px', fontFamily: 'Darker Grotesque' }}
                      />
                      <YAxis 
                        stroke="#64748b"
                        style={{ fontSize: '14px', fontFamily: 'Darker Grotesque' }}
                      />
                      <Tooltip
                        contentStyle={{ 
                          borderRadius: '8px', 
                          border: '1px solid #e2e8f0',
                          fontFamily: 'Darker Grotesque',
                          fontSize: '15px'
                        }}
                      />
                      <Legend 
                        wrapperStyle={{ fontFamily: 'Darker Grotesque', fontSize: '15px' }}
                      />
                      <Bar dataKey="success" fill="#10b981" name="Thành công" radius={[8, 8, 0, 0]} />
                      <Bar dataKey="failed" fill="#ef4444" name="Thất bại" radius={[8, 8, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                {/* Table with sticky header */}
                <div className="border rounded-lg overflow-hidden">
                  <div className="overflow-auto max-h-[400px]">
                    <table className="w-full">
                      <thead className="sticky top-0 bg-gradient-to-r from-green-50 to-green-100 z-10">
                        <tr>
                          <th className="text-left p-4 font-darker-grotesque text-slate-900 border-b border-slate-200" style={{ fontSize: '18px', fontWeight: 600 }}>Phương thức</th>
                          <th className="text-center p-4 font-darker-grotesque text-slate-900 border-b border-slate-200" style={{ fontSize: '18px', fontWeight: 600 }}>Thành công</th>
                          <th className="text-center p-4 font-darker-grotesque text-slate-900 border-b border-slate-200" style={{ fontSize: '18px', fontWeight: 600 }}>Thất bại</th>
                          <th className="text-center p-4 font-darker-grotesque text-slate-900 border-b border-slate-200" style={{ fontSize: '18px', fontWeight: 600 }}>Tổng</th>
                          <th className="text-center p-4 font-darker-grotesque text-slate-900 border-b border-slate-200" style={{ fontSize: '18px', fontWeight: 600 }}>Tỷ lệ</th>
                        </tr>
                      </thead>
                      <tbody>
                        {paymentData.map((item, idx) => {
                          const rate = ((item.success / item.total) * 100).toFixed(1);
                          return (
                            <tr key={idx} className={`border-b border-slate-100 hover:bg-green-50/30 transition-colors ${idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'}`}>
                              <td className="p-4 font-darker-grotesque text-slate-900" style={{ fontSize: '17px', fontWeight: 500 }}>{item.method}</td>
                              <td className="p-4 text-center font-alata text-green-600" style={{ fontSize: '18px', fontWeight: 600 }}>
                                {item.success}
                              </td>
                              <td className="p-4 text-center font-alata text-red-600" style={{ fontSize: '18px', fontWeight: 600 }}>
                                {item.failed}
                              </td>
                              <td className="p-4 text-center font-alata text-slate-900" style={{ fontSize: '18px', fontWeight: 600 }}>
                                {item.total}
                              </td>
                              <td className="p-4 text-center">
                                <span className={`font-darker-grotesque px-3 py-1 rounded-full ${parseFloat(rate) >= 90 ? 'bg-green-100 text-green-700' : parseFloat(rate) >= 80 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'}`} style={{ fontSize: '16px', fontWeight: 600 }}>
                                  {rate}%
                                </span>
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
          </TabsContent>

          {/* AR Aging Tab */}
          <TabsContent value="ar" className="space-y-6">
            {/* KPI Cards */}
            <div className="grid grid-cols-4 gap-4">
              <Card className="border-0 shadow-md bg-gradient-to-br from-orange-500 to-orange-600 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 cursor-pointer">
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-orange-100 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>Tổng phải thu</p>
                      <p className="text-white font-alata mt-2" style={{ fontSize: '28px', fontWeight: 700 }}>
                        {formatCurrencyShort(totalAR)}₫
                      </p>
                    </div>
                    <DollarSign className="size-10 text-orange-200" />
                  </div>
                </CardContent>
              </Card>

              <Card className="border-0 shadow-md bg-gradient-to-br from-red-500 to-red-600 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 cursor-pointer">
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-red-100 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>Nợ quá hạn</p>
                      <p className="text-white font-alata mt-2" style={{ fontSize: '28px', fontWeight: 700 }}>
                        {formatCurrencyShort(overdueAmount)}₫
                      </p>
                    </div>
                    <AlertCircle className="size-10 text-red-200" />
                  </div>
                </CardContent>
              </Card>

              <Card className="border-0 shadow-md bg-gradient-to-br from-amber-500 to-amber-600 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 cursor-pointer">
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-amber-100 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>DSO</p>
                      <p className="text-white font-alata mt-2" style={{ fontSize: '28px', fontWeight: 700 }}>
                        {dso} ngày
                      </p>
                    </div>
                    <Clock className="size-10 text-amber-200" />
                  </div>
                </CardContent>
              </Card>

              <Card className="border-0 shadow-md bg-gradient-to-br from-rose-500 to-rose-600 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 cursor-pointer">
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-rose-100 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>Nhóm nợ lớn nhất</p>
                      <p className="text-white font-alata mt-2" style={{ fontSize: '20px', fontWeight: 700 }}>
                        {largestBucket.range}
                      </p>
                      <p className="text-rose-200 font-darker-grotesque mt-1" style={{ fontSize: '14px' }}>
                        {formatCurrencyShort(largestBucket.amount)}₫
                      </p>
                    </div>
                    <TrendingUp className="size-10 text-rose-200" />
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Insight */}
            <Card className="border-0 shadow-md bg-gradient-to-r from-orange-50 to-amber-50 border-l-4 border-orange-500">
              <CardContent className="pt-6">
                <div className="flex items-start gap-3">
                  <div className="p-2 bg-orange-100 rounded-lg">
                    <AlertCircle className="size-6 text-orange-600" />
                  </div>
                  <div>
                    <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '16px', fontWeight: 600 }}>Thông tin quan trọng</p>
                    <p className="text-slate-700 font-darker-grotesque mt-1" style={{ fontSize: '17px' }}>
                      Nhóm <span className="font-alata text-orange-600" style={{ fontWeight: 700 }}>{largestBucket.range}</span> chiếm tỷ lệ cao nhất 
                      ({formatCurrency(largestBucket.amount)}). DSO hiện tại = <span className="font-alata text-orange-600" style={{ fontWeight: 700 }}>{dso} ngày</span>.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Chart and Table */}
            <Card className="border-0 shadow-lg bg-white">
              <CardHeader className="flex flex-row items-center justify-between pb-4">
                <div>
                  <CardTitle className="text-slate-900 font-alata" style={{ fontSize: '24px', fontWeight: 400 }}>
                    Phân tích công nợ
                  </CardTitle>
                  <CardDescription className="font-darker-grotesque mt-1" style={{ fontSize: '16px' }}>
                    Phân loại theo độ tuổi nợ
                  </CardDescription>
                </div>
                <div className="flex gap-2">
                  <Button 
                    size="sm" 
                    variant="outline"
                    onClick={() => handleDownload('pdf', 'Công nợ')}
                    className="font-darker-grotesque border-orange-300 text-orange-600 hover:bg-orange-50 hover:text-orange-700"
                    style={{ fontSize: '16px' }}
                  >
                    <Download className="size-4 mr-2" />
                    PDF
                  </Button>
                  <Button 
                    size="sm" 
                    variant="outline"
                    onClick={() => handleDownload('xlsx', 'Công nợ')}
                    disabled={isExporting('Công nợ')}
                    className="font-darker-grotesque border-orange-300 text-orange-600 hover:bg-orange-50 hover:text-orange-700"
                    style={{ fontSize: '16px' }}
                  >
                    {isExporting('Công nợ') ? (
                      <Loader2 className="size-4 mr-2 animate-spin" />
                    ) : (
                      <Download className="size-4 mr-2" />
                    )}
                    XLSX
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="h-[350px] mb-6">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={arAgingData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                      <XAxis 
                        dataKey="range" 
                        stroke="#64748b"
                        style={{ fontSize: '14px', fontFamily: 'Darker Grotesque' }}
                      />
                      <YAxis 
                        stroke="#64748b"
                        tickFormatter={formatCurrencyShort}
                        style={{ fontSize: '14px', fontFamily: 'Darker Grotesque' }}
                      />
                      <Tooltip
                        formatter={(value: number) => [formatCurrency(value), 'Số tiền']}
                        contentStyle={{ 
                          borderRadius: '8px', 
                          border: '1px solid #e2e8f0',
                          fontFamily: 'Darker Grotesque',
                          fontSize: '15px'
                        }}
                      />
                      <Bar dataKey="amount" fill="#f97316" name="Số tiền" radius={[8, 8, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                {/* Table with sticky header */}
                <div className="border rounded-lg overflow-hidden">
                  <div className="overflow-auto max-h-[400px]">
                    <table className="w-full">
                      <thead className="sticky top-0 bg-gradient-to-r from-orange-50 to-orange-100 z-10">
                        <tr>
                          <th className="text-left p-4 font-darker-grotesque text-slate-900 border-b border-slate-200" style={{ fontSize: '18px', fontWeight: 600 }}>Nhóm tuổi nợ</th>
                          <th className="text-center p-4 font-darker-grotesque text-slate-900 border-b border-slate-200" style={{ fontSize: '18px', fontWeight: 600 }}>Số tiền</th>
                          <th className="text-center p-4 font-darker-grotesque text-slate-900 border-b border-slate-200" style={{ fontSize: '18px', fontWeight: 600 }}>Số lượng</th>
                          <th className="text-right p-4 font-darker-grotesque text-slate-900 border-b border-slate-200" style={{ fontSize: '18px', fontWeight: 600 }}>% Tổng</th>
                        </tr>
                      </thead>
                      <tbody>
                        {arAgingData.map((item, idx) => {
                          const percent = ((item.amount / totalAR) * 100).toFixed(1);
                          return (
                            <tr key={idx} className={`border-b border-slate-100 hover:bg-orange-50/30 transition-colors ${idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'}`}>
                              <td className="p-4 font-darker-grotesque text-slate-900" style={{ fontSize: '17px', fontWeight: 500 }}>{item.range}</td>
                              <td className="p-4 text-center font-alata text-slate-900" style={{ fontSize: '19px', fontWeight: 600 }}>
                                {formatCurrency(item.amount)}
                              </td>
                              <td className="p-4 text-center font-darker-grotesque text-slate-700" style={{ fontSize: '17px' }}>
                                {item.count}
                              </td>
                              <td className="p-4 text-right font-darker-grotesque text-orange-600" style={{ fontSize: '17px', fontWeight: 600 }}>
                                {percent}%
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
          </TabsContent>

          {/* Reconciliation Tab */}
          <TabsContent value="reconcile" className="space-y-6">
            {/* KPI Cards */}
            <div className="grid grid-cols-4 gap-4">
              <Card className="border-0 shadow-md bg-gradient-to-br from-purple-500 to-purple-600 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 cursor-pointer">
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-purple-100 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>Đã đối soát</p>
                      <p className="text-white font-alata mt-2" style={{ fontSize: '28px', fontWeight: 700 }}>
                        {formatCurrencyShort(totalReconciled)}₫
                      </p>
                    </div>
                    <CheckCircle className="size-10 text-purple-200" />
                  </div>
                </CardContent>
              </Card>

              <Card className="border-0 shadow-md bg-gradient-to-br from-pink-500 to-pink-600 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 cursor-pointer">
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-pink-100 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>Chưa đối soát</p>
                      <p className="text-white font-alata mt-2" style={{ fontSize: '28px', fontWeight: 700 }}>
                        {formatCurrencyShort(totalOutstanding)}₫
                      </p>
                    </div>
                    <Clock className="size-10 text-pink-200" />
                  </div>
                </CardContent>
              </Card>

              <Card className="border-0 shadow-md bg-gradient-to-br from-indigo-500 to-indigo-600 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 cursor-pointer">
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-indigo-100 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>Tỷ lệ đối soát</p>
                      <p className="text-white font-alata mt-2" style={{ fontSize: '28px', fontWeight: 700 }}>
                        {reconRate}%
                      </p>
                    </div>
                    <Activity className="size-10 text-indigo-200" />
                  </div>
                </CardContent>
              </Card>

              <Card className="border-0 shadow-md bg-gradient-to-br from-violet-500 to-violet-600 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 cursor-pointer">
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-violet-100 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>Ngày đối soát tốt</p>
                      <p className="text-white font-alata mt-2" style={{ fontSize: '20px', fontWeight: 700 }}>
                        {bestReconDay.date}
                      </p>
                      <p className="text-violet-200 font-darker-grotesque mt-1" style={{ fontSize: '14px' }}>
                        {formatCurrencyShort(bestReconDay.reconciled)}₫
                      </p>
                    </div>
                    <TrendingUp className="size-10 text-violet-200" />
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Insight */}
            <Card className="border-0 shadow-md bg-gradient-to-r from-purple-50 to-pink-50 border-l-4 border-purple-500">
              <CardContent className="pt-6">
                <div className="flex items-start gap-3">
                  <div className="p-2 bg-purple-100 rounded-lg">
                    <CheckCircle className="size-6 text-purple-600" />
                  </div>
                  <div>
                    <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '16px', fontWeight: 600 }}>Thông tin quan trọng</p>
                    <p className="text-slate-700 font-darker-grotesque mt-1" style={{ fontSize: '17px' }}>
                      Tỷ lệ đối soát đạt <span className="font-alata text-purple-600" style={{ fontWeight: 700 }}>{reconRate}%</span>, tăng 
                      <span className="font-alata text-purple-600" style={{ fontWeight: 700 }}> 3.2%</span> so với kỳ trước.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Chart and Table */}
            <Card className="border-0 shadow-lg bg-white">
              <CardHeader className="flex flex-row items-center justify-between pb-4">
                <div>
                  <CardTitle className="text-slate-900 font-alata" style={{ fontSize: '24px', fontWeight: 400 }}>
                    Biểu đồ đối soát
                  </CardTitle>
                  <CardDescription className="font-darker-grotesque mt-1" style={{ fontSize: '16px' }}>
                    Theo ngày trong tuần
                  </CardDescription>
                </div>
                <div className="flex gap-2">
                  <Button 
                    size="sm" 
                    variant="outline"
                    onClick={() => handleDownload('pdf', 'Đối soát')}
                    className="font-darker-grotesque border-purple-300 text-purple-600 hover:bg-purple-50 hover:text-purple-700"
                    style={{ fontSize: '16px' }}
                  >
                    <Download className="size-4 mr-2" />
                    PDF
                  </Button>
                  <Button 
                    size="sm" 
                    variant="outline"
                    onClick={() => handleDownload('xlsx', 'Đối soát')}
                    disabled={isExporting('Đối soát')}
                    className="font-darker-grotesque border-purple-300 text-purple-600 hover:bg-purple-50 hover:text-purple-700"
                    style={{ fontSize: '16px' }}
                  >
                    {isExporting('Đối soát') ? (
                      <Loader2 className="size-4 mr-2 animate-spin" />
                    ) : (
                      <Download className="size-4 mr-2" />
                    )}
                    XLSX
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="h-[350px] mb-6">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={reconciliationData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                      <XAxis 
                        dataKey="date" 
                        stroke="#64748b"
                        style={{ fontSize: '14px', fontFamily: 'Darker Grotesque' }}
                      />
                      <YAxis 
                        stroke="#64748b"
                        tickFormatter={formatCurrencyShort}
                        style={{ fontSize: '14px', fontFamily: 'Darker Grotesque' }}
                      />
                      <Tooltip
                        formatter={(value: number) => [formatCurrency(value), '']}
                        contentStyle={{ 
                          borderRadius: '8px', 
                          border: '1px solid #e2e8f0',
                          fontFamily: 'Darker Grotesque',
                          fontSize: '15px'
                        }}
                      />
                      <Legend 
                        wrapperStyle={{ fontFamily: 'Darker Grotesque', fontSize: '15px' }}
                      />
                      <Bar dataKey="reconciled" fill="#9333ea" name="Đã đối soát" radius={[8, 8, 0, 0]} />
                      <Bar dataKey="pending" fill="#ec4899" name="Chưa đối soát" radius={[8, 8, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                {/* Table with sticky header */}
                <div className="border rounded-lg overflow-hidden">
                  <div className="overflow-auto max-h-[400px]">
                    <table className="w-full">
                      <thead className="sticky top-0 bg-gradient-to-r from-purple-50 to-purple-100 z-10">
                        <tr>
                          <th className="text-left p-4 font-darker-grotesque text-slate-900 border-b border-slate-200" style={{ fontSize: '18px', fontWeight: 600 }}>Ngày</th>
                          <th className="text-center p-4 font-darker-grotesque text-slate-900 border-b border-slate-200" style={{ fontSize: '18px', fontWeight: 600 }}>Đã đối soát</th>
                          <th className="text-center p-4 font-darker-grotesque text-slate-900 border-b border-slate-200" style={{ fontSize: '18px', fontWeight: 600 }}>Chưa đối soát</th>
                          <th className="text-right p-4 font-darker-grotesque text-slate-900 border-b border-slate-200" style={{ fontSize: '18px', fontWeight: 600 }}>Tỷ lệ</th>
                        </tr>
                      </thead>
                      <tbody>
                        {reconciliationData.map((item, idx) => {
                          const rate = ((item.reconciled / (item.reconciled + item.pending)) * 100).toFixed(1);
                          return (
                            <tr key={idx} className={`border-b border-slate-100 hover:bg-purple-50/30 transition-colors ${idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'}`}>
                              <td className="p-4 font-darker-grotesque text-slate-700" style={{ fontSize: '17px' }}>{item.date}</td>
                              <td className="p-4 text-center font-alata text-purple-600" style={{ fontSize: '19px', fontWeight: 600 }}>
                                {formatCurrency(item.reconciled)}
                              </td>
                              <td className="p-4 text-center font-alata text-pink-600" style={{ fontSize: '19px', fontWeight: 600 }}>
                                {formatCurrency(item.pending)}
                              </td>
                              <td className="p-4 text-right">
                                <span className={`font-darker-grotesque px-3 py-1 rounded-full ${parseFloat(rate) >= 90 ? 'bg-green-100 text-green-700' : parseFloat(rate) >= 80 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'}`} style={{ fontSize: '16px', fontWeight: 600 }}>
                                  {rate}%
                                </span>
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
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
