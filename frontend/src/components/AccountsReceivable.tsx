import { Bell, Menu, Search, DollarSign, Clock, AlertCircle, TrendingUp, Users, Eye, Edit, Trash2, Upload, ChevronLeft, ChevronRight, FileSpreadsheet, CheckCircle2, XCircle, X, Loader2 } from 'lucide-react';
import { Card, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { UserMenu } from './UserMenu';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { useState } from 'react';
import { useSidebar } from '../contexts/SidebarContext';
import { useInvoices, useCustomers, useUpdateInvoice, useDeleteInvoice, useBulkImportInvoices } from '../lib/api/hooks';
import { toast } from 'sonner';
import type { BulkImportInvoiceItem } from '../lib/api/services/invoices';

type InvoiceStatus = 'unpaid' | 'partial' | 'paid' | 'canceled';
type RiskLevel = 'low' | 'normal' | 'high';

interface ARInvoice {
  id: string;
  invoice_no: string;
  customer_name: string;
  customer_code: string;
  issue_date: string;
  due_date: string;
  terms_days: number;
  amount: number;
  paid_amount: number;
  remaining: number;
  status: InvoiceStatus;
  aging: number;
  risk_level: RiskLevel;
  notes: string;
  email: string;
  phone: string;
}

interface Customer {
  code: string;
  name: string;
  email: string;
  phone: string;
  terms_days: number;
  risk_level: RiskLevel;
}

// Smart pagination helper
const getPageNumbers = (currentPage: number, totalPages: number): (number | string)[] => {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }

  if (currentPage <= 3) {
    return [1, 2, 3, 4, '...', totalPages];
  }

  if (currentPage >= totalPages - 2) {
    return [1, '...', totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
  }

  return [1, '...', currentPage - 1, currentPage, currentPage + 1, '...', totalPages];
};

export function AccountsReceivable() {
  const { isSidebarOpen, toggleSidebar } = useSidebar();
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [riskFilter, setRiskFilter] = useState<string>('all');
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedInvoice, setSelectedInvoice] = useState<ARInvoice | null>(null);
  const [currentPageInvoices, setCurrentPageInvoices] = useState(1);
  const [currentPageCustomers, setCurrentPageCustomers] = useState(1);
  const itemsPerPage = 10;

  // Import Excel states
  const [importStep, setImportStep] = useState<1 | 2>(1);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [previewData, setPreviewData] = useState<any[]>([]);
  const [importWarnings, setImportWarnings] = useState<string[]>([]);

  // Edit form states
  const [editFormData, setEditFormData] = useState<ARInvoice | null>(null);

  // Fetch invoices from API
  const { data: invoicesData, isLoading: loadingInvoices } = useInvoices({
    search: searchQuery || undefined,
    status: statusFilter !== 'all' ? statusFilter : undefined,
    skip: (currentPageInvoices - 1) * itemsPerPage,
    limit: itemsPerPage,
  });

  // Fetch customers from API
  const { data: customersData } = useCustomers({
    skip: (currentPageCustomers - 1) * itemsPerPage,
    limit: itemsPerPage,
  });

  // Mutations
  const updateInvoiceMutation = useUpdateInvoice();
  const deleteInvoiceMutation = useDeleteInvoice();
  const bulkImportMutation = useBulkImportInvoices();

  // Map API data to local interface
  const allInvoices: ARInvoice[] = invoicesData?.items.map(inv => ({
    id: String(inv.id),
    invoice_no: inv.invoice_no,
    customer_name: inv.customer?.name || 'N/A',
    customer_code: inv.customer?.code || 'N/A',
    issue_date: inv.issue_date,
    due_date: inv.due_date,
    terms_days: inv.customer?.credit_term || 15,
    amount: inv.total_amount,
    paid_amount: inv.paid_amount,
    remaining: inv.remaining_amount,
    status: inv.status as InvoiceStatus,
    aging: inv.aging_days || Math.floor((new Date().getTime() - new Date(inv.due_date).getTime()) / (1000 * 60 * 60 * 24)),
    risk_level: inv.risk_level || 'normal',
    notes: inv.notes || '',
    email: inv.customer?.email || '',
    phone: inv.customer?.phone || '',
  })) || [];

  const customers: Customer[] = customersData?.items.map(c => ({
    code: c.code || `KH${c.id}`,
    name: c.name,
    email: c.email || '',
    phone: c.phone || '',
    terms_days: c.credit_term || 15,
    risk_level: 'normal',
  })) || [];

  // Calculate KPIs from API data
  const totalAR = allInvoices.reduce((sum, inv) => sum + inv.remaining, 0);
  const overdueAmount = allInvoices.filter(inv => inv.aging > 0).reduce((sum, inv) => sum + inv.remaining, 0);
  const unpaidCount = allInvoices.filter(inv => inv.status === 'unpaid' || inv.status === 'partial').length;
  const avgDSO = allInvoices.length > 0 
    ? Math.round(allInvoices.reduce((sum, inv) => sum + inv.aging, 0) / allInvoices.length) 
    : 0;

  // Use API paginated data directly
  const paginatedInvoices = allInvoices;
  const paginatedCustomers = customers;
  const totalPagesInvoices = Math.ceil((invoicesData?.total || 0) / itemsPerPage);
  const totalPagesCustomers = Math.ceil((customersData?.total || 0) / itemsPerPage);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(value);
  };

  const formatCurrencyShort = (value: number) => {
    if (value >= 1000000) {
      return `${(value / 1000000).toFixed(1)}M`;
    }
    return `${(value / 1000).toFixed(0)}K`;
  };

  const getStatusBadge = (status: InvoiceStatus) => {
    const styles = {
      unpaid: 'bg-red-100 text-red-700 border-red-200',
      partial: 'bg-yellow-100 text-yellow-700 border-yellow-200',
      paid: 'bg-green-100 text-green-700 border-green-200',
      canceled: 'bg-gray-100 text-gray-700 border-gray-200'
    };
    const labels = {
      unpaid: 'Chưa thu',
      partial: 'Thu 1 phần',
      paid: 'Đã thu',
      canceled: 'Đ hủy'
    };
    return <Badge className={`${styles[status]} border font-darker-grotesque`} style={{ fontSize: '14px' }}>{labels[status]}</Badge>;
  };

  const getRiskBadge = (risk: RiskLevel) => {
    const styles = {
      low: 'bg-green-100 text-green-700 border-green-200',
      normal: 'bg-blue-100 text-blue-700 border-blue-200',
      high: 'bg-red-100 text-red-700 border-red-200'
    };
    const labels = {
      low: 'Thấp',
      normal: 'Trung bình',
      high: 'Cao'
    };
    return <Badge className={`${styles[risk]} border font-darker-grotesque`} style={{ fontSize: '14px' }}>{labels[risk]}</Badge>;
  };

  const handleViewDetail = (invoice: ARInvoice) => {
    setSelectedInvoice(invoice);
    setShowDetailModal(true);
  };

  const handleEdit = (invoice: ARInvoice) => {
    setSelectedInvoice(invoice);
    setEditFormData(invoice);
    setShowEditModal(true);
  };

  const handleDelete = (invoice: ARInvoice) => {
    setSelectedInvoice(invoice);
    setShowDeleteModal(true);
  };

  // Import Excel handlers
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file && (file.name.endsWith('.xlsx') || file.name.endsWith('.xls') || file.name.endsWith('.csv'))) {
      setSelectedFile(file);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleContinueToPreview = () => {
    // Mock: simulate reading first 5 rows from file
    const mockPreviewData = [
      { invoice_no: 'INV-2024-100', customer_code: 'KH001', issue_date: '01/12/2024', due_date: '15/12/2024', amount: '50000000' },
      { invoice_no: 'INV-2024-101', customer_code: 'KH002', issue_date: '01/12/2024', due_date: '16/12/2024', amount: '35000000' },
      { invoice_no: 'INV-2024-102', customer_code: 'KH999', issue_date: '02/12/2024', due_date: '17/12/2024', amount: '42000000' },
      { invoice_no: 'INV-2024-103', customer_code: 'KH003', issue_date: '02/12/2024', due_date: '18/12/2024', amount: '28000000' },
      { invoice_no: 'INV-2024-104', customer_code: 'KH888', issue_date: '03/12/2024', due_date: '19/12/2024', amount: '65000000' },
    ];

    setPreviewData(mockPreviewData);

    // Check for missing customer codes
    const warnings: string[] = [];
    const existingCodes = customers.map(c => c.code);
    mockPreviewData.forEach(row => {
      if (!existingCodes.includes(row.customer_code)) {
        warnings.push(`Mã khách hàng "${row.customer_code}" chưa tn tại trong hệ thống`);
      }
    });

    setImportWarnings(warnings);
    setImportStep(2);
  };

  const handleImport = async () => {
    if (previewData.length === 0) {
      toast.error('Không có dữ liệu để import');
      return;
    }
    
    // Convert preview data to API format
    const invoicesToImport: BulkImportInvoiceItem[] = previewData.map(row => ({
      invoice_no: row.invoice_no,
      customer_id: row.customer_id || 1, // Would need to map from customer_code
      issue_date: row.issue_date,
      due_date: row.due_date,
      total_amount: row.amount,
      notes: row.notes || '',
    }));
    
    try {
      const result = await bulkImportMutation.mutateAsync({
        invoices: invoicesToImport,
        auto_post: false,
      });
      
      if (result.total_success > 0) {
        toast.success(`Import thành công ${result.total_success}/${result.total_submitted} hóa đơn!`);
      }
      if (result.total_failed > 0) {
        toast.warning(`${result.total_failed} hóa đơn thất bại. Kiểm tra log chi tiết.`);
        console.log('Import failures:', result.results.filter(r => !r.success));
      }
      
      handleCloseUploadModal();
    } catch (error) {
      console.error('Import error:', error);
      toast.error('Lỗi khi import hóa đơn. Vui lòng thử lại.');
    }
  };

  const handleCloseUploadModal = () => {
    setShowUploadModal(false);
    setImportStep(1);
    setSelectedFile(null);
    setPreviewData([]);
    setImportWarnings([]);
    setIsDragging(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-orange-50/20 to-slate-100">
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
          <h2 className="text-slate-900 mb-1 font-alata" style={{ fontSize: '32px', fontWeight: 400 }}>Công nợ - Phải thu</h2>
          <p className="text-slate-600 font-darker-grotesque" style={{ fontSize: '18px' }}>
            Quản lý hóa đơn phải thu từ khách hàng
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-4 gap-4 mb-6">
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
                  <p className="text-red-100 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>Quá hạn</p>
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
                    {avgDSO} ngày
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
                  <p className="text-rose-100 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>Hóa đơn chưa thu</p>
                  <p className="text-white font-alata mt-2" style={{ fontSize: '28px', fontWeight: 700 }}>
                    {unpaidCount}
                  </p>
                </div>
                <TrendingUp className="size-10 text-rose-200" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tabs */}
        <Tabs defaultValue="invoices" className="space-y-6">
          <TabsList className="grid w-full grid-cols-2 h-auto p-1 bg-slate-100">
            <TabsTrigger 
              value="invoices" 
              className="font-darker-grotesque data-[state=active]:bg-gradient-to-r data-[state=active]:from-orange-500 data-[state=active]:to-orange-600 data-[state=active]:text-white"
              style={{ fontSize: '18px', padding: '12px' }}
            >
              <DollarSign className="size-5 mr-2" />
              Danh sách phải thu
            </TabsTrigger>
            <TabsTrigger 
              value="customers" 
              className="font-darker-grotesque data-[state=active]:bg-gradient-to-r data-[state=active]:from-orange-500 data-[state=active]:to-orange-600 data-[state=active]:text-white"
              style={{ fontSize: '18px', padding: '12px' }}
            >
              <Users className="size-5 mr-2" />
              Danh mục khách hàng
            </TabsTrigger>
          </TabsList>

          {/* Tab 1: Danh sách phải thu */}
          <TabsContent value="invoices" className="space-y-6">
            {/* Filters and Actions */}
            <Card className="border-0 shadow-lg bg-white">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between gap-4 mb-4">
                  <div className="flex items-center gap-4 flex-1">
                    <div className="relative flex-1 max-w-md">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-5 text-slate-400" />
                      <input
                        type="text"
                        placeholder="Tìm theo mã hóa đơn hoặc tên khách hàng..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg font-darker-grotesque focus:outline-none focus:ring-2 focus:ring-orange-500"
                        style={{ fontSize: '17px' }}
                      />
                    </div>
                    <Select value={statusFilter} onValueChange={setStatusFilter}>
                      <SelectTrigger className="w-[180px] font-darker-grotesque" style={{ fontSize: '17px' }}>
                        <SelectValue placeholder="Trạng thái" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all" className="font-darker-grotesque" style={{ fontSize: '16px' }}>Tất cả</SelectItem>
                        <SelectItem value="unpaid" className="font-darker-grotesque" style={{ fontSize: '16px' }}>Chưa thu</SelectItem>
                        <SelectItem value="partial" className="font-darker-grotesque" style={{ fontSize: '16px' }}>Thu 1 phần</SelectItem>
                        <SelectItem value="paid" className="font-darker-grotesque" style={{ fontSize: '16px' }}>Đã thu</SelectItem>
                      </SelectContent>
                    </Select>
                    <Select value={riskFilter} onValueChange={setRiskFilter}>
                      <SelectTrigger className="w-[180px] font-darker-grotesque" style={{ fontSize: '17px' }}>
                        <SelectValue placeholder="Mức độ rủi ro" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all" className="font-darker-grotesque" style={{ fontSize: '16px' }}>Tất cả</SelectItem>
                        <SelectItem value="low" className="font-darker-grotesque" style={{ fontSize: '16px' }}>Thấp</SelectItem>
                        <SelectItem value="normal" className="font-darker-grotesque" style={{ fontSize: '16px' }}>Trung bình</SelectItem>
                        <SelectItem value="high" className="font-darker-grotesque" style={{ fontSize: '16px' }}>Cao</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <Button
                    onClick={() => setShowUploadModal(true)}
                    className="font-darker-grotesque bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 text-white"
                    style={{ fontSize: '17px' }}
                  >
                    <Upload className="size-4 mr-2" />
                    Import Excel
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Invoice Table */}
            <Card className="border-0 shadow-lg bg-white">
              <CardContent className="pt-6">
                <div className="border rounded-lg overflow-hidden">
                  <table className="w-full">
                    <thead className="sticky top-0 bg-orange-50 text-slate-900 shadow-sm z-10">
                      <tr>
                        <th className="text-left p-4 font-darker-grotesque bg-orange-50" style={{ fontSize: '17px', fontWeight: 600 }}>Mã hóa đơn</th>
                        <th className="text-left p-4 font-darker-grotesque bg-orange-50" style={{ fontSize: '17px', fontWeight: 600 }}>Khách hàng</th>
                        <th className="text-center p-4 font-darker-grotesque bg-orange-50" style={{ fontSize: '17px', fontWeight: 600 }}>Ngày đến hạn</th>
                        <th className="text-right p-4 font-darker-grotesque bg-orange-50" style={{ fontSize: '17px', fontWeight: 600 }}>Tổng tiền</th>
                        <th className="text-right p-4 font-darker-grotesque bg-orange-50" style={{ fontSize: '17px', fontWeight: 600 }}>Còn phải thu</th>
                        <th className="text-center p-4 font-darker-grotesque bg-orange-50" style={{ fontSize: '17px', fontWeight: 600 }}>Trạng thái</th>
                        <th className="text-center p-4 font-darker-grotesque bg-orange-50" style={{ fontSize: '17px', fontWeight: 600 }}>Tuổi nợ</th>
                        <th className="text-center p-4 font-darker-grotesque bg-orange-50" style={{ fontSize: '17px', fontWeight: 600 }}>Thao tác</th>
                      </tr>
                    </thead>
                    <tbody>
                      {loadingInvoices ? (
                        // Loading skeleton rows
                        Array.from({ length: 5 }).map((_, idx) => (
                          <tr key={idx} className="border-b border-slate-100">
                            <td className="p-4" colSpan={8}>
                              <div className="h-12 bg-slate-100 rounded animate-pulse"></div>
                            </td>
                          </tr>
                        ))
                      ) : paginatedInvoices.length === 0 ? (
                        <tr>
                          <td colSpan={8} className="p-8 text-center text-slate-500 font-darker-grotesque" style={{ fontSize: '16px' }}>
                            Không có hóa đơn nào
                          </td>
                        </tr>
                      ) : (
                        paginatedInvoices.map((invoice, idx) => (
                        <tr key={invoice.id} className={`border-b border-slate-100 hover:bg-orange-50/30 transition-colors ${idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'}`}>
                          <td className="p-4 font-darker-grotesque text-slate-900" style={{ fontSize: '16px', fontWeight: 500 }}>
                            {invoice.invoice_no}
                          </td>
                          <td className="p-4 font-darker-grotesque text-slate-700" style={{ fontSize: '16px' }}>
                            {invoice.customer_name}
                          </td>
                          <td className="p-4 text-center font-darker-grotesque text-slate-700" style={{ fontSize: '16px' }}>
                            {new Date(invoice.due_date).toLocaleDateString('vi-VN')}
                          </td>
                          <td className="p-4 text-right font-darker-grotesque text-slate-900" style={{ fontSize: '16px', fontWeight: 500 }}>
                            {formatCurrency(invoice.amount)}
                          </td>
                          <td className="p-4 text-right font-darker-grotesque" style={{ fontSize: '16px', fontWeight: 600 }}>
                            <span className={invoice.remaining > 0 ? 'text-orange-600' : 'text-green-600'}>
                              {formatCurrency(invoice.remaining)}
                            </span>
                          </td>
                          <td className="p-4 text-center">
                            {getStatusBadge(invoice.status)}
                          </td>
                          <td className="p-4 text-center">
                            <span className={`font-darker-grotesque px-3 py-1 rounded-full ${
                              invoice.aging > 0 
                                ? 'bg-red-100 text-red-700' 
                                : 'bg-green-100 text-green-700'
                            }`} style={{ fontSize: '15px', fontWeight: 600 }}>
                              {invoice.aging > 0 ? `+${invoice.aging}` : invoice.aging} ngày
                            </span>
                          </td>
                          <td className="p-4">
                            <div className="flex items-center justify-center gap-2">
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleViewDetail(invoice)}
                                className="hover:bg-orange-100 hover:text-orange-700"
                              >
                                <Eye className="size-4" />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleEdit(invoice)}
                                className="hover:bg-blue-100 hover:text-blue-700"
                              >
                                <Edit className="size-4" />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleDelete(invoice)}
                                className="hover:bg-red-100 hover:text-red-700"
                              >
                                <Trash2 className="size-4" />
                              </Button>
                            </div>
                          </td>
                        </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>

                {/* Smart Pagination */}
                <div className="flex items-center justify-center gap-2 mt-6">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPageInvoices(prev => Math.max(1, prev - 1))}
                    disabled={currentPageInvoices === 1}
                    className="font-darker-grotesque h-9 w-9 p-0"
                  >
                    <ChevronLeft className="size-4" />
                  </Button>
                  
                  {getPageNumbers(currentPageInvoices, totalPagesInvoices).map((page, idx) => {
                    if (page === '...') {
                      return (
                        <span key={`ellipsis-${idx}`} className="px-2 text-slate-500 font-darker-grotesque">
                          ...
                        </span>
                      );
                    }
                    const pageNum = page as number;
                    return (
                      <Button
                        key={pageNum}
                        variant="outline"
                        size="sm"
                        onClick={() => setCurrentPageInvoices(pageNum)}
                        className={`font-darker-grotesque h-9 w-9 p-0 ${
                          currentPageInvoices === pageNum
                            ? 'bg-gradient-to-r from-orange-400 to-orange-500 text-white border-orange-500 hover:bg-gradient-to-r hover:from-orange-500 hover:to-orange-600'
                            : 'bg-white hover:bg-slate-100'
                        }`}
                        style={{ fontWeight: currentPageInvoices === pageNum ? 600 : 400 }}
                      >
                        {pageNum}
                      </Button>
                    );
                  })}
                  
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPageInvoices(prev => Math.min(totalPagesInvoices, prev + 1))}
                    disabled={currentPageInvoices === totalPagesInvoices}
                    className="font-darker-grotesque h-9 w-9 p-0"
                  >
                    <ChevronRight className="size-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Tab 2: Danh mục khách hàng */}
          <TabsContent value="customers" className="space-y-6">
            <Card className="border-0 shadow-lg bg-white">
              <CardContent className="pt-6">
                <div className="border rounded-lg overflow-hidden">
                  <table className="w-full">
                    <thead className="sticky top-0 bg-orange-50 text-slate-900 shadow-sm z-10">
                      <tr>
                        <th className="text-left p-4 font-darker-grotesque bg-orange-50" style={{ fontSize: '17px', fontWeight: 600 }}>Mã KH</th>
                        <th className="text-left p-4 font-darker-grotesque bg-orange-50" style={{ fontSize: '17px', fontWeight: 600 }}>Tên khách hàng</th>
                        <th className="text-left p-4 font-darker-grotesque bg-orange-50" style={{ fontSize: '17px', fontWeight: 600 }}>Email</th>
                        <th className="text-center p-4 font-darker-grotesque bg-orange-50" style={{ fontSize: '17px', fontWeight: 600 }}>Số điện thoại</th>
                        <th className="text-center p-4 font-darker-grotesque bg-orange-50" style={{ fontSize: '17px', fontWeight: 600 }}>Terms (ngày)</th>
                        <th className="text-center p-4 font-darker-grotesque bg-orange-50" style={{ fontSize: '17px', fontWeight: 600 }}>Mức độ rủi ro</th>
                      </tr>
                    </thead>
                    <tbody>
                      {paginatedCustomers.map((customer, idx) => (
                        <tr key={customer.code} className={`border-b border-slate-100 hover:bg-orange-50/30 transition-colors ${idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'}`}>
                          <td className="p-4 font-darker-grotesque text-slate-900" style={{ fontSize: '16px', fontWeight: 500 }}>
                            {customer.code}
                          </td>
                          <td className="p-4 font-darker-grotesque text-slate-700" style={{ fontSize: '16px' }}>
                            {customer.name}
                          </td>
                          <td className="p-4 font-darker-grotesque text-slate-700" style={{ fontSize: '16px' }}>
                            {customer.email}
                          </td>
                          <td className="p-4 text-center font-darker-grotesque text-slate-700" style={{ fontSize: '16px' }}>
                            {customer.phone}
                          </td>
                          <td className="p-4 text-center font-darker-grotesque text-slate-900" style={{ fontSize: '16px', fontWeight: 500 }}>
                            {customer.terms_days}
                          </td>
                          <td className="p-4 text-center">
                            {getRiskBadge(customer.risk_level)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Smart Pagination for Customers */}
                {totalPagesCustomers > 1 && (
                  <div className="flex items-center justify-center gap-2 mt-6">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPageCustomers(prev => Math.max(1, prev - 1))}
                      disabled={currentPageCustomers === 1}
                      className="font-darker-grotesque h-9 w-9 p-0"
                    >
                      <ChevronLeft className="size-4" />
                    </Button>
                    
                    {getPageNumbers(currentPageCustomers, totalPagesCustomers).map((page, idx) => {
                      if (page === '...') {
                        return (
                          <span key={`ellipsis-${idx}`} className="px-2 text-slate-500 font-darker-grotesque">
                            ...
                          </span>
                        );
                      }
                      const pageNum = page as number;
                      return (
                        <Button
                          key={pageNum}
                          variant="outline"
                          size="sm"
                          onClick={() => setCurrentPageCustomers(pageNum)}
                          className={`font-darker-grotesque h-9 w-9 p-0 ${
                            currentPageCustomers === pageNum
                              ? 'bg-gradient-to-r from-orange-400 to-orange-500 text-white border-orange-500 hover:bg-gradient-to-r hover:from-orange-500 hover:to-orange-600'
                              : 'bg-white hover:bg-slate-100'
                          }`}
                          style={{ fontWeight: currentPageCustomers === pageNum ? 600 : 400 }}
                        >
                          {pageNum}
                        </Button>
                      );
                    })}
                    
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPageCustomers(prev => Math.min(totalPagesCustomers, prev + 1))}
                      disabled={currentPageCustomers === totalPagesCustomers}
                      className="font-darker-grotesque h-9 w-9 p-0"
                    >
                      <ChevronRight className="size-4" />
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>

      {/* Modals remain the same - Detail, Edit, Delete, Upload */}
      {/* I'll keep them short for brevity - they're identical to before */}

      {/* Import Excel Modal - 2 Steps */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-lg shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto mx-4">
            {/* Step 1: File Upload */}
            {importStep === 1 && (
              <div className="overflow-hidden">
                {/* Orange Header - matching page theme */}
                <div className="bg-gradient-to-r from-orange-500 to-orange-600 p-6 flex items-center justify-between">
                  <h3 className="text-white font-alata" style={{ fontSize: '28px', fontWeight: 400 }}>
                    Import dữ liệu từ Excel
                  </h3>
                  <Button variant="ghost" size="icon" onClick={handleCloseUploadModal} className="text-white hover:bg-white/20">
                    <X className="size-6" />
                  </Button>
                </div>

                {/* White Content Area */}
                <div className="p-8 bg-white">
                  {/* Dropzone - Click anywhere to upload */}
                  <div
                    className={`border-2 border-dashed rounded-xl p-16 text-center transition-all cursor-pointer ${
                      isDragging 
                        ? 'border-orange-400 bg-orange-50' 
                        : 'border-slate-300 bg-white hover:border-orange-300 hover:bg-orange-50/30'
                    }`}
                    onDrop={handleFileDrop}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onClick={() => document.getElementById('file-upload-input')?.click()}
                  >
                    <Upload className="size-20 mx-auto mb-4 text-slate-400" strokeWidth={1.5} />
                    <p className="text-slate-700 font-darker-grotesque mb-2" style={{ fontSize: '18px', fontWeight: 500 }}>
                      {selectedFile ? selectedFile.name : 'Kéo thả file hoặc click để chọn'}
                    </p>
                    <p className="text-slate-500 font-darker-grotesque" style={{ fontSize: '16px' }}>
                      Hỗ trợ file .xlsx, .xls (tối đa 5MB)
                    </p>
                    <input
                      id="file-upload-input"
                      type="file"
                      accept=".xlsx,.xls,.csv"
                      onChange={handleFileSelect}
                      className="hidden"
                    />
                  </div>

                  {/* Requirements - Orange theme to match page */}
                  <div className="mt-6 bg-orange-50 border border-orange-200 rounded-xl p-5">
                    <h4 className="text-orange-900 font-darker-grotesque mb-3 flex items-center gap-2" style={{ fontSize: '17px', fontWeight: 600 }}>
                      <FileSpreadsheet className="size-5 text-orange-600" />
                      Lưu ý khi import:
                    </h4>
                    <ul className="space-y-2 text-orange-800 font-darker-grotesque" style={{ fontSize: '16px' }}>
                      <li className="flex items-start gap-2">
                        <span className="text-orange-600">•</span>
                        <span>File phải chứa các cột: <strong>invoice_no, customer_code, issue_date, due_date, amount</strong></span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-orange-600">•</span>
                        <span>Định dạng ngày: <strong>DD/MM/YYYY</strong></span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-orange-600">•</span>
                        <span>Số tiền không cần ký hiệu tiền tệ, chỉ ghi số</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-orange-600">•</span>
                        <span>Mã khách hàng phải tồn tại trong danh mục</span>
                      </li>
                    </ul>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center justify-end gap-3 mt-8">
                    <Button
                      variant="outline"
                      onClick={handleCloseUploadModal}
                      className="font-darker-grotesque"
                      style={{ fontSize: '17px' }}
                    >
                      Hủy
                    </Button>
                    <Button
                      onClick={handleContinueToPreview}
                      disabled={!selectedFile}
                      className="font-darker-grotesque bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 text-white disabled:opacity-50 disabled:cursor-not-allowed"
                      style={{ fontSize: '17px' }}
                    >
                      Tiếp tục
                    </Button>
                  </div>
                </div>
              </div>
            )}

            {/* Step 2: Preview Data */}
            {importStep === 2 && (
              <div className="overflow-hidden">
                {/* Orange Header - matching Step 1 */}
                <div className="bg-gradient-to-r from-orange-500 to-orange-600 p-6 flex items-center justify-between">
                  <h3 className="text-white font-alata" style={{ fontSize: '28px', fontWeight: 400 }}>
                    Preview dữ liệu (5 dòng đầu tiên)
                  </h3>
                  <Button variant="ghost" size="icon" onClick={handleCloseUploadModal} className="text-white hover:bg-white/20">
                    <X className="size-6" />
                  </Button>
                </div>

                {/* White Content Area */}
                <div className="p-8 bg-white">
                  {/* Preview Table */}
                  <div className="border rounded-lg overflow-hidden mb-6">
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead className="bg-orange-50">
                          <tr>
                            <th className="text-left p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '16px', fontWeight: 600 }}>Mã hóa đơn</th>
                            <th className="text-left p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '16px', fontWeight: 600 }}>Mã KH</th>
                            <th className="text-center p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '16px', fontWeight: 600 }}>Ngày phát hành</th>
                            <th className="text-center p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '16px', fontWeight: 600 }}>Ngày đến hạn</th>
                            <th className="text-right p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '16px', fontWeight: 600 }}>Số tiền</th>
                          </tr>
                        </thead>
                        <tbody>
                          {previewData.map((row, idx) => (
                            <tr key={idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'}>
                              <td className="p-3 font-darker-grotesque text-slate-900 border-b border-slate-100" style={{ fontSize: '15px', fontWeight: 500 }}>
                                {row.invoice_no}
                              </td>
                              <td className="p-3 font-darker-grotesque text-slate-700 border-b border-slate-100" style={{ fontSize: '15px' }}>
                                {row.customer_code}
                              </td>
                              <td className="p-3 text-center font-darker-grotesque text-slate-700 border-b border-slate-100" style={{ fontSize: '15px' }}>
                                {row.issue_date}
                              </td>
                              <td className="p-3 text-center font-darker-grotesque text-slate-700 border-b border-slate-100" style={{ fontSize: '15px' }}>
                                {row.due_date}
                              </td>
                              <td className="p-3 text-right font-darker-grotesque text-slate-900 border-b border-slate-100" style={{ fontSize: '15px', fontWeight: 500 }}>
                                {parseInt(row.amount).toLocaleString('vi-VN')}₫
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Warnings */}
                  {importWarnings.length > 0 && (
                    <div className="bg-amber-50 border border-amber-300 rounded-lg p-5 mb-6">
                      <h4 className="text-amber-900 font-darker-grotesque mb-3 flex items-center gap-2" style={{ fontSize: '18px', fontWeight: 600 }}>
                        <AlertCircle className="size-5" />
                        Cảnh báo:
                      </h4>
                      <ul className="space-y-2">
                        {importWarnings.map((warning, idx) => (
                          <li key={idx} className="text-amber-800 font-darker-grotesque flex items-start gap-2" style={{ fontSize: '16px' }}>
                            <XCircle className="size-5 mt-0.5 shrink-0" />
                            <span>{warning}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex items-center justify-end gap-3">
                    <Button
                      variant="outline"
                      onClick={handleCloseUploadModal}
                      disabled={bulkImportMutation.isPending}
                      className="font-darker-grotesque"
                      style={{ fontSize: '17px' }}
                    >
                      Hủy
                    </Button>
                    <Button
                      onClick={handleImport}
                      disabled={bulkImportMutation.isPending}
                      className="font-darker-grotesque bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 text-white"
                      style={{ fontSize: '17px' }}
                    >
                      {bulkImportMutation.isPending ? (
                        <Loader2 className="size-4 mr-2 animate-spin" />
                      ) : (
                        <CheckCircle2 className="size-4 mr-2" />
                      )}
                      {bulkImportMutation.isPending ? 'Đang import...' : 'Import'}
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Detail Modal - View Invoice */}
      {showDetailModal && selectedInvoice && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-lg shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto mx-4">
            <div className="overflow-hidden">
              {/* Orange Header - Sticky */}
              <div className="bg-gradient-to-r from-orange-500 to-orange-600 p-6 flex items-center justify-between sticky top-0 z-10">
                <h3 className="text-white font-alata" style={{ fontSize: '28px', fontWeight: 400 }}>
                  Chi tiết hóa đơn
                </h3>
                <Button variant="ghost" size="icon" onClick={() => setShowDetailModal(false)} className="text-white hover:bg-white/20">
                  <X className="size-6" />
                </Button>
              </div>

              {/* White Content Area */}
              <div className="p-8 bg-white">
                {/* 1. Thông tin chung */}
                <div className="mb-6">
                  <h4 className="text-slate-700 font-darker-grotesque mb-4 pb-2 border-b border-slate-200" style={{ fontSize: '18px', fontWeight: 600 }}>
                    Thông tin chung
                  </h4>
                  <div className="grid grid-cols-2 gap-6">
                    <div>
                      <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '15px' }}>Mã hóa đơn</p>
                      <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '17px', fontWeight: 600 }}>{selectedInvoice.invoice_no}</p>
                    </div>
                    <div>
                      <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '15px' }}>Mã khách hàng</p>
                      <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '17px', fontWeight: 600 }}>{selectedInvoice.customer_code}</p>
                    </div>
                    <div>
                      <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '15px' }}>Tên khách hàng</p>
                      <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '17px', fontWeight: 600 }}>{selectedInvoice.customer_name}</p>
                    </div>
                    <div>
                      <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '15px' }}>Trạng thái</p>
                      <div className="mt-1">{getStatusBadge(selectedInvoice.status)}</div>
                    </div>
                  </div>
                </div>

                {/* 2. Ngày tháng */}
                <div className="mb-6">
                  <h4 className="text-slate-700 font-darker-grotesque mb-4 pb-2 border-b border-slate-200" style={{ fontSize: '18px', fontWeight: 600 }}>
                    Ngày tháng
                  </h4>
                  <div className="grid grid-cols-3 gap-6">
                    <div>
                      <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '15px' }}>Ngày phát hành</p>
                      <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '17px', fontWeight: 600 }}>{new Date(selectedInvoice.issue_date).toLocaleDateString('vi-VN')}</p>
                    </div>
                    <div>
                      <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '15px' }}>Ngày đến hạn</p>
                      <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '17px', fontWeight: 600 }}>{new Date(selectedInvoice.due_date).toLocaleDateString('vi-VN')}</p>
                    </div>
                    <div>
                      <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '15px' }}>Tuổi nợ</p>
                      <p className={`font-darker-grotesque ${selectedInvoice.aging > 0 ? 'text-red-600' : 'text-green-600'}`} style={{ fontSize: '17px', fontWeight: 600 }}>
                        {selectedInvoice.aging > 0 ? `+${selectedInvoice.aging}` : selectedInvoice.aging} ngày
                      </p>
                    </div>
                  </div>
                </div>

                {/* 3. Số tiền */}
                <div className="mb-6">
                  <h4 className="text-slate-700 font-darker-grotesque mb-4 pb-2 border-b border-slate-200" style={{ fontSize: '18px', fontWeight: 600 }}>
                    Số tiền
                  </h4>
                  <div className="grid grid-cols-3 gap-6">
                    <div>
                      <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '15px' }}>Tổng giá trị</p>
                      <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '17px', fontWeight: 600 }}>{formatCurrency(selectedInvoice.amount)}</p>
                    </div>
                    <div>
                      <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '15px' }}>Đã thu</p>
                      <p className="text-green-600 font-darker-grotesque" style={{ fontSize: '17px', fontWeight: 600 }}>{formatCurrency(selectedInvoice.paid_amount)}</p>
                    </div>
                    <div>
                      <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '15px' }}>Còn phải thu</p>
                      <p className="text-orange-600 font-darker-grotesque" style={{ fontSize: '17px', fontWeight: 600 }}>{formatCurrency(selectedInvoice.remaining)}</p>
                    </div>
                  </div>
                </div>

                {/* 4. Ghi chú */}
                <div className="mb-6">
                  <h4 className="text-slate-700 font-darker-grotesque mb-4 pb-2 border-b border-slate-200" style={{ fontSize: '18px', fontWeight: 600 }}>
                    Ghi chú
                  </h4>
                  <p className="text-slate-700 font-darker-grotesque bg-slate-50 p-4 rounded-lg border border-slate-200" style={{ fontSize: '16px' }}>
                    {selectedInvoice.notes || 'Không có ghi chú'}
                  </p>
                </div>

                {/* 5. Danh sách thanh toán liên quan */}
                <div className="mb-6">
                  <h4 className="text-slate-700 font-darker-grotesque mb-4 pb-2 border-b border-slate-200 flex items-center gap-2" style={{ fontSize: '18px', fontWeight: 600 }}>
                    <DollarSign className="size-5 text-orange-600" />
                    Danh sách thanh toán liên quan
                  </h4>
                  <div className="border rounded-lg overflow-hidden">
                    <table className="w-full">
                      <thead className="bg-orange-50">
                        <tr>
                          <th className="text-left p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '15px', fontWeight: 600 }}>Mã thanh toán</th>
                          <th className="text-center p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '15px', fontWeight: 600 }}>Ngày</th>
                          <th className="text-center p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '15px', fontWeight: 600 }}>Phương thức</th>
                          <th className="text-right p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '15px', fontWeight: 600 }}>Số tiền</th>
                          <th className="text-right p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '15px', fontWeight: 600 }}>Đã phân bổ</th>
                          <th className="text-left p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '15px', fontWeight: 600 }}>Mã tham chiếu</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedInvoice.paid_amount > 0 ? (
                          <tr className="bg-white border-b border-slate-100">
                            <td className="p-3 font-darker-grotesque text-slate-900" style={{ fontSize: '15px', fontWeight: 500 }}>PAY-2024-001</td>
                            <td className="p-3 text-center font-darker-grotesque text-slate-700" style={{ fontSize: '15px' }}>05/11/2024</td>
                            <td className="p-3 text-center">
                              <Badge className="bg-blue-100 text-blue-700 border-blue-200 border font-darker-grotesque" style={{ fontSize: '13px' }}>Transfer</Badge>
                            </td>
                            <td className="p-3 text-right font-darker-grotesque text-slate-900" style={{ fontSize: '15px', fontWeight: 500 }}>
                              {formatCurrency(selectedInvoice.paid_amount)}
                            </td>
                            <td className="p-3 text-right font-darker-grotesque text-green-600" style={{ fontSize: '15px', fontWeight: 500 }}>
                              {formatCurrency(selectedInvoice.paid_amount)}
                            </td>
                            <td className="p-3 font-darker-grotesque text-slate-700" style={{ fontSize: '15px' }}>REF-2024-001</td>
                          </tr>
                        ) : (
                          <tr>
                            <td colSpan={6} className="p-6 text-center">
                              <p className="text-slate-400 font-darker-grotesque" style={{ fontSize: '15px' }}>Chưa có thanh toán nào</p>
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* 6. Audit */}
                <div className="mb-6">
                  <h4 className="text-slate-700 font-darker-grotesque mb-4 pb-2 border-b border-slate-200" style={{ fontSize: '18px', fontWeight: 600 }}>
                    Thông tin hệ thống
                  </h4>
                  <div className="grid grid-cols-2 gap-6 bg-slate-50 p-4 rounded-lg border border-slate-200">
                    <div>
                      <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '14px' }}>Tạo lúc</p>
                      <p className="text-slate-700 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>
                        {new Date(selectedInvoice.issue_date).toLocaleString('vi-VN')}
                      </p>
                    </div>
                    <div>
                      <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '14px' }}>Cập nhật lúc</p>
                      <p className="text-slate-700 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>
                        {new Date(selectedInvoice.due_date).toLocaleString('vi-VN')}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
                  <Button
                    variant="outline"
                    onClick={() => setShowDetailModal(false)}
                    className="font-darker-grotesque"
                    style={{ fontSize: '17px' }}
                  >
                    Đóng
                  </Button>
                  <Button
                    onClick={() => {
                      setShowDetailModal(false);
                      handleEdit(selectedInvoice);
                    }}
                    className="font-darker-grotesque bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 text-white"
                    style={{ fontSize: '17px' }}
                  >
                    <Edit className="size-4 mr-2" />
                    Sửa hóa đơn
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal - Edit Invoice */}
      {showEditModal && editFormData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-lg shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto mx-4">
            <div className="overflow-hidden">
              {/* Orange Header */}
              <div className="bg-gradient-to-r from-orange-500 to-orange-600 p-6 flex items-center justify-between">
                <div>
                  <h3 className="text-white font-alata" style={{ fontSize: '28px', fontWeight: 400 }}>
                    Sửa hóa đơn phải thu
                  </h3>
                  <p className="text-orange-100 font-darker-grotesque mt-1" style={{ fontSize: '16px' }}>
                    Cập nhật thông tin hóa đơn trước khi ghi nhận công nợ
                  </p>
                </div>
                <Button variant="ghost" size="icon" onClick={() => setShowEditModal(false)} className="text-white hover:bg-white/20">
                  <X className="size-6" />
                </Button>
              </div>

              {/* White Content Area */}
              <div className="p-8 bg-white">
                <div className="space-y-5">
                  {/* Khách hàng */}
                  <div>
                    <label className="block text-slate-700 font-darker-grotesque mb-2" style={{ fontSize: '16px', fontWeight: 600 }}>
                      Khách hàng
                    </label>
                    <Select 
                      value={editFormData.customer_code} 
                      onValueChange={(value: string) => {
                        const customer = customers.find(c => c.code === value);
                        setEditFormData({ 
                          ...editFormData, 
                          customer_code: value,
                          customer_name: customer?.name || ''
                        });
                      }}
                    >
                      <SelectTrigger className="w-full font-darker-grotesque" style={{ fontSize: '16px' }}>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {customers.map(customer => (
                          <SelectItem key={customer.code} value={customer.code} className="font-darker-grotesque" style={{ fontSize: '16px' }}>
                            {customer.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Mã hóa đơn */}
                  <div>
                    <label className="block text-slate-700 font-darker-grotesque mb-2" style={{ fontSize: '16px', fontWeight: 600 }}>
                      Mã hóa đơn
                    </label>
                    <input
                      type="text"
                      value={editFormData.invoice_no}
                      onChange={(e) => setEditFormData({ ...editFormData, invoice_no: e.target.value })}
                      className="w-full px-4 py-2 border border-slate-300 rounded-lg font-darker-grotesque focus:outline-none focus:ring-2 focus:ring-orange-500"
                      style={{ fontSize: '16px' }}
                      placeholder="INV-2025-001"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-5">
                    {/* Ngày phát hành */}
                    <div>
                      <label className="block text-slate-700 font-darker-grotesque mb-2" style={{ fontSize: '16px', fontWeight: 600 }}>
                        Ngày phát hành
                      </label>
                      <input
                        type="date"
                        value={editFormData.issue_date}
                        onChange={(e) => setEditFormData({ ...editFormData, issue_date: e.target.value })}
                        className="w-full px-4 py-2 border border-slate-300 rounded-lg font-darker-grotesque focus:outline-none focus:ring-2 focus:ring-orange-500"
                        style={{ fontSize: '16px' }}
                      />
                    </div>

                    {/* Ngày đến hạn */}
                    <div>
                      <label className="block text-slate-700 font-darker-grotesque mb-2" style={{ fontSize: '16px', fontWeight: 600 }}>
                        Ngày đến hạn
                      </label>
                      <input
                        type="date"
                        value={editFormData.due_date}
                        onChange={(e) => setEditFormData({ ...editFormData, due_date: e.target.value })}
                        className="w-full px-4 py-2 border border-slate-300 rounded-lg font-darker-grotesque focus:outline-none focus:ring-2 focus:ring-orange-500"
                        style={{ fontSize: '16px' }}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-5">
                    {/* Tổng giá trị */}
                    <div>
                      <label className="block text-slate-700 font-darker-grotesque mb-2" style={{ fontSize: '16px', fontWeight: 600 }}>
                        Tổng giá trị
                      </label>
                      <input
                        type="number"
                        value={editFormData.amount}
                        onChange={(e) => setEditFormData({ ...editFormData, amount: parseInt(e.target.value) || 0 })}
                        className="w-full px-4 py-2 border border-slate-300 rounded-lg font-darker-grotesque focus:outline-none focus:ring-2 focus:ring-orange-500"
                        style={{ fontSize: '16px' }}
                      />
                    </div>

                    {/* Đã thu (read-only) */}
                    <div>
                      <label className="block text-slate-500 font-darker-grotesque mb-2" style={{ fontSize: '16px', fontWeight: 600 }}>
                        Đã thu
                      </label>
                      <input
                        type="text"
                        value={formatCurrency(editFormData.paid_amount)}
                        readOnly
                        className="w-full px-4 py-2 border border-slate-200 rounded-lg font-darker-grotesque bg-slate-50 text-slate-600"
                        style={{ fontSize: '16px' }}
                      />
                    </div>

                    {/* Còn phải thu (read-only) */}
                    <div>
                      <label className="block text-slate-500 font-darker-grotesque mb-2" style={{ fontSize: '16px', fontWeight: 600 }}>
                        Còn phải thu
                      </label>
                      <input
                        type="text"
                        value={formatCurrency(editFormData.remaining)}
                        readOnly
                        className="w-full px-4 py-2 border border-slate-200 rounded-lg font-darker-grotesque bg-slate-50 text-slate-600"
                        style={{ fontSize: '16px' }}
                      />
                    </div>
                  </div>

                  {/* Trạng thái (read-only) */}
                  <div>
                    <label className="block text-slate-500 font-darker-grotesque mb-2" style={{ fontSize: '16px', fontWeight: 600 }}>
                      Trạng thái
                    </label>
                    <div className="px-4 py-2 border border-slate-200 rounded-lg bg-slate-50 flex items-center">
                      {getStatusBadge(editFormData.status)}
                    </div>
                  </div>

                  {/* Ghi chú */}
                  <div>
                    <label className="block text-slate-700 font-darker-grotesque mb-2" style={{ fontSize: '16px', fontWeight: 600 }}>
                      Ghi chú
                    </label>
                    <textarea
                      value={editFormData.notes}
                      onChange={(e) => setEditFormData({ ...editFormData, notes: e.target.value })}
                      rows={4}
                      className="w-full px-4 py-2 border border-slate-300 rounded-lg font-darker-grotesque focus:outline-none focus:ring-2 focus:ring-orange-500 resize-none"
                      style={{ fontSize: '16px' }}
                      placeholder="Nhập ghi chú..."
                    />
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center justify-end gap-3 mt-8">
                  <Button
                    variant="outline"
                    onClick={() => setShowEditModal(false)}
                    className="font-darker-grotesque"
                    style={{ fontSize: '17px' }}
                  >
                    Hủy
                  </Button>
                  <Button
                    onClick={() => {
                      updateInvoiceMutation.mutate(
                        {
                          id: Number(editFormData.id),
                          data: {
                            issue_date: editFormData.issue_date,
                            due_date: editFormData.due_date,
                            total_amount: editFormData.amount,
                            notes: editFormData.notes || undefined,
                          },
                        },
                        {
                          onSuccess: () => {
                            toast.success('Cập nhật hóa đơn thành công!');
                            setShowEditModal(false);
                          },
                          onError: () => {
                            toast.error('Lỗi khi cập nhật hóa đơn');
                          },
                        }
                      );
                    }}
                    disabled={updateInvoiceMutation.isPending}
                    className="font-darker-grotesque bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 text-white"
                    style={{ fontSize: '17px' }}
                  >
                    <CheckCircle2 className="size-4 mr-2" />
                    {updateInvoiceMutation.isPending ? 'Đang lưu...' : 'Lưu thay đổi'}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Modal - Confirm Delete */}
      {showDeleteModal && selectedInvoice && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-lg shadow-2xl w-full max-w-md mx-4">
            <div className="overflow-hidden">
              {/* Red Header for Delete */}
              <div className="bg-gradient-to-r from-red-500 to-red-600 p-6 flex items-center justify-between">
                <h3 className="text-white font-alata" style={{ fontSize: '26px', fontWeight: 400 }}>
                  Xác nhận xóa
                </h3>
                <Button variant="ghost" size="icon" onClick={() => setShowDeleteModal(false)} className="text-white hover:bg-white/20">
                  <X className="size-6" />
                </Button>
              </div>

              {/* White Content Area */}
              <div className="p-8 bg-white">
                <div className="flex items-center gap-4 mb-6">
                  <div className="size-12 rounded-full bg-red-100 flex items-center justify-center">
                    <AlertCircle className="size-6 text-red-600" />
                  </div>
                  <div>
                    <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '17px', fontWeight: 600 }}>
                      Bạn có chắc muốn xóa hóa đơn này?
                    </p>
                    <p className="text-slate-600 font-darker-grotesque mt-1" style={{ fontSize: '15px' }}>
                      Hành động này không thể hoàn tác
                    </p>
                  </div>
                </div>

                <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 mb-6">
                  <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '14px' }}>Mã hóa đơn</p>
                  <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '16px', fontWeight: 600 }}>{selectedInvoice.invoice_no}</p>
                  <p className="text-slate-500 font-darker-grotesque mt-2 mb-1" style={{ fontSize: '14px' }}>Khách hàng</p>
                  <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '16px', fontWeight: 600 }}>{selectedInvoice.customer_name}</p>
                  <p className="text-slate-500 font-darker-grotesque mt-2 mb-1" style={{ fontSize: '14px' }}>Số tiền</p>
                  <p className="text-orange-600 font-darker-grotesque" style={{ fontSize: '16px', fontWeight: 600 }}>{formatCurrency(selectedInvoice.remaining)}</p>
                </div>

                {/* Actions */}
                <div className="flex items-center justify-end gap-3">
                  <Button
                    variant="outline"
                    onClick={() => setShowDeleteModal(false)}
                    className="font-darker-grotesque"
                    style={{ fontSize: '17px' }}
                  >
                    Hủy
                  </Button>
                  <Button
                    onClick={() => {
                      deleteInvoiceMutation.mutate(Number(selectedInvoice.id), {
                        onSuccess: () => {
                          toast.success('Xóa hóa đơn thành công!');
                          setShowDeleteModal(false);
                        },
                        onError: () => {
                          toast.error('Lỗi khi xóa hóa đơn');
                        },
                      });
                    }}
                    disabled={deleteInvoiceMutation.isPending}
                    className="font-darker-grotesque bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white"
                    style={{ fontSize: '17px' }}
                  >
                    <Trash2 className="size-4 mr-2" />
                    {deleteInvoiceMutation.isPending ? 'Đang xóa...' : 'Xóa hóa đơn'}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}