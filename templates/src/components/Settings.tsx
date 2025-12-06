import { Bell, Menu, X, Save, Clock, RefreshCw, Info, TrendingUp, AlertTriangle, Calendar, Zap } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { UserMenu } from './UserMenu';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { useState, useEffect } from 'react';
import { Badge } from './ui/badge';
import { useSidebar } from '../contexts/SidebarContext';
import { useAISettings, useUpdateAISettings } from '../lib/api/hooks';
import { toast } from 'sonner';

export function Settings() {
  const { isSidebarOpen, toggleSidebar } = useSidebar();
  
  // Fetch settings from API
  const { data: settings } = useAISettings();
  const updateSettingsMutation = useUpdateAISettings();

  // Prophet Config State
  const [forecastWindow, setForecastWindow] = useState('30');
  const [forecastConfidence, setForecastConfidence] = useState(0.95);
  const [seasonalityMode, setSeasonalityMode] = useState('multiplicative');

  // Anomaly Detection Config State
  const [anomalyThreshold, setAnomalyThreshold] = useState(0.85);
  const [minAnomalyAmount, setMinAnomalyAmount] = useState(1000000);
  const [alertSeverity, setAlertSeverity] = useState('medium');

  // Job Schedule State
  const [forecastFrequency, setForecastFrequency] = useState('daily');
  const [weekDay, setWeekDay] = useState('monday');
  const [jobTime, setJobTime] = useState('02:00');
  const [autoRetry, setAutoRetry] = useState(true);

  const [showSaveSuccess, setShowSaveSuccess] = useState(false);

  // Load settings from API when available
  useEffect(() => {
    if (settings) {
      setForecastWindow(String(settings.forecast_window || 30));
      setForecastConfidence(settings.forecast_confidence || 0.95);
      setSeasonalityMode(settings.seasonality_mode || 'multiplicative');
      setAnomalyThreshold(settings.anomaly_threshold || 0.85);
      setMinAnomalyAmount(settings.min_anomaly_amount || 1000000);
    }
  }, [settings]);

  const handleSaveSettings = () => {
    updateSettingsMutation.mutate(
      {
        forecast_window: parseInt(forecastWindow),
        forecast_confidence: forecastConfidence,
        seasonality_mode: seasonalityMode,
        anomaly_threshold: anomalyThreshold,
        min_anomaly_amount: minAnomalyAmount,
      },
      {
        onSuccess: () => {
          setShowSaveSuccess(true);
          setTimeout(() => setShowSaveSuccess(false), 3000);
          toast.success('Đã lưu cấu hình thành công!');
        },
        onError: () => {
          toast.error('Lỗi khi lưu cấu hình');
        },
      }
    );
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(value);
  };

  const weekDays = [
    { value: 'monday', label: 'Thứ 2' },
    { value: 'tuesday', label: 'Thứ 3' },
    { value: 'wednesday', label: 'Thứ 4' },
    { value: 'thursday', label: 'Thứ 5' },
    { value: 'friday', label: 'Thứ 6' },
    { value: 'saturday', label: 'Thứ 7' },
    { value: 'sunday', label: 'Chủ nhật' },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-emerald-50/20 to-slate-100">
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
      <main className="p-8 max-w-[1400px] mx-auto">
        <div className="mb-6" style={{ lineHeight: 1.2 }}>
          <h2 className="text-slate-900 mb-1 font-alata" style={{ fontSize: '32px', fontWeight: 400 }}>Cấu hình hệ thống</h2>
          <p className="text-slate-600 font-darker-grotesque" style={{ fontSize: '18px' }}>
            Tùy chỉnh các thông số Prophet, Anomaly Detection và lịch chạy dự báo
          </p>
        </div>

        {/* Success Message */}
        {showSaveSuccess && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg flex items-center gap-3">
            <div className="size-10 bg-green-500 rounded-full flex items-center justify-center">
              <Save className="size-5 text-white" />
            </div>
            <div>
              <p className="text-green-900 font-darker-grotesque" style={{ fontSize: '17px', fontWeight: 600 }}>
                Lưu cấu hình thành công!
              </p>
              <p className="text-green-700 font-darker-grotesque" style={{ fontSize: '15px' }}>
                Các thay đổi đã được áp dụng vào hệ thống
              </p>
            </div>
          </div>
        )}

        {/* Overview Cards */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <Card className="border-0 shadow-md bg-gradient-to-br from-emerald-500 to-emerald-600 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 cursor-pointer">
            <CardContent className="pt-6">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-emerald-100 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>Mô hình Prophet</p>
                  <p className="text-white font-alata mt-2" style={{ fontSize: '24px', fontWeight: 700 }}>
                    Hoạt động
                  </p>
                </div>
                <TrendingUp className="size-10 text-emerald-200" />
              </div>
            </CardContent>
          </Card>

          <Card className="border-0 shadow-md bg-gradient-to-br from-teal-500 to-teal-600 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 cursor-pointer">
            <CardContent className="pt-6">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-teal-100 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>Anomaly Detection</p>
                  <p className="text-white font-alata mt-2" style={{ fontSize: '24px', fontWeight: 700 }}>
                    Hoạt động
                  </p>
                </div>
                <AlertTriangle className="size-10 text-teal-200" />
              </div>
            </CardContent>
          </Card>

          <Card className="border-0 shadow-md bg-gradient-to-br from-cyan-500 to-cyan-600 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 cursor-pointer">
            <CardContent className="pt-6">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-cyan-100 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>Lần chạy gần nhất</p>
                  <p className="text-white font-alata mt-2" style={{ fontSize: '24px', fontWeight: 700 }}>
                    Hôm nay
                  </p>
                </div>
                <Clock className="size-10 text-cyan-200" />
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          {/* Row 1: Prophet + Anomaly Detection */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Prophet Configuration */}
            <Card className="border-0 shadow-lg bg-white">
              <CardHeader className="border-b bg-gradient-to-r from-emerald-50 to-green-50 pb-4">
                <div className="flex items-center gap-3">
                  <div className="p-3 bg-emerald-500 rounded-lg">
                    <TrendingUp className="size-6 text-white" />
                  </div>
                  <div>
                    <CardTitle className="font-alata text-slate-900" style={{ fontSize: '24px', fontWeight: 500 }}>
                      Cấu hình Prophet
                    </CardTitle>
                    <CardDescription className="font-darker-grotesque text-slate-600 mt-1" style={{ fontSize: '16px' }}>
                      Mô hình dự báo dòng tiền
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-6 space-y-6">
                {/* Forecast Window */}
                <div>
                  <label className="block mb-3">
                    <span className="font-darker-grotesque text-slate-900" style={{ fontSize: '17px', fontWeight: 600 }}>
                      Cửa sổ dự báo
                    </span>
                  </label>
                  <Select value={forecastWindow} onValueChange={setForecastWindow}>
                    <SelectTrigger className="font-darker-grotesque" style={{ fontSize: '17px' }}>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="7" className="font-darker-grotesque" style={{ fontSize: '16px' }}>7 ngày</SelectItem>
                      <SelectItem value="14" className="font-darker-grotesque" style={{ fontSize: '16px' }}>14 ngày</SelectItem>
                      <SelectItem value="30" className="font-darker-grotesque" style={{ fontSize: '16px' }}>30 ngày</SelectItem>
                      <SelectItem value="60" className="font-darker-grotesque" style={{ fontSize: '16px' }}>60 ngày</SelectItem>
                      <SelectItem value="90" className="font-darker-grotesque" style={{ fontSize: '16px' }}>90 ngày</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="mt-2 text-slate-600 font-darker-grotesque" style={{ fontSize: '14px' }}>
                    Số ngày dự báo trong tương lai
                  </p>
                </div>

                {/* Forecast Confidence */}
                <div>
                  <label className="flex items-center gap-2 mb-3">
                    <span className="font-darker-grotesque text-slate-900" style={{ fontSize: '17px', fontWeight: 600 }}>
                      Độ tin cậy dự báo
                    </span>
                    <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200 border font-darker-grotesque" style={{ fontSize: '13px' }}>
                      {(forecastConfidence * 100).toFixed(0)}%
                    </Badge>
                  </label>
                  <div className="space-y-2">
                    <input
                      type="range"
                      min="0.80"
                      max="0.99"
                      step="0.01"
                      value={forecastConfidence}
                      onChange={(e) => setForecastConfidence(parseFloat(e.target.value))}
                      className="w-full h-2 bg-emerald-200 rounded-lg appearance-none cursor-pointer accent-emerald-500"
                    />
                    <div className="flex justify-between text-slate-500 font-darker-grotesque" style={{ fontSize: '14px' }}>
                      <span>80%</span>
                      <span>90%</span>
                      <span>99%</span>
                    </div>
                  </div>
                  <div className="mt-3 p-3 bg-blue-50 rounded-lg flex items-start gap-2">
                    <Info className="size-4 text-blue-600 mt-0.5 flex-shrink-0" />
                    <p className="text-blue-800 font-darker-grotesque" style={{ fontSize: '14px' }}>
                      Độ tin cậy cao hơn sẽ tạo khoảng dự báo rộng hơn
                    </p>
                  </div>
                </div>

                {/* Seasonality Mode */}
                <div>
                  <label className="block mb-3">
                    <span className="font-darker-grotesque text-slate-900" style={{ fontSize: '17px', fontWeight: 600 }}>
                      Chế độ mùa vụ
                    </span>
                  </label>
                  <Select value={seasonalityMode} onValueChange={setSeasonalityMode}>
                    <SelectTrigger className="font-darker-grotesque" style={{ fontSize: '17px' }}>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="additive" className="font-darker-grotesque" style={{ fontSize: '16px' }}>
                        Additive (Cộng tính)
                      </SelectItem>
                      <SelectItem value="multiplicative" className="font-darker-grotesque" style={{ fontSize: '16px' }}>
                        Multiplicative (Nhân tính)
                      </SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="mt-2 text-slate-600 font-darker-grotesque" style={{ fontSize: '14px' }}>
                    Multiplicative phù hợp với dữ liệu có xu hướng tăng trưởng
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Anomaly Detection Configuration */}
            <Card className="border-0 shadow-lg bg-white">
              <CardHeader className="border-b bg-gradient-to-r from-teal-50 to-cyan-50 pb-4">
                <div className="flex items-center gap-3">
                  <div className="p-3 bg-teal-500 rounded-lg">
                    <AlertTriangle className="size-6 text-white" />
                  </div>
                  <div>
                    <CardTitle className="font-alata text-slate-900" style={{ fontSize: '24px', fontWeight: 500 }}>
                      Cấu hình Anomaly Detection
                    </CardTitle>
                    <CardDescription className="font-darker-grotesque text-slate-600 mt-1" style={{ fontSize: '16px' }}>
                      Phát hiện cảnh báo bất thường
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-6 space-y-6">
                {/* Anomaly Threshold */}
                <div>
                  <label className="flex items-center gap-2 mb-3">
                    <span className="font-darker-grotesque text-slate-900" style={{ fontSize: '17px', fontWeight: 600 }}>
                      Ngưỡng bất thường
                    </span>
                    <Badge className="bg-teal-100 text-teal-700 border-teal-200 border font-darker-grotesque" style={{ fontSize: '13px' }}>
                      {anomalyThreshold}
                    </Badge>
                  </label>
                  <div className="space-y-2">
                    <input
                      type="range"
                      min="0.5"
                      max="1.0"
                      step="0.05"
                      value={anomalyThreshold}
                      onChange={(e) => setAnomalyThreshold(parseFloat(e.target.value))}
                      className="w-full h-2 bg-teal-200 rounded-lg appearance-none cursor-pointer accent-teal-500"
                    />
                    <div className="flex justify-between text-slate-500 font-darker-grotesque" style={{ fontSize: '14px' }}>
                      <span>0.5 (Nhạy)</span>
                      <span>0.75</span>
                      <span>1.0 (Chặt chẽ)</span>
                    </div>
                  </div>
                  <div className="mt-3 p-3 bg-blue-50 rounded-lg flex items-start gap-2">
                    <Info className="size-4 text-blue-600 mt-0.5 flex-shrink-0" />
                    <p className="text-blue-800 font-darker-grotesque" style={{ fontSize: '14px' }}>
                      Giá trị cao hơn sẽ giảm số lượng cảnh báo nhưng có thể bỏ sót bất thường
                    </p>
                  </div>
                </div>

                {/* Min Anomaly Amount */}
                <div>
                  <label className="block mb-3">
                    <span className="font-darker-grotesque text-slate-900" style={{ fontSize: '17px', fontWeight: 600 }}>
                      Ngưỡng số tiền tối thiểu
                    </span>
                  </label>
                  <div className="relative">
                    <input
                      type="number"
                      value={minAnomalyAmount}
                      onChange={(e) => setMinAnomalyAmount(parseInt(e.target.value))}
                      className="w-full px-4 py-3 border border-slate-300 rounded-lg font-darker-grotesque focus:outline-none focus:ring-2 focus:ring-teal-500"
                      style={{ fontSize: '17px' }}
                      step="100000"
                    />
                    <span className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 font-darker-grotesque" style={{ fontSize: '16px' }}>
                      VND
                    </span>
                  </div>
                  <p className="mt-2 text-teal-700 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 600 }}>
                    ≈ {formatCurrency(minAnomalyAmount)}
                  </p>
                  <p className="mt-1 text-slate-600 font-darker-grotesque" style={{ fontSize: '14px' }}>
                    Chỉ cảnh báo giao dịch lớn hơn mức này
                  </p>
                </div>

                {/* Alert Severity */}
                <div>
                  <label className="block mb-3">
                    <span className="font-darker-grotesque text-slate-900" style={{ fontSize: '17px', fontWeight: 600 }}>
                      Mức độ cảnh báo mặc định
                    </span>
                  </label>
                  <Select value={alertSeverity} onValueChange={setAlertSeverity}>
                    <SelectTrigger className="font-darker-grotesque" style={{ fontSize: '17px' }}>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="low" className="font-darker-grotesque" style={{ fontSize: '16px' }}>
                        <div className="flex items-center gap-2">
                          <div className="size-3 bg-green-500 rounded-full"></div>
                          Thấp
                        </div>
                      </SelectItem>
                      <SelectItem value="medium" className="font-darker-grotesque" style={{ fontSize: '16px' }}>
                        <div className="flex items-center gap-2">
                          <div className="size-3 bg-yellow-500 rounded-full"></div>
                          Trung bình
                        </div>
                      </SelectItem>
                      <SelectItem value="high" className="font-darker-grotesque" style={{ fontSize: '16px' }}>
                        <div className="flex items-center gap-2">
                          <div className="size-3 bg-red-500 rounded-full"></div>
                          Cao
                        </div>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Row 2: Job Schedule - Full Width */}
          <Card className="border-0 shadow-lg bg-white">
            <CardHeader className="border-b bg-gradient-to-r from-cyan-50 to-blue-50 pb-4">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-cyan-500 rounded-lg">
                  <Clock className="size-6 text-white" />
                </div>
                <div>
                  <CardTitle className="font-alata text-slate-900" style={{ fontSize: '24px', fontWeight: 500 }}>
                    Lịch chạy job dự báo
                  </CardTitle>
                  <CardDescription className="font-darker-grotesque text-slate-600 mt-1" style={{ fontSize: '16px' }}>
                    Cấu hình tần suất và thời gian chạy tự động cho cả Prophet và Anomaly Detection
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Left Column */}
                <div className="space-y-6">
                  {/* Forecast Frequency */}
                  <div>
                    <label className="block mb-3">
                      <span className="font-darker-grotesque text-slate-900" style={{ fontSize: '17px', fontWeight: 600 }}>
                        Tần suất cập nhật dự báo
                      </span>
                    </label>
                    <div className="grid grid-cols-2 gap-3">
                      <button
                        onClick={() => setForecastFrequency('daily')}
                        className={`p-4 rounded-lg border-2 transition-all duration-200 ${
                          forecastFrequency === 'daily'
                            ? 'border-cyan-500 bg-cyan-50'
                            : 'border-slate-200 hover:border-slate-300'
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <div className={`p-2 rounded-lg ${forecastFrequency === 'daily' ? 'bg-cyan-500' : 'bg-slate-200'}`}>
                            <RefreshCw className={`size-5 ${forecastFrequency === 'daily' ? 'text-white' : 'text-slate-600'}`} />
                          </div>
                          <div className="text-left">
                            <p className={`font-darker-grotesque ${forecastFrequency === 'daily' ? 'text-cyan-900' : 'text-slate-900'}`} style={{ fontSize: '16px', fontWeight: 600 }}>
                              Hàng ngày
                            </p>
                            <p className="text-slate-600 font-darker-grotesque" style={{ fontSize: '14px' }}>
                              Daily update
                            </p>
                          </div>
                        </div>
                      </button>
                      <button
                        onClick={() => setForecastFrequency('weekly')}
                        className={`p-4 rounded-lg border-2 transition-all duration-200 ${
                          forecastFrequency === 'weekly'
                            ? 'border-cyan-500 bg-cyan-50'
                            : 'border-slate-200 hover:border-slate-300'
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <div className={`p-2 rounded-lg ${forecastFrequency === 'weekly' ? 'bg-cyan-500' : 'bg-slate-200'}`}>
                            <Calendar className={`size-5 ${forecastFrequency === 'weekly' ? 'text-white' : 'text-slate-600'}`} />
                          </div>
                          <div className="text-left">
                            <p className={`font-darker-grotesque ${forecastFrequency === 'weekly' ? 'text-cyan-900' : 'text-slate-900'}`} style={{ fontSize: '16px', fontWeight: 600 }}>
                              Hàng tuần
                            </p>
                            <p className="text-slate-600 font-darker-grotesque" style={{ fontSize: '14px' }}>
                              Weekly update
                            </p>
                          </div>
                        </div>
                      </button>
                    </div>
                  </div>

                  {/* Week Day Selection - Only show when Weekly is selected */}
                  {forecastFrequency === 'weekly' && (
                    <div>
                      <label className="block mb-3">
                        <span className="font-darker-grotesque text-slate-900" style={{ fontSize: '17px', fontWeight: 600 }}>
                          Ngày trong tuần
                        </span>
                      </label>
                      <Select value={weekDay} onValueChange={setWeekDay}>
                        <SelectTrigger className="font-darker-grotesque" style={{ fontSize: '17px' }}>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {weekDays.map((day) => (
                            <SelectItem key={day.value} value={day.value} className="font-darker-grotesque" style={{ fontSize: '16px' }}>
                              {day.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <p className="mt-2 text-slate-600 font-darker-grotesque" style={{ fontSize: '14px' }}>
                        Job sẽ chạy vào ngày này hàng tuần
                      </p>
                    </div>
                  )}

                  {/* Job Time */}
                  <div>
                    <label className="block mb-3">
                      <span className="font-darker-grotesque text-slate-900" style={{ fontSize: '17px', fontWeight: 600 }}>
                        Giờ chạy job
                      </span>
                    </label>
                    <input
                      type="time"
                      value={jobTime}
                      onChange={(e) => setJobTime(e.target.value)}
                      className="w-full px-4 py-3 border border-slate-300 rounded-lg font-darker-grotesque focus:outline-none focus:ring-2 focus:ring-cyan-500"
                      style={{ fontSize: '17px' }}
                    />
                    <p className="mt-2 text-slate-600 font-darker-grotesque" style={{ fontSize: '14px' }}>
                      Múi giờ: Asia/Ho_Chi_Minh (UTC+7)
                    </p>
                  </div>
                </div>

                {/* Right Column */}
                <div className="space-y-6">
                  {/* Auto Retry */}
                  <div>
                    <label className="flex items-center justify-between p-4 bg-slate-50 rounded-lg cursor-pointer hover:bg-slate-100 transition-colors">
                      <div>
                        <p className="font-darker-grotesque text-slate-900" style={{ fontSize: '17px', fontWeight: 600 }}>
                          Tự động thử lại khi lỗi
                        </p>
                        <p className="text-slate-600 font-darker-grotesque mt-1" style={{ fontSize: '14px' }}>
                          Thử lại tối đa 3 lần nếu job thất bại
                        </p>
                      </div>
                      <input
                        type="checkbox"
                        checked={autoRetry}
                        onChange={(e) => setAutoRetry(e.target.checked)}
                        className="size-5 accent-cyan-500 cursor-pointer"
                      />
                    </label>
                  </div>

                  {/* Job Info */}
                  <div className="p-4 bg-gradient-to-r from-cyan-50 to-blue-50 rounded-lg border border-cyan-200">
                    <div className="flex items-start gap-3">
                      <Zap className="size-5 text-cyan-600 mt-1 flex-shrink-0" />
                      <div className="space-y-2">
                        <p className="font-darker-grotesque text-cyan-900" style={{ fontSize: '16px', fontWeight: 600 }}>
                          Thông tin job tiếp theo
                        </p>
                        <div className="space-y-1">
                          <p className="text-cyan-800 font-darker-grotesque" style={{ fontSize: '14px' }}>
                            • Lịch chạy: {forecastFrequency === 'daily' 
                              ? 'Hàng ngày' 
                              : `Hàng tuần (${weekDays.find(d => d.value === weekDay)?.label})`} lúc {jobTime}
                          </p>
                          <p className="text-cyan-800 font-darker-grotesque" style={{ fontSize: '14px' }}>
                            • Thời gian ước tính: ~2-3 phút
                          </p>
                          <p className="text-cyan-800 font-darker-grotesque" style={{ fontSize: '14px' }}>
                            • Trạng thái: {autoRetry ? 'Có retry' : 'Không retry'}
                          </p>
                          <p className="text-cyan-800 font-darker-grotesque" style={{ fontSize: '14px' }}>
                            • Chạy cả Prophet và Anomaly Detection
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Manual Run Button */}
                  <Button
                    onClick={() => alert('Đang chạy job thủ công cho cả Prophet và Anomaly Detection...')}
                    variant="outline"
                    className="w-full font-darker-grotesque border-cyan-300 text-cyan-700 hover:bg-cyan-50"
                    style={{ fontSize: '17px' }}
                  >
                    <RefreshCw className="size-4 mr-2" />
                    Chạy thủ công ngay
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Save Button */}
        <div className="mt-8 flex justify-end gap-4">
          <Button
            variant="outline"
            onClick={() => {
              // Reset to defaults
              setForecastWindow('30');
              setForecastConfidence(0.95);
              setSeasonalityMode('multiplicative');
              setAnomalyThreshold(0.85);
              setMinAnomalyAmount(1000000);
              setAlertSeverity('medium');
              setForecastFrequency('daily');
              setWeekDay('monday');
              setJobTime('02:00');
              setAutoRetry(true);
            }}
            className="font-darker-grotesque"
            style={{ fontSize: '17px' }}
          >
            Khôi phục mặc định
          </Button>
          <Button
            onClick={handleSaveSettings}
            className="font-darker-grotesque bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white px-8"
            style={{ fontSize: '17px' }}
          >
            <Save className="size-4 mr-2" />
            Lưu cấu hình
          </Button>
        </div>
      </main>
    </div>
  );
}