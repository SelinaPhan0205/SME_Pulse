import { Bell, Menu, Search, DollarSign, Clock, AlertCircle, TrendingDown, Building2, Eye, Edit, Trash2, Upload, ChevronLeft, ChevronRight, FileSpreadsheet, CheckCircle2, XCircle, X } from 'lucide-react';
import { Card, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { UserMenu } from './UserMenu';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { useState, useRef } from 'react';
import { useSidebar } from '../contexts/SidebarContext';
import { useBills, useSuppliers, useUpdateBill, useDeleteBill } from '../lib/api/hooks';
import { toast } from 'sonner';

type BillStatus = 'unpaid' | 'partial' | 'paid' | 'canceled';

interface APBill {
  id: string;
  bill_no: string;
  supplier_name: string;
  supplier_code: string;
  issue_date: string;
  due_date: string;
  terms_days: number;
  amount: number;
  paid_amount: number;
  remaining: number;
  status: BillStatus;
  aging: number;
  notes: string;
  email: string;
  phone: string;
}

interface Supplier {
  code: string;
  name: string;
  email: string;
  phone: string;
  terms_days: number;
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

export function AccountsPayable() {
  const { isSidebarOpen, toggleSidebar } = useSidebar();
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedBill, setSelectedBill] = useState<APBill | null>(null);
  const [currentPageBills, setCurrentPageBills] = useState(1);
  const [currentPageSuppliers, setCurrentPageSuppliers] = useState(1);
  const itemsPerPage = 10;

  // Import Excel states
  const [importStep, setImportStep] = useState<1 | 2>(1);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [previewData, setPreviewData] = useState<any[]>([]);
  const [importWarnings, setImportWarnings] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Edit form states
  const [editFormData, setEditFormData] = useState<APBill | null>(null);

  // Fetch bills from API
  const { data: billsData, isLoading: loadingBills } = useBills({
    search: searchQuery || undefined,
    status: statusFilter !== 'all' ? statusFilter : undefined,
    skip: (currentPageBills - 1) * itemsPerPage,
    limit: itemsPerPage,
  });

  // Fetch suppliers from API
  const { data: suppliersData } = useSuppliers({
    skip: (currentPageSuppliers - 1) * itemsPerPage,
    limit: itemsPerPage,
  });

  // Mutations
  const updateBillMutation = useUpdateBill();
  const deleteBillMutation = useDeleteBill();

  // Map API data to local interface
  const allBills: APBill[] = billsData?.items.map(bill => ({
    id: String(bill.id),
    bill_no: bill.bill_no,
    supplier_name: bill.supplier?.name || 'N/A',
    supplier_code: bill.supplier?.code || 'N/A',
    issue_date: bill.issue_date,
    due_date: bill.due_date,
    terms_days: bill.supplier?.payment_term || 30,
    amount: bill.total_amount,
    paid_amount: bill.paid_amount,
    remaining: bill.remaining_amount,
    status: bill.status as BillStatus,
    aging: bill.aging_days || Math.floor((new Date().getTime() - new Date(bill.due_date).getTime()) / (1000 * 60 * 60 * 24)),
    notes: bill.notes || '',
    email: bill.supplier?.email || '',
    phone: bill.supplier?.phone || '',
  })) || [];

  const suppliers: Supplier[] = suppliersData?.items.map(s => ({
    code: s.code || `NCC${s.id}`,
    name: s.name,
    email: s.email || '',
    phone: s.phone || '',
    terms_days: s.payment_term || 30,
  })) || [];

  // Calculate KPIs from API data
  const totalAP = allBills.reduce((sum, bill) => sum + bill.remaining, 0);
  const overdueAmount = allBills.filter(bill => bill.aging > 0).reduce((sum, bill) => sum + bill.remaining, 0);
  const unpaidCount = allBills.filter(bill => bill.status === 'unpaid' || bill.status === 'partial').length;
  const upcomingDue = allBills.filter(bill => bill.aging >= -7 && bill.aging < 0 && bill.status !== 'paid').length;

  // Use API paginated data directly
  const paginatedBills = allBills;
  const paginatedSuppliers = suppliers;
  const totalPagesBills = Math.ceil((billsData?.total || 0) / itemsPerPage);
  const totalPagesSuppliers = Math.ceil((suppliersData?.total || 0) / itemsPerPage);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(value);
  };

  const formatCurrencyShort = (value: number) => {
    if (value >= 1000000) {
      return `${(value / 1000000).toFixed(1)}M`;
    }
    return `${(value / 1000).toFixed(0)}K`;
  };

  const getStatusBadge = (status: BillStatus) => {
    const styles = {
      unpaid: 'bg-red-100 text-red-700 border-red-200',
      partial: 'bg-yellow-100 text-yellow-700 border-yellow-200',
      paid: 'bg-green-100 text-green-700 border-green-200',
      canceled: 'bg-gray-100 text-gray-700 border-gray-200'
    };
    const labels = {
      unpaid: 'Chưa trả',
      partial: 'Trả 1 phần',
      paid: 'Đã trả',
      canceled: 'Đã hủy'
    };
    return <Badge className={`${styles[status]} border font-darker-grotesque`} style={{ fontSize: '14px' }}>{labels[status]}</Badge>;
  };

  const handleViewDetail = (bill: APBill) => {
    setSelectedBill(bill);
    setShowDetailModal(true);
  };

  const handleEdit = (bill: APBill) => {
    setSelectedBill(bill);
    setEditFormData(bill);
    setShowEditModal(true);
  };

  const handleDelete = (bill: APBill) => {
    setSelectedBill(bill);
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
      { bill_no: 'BILL-2024-100', supplier_code: 'NCC001', issue_date: '01/12/2024', due_date: '31/12/2024', amount: '80000000' },
      { bill_no: 'BILL-2024-101', supplier_code: 'NCC002', issue_date: '01/12/2024', due_date: '31/12/2024', amount: '55000000' },
      { bill_no: 'BILL-2024-102', supplier_code: 'NCC999', issue_date: '02/12/2024', due_date: '01/01/2025', amount: '72000000' },
      { bill_no: 'BILL-2024-103', supplier_code: 'NCC003', issue_date: '02/12/2024', due_date: '01/01/2025', amount: '48000000' },
      { bill_no: 'BILL-2024-104', supplier_code: 'NCC888', issue_date: '03/12/2024', due_date: '02/01/2025', amount: '95000000' },
    ];

    setPreviewData(mockPreviewData);

    // Check for missing supplier codes
    const warnings: string[] = [];
    const existingCodes = suppliers.map(c => c.code);
    mockPreviewData.forEach(row => {
      if (!existingCodes.includes(row.supplier_code)) {
        warnings.push(`Mã nhà cung cấp "${row.supplier_code}" chưa tồn tại trong hệ thống`);
      }
    });

    setImportWarnings(warnings);
    setImportStep(2);
  };

  const handleImport = () => {
    // Simulate importing data
    alert(`Import thành công ${previewData.length} hóa đơn!`);
    handleCloseUploadModal();
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
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-purple-50/20 to-slate-100">
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
          <h2 className="text-slate-900 mb-1 font-alata" style={{ fontSize: '32px', fontWeight: 400 }}>Công nợ - Phải trả</h2>
          <p className="text-slate-600 font-darker-grotesque" style={{ fontSize: '18px' }}>
            Quản lý hóa đơn phải trả cho nhà cung cấp
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <Card className="border-0 shadow-md bg-gradient-to-br from-purple-500 to-purple-600 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 cursor-pointer">
            <CardContent className="pt-6">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-purple-100 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>Tổng phải trả</p>
                  <p className="text-white font-alata mt-2" style={{ fontSize: '28px', fontWeight: 700 }}>
                    {formatCurrencyShort(totalAP)}₫
                  </p>
                </div>
                <DollarSign className="size-10 text-purple-200" />
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

          <Card className="border-0 shadow-md bg-gradient-to-br from-indigo-500 to-indigo-600 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 cursor-pointer">
            <CardContent className="pt-6">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-indigo-100 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>Sắp đến hạn</p>
                  <p className="text-white font-alata mt-2" style={{ fontSize: '28px', fontWeight: 700 }}>
                    {upcomingDue}
                  </p>
                </div>
                <Clock className="size-10 text-indigo-200" />
              </div>
            </CardContent>
          </Card>

          <Card className="border-0 shadow-md bg-gradient-to-br from-violet-500 to-violet-600 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 cursor-pointer">
            <CardContent className="pt-6">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-violet-100 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>Hóa đơn chưa trả</p>
                  <p className="text-white font-alata mt-2" style={{ fontSize: '28px', fontWeight: 700 }}>
                    {unpaidCount}
                  </p>
                </div>
                <TrendingDown className="size-10 text-violet-200" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tabs */}
        <Tabs defaultValue="bills" className="space-y-6">
          <TabsList className="grid w-full grid-cols-2 h-auto p-1 bg-slate-100">
            <TabsTrigger 
              value="bills" 
              className="font-darker-grotesque data-[state=active]:bg-gradient-to-r data-[state=active]:from-purple-500 data-[state=active]:to-purple-600 data-[state=active]:text-white"
              style={{ fontSize: '18px', padding: '12px' }}
            >
              <DollarSign className="size-5 mr-2" />
              Danh sách phải trả
            </TabsTrigger>
            <TabsTrigger 
              value="suppliers" 
              className="font-darker-grotesque data-[state=active]:bg-gradient-to-r data-[state=active]:from-purple-500 data-[state=active]:to-purple-600 data-[state=active]:text-white"
              style={{ fontSize: '18px', padding: '12px' }}
            >
              <Building2 className="size-5 mr-2" />
              Danh mục nhà cung cấp
            </TabsTrigger>
          </TabsList>

          {/* Tab 1: Danh sách phải trả */}
          <TabsContent value="bills" className="space-y-6">
            {/* Filters and Actions */}
            <Card className="border-0 shadow-lg bg-white">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between gap-4 mb-4">
                  <div className="flex items-center gap-4 flex-1">
                    <div className="relative flex-1 max-w-md">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-5 text-slate-400" />
                      <input
                        type="text"
                        placeholder="Tìm theo mã hóa đơn hoặc tên nhà cung cấp..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg font-darker-grotesque focus:outline-none focus:ring-2 focus:ring-purple-500"
                        style={{ fontSize: '17px' }}
                      />
                    </div>
                    <Select value={statusFilter} onValueChange={setStatusFilter}>
                      <SelectTrigger className="w-[180px] font-darker-grotesque" style={{ fontSize: '17px' }}>
                        <SelectValue placeholder="Trạng thái" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all" className="font-darker-grotesque" style={{ fontSize: '16px' }}>Tất cả</SelectItem>
                        <SelectItem value="unpaid" className="font-darker-grotesque" style={{ fontSize: '16px' }}>Chưa trả</SelectItem>
                        <SelectItem value="partial" className="font-darker-grotesque" style={{ fontSize: '16px' }}>Trả 1 phần</SelectItem>
                        <SelectItem value="paid" className="font-darker-grotesque" style={{ fontSize: '16px' }}>Đã trả</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <Button
                    onClick={() => setShowUploadModal(true)}
                    className="font-darker-grotesque bg-gradient-to-r from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700 text-white"
                    style={{ fontSize: '17px' }}
                  >
                    <Upload className="size-4 mr-2" />
                    Import Excel
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Bills Table */}
            <Card className="border-0 shadow-lg bg-white">
              <CardContent className="pt-6">
                <div className="border rounded-lg overflow-hidden">
                  <table className="w-full">
                    <thead className="sticky top-0 bg-purple-50 text-slate-900 shadow-sm z-10">
                      <tr>
                        <th className="text-left p-4 font-darker-grotesque bg-purple-50" style={{ fontSize: '17px', fontWeight: 600 }}>Mã hóa đơn</th>
                        <th className="text-left p-4 font-darker-grotesque bg-purple-50" style={{ fontSize: '17px', fontWeight: 600 }}>Nhà cung cấp</th>
                        <th className="text-center p-4 font-darker-grotesque bg-purple-50" style={{ fontSize: '17px', fontWeight: 600 }}>Ngày đến hạn</th>
                        <th className="text-right p-4 font-darker-grotesque bg-purple-50" style={{ fontSize: '17px', fontWeight: 600 }}>Tổng tiền</th>
                        <th className="text-right p-4 font-darker-grotesque bg-purple-50" style={{ fontSize: '17px', fontWeight: 600 }}>Còn phải trả</th>
                        <th className="text-center p-4 font-darker-grotesque bg-purple-50" style={{ fontSize: '17px', fontWeight: 600 }}>Trạng thái</th>
                        <th className="text-center p-4 font-darker-grotesque bg-purple-50" style={{ fontSize: '17px', fontWeight: 600 }}>Tuổi nợ</th>
                        <th className="text-center p-4 font-darker-grotesque bg-purple-50" style={{ fontSize: '17px', fontWeight: 600 }}>Thao tác</th>
                      </tr>
                    </thead>
                    <tbody>
                      {loadingBills ? (
                        Array.from({ length: 5 }).map((_, idx) => (
                          <tr key={idx} className="border-b border-slate-100">
                            <td className="p-4" colSpan={8}>
                              <div className="h-12 bg-slate-100 rounded animate-pulse"></div>
                            </td>
                          </tr>
                        ))
                      ) : paginatedBills.length === 0 ? (
                        <tr>
                          <td colSpan={8} className="p-8 text-center text-slate-500 font-darker-grotesque" style={{ fontSize: '16px' }}>
                            Không có hóa đơn nào
                          </td>
                        </tr>
                      ) : (
                        paginatedBills.map((bill, idx) => (
                        <tr key={bill.id} className={`border-b border-slate-100 hover:bg-purple-50/30 transition-colors ${idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'}`}>
                          <td className="p-4 font-darker-grotesque text-slate-900" style={{ fontSize: '16px', fontWeight: 500 }}>
                            {bill.bill_no}
                          </td>
                          <td className="p-4 font-darker-grotesque text-slate-700" style={{ fontSize: '16px' }}>
                            {bill.supplier_name}
                          </td>
                          <td className="p-4 text-center font-darker-grotesque text-slate-700" style={{ fontSize: '16px' }}>
                            {new Date(bill.due_date).toLocaleDateString('vi-VN')}
                          </td>
                          <td className="p-4 text-right font-darker-grotesque text-slate-900" style={{ fontSize: '16px', fontWeight: 500 }}>
                            {formatCurrency(bill.amount)}
                          </td>
                          <td className="p-4 text-right font-darker-grotesque" style={{ fontSize: '16px', fontWeight: 600 }}>
                            <span className={bill.remaining > 0 ? 'text-purple-600' : 'text-green-600'}>
                              {formatCurrency(bill.remaining)}
                            </span>
                          </td>
                          <td className="p-4 text-center">
                            {getStatusBadge(bill.status)}
                          </td>
                          <td className="p-4 text-center">
                            <span className={`font-darker-grotesque px-3 py-1 rounded-full ${
                              bill.aging > 0 
                                ? 'bg-red-100 text-red-700' 
                                : 'bg-green-100 text-green-700'
                            }`} style={{ fontSize: '15px', fontWeight: 600 }}>
                              {bill.aging > 0 ? `+${bill.aging}` : bill.aging} ngày
                            </span>
                          </td>
                          <td className="p-4">
                            <div className="flex items-center justify-center gap-2">
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleViewDetail(bill)}
                                className="hover:bg-purple-100 hover:text-purple-700"
                              >
                                <Eye className="size-4" />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleEdit(bill)}
                                className="hover:bg-blue-100 hover:text-blue-700"
                              >
                                <Edit className="size-4" />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleDelete(bill)}
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
                    onClick={() => setCurrentPageBills(prev => Math.max(1, prev - 1))}
                    disabled={currentPageBills === 1}
                    className="font-darker-grotesque h-9 w-9 p-0"
                  >
                    <ChevronLeft className="size-4" />
                  </Button>
                  
                  {getPageNumbers(currentPageBills, totalPagesBills).map((page, idx) => {
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
                        onClick={() => setCurrentPageBills(pageNum)}
                        className={`font-darker-grotesque h-9 w-9 p-0 ${
                          currentPageBills === pageNum
                            ? 'bg-gradient-to-r from-purple-400 to-purple-500 text-white border-purple-500 hover:bg-gradient-to-r hover:from-purple-500 hover:to-purple-600'
                            : 'bg-white hover:bg-slate-100'
                        }`}
                        style={{ fontWeight: currentPageBills === pageNum ? 600 : 400 }}
                      >
                        {pageNum}
                      </Button>
                    );
                  })}
                  
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPageBills(prev => Math.min(totalPagesBills, prev + 1))}
                    disabled={currentPageBills === totalPagesBills}
                    className="font-darker-grotesque h-9 w-9 p-0"
                  >
                    <ChevronRight className="size-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Tab 2: Danh mục nhà cung cấp */}
          <TabsContent value="suppliers" className="space-y-6">
            <Card className="border-0 shadow-lg bg-white">
              <CardContent className="pt-6">
                <div className="border rounded-lg overflow-hidden">
                  <table className="w-full">
                    <thead className="sticky top-0 bg-purple-50 text-slate-900 shadow-sm z-10">
                      <tr>
                        <th className="text-left p-4 font-darker-grotesque bg-purple-50" style={{ fontSize: '17px', fontWeight: 600 }}>Mã NCC</th>
                        <th className="text-left p-4 font-darker-grotesque bg-purple-50" style={{ fontSize: '17px', fontWeight: 600 }}>Tên nhà cung cấp</th>
                        <th className="text-left p-4 font-darker-grotesque bg-purple-50" style={{ fontSize: '17px', fontWeight: 600 }}>Email</th>
                        <th className="text-center p-4 font-darker-grotesque bg-purple-50" style={{ fontSize: '17px', fontWeight: 600 }}>Số điện thoại</th>
                        <th className="text-center p-4 font-darker-grotesque bg-purple-50" style={{ fontSize: '17px', fontWeight: 600 }}>Terms (ngày)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {paginatedSuppliers.map((supplier, idx) => (
                        <tr key={supplier.code} className={`border-b border-slate-100 hover:bg-purple-50/30 transition-colors ${idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'}`}>
                          <td className="p-4 font-darker-grotesque text-slate-900" style={{ fontSize: '16px', fontWeight: 500 }}>
                            {supplier.code}
                          </td>
                          <td className="p-4 font-darker-grotesque text-slate-700" style={{ fontSize: '16px' }}>
                            {supplier.name}
                          </td>
                          <td className="p-4 font-darker-grotesque text-slate-700" style={{ fontSize: '16px' }}>
                            {supplier.email}
                          </td>
                          <td className="p-4 text-center font-darker-grotesque text-slate-700" style={{ fontSize: '16px' }}>
                            {supplier.phone}
                          </td>
                          <td className="p-4 text-center font-darker-grotesque text-slate-900" style={{ fontSize: '16px', fontWeight: 500 }}>
                            {supplier.terms_days}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Smart Pagination for Suppliers */}
                {totalPagesSuppliers > 1 && (
                  <div className="flex items-center justify-center gap-2 mt-6">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPageSuppliers(prev => Math.max(1, prev - 1))}
                      disabled={currentPageSuppliers === 1}
                      className="font-darker-grotesque h-9 w-9 p-0"
                    >
                      <ChevronLeft className="size-4" />
                    </Button>
                    
                    {getPageNumbers(currentPageSuppliers, totalPagesSuppliers).map((page, idx) => {
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
                          onClick={() => setCurrentPageSuppliers(pageNum)}
                          className={`font-darker-grotesque h-9 w-9 p-0 ${
                            currentPageSuppliers === pageNum
                              ? 'bg-gradient-to-r from-purple-400 to-purple-500 text-white border-purple-500 hover:bg-gradient-to-r hover:from-purple-500 hover:to-purple-600'
                              : 'bg-white hover:bg-slate-100'
                          }`}
                          style={{ fontWeight: currentPageSuppliers === pageNum ? 600 : 400 }}
                        >
                          {pageNum}
                        </Button>
                      );
                    })}
                    
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPageSuppliers(prev => Math.min(totalPagesSuppliers, prev + 1))}
                      disabled={currentPageSuppliers === totalPagesSuppliers}
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

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-lg shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto mx-4">
            {/* Step 1: File Upload */}
            {importStep === 1 && (
              <div className="overflow-hidden">
                {/* Purple Header - matching page theme */}
                <div className="bg-gradient-to-r from-purple-500 to-purple-600 p-6 flex items-center justify-between">
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
                        ? 'border-purple-400 bg-purple-50' 
                        : 'border-slate-300 bg-white hover:border-purple-300 hover:bg-purple-50/30'
                    }`}
                    onDrop={handleFileDrop}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <Upload className="size-20 mx-auto mb-4 text-slate-400" strokeWidth={1.5} />
                    <p className="text-slate-700 font-darker-grotesque mb-2" style={{ fontSize: '18px', fontWeight: 500 }}>
                      {selectedFile ? selectedFile.name : 'Kéo thả file hoặc click để chọn'}
                    </p>
                    <p className="text-slate-500 font-darker-grotesque" style={{ fontSize: '16px' }}>
                      Hỗ trợ file .xlsx, .xls (tối đa 5MB)
                    </p>
                    <input
                      type="file"
                      accept=".xlsx,.xls,.csv"
                      onChange={handleFileSelect}
                      className="hidden"
                      ref={fileInputRef}
                    />
                  </div>

                  {/* Requirements - Purple theme to match page */}
                  <div className="mt-6 bg-purple-50 border border-purple-200 rounded-xl p-5">
                    <h4 className="text-purple-900 font-darker-grotesque mb-3 flex items-center gap-2" style={{ fontSize: '17px', fontWeight: 600 }}>
                      <FileSpreadsheet className="size-5 text-purple-600" />
                      Lưu ý khi import:
                    </h4>
                    <ul className="space-y-2 text-purple-800 font-darker-grotesque" style={{ fontSize: '16px' }}>
                      <li className="flex items-start gap-2">
                        <span className="text-purple-600">•</span>
                        <span>File phải chứa các cột: <strong>bill_no, supplier_code, issue_date, due_date, amount</strong></span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-purple-600">•</span>
                        <span>Định dạng ngày: <strong>DD/MM/YYYY</strong></span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-purple-600">•</span>
                        <span>Số tiền không cần ký hiệu tiền tệ, chỉ ghi số</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-purple-600">•</span>
                        <span>Mã nhà cung cấp phải tồn tại trong danh mục</span>
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
                      className="font-darker-grotesque bg-gradient-to-r from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700 text-white disabled:opacity-50 disabled:cursor-not-allowed"
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
                {/* Purple Header - matching Step 1 */}
                <div className="bg-gradient-to-r from-purple-500 to-purple-600 p-6 flex items-center justify-between">
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
                        <thead className="bg-purple-50">
                          <tr>
                            <th className="text-left p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '16px', fontWeight: 600 }}>Mã hóa đơn</th>
                            <th className="text-left p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '16px', fontWeight: 600 }}>Mã NCC</th>
                            <th className="text-center p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '16px', fontWeight: 600 }}>Ngày phát hành</th>
                            <th className="text-center p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '16px', fontWeight: 600 }}>Ngày đến hạn</th>
                            <th className="text-right p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '16px', fontWeight: 600 }}>Số tiền</th>
                          </tr>
                        </thead>
                        <tbody>
                          {previewData.map((row, idx) => (
                            <tr key={idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'}>
                              <td className="p-3 font-darker-grotesque text-slate-900 border-b border-slate-100" style={{ fontSize: '15px', fontWeight: 500 }}>
                                {row.bill_no}
                              </td>
                              <td className="p-3 font-darker-grotesque text-slate-700 border-b border-slate-100" style={{ fontSize: '15px' }}>
                                {row.supplier_code}
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
                      className="font-darker-grotesque"
                      style={{ fontSize: '17px' }}
                    >
                      Hủy
                    </Button>
                    <Button
                      onClick={handleImport}
                      className="font-darker-grotesque bg-gradient-to-r from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700 text-white"
                      style={{ fontSize: '17px' }}
                    >
                      <CheckCircle2 className="size-4 mr-2" />
                      Import
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Detail Modal - View Bill */}
      {showDetailModal && selectedBill && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-lg shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto mx-4">
            <div className="overflow-hidden">
              {/* Purple Header - Sticky */}
              <div className="bg-gradient-to-r from-purple-500 to-purple-600 p-6 flex items-center justify-between sticky top-0 z-10">
                <h3 className="text-white font-alata" style={{ fontSize: '28px', fontWeight: 400 }}>
                  Chi tiết hóa đơn phải trả
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
                      <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '17px', fontWeight: 600 }}>{selectedBill.bill_no}</p>
                    </div>
                    <div>
                      <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '15px' }}>Mã nhà cung cấp</p>
                      <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '17px', fontWeight: 600 }}>{selectedBill.supplier_code}</p>
                    </div>
                    <div>
                      <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '15px' }}>Tên nhà cung cấp</p>
                      <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '17px', fontWeight: 600 }}>{selectedBill.supplier_name}</p>
                    </div>
                    <div>
                      <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '15px' }}>Trạng thái</p>
                      <div className="mt-1">{getStatusBadge(selectedBill.status)}</div>
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
                      <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '17px', fontWeight: 600 }}>{new Date(selectedBill.issue_date).toLocaleDateString('vi-VN')}</p>
                    </div>
                    <div>
                      <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '15px' }}>Ngày đến hạn</p>
                      <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '17px', fontWeight: 600 }}>{new Date(selectedBill.due_date).toLocaleDateString('vi-VN')}</p>
                    </div>
                    <div>
                      <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '15px' }}>Tuổi nợ</p>
                      <p className={`font-darker-grotesque ${selectedBill.aging > 0 ? 'text-red-600' : 'text-green-600'}`} style={{ fontSize: '17px', fontWeight: 600 }}>
                        {selectedBill.aging > 0 ? `+${selectedBill.aging}` : selectedBill.aging} ngày
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
                      <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '17px', fontWeight: 600 }}>{formatCurrency(selectedBill.amount)}</p>
                    </div>
                    <div>
                      <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '15px' }}>Đã chi</p>
                      <p className="text-green-600 font-darker-grotesque" style={{ fontSize: '17px', fontWeight: 600 }}>{formatCurrency(selectedBill.paid_amount)}</p>
                    </div>
                    <div>
                      <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '15px' }}>Còn phải trả</p>
                      <p className="text-purple-600 font-darker-grotesque" style={{ fontSize: '17px', fontWeight: 600 }}>{formatCurrency(selectedBill.remaining)}</p>
                    </div>
                  </div>
                </div>

                {/* 4. Ghi chú */}
                <div className="mb-6">
                  <h4 className="text-slate-700 font-darker-grotesque mb-4 pb-2 border-b border-slate-200" style={{ fontSize: '18px', fontWeight: 600 }}>
                    Ghi chú
                  </h4>
                  <p className="text-slate-700 font-darker-grotesque bg-slate-50 p-4 rounded-lg border border-slate-200" style={{ fontSize: '16px' }}>
                    {selectedBill.notes || 'Không có ghi chú'}
                  </p>
                </div>

                {/* 5. Danh sách thanh toán liên quan */}
                <div className="mb-6">
                  <h4 className="text-slate-700 font-darker-grotesque mb-4 pb-2 border-b border-slate-200 flex items-center gap-2" style={{ fontSize: '18px', fontWeight: 600 }}>
                    <DollarSign className="size-5 text-purple-600" />
                    Danh sách thanh toán liên quan
                  </h4>
                  <div className="border rounded-lg overflow-hidden">
                    <table className="w-full">
                      <thead className="bg-purple-50">
                        <tr>
                          <th className="text-left p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '15px', fontWeight: 600 }}>Mã thanh toán</th>
                          <th className="text-center p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '15px', fontWeight: 600 }}>Ngày</th>
                          <th className="text-center p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '15px', fontWeight: 600 }}>Phương thức</th>
                          <th className="text-right p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '15px', fontWeight: 600 }}>Số tiền thanh toán</th>
                          <th className="text-right p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '15px', fontWeight: 600 }}>Đã phân bổ</th>
                          <th className="text-left p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '15px', fontWeight: 600 }}>Mã tham chiếu</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedBill.paid_amount > 0 ? (
                          <tr className="bg-white border-b border-slate-100">
                            <td className="p-3 font-darker-grotesque text-slate-900" style={{ fontSize: '15px', fontWeight: 500 }}>PAY-2024-001</td>
                            <td className="p-3 text-center font-darker-grotesque text-slate-700" style={{ fontSize: '15px' }}>15/11/2024</td>
                            <td className="p-3 text-center">
                              <Badge className="bg-blue-100 text-blue-700 border-blue-200 border font-darker-grotesque" style={{ fontSize: '13px' }}>Transfer</Badge>
                            </td>
                            <td className="p-3 text-right font-darker-grotesque text-slate-900" style={{ fontSize: '15px', fontWeight: 500 }}>
                              {formatCurrency(selectedBill.paid_amount)}
                            </td>
                            <td className="p-3 text-right font-darker-grotesque text-green-600" style={{ fontSize: '15px', fontWeight: 500 }}>
                              {formatCurrency(selectedBill.paid_amount)}
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
                        {new Date(selectedBill.issue_date).toLocaleString('vi-VN')}
                      </p>
                    </div>
                    <div>
                      <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '14px' }}>Cập nhật lúc</p>
                      <p className="text-slate-700 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>
                        {new Date(selectedBill.due_date).toLocaleString('vi-VN')}
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
                      handleEdit(selectedBill);
                    }}
                    className="font-darker-grotesque bg-gradient-to-r from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700 text-white"
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

      {/* Edit Modal - Edit Bill */}
      {showEditModal && editFormData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-lg shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto mx-4">
            <div className="overflow-hidden">
              {/* Purple Header */}
              <div className="bg-gradient-to-r from-purple-500 to-purple-600 p-6 flex items-center justify-between">
                <div>
                  <h3 className="text-white font-alata" style={{ fontSize: '28px', fontWeight: 400 }}>
                    Sửa hóa đơn phải trả
                  </h3>
                  <p className="text-purple-100 font-darker-grotesque mt-1" style={{ fontSize: '16px' }}>
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
                  {/* Nhà cung cấp */}
                  <div>
                    <label className="block text-slate-700 font-darker-grotesque mb-2" style={{ fontSize: '16px', fontWeight: 600 }}>
                      Nhà cung cấp
                    </label>
                    <Select 
                      value={editFormData.supplier_code} 
                      onValueChange={(value: string) => {
                        const supplier = suppliers.find(s => s.code === value);
                        setEditFormData({ 
                          ...editFormData, 
                          supplier_code: value,
                          supplier_name: supplier?.name || ''
                        });
                      }}
                    >
                      <SelectTrigger className="w-full font-darker-grotesque" style={{ fontSize: '16px' }}>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {suppliers.map(supplier => (
                          <SelectItem key={supplier.code} value={supplier.code} className="font-darker-grotesque" style={{ fontSize: '16px' }}>
                            {supplier.code} - {supplier.name}
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
                      value={editFormData.bill_no}
                      onChange={(e) => setEditFormData({ ...editFormData, bill_no: e.target.value })}
                      className="w-full px-4 py-2 border border-slate-300 rounded-lg font-darker-grotesque focus:outline-none focus:ring-2 focus:ring-purple-500"
                      style={{ fontSize: '16px' }}
                      placeholder="BILL-2025-001"
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
                        className="w-full px-4 py-2 border border-slate-300 rounded-lg font-darker-grotesque focus:outline-none focus:ring-2 focus:ring-purple-500"
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
                        className="w-full px-4 py-2 border border-slate-300 rounded-lg font-darker-grotesque focus:outline-none focus:ring-2 focus:ring-purple-500"
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
                        className="w-full px-4 py-2 border border-slate-300 rounded-lg font-darker-grotesque focus:outline-none focus:ring-2 focus:ring-purple-500"
                        style={{ fontSize: '16px' }}
                      />
                    </div>

                    {/* Đã chi (read-only) */}
                    <div>
                      <label className="block text-slate-500 font-darker-grotesque mb-2" style={{ fontSize: '16px', fontWeight: 600 }}>
                        Đã chi
                      </label>
                      <input
                        type="text"
                        value={formatCurrency(editFormData.paid_amount)}
                        readOnly
                        className="w-full px-4 py-2 border border-slate-200 rounded-lg font-darker-grotesque bg-slate-50 text-slate-600"
                        style={{ fontSize: '16px' }}
                      />
                    </div>

                    {/* Còn phải trả (read-only) */}
                    <div>
                      <label className="block text-slate-500 font-darker-grotesque mb-2" style={{ fontSize: '16px', fontWeight: 600 }}>
                        Còn phải trả
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
                      className="w-full px-4 py-2 border border-slate-300 rounded-lg font-darker-grotesque focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
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
                      updateBillMutation.mutate(
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
                    disabled={updateBillMutation.isPending}
                    className="font-darker-grotesque bg-gradient-to-r from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700 text-white"
                    style={{ fontSize: '17px' }}
                  >
                    <CheckCircle2 className="size-4 mr-2" />
                    {updateBillMutation.isPending ? 'Đang lưu...' : 'Lưu thay đổi'}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Modal - Confirm Delete */}
      {showDeleteModal && selectedBill && (
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
                  <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '16px', fontWeight: 600 }}>{selectedBill.bill_no}</p>
                  <p className="text-slate-500 font-darker-grotesque mt-2 mb-1" style={{ fontSize: '14px' }}>Nhà cung cấp</p>
                  <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '16px', fontWeight: 600 }}>{selectedBill.supplier_name}</p>
                  <p className="text-slate-500 font-darker-grotesque mt-2 mb-1" style={{ fontSize: '14px' }}>Còn phải trả</p>
                  <p className="text-purple-600 font-darker-grotesque" style={{ fontSize: '16px', fontWeight: 600 }}>{formatCurrency(selectedBill.remaining)}</p>
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
                      deleteBillMutation.mutate(Number(selectedBill.id), {
                        onSuccess: () => {
                          toast.success('Xóa hóa đơn thành công!');
                          setShowDeleteModal(false);
                        },
                        onError: () => {
                          toast.error('Lỗi khi xóa hóa đơn');
                        },
                      });
                    }}
                    disabled={deleteBillMutation.isPending}
                    className="font-darker-grotesque bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white"
                    style={{ fontSize: '17px' }}
                  >
                    <Trash2 className="size-4 mr-2" />
                    {deleteBillMutation.isPending ? 'Đang xóa...' : 'Xóa hóa đơn'}
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