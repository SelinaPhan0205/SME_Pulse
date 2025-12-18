import { Bell, Menu, Plus, QrCode, Download, CheckCircle, AlertTriangle, CreditCard, DollarSign, X } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { UserMenu } from './UserMenu';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from './ui/dialog';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import { ChevronLeft, ChevronRight, Eye } from 'lucide-react';
import { useSidebar } from '../contexts/SidebarContext';
import { usePayments, useAccounts, useCreatePayment, useReconciliationKPI, useAutoMatchReconciliation, useConfirmReconciliation } from '../lib/api/hooks';
import { toast } from 'sonner';

interface Allocation {
  type: 'AR' | 'AP';
  code: string;
  dueDate: string;
  totalAmount: number;
  paidAmount: number;
  allocated: number;
  remaining: number;
}

interface Payment {
  id: number;
  code: string;
  date: string;
  amount: number;
  method: string;
  accountName: string;
  accountNumber: string;
  bankName: string;
  reference: string;
  memo: string;
  status: string;
  allocations: Allocation[];
  createdAt: string;
  updatedAt: string;
}

interface Account {
  id: number;
  bankName: string;
  accountNumber: string;
  accountName: string;
  display: string;
}

interface UnpaidInvoice {
  id: number;
  type: 'AR' | 'AP';
  code: string;
  customerSupplier: string;
  dueDate: string;
  remaining: number;
  selected: boolean;
  allocatedAmount: number;
}

export function Payments() {
  const { isSidebarOpen, toggleSidebar } = useSidebar();
  const [selectedMethod, setSelectedMethod] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');

  // Reset to page 1 when filters change
  useEffect(() => {
    setCurrentPagePayments(1);
  }, [selectedMethod, searchTerm]);
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [isQRDialogOpen, setIsQRDialogOpen] = useState(false);
  const [currentPagePayments, setCurrentPagePayments] = useState(1);
  const [currentPageReconcile, setCurrentPageReconcile] = useState(1);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [selectedPayment, setSelectedPayment] = useState<Payment | null>(null);
  const [showReconcileModal, setShowReconcileModal] = useState(false);
  const [selectedReconcile, setSelectedReconcile] = useState<any>(null);
  const itemsPerPage = 10;

  // Fetch ALL payments from API (để filter ở client hoạt động)
  // Nếu có nhiều data, nên chuyển sang server-side filtering
  const { data: paymentsData, isLoading: loadingPayments, refetch: refetchPayments } = usePayments({
    skip: 0,
    limit: 1000, // Load all payments for client-side filtering
  });

  // Fetch accounts from API
  const { data: accountsData } = useAccounts();

  // Fetch reconciliation KPI
  const { data: reconciliationData, isLoading: loadingReconciliation, refetch: refetchReconciliation } = useReconciliationKPI();

  // Mutations
  const createPaymentMutation = useCreatePayment();
  const autoMatchMutation = useAutoMatchReconciliation();
  const confirmReconciliationMutation = useConfirmReconciliation();

  // QR Code states
  const [qrAmount, setQrAmount] = useState('');
  const [qrDescription, setQrDescription] = useState('');

  // Add Payment Form states
  const [formDate, setFormDate] = useState('');
  const [formAmount, setFormAmount] = useState('');
  const [formAccountId, setFormAccountId] = useState('');
  const [formMethod, setFormMethod] = useState('');
  const [formReference, setFormReference] = useState('');
  const [formNotes, setFormNotes] = useState('');
  const [unpaidInvoices, setUnpaidInvoices] = useState<UnpaidInvoice[]>([
    { id: 1, type: 'AP', code: 'BILL-2024-001', customerSupplier: 'NCC ABC', dueDate: '30/11/2024', remaining: 25039440, selected: false, allocatedAmount: 0 },
    { id: 2, type: 'AR', code: 'INV-2024-005', customerSupplier: 'Công ty XYZ', dueDate: '05/12/2024', remaining: 10000000, selected: false, allocatedAmount: 0 },
    { id: 3, type: 'AP', code: 'BILL-2024-002', customerSupplier: 'NCC DEF', dueDate: '10/12/2024', remaining: 15000000, selected: false, allocatedAmount: 0 },
    { id: 4, type: 'AR', code: 'INV-2024-006', customerSupplier: 'Công ty AAA', dueDate: '15/12/2024', remaining: 8000000, selected: false, allocatedAmount: 0 },
  ]);

  // Map accounts from API
  const accounts: Account[] = accountsData?.items.map(acc => ({
    id: acc.id,
    bankName: acc.bank_name || 'Cash',
    accountNumber: acc.account_number || '-',
    accountName: acc.name,
    display: `${acc.bank_name || 'Cash'} – ${acc.account_number || 'N/A'} – ${acc.name}`,
  })) || [];

  // Map payments from API
  const allPayments: Payment[] = paymentsData?.items.map(pay => ({
    id: pay.id,
    code: `PAY-${pay.id}`,
    date: new Date(pay.transaction_date).toLocaleDateString('vi-VN'),
    amount: pay.amount,
    method: pay.payment_method || 'transfer',
    accountName: pay.account?.name || 'N/A',
    accountNumber: pay.account?.account_number || '-',
    bankName: pay.account?.bank_name || 'Cash',
    reference: pay.reference_code || '',
    memo: pay.notes || '',
    status: 'verified',
    allocations: pay.allocations?.map(alloc => ({
      type: alloc.ar_invoice_id ? 'AR' as const : 'AP' as const,
      code: alloc.ar_invoice_id ? `INV-${alloc.ar_invoice_id}` : `BILL-${alloc.ap_bill_id}`,
      dueDate: 'N/A',
      totalAmount: alloc.allocated_amount,
      paidAmount: 0,
      allocated: alloc.allocated_amount,
      remaining: 0,
    })) || [],
    createdAt: new Date(pay.created_at).toLocaleString('vi-VN'),
    updatedAt: new Date(pay.updated_at).toLocaleString('vi-VN'),
  })) || [];

  // Generate reconciliation data from real payments (simulated bank transactions)
  // Backend simulates bank_transaction_id = payment.id + 10000
  // We create reconcile entries showing comparison between "bank" and "POS/system"
  const reconcileData = allPayments.map((payment, idx) => {
    // Simulate: Most payments are matched, some have differences for demo
    const isMatched = idx % 5 !== 3; // Every 5th payment (starting from 4th) is unmatched for demo
    const hasMismatch = idx % 7 === 2; // Every 7th payment (starting from 3rd) has small mismatch
    
    let bankAmount = payment.amount;
    let posAmount = payment.amount;
    let difference = 0;
    let status: 'matched' | 'mismatch' | 'unmatched' = 'matched';
    
    if (!isMatched) {
      // Unmatched: bank has transaction but POS doesn't
      posAmount = 0;
      difference = bankAmount;
      status = 'unmatched';
    } else if (hasMismatch) {
      // Mismatch: small difference between bank and POS
      const mismatchAmount = Math.round(payment.amount * 0.001); // 0.1% difference
      posAmount = payment.amount - mismatchAmount;
      difference = mismatchAmount;
      status = 'mismatch';
    }
    
    return {
      id: payment.id + 10000, // Simulated bank transaction ID
      paymentId: payment.id,
      date: payment.date,
      bankAmount,
      posAmount,
      difference,
      reference: payment.reference || `REF-${payment.id}`,
      status,
    };
  });

  // Use API data for summary cards if available
  // ReconciliationKPI: { total_transactions, matched, unmatched, suspicious, match_rate }
  const matchedCount = reconciliationData?.matched || reconcileData.filter(r => r.status === 'matched').length;
  const unmatchedCount = reconciliationData?.unmatched || reconcileData.filter(r => r.status === 'unmatched').length;
  const mismatchCount = reconcileData.filter(r => r.status === 'mismatch').length;

  const getMethodBadge = (method: string) => {
    const methodConfig = {
      cash: { label: 'Tiền mặt', color: 'bg-amber-100 text-amber-700 border-amber-200' },
      transfer: { label: 'Chuyển khoản', color: 'bg-blue-100 text-blue-700 border-blue-200' },
      vietqr: { label: 'VietQR', color: 'bg-emerald-100 text-emerald-700 border-emerald-200' },
      card: { label: 'Thẻ', color: 'bg-purple-100 text-purple-700 border-purple-200' },
    };
    const config = methodConfig[method as keyof typeof methodConfig] || methodConfig.cash;
    return <Badge variant="outline" className={`${config.color} font-darker-grotesque border`} style={{ fontSize: '15px' }}>{config.label}</Badge>;
  };

  const getStatusBadge = (status: string) => {
    if (status === 'verified') {
      return <Badge className="bg-green-100 text-green-700 border-green-200 font-darker-grotesque border" style={{ fontSize: '15px' }}>Đã xác minh</Badge>;
    }
    return <Badge className="bg-yellow-100 text-yellow-700 border-yellow-200 font-darker-grotesque border" style={{ fontSize: '15px' }}>Chờ xác minh</Badge>;
  };

  const getReconcileStatus = (status: string) => {
    const statusConfig = {
      matched: { label: 'Khớp', color: 'bg-green-100 text-green-700 border-green-200', icon: CheckCircle },
      mismatch: { label: 'Lệch', color: 'bg-red-100 text-red-700 border-red-200', icon: AlertTriangle },
      unmatched: { label: 'Chưa ghép', color: 'bg-yellow-100 text-yellow-700 border-yellow-200', icon: AlertTriangle },
    };
    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.matched;
    const Icon = config.icon;
    return (
      <Badge variant="outline" className={`${config.color} font-darker-grotesque border flex items-center gap-1 w-fit`} style={{ fontSize: '15px' }}>
        <Icon className="size-3.5" />
        {config.label}
      </Badge>
    );
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount);
  };

  const filteredPayments = allPayments.filter(payment => {
    const matchMethod = selectedMethod === 'all' || payment.method === selectedMethod;
    const matchSearch = searchTerm === '' || 
                       payment.accountName.toLowerCase().includes(searchTerm.toLowerCase()) ||
                       payment.reference.toLowerCase().includes(searchTerm.toLowerCase()) ||
                       payment.code.toLowerCase().includes(searchTerm.toLowerCase()) ||
                       payment.memo.toLowerCase().includes(searchTerm.toLowerCase());
    return matchMethod && matchSearch;
  });

  // Paginate the FILTERED payments (not allPayments)
  const paginatedPayments = filteredPayments.slice(
    (currentPagePayments - 1) * itemsPerPage,
    currentPagePayments * itemsPerPage
  );
  const totalPagesPayments = Math.ceil(filteredPayments.length / itemsPerPage);
  const paginatedReconcile = reconcileData.slice((currentPageReconcile - 1) * itemsPerPage, currentPageReconcile * itemsPerPage);

  const handleViewDetail = (payment: Payment) => {
    setSelectedPayment(payment);
    setShowDetailModal(true);
  };

  // Generate VietQR URL
  const generateQRUrl = () => {
    if (!qrAmount || !qrDescription) return null;
    
    // VietQR format: https://img.vietqr.io/image/{BANK_ID}-{ACCOUNT_NO}-{TEMPLATE}.png?amount={AMOUNT}&addInfo={DESCRIPTION}
    const bankId = 'MB'; // MB Bank
    const accountNo = '123456789';
    const template = 'compact2'; // compact layout
    
    return `https://img.vietqr.io/image/${bankId}-${accountNo}-${template}.png?amount=${qrAmount}&addInfo=${encodeURIComponent(qrDescription)}&accountName=CONG%20TY%20ABC`;
  };

  const qrUrl = generateQRUrl();

  // Toggle invoice selection
  const toggleInvoiceSelection = (id: number) => {
    setUnpaidInvoices(prev => 
      prev.map(inv => 
        inv.id === id 
          ? { ...inv, selected: !inv.selected, allocatedAmount: !inv.selected ? 0 : inv.allocatedAmount }
          : inv
      )
    );
  };

  // Update allocated amount
  const updateAllocatedAmount = (id: number, amount: number) => {
    setUnpaidInvoices(prev =>
      prev.map(inv => 
        inv.id === id ? { ...inv, allocatedAmount: amount } : inv
      )
    );
  };

  // Calculate total allocated
  const totalAllocated = unpaidInvoices
    .filter(inv => inv.selected)
    .reduce((sum, inv) => sum + inv.allocatedAmount, 0);

  // Handle form submit
  const handleSubmitPayment = () => {
    // Validation
    if (!formDate || !formAmount || !formAccountId || !formMethod) {
      toast.error('Vui lòng điền đầy đủ thông tin bắt buộc!');
      return;
    }

    const allocations = unpaidInvoices
      .filter(inv => inv.selected && inv.allocatedAmount > 0)
      .map(inv => ({
        [inv.type === 'AP' ? 'ap_bill_id' : 'ar_invoice_id']: inv.id,
        allocated_amount: inv.allocatedAmount
      }));

    const payload = {
      transaction_date: formDate,
      amount: parseInt(formAmount),
      account_id: parseInt(formAccountId),
      payment_method: formMethod,
      reference_code: formReference || undefined,
      notes: formNotes || undefined,
      allocations
    };

    console.log('Payment payload before submit:', payload);

    // Call API to create payment
    createPaymentMutation.mutate(payload, {
      onSuccess: () => {
        toast.success('Tạo payment thành công!');
        
        // Refetch payments list to show new payment
        refetchPayments();
        
        // Reset form
        setFormDate('');
        setFormAmount('');
        setFormAccountId('');
        setFormMethod('');
        setFormReference('');
        setFormNotes('');
        setUnpaidInvoices(prev => prev.map(inv => ({ ...inv, selected: false, allocatedAmount: 0 })));
        setIsAddDialogOpen(false);
      },
      onError: (error: any) => {
        console.error('Payment creation error:', error);
        console.error('Error response:', error.response);
        console.error('Error data:', error.response?.data);
        
        // Extract error message properly
        let errorMessage = 'Unknown error';
        if (error.response?.data?.detail) {
          if (typeof error.response.data.detail === 'string') {
            errorMessage = error.response.data.detail;
          } else if (Array.isArray(error.response.data.detail)) {
            errorMessage = error.response.data.detail.map((e: any) => e.msg).join(', ');
          } else {
            errorMessage = JSON.stringify(error.response.data.detail);
          }
        } else if (error.message) {
          errorMessage = error.message;
        }
        
        toast.error(`Lỗi khi tạo payment: ${errorMessage}`);
      }
    });
  };

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
      <main className="p-8 max-w-[1600px] mx-auto">
        <div className="mb-6" style={{ lineHeight: 1.2 }}>
          <h2 className="text-slate-900 mb-1 font-alata" style={{ fontSize: '32px', fontWeight: 700 }}>Thanh toán</h2>
          <p className="text-slate-600 font-darker-grotesque" style={{ fontSize: '18px' }}>
            Quản lý thanh toán và đối soát giao dịch
          </p>
        </div>

        {/* Tabs */}
        <Tabs defaultValue="payments" className="space-y-6">
          <TabsList className="grid w-full grid-cols-2 h-auto p-1 bg-slate-100/80">
            <TabsTrigger 
              value="payments" 
              className="font-darker-grotesque data-[state=active]:bg-gradient-to-r data-[state=active]:from-emerald-500 data-[state=active]:to-emerald-600 data-[state=active]:text-white data-[state=active]:shadow-md transition-all"
              style={{ fontSize: '20px', padding: '14px' }}
            >
              <CreditCard className="size-5 mr-2" />
              Danh sách thanh toán
            </TabsTrigger>
            <TabsTrigger 
              value="reconcile" 
              className="font-darker-grotesque data-[state=active]:bg-gradient-to-r data-[state=active]:from-blue-500 data-[state=active]:to-blue-600 data-[state=active]:text-white data-[state=active]:shadow-md transition-all"
              style={{ fontSize: '20px', padding: '14px' }}
            >
              <CheckCircle className="size-5 mr-2" />
              Đối soát
            </TabsTrigger>
          </TabsList>

          {/* Payments Tab */}
          <TabsContent value="payments" className="space-y-6">
            {/* Filters and Actions */}
            <Card className="border-0 shadow-lg bg-white">
              <CardContent className="pt-6">
                <div className="flex flex-wrap items-center gap-4">
                  <div className="flex-1 max-w-md">
                    <Input
                      placeholder="Tìm kiếm theo tên, mã tham chiếu..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="font-darker-grotesque"
                      style={{ fontSize: '17px' }}
                    />
                  </div>
                  <Select value={selectedMethod} onValueChange={setSelectedMethod}>
                    <SelectTrigger className="w-[200px] font-darker-grotesque" style={{ fontSize: '17px' }}>
                      <SelectValue placeholder="Tất cả phương thức" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all" className="font-darker-grotesque" style={{ fontSize: '16px' }}>Tất cả</SelectItem>
                      <SelectItem value="transfer" className="font-darker-grotesque" style={{ fontSize: '16px' }}>Chuyển khoản</SelectItem>
                      <SelectItem value="vietqr" className="font-darker-grotesque" style={{ fontSize: '16px' }}>VietQR</SelectItem>
                      <SelectItem value="cash" className="font-darker-grotesque" style={{ fontSize: '16px' }}>Tiền mặt</SelectItem>
                      <SelectItem value="card" className="font-darker-grotesque" style={{ fontSize: '16px' }}>Thẻ</SelectItem>
                    </SelectContent>
                  </Select>
                  <div className="ml-auto flex gap-2">
                    <Button 
                      onClick={() => setIsQRDialogOpen(true)}
                      className="bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 font-darker-grotesque shadow-md"
                      style={{ fontSize: '17px' }}
                    >
                      <QrCode className="size-4 mr-2" />
                      Tạo VietQR
                    </Button>
                    <Button 
                      onClick={() => setIsAddDialogOpen(true)}
                      className="bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 font-darker-grotesque shadow-md"
                      style={{ fontSize: '17px' }}
                    >
                      <Plus className="size-4 mr-2" />
                      Thêm thanh toán
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Payments Table */}
            <Card className="border-0 shadow-lg bg-white">
              <CardHeader>
                <CardTitle className="text-slate-900 font-alata" style={{ fontSize: '24px', fontWeight: 400 }}>
                  Danh sách thanh toán
                </CardTitle>
                <CardDescription className="font-darker-grotesque" style={{ fontSize: '16px' }}>
                  {filteredPayments.length} giao dịch
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="border rounded-lg overflow-x-auto">
                  <table className="w-full table-auto">
                    <thead className="bg-gradient-to-r from-emerald-50 to-emerald-100/50">
                      <tr>
                        <th className="text-left px-3 py-3 font-darker-grotesque text-slate-900 border-b border-slate-200" style={{ fontSize: '16px', fontWeight: 500 }}>Ngày</th>
                        <th className="text-left px-3 py-3 font-darker-grotesque text-slate-900 border-b border-slate-200" style={{ fontSize: '16px', fontWeight: 500 }}>Tên tài khoản</th>
                        <th className="text-right px-3 py-3 font-darker-grotesque text-slate-900 border-b border-slate-200" style={{ fontSize: '16px', fontWeight: 500 }}>Số tiền</th>
                        <th className="text-center px-3 py-3 font-darker-grotesque text-slate-900 border-b border-slate-200" style={{ fontSize: '16px', fontWeight: 500 }}>Phương thức</th>
                        <th className="text-left px-3 py-3 font-darker-grotesque text-slate-900 border-b border-slate-200" style={{ fontSize: '16px', fontWeight: 500 }}>Mã tham chiếu</th>
                        <th className="text-center px-3 py-3 font-darker-grotesque text-slate-900 border-b border-slate-200" style={{ fontSize: '16px', fontWeight: 500 }}>Trạng thái</th>
                        <th className="text-center px-3 py-3 font-darker-grotesque text-slate-900 border-b border-slate-200" style={{ fontSize: '16px', fontWeight: 500 }}>Thao tác</th>
                      </tr>
                    </thead>
                    <tbody>
                      {paginatedPayments.map((payment, idx) => (
                        <tr key={payment.id} className={`border-b border-slate-100 hover:bg-emerald-50/30 transition-colors ${idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'}`}>
                          <td className="px-3 py-3 font-darker-grotesque text-slate-700 whitespace-nowrap" style={{ fontSize: '16px' }}>{payment.date}</td>
                          <td className="px-3 py-3 font-darker-grotesque text-slate-900" style={{ fontSize: '16px' }}>{payment.accountName}</td>
                          <td className="px-3 py-3 text-right font-darker-grotesque text-slate-900 whitespace-nowrap" style={{ fontSize: '16px', fontWeight: 500 }}>
                            {formatCurrency(payment.amount)}
                          </td>
                          <td className="px-3 py-3 text-center">{getMethodBadge(payment.method)}</td>
                          <td className="px-3 py-3 font-darker-grotesque text-slate-600" style={{ fontSize: '15px' }}>{payment.reference}</td>
                          <td className="px-3 py-3 text-center">{getStatusBadge(payment.status)}</td>
                          <td className="px-3 py-3">
                            <div className="flex gap-2 justify-center">
                              <Button 
                                size="sm" 
                                variant="ghost" 
                                className="h-8 w-8 p-0 hover:bg-emerald-100 hover:text-emerald-700"
                                onClick={() => handleViewDetail(payment)}
                                title="Xem chi tiết"
                              >
                                <Eye className="size-4" />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                
                {/* Pagination - emerald color for payments tab */}
                <div className="flex justify-center items-center gap-2 mt-6">
                  <Button
                    variant="outline"
                    size="icon"
                    className="h-10 w-10"
                    onClick={() => setCurrentPagePayments(Math.max(1, currentPagePayments - 1))}
                    disabled={currentPagePayments === 1}
                  >
                    <ChevronLeft className="size-4" />
                  </Button>
                  
                  {(() => {
                    const totalPages = Math.ceil(filteredPayments.length / itemsPerPage);
                    const pages = [];
                    
                    if (totalPages <= 7) {
                      for (let i = 1; i <= totalPages; i++) {
                        pages.push(i);
                      }
                    } else {
                      if (currentPagePayments <= 3) {
                        pages.push(1, 2, 3, 4, '...', totalPages);
                      } else if (currentPagePayments >= totalPages - 2) {
                        pages.push(1, '...', totalPages - 3, totalPages - 2, totalPages - 1, totalPages);
                      } else {
                        pages.push(1, '...', currentPagePayments - 1, currentPagePayments, currentPagePayments + 1, '...', totalPages);
                      }
                    }
                    
                    return pages.map((page, idx) => {
                      if (page === '...') {
                        return (
                          <span key={`ellipsis-${idx}`} className="px-2 text-slate-500 font-darker-grotesque" style={{ fontSize: '18px' }}>
                            ...
                          </span>
                        );
                      }
                      return (
                        <Button
                          key={page}
                          variant={currentPagePayments === page ? 'default' : 'outline'}
                          className={`h-10 w-10 font-darker-grotesque ${
                            currentPagePayments === page 
                              ? 'bg-gradient-to-r from-emerald-400 to-emerald-500 text-white shadow-md hover:from-emerald-500 hover:to-emerald-600' 
                              : 'hover:bg-slate-100'
                          }`}
                          style={{ fontSize: '17px', fontWeight: currentPagePayments === page ? 600 : 400 }}
                          onClick={() => setCurrentPagePayments(page as number)}
                        >
                          {page}
                        </Button>
                      );
                    });
                  })()}
                  
                  <Button
                    variant="outline"
                    size="icon"
                    className="h-10 w-10"
                    onClick={() => setCurrentPagePayments(Math.min(Math.ceil(filteredPayments.length / itemsPerPage), currentPagePayments + 1))}
                    disabled={currentPagePayments === Math.ceil(filteredPayments.length / itemsPerPage)}
                  >
                    <ChevronRight className="size-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Reconcile Tab */}
          <TabsContent value="reconcile" className="space-y-6">
            {/* Summary Cards - Moved to top */}
            <div className="grid grid-cols-3 gap-4">
              <Card className="border border-green-200 bg-gradient-to-br from-green-50 to-white shadow-md">
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-slate-600 font-darker-grotesque" style={{ fontSize: '16px' }}>Giao dịch khớp</p>
                      <p className="text-green-700 font-alata mt-1" style={{ fontSize: '32px', fontWeight: 600 }}>
                        {loadingReconciliation ? '...' : matchedCount}
                      </p>
                    </div>
                    <CheckCircle className="size-12 text-green-600" />
                  </div>
                </CardContent>
              </Card>
              <Card className="border border-red-200 bg-gradient-to-br from-red-50 to-white shadow-md">
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-slate-600 font-darker-grotesque" style={{ fontSize: '16px' }}>Giao dịch lệch</p>
                      <p className="text-red-700 font-alata mt-1" style={{ fontSize: '32px', fontWeight: 600 }}>
                        {loadingReconciliation ? '...' : mismatchCount}
                      </p>
                    </div>
                    <AlertTriangle className="size-12 text-red-600" />
                  </div>
                </CardContent>
              </Card>
              <Card className="border border-yellow-200 bg-gradient-to-br from-yellow-50 to-white shadow-md">
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-slate-600 font-darker-grotesque" style={{ fontSize: '16px' }}>Chưa ghép</p>
                      <p className="text-yellow-700 font-alata mt-1" style={{ fontSize: '32px', fontWeight: 600 }}>
                        {loadingReconciliation ? '...' : unmatchedCount}
                      </p>
                    </div>
                    <AlertTriangle className="size-12 text-yellow-600" />
                  </div>
                </CardContent>
              </Card>
            </div>

            <Card className="border-0 shadow-lg bg-white">
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="text-slate-900 font-alata" style={{ fontSize: '24px', fontWeight: 400 }}>
                    Đối soát giao dịch
                  </CardTitle>
                  <CardDescription className="font-darker-grotesque" style={{ fontSize: '16px' }}>
                    So sánh giao dịch giữa hệ thống POS và ngân hàng
                  </CardDescription>
                </div>
                <Button
                  onClick={() => {
                    autoMatchMutation.mutate(
                      { tolerance: 1000 },
                      {
                        onSuccess: (result) => {
                          if (result.total_matched > 0) {
                            toast.success(`Đã ghép tự động ${result.total_matched} giao dịch!`);
                          } else {
                            toast.info('Tất cả giao dịch đã được ghép.');
                          }
                          refetchReconciliation();
                          refetchPayments();
                        },
                        onError: (error: any) => {
                          toast.error('Lỗi: ' + (error?.response?.data?.detail || error?.message));
                        }
                      }
                    );
                  }}
                  disabled={autoMatchMutation.isPending}
                  className="bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 font-darker-grotesque"
                  style={{ fontSize: '16px' }}
                >
                  <CheckCircle className="size-4 mr-2" />
                  {autoMatchMutation.isPending ? 'Đang xử lý...' : 'Ghép tự động tất cả'}
                </Button>
              </CardHeader>
              <CardContent>
                <div className="border rounded-lg overflow-x-auto">
                  <table className="w-full table-auto">
                    <thead className="bg-gradient-to-r from-blue-50 to-blue-100/50">
                      <tr>
                        <th className="text-left px-3 py-3 font-darker-grotesque text-slate-900 border-b border-slate-200" style={{ fontSize: '16px', fontWeight: 500 }}>Ngày</th>
                        <th className="text-left px-3 py-3 font-darker-grotesque text-slate-900 border-b border-slate-200" style={{ fontSize: '16px', fontWeight: 500 }}>Mã tham chiếu</th>
                        <th className="text-right px-3 py-3 font-darker-grotesque text-slate-900 border-b border-slate-200" style={{ fontSize: '16px', fontWeight: 500 }}>Số tiền Bank</th>
                        <th className="text-right px-3 py-3 font-darker-grotesque text-slate-900 border-b border-slate-200" style={{ fontSize: '16px', fontWeight: 500 }}>Số tiền POS</th>
                        <th className="text-right px-3 py-3 font-darker-grotesque text-slate-900 border-b border-slate-200" style={{ fontSize: '16px', fontWeight: 500 }}>Chênh lệch</th>
                        <th className="text-center px-3 py-3 font-darker-grotesque text-slate-900 border-b border-slate-200" style={{ fontSize: '16px', fontWeight: 500 }}>Trạng thái</th>
                        <th className="text-center px-3 py-3 font-darker-grotesque text-slate-900 border-b border-slate-200" style={{ fontSize: '16px', fontWeight: 500 }}>Thao tác</th>
                      </tr>
                    </thead>
                    <tbody>
                      {paginatedReconcile.map((item, idx) => (
                        <tr key={item.id} className={`border-b border-slate-100 hover:bg-blue-50/30 transition-colors ${idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'}`}>
                          <td className="px-3 py-3 font-darker-grotesque text-slate-700 whitespace-nowrap" style={{ fontSize: '16px' }}>{item.date}</td>
                          <td className="px-3 py-3 font-darker-grotesque text-slate-600" style={{ fontSize: '15px' }}>{item.reference}</td>
                          <td className="px-3 py-3 text-right font-darker-grotesque text-slate-900 whitespace-nowrap" style={{ fontSize: '16px', fontWeight: 500 }}>
                            {item.bankAmount > 0 ? formatCurrency(item.bankAmount) : '-'}
                          </td>
                          <td className="px-3 py-3 text-right font-darker-grotesque text-slate-900 whitespace-nowrap" style={{ fontSize: '16px', fontWeight: 500 }}>
                            {item.posAmount > 0 ? formatCurrency(item.posAmount) : '-'}
                          </td>
                          <td className="px-3 py-3 text-right font-darker-grotesque whitespace-nowrap" style={{ fontSize: '16px', fontWeight: 500 }}>
                            <span className={item.difference === 0 ? 'text-green-600' : item.difference > 0 ? 'text-red-600' : 'text-orange-600'}>
                              {item.difference === 0 ? '0 ₫' : formatCurrency(Math.abs(item.difference))}
                            </span>
                          </td>
                          <td className="px-3 py-3"><div className="flex justify-center">{getReconcileStatus(item.status)}</div></td>
                          <td className="px-3 py-3">
                            {item.status === 'unmatched' && (
                              <div className="flex justify-center">
                                <Button 
                                  size="sm" 
                                  onClick={() => {
                                    setSelectedReconcile(item);
                                    setShowReconcileModal(true);
                                  }}
                                  className="bg-blue-600 hover:bg-blue-700 font-darker-grotesque px-3 py-1" 
                                  style={{ fontSize: '14px' }}
                                >
                                  Ghép tự động
                                </Button>
                              </div>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                
                {/* Pagination - blue color for reconcile tab */}
                <div className="flex justify-center items-center gap-2 mt-6">
                  <Button
                    variant="outline"
                    size="icon"
                    className="h-10 w-10"
                    onClick={() => setCurrentPageReconcile(Math.max(1, currentPageReconcile - 1))}
                    disabled={currentPageReconcile === 1}
                  >
                    <ChevronLeft className="size-4" />
                  </Button>
                  
                  {(() => {
                    const totalPages = Math.ceil(reconcileData.length / itemsPerPage);
                    const pages = [];
                    
                    if (totalPages <= 7) {
                      for (let i = 1; i <= totalPages; i++) {
                        pages.push(i);
                      }
                    } else {
                      if (currentPageReconcile <= 3) {
                        pages.push(1, 2, 3, 4, '...', totalPages);
                      } else if (currentPageReconcile >= totalPages - 2) {
                        pages.push(1, '...', totalPages - 3, totalPages - 2, totalPages - 1, totalPages);
                      } else {
                        pages.push(1, '...', currentPageReconcile - 1, currentPageReconcile, currentPageReconcile + 1, '...', totalPages);
                      }
                    }
                    
                    return pages.map((page, idx) => {
                      if (page === '...') {
                        return (
                          <span key={`ellipsis-${idx}`} className="px-2 text-slate-500 font-darker-grotesque" style={{ fontSize: '18px' }}>
                            ...
                          </span>
                        );
                      }
                      return (
                        <Button
                          key={page}
                          variant={currentPageReconcile === page ? 'default' : 'outline'}
                          className={`h-10 w-10 font-darker-grotesque ${
                            currentPageReconcile === page 
                              ? 'bg-gradient-to-r from-sky-400 to-sky-500 text-white shadow-md hover:from-sky-500 hover:to-sky-600' 
                              : 'hover:bg-slate-100'
                          }`}
                          style={{ fontSize: '17px', fontWeight: currentPageReconcile === page ? 600 : 400 }}
                          onClick={() => setCurrentPageReconcile(page as number)}
                        >
                          {page}
                        </Button>
                      );
                    });
                  })()}
                  
                  <Button
                    variant="outline"
                    size="icon"
                    className="h-10 w-10"
                    onClick={() => setCurrentPageReconcile(Math.min(Math.ceil(reconcileData.length / itemsPerPage), currentPageReconcile + 1))}
                    disabled={currentPageReconcile === Math.ceil(reconcileData.length / itemsPerPage)}
                  >
                    <ChevronRight className="size-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* QR Dialog - FIXED SIZE */}
        <Dialog open={isQRDialogOpen} onOpenChange={setIsQRDialogOpen}>
          <DialogContent className="sm:max-w-[500px] max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="font-alata" style={{ fontSize: '24px' }}>Tạo mã VietQR</DialogTitle>
              <DialogDescription className="font-darker-grotesque" style={{ fontSize: '16px' }}>
                Tạo mã QR để nhận thanh toán nhanh chóng
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="qr-amount" className="font-darker-grotesque" style={{ fontSize: '16px' }}>Số tiền</Label>
                <Input 
                  id="qr-amount" 
                  type="number"
                  placeholder="Nhập số tiền" 
                  value={qrAmount}
                  onChange={(e) => setQrAmount(e.target.value)}
                  className="font-darker-grotesque" 
                  style={{ fontSize: '16px' }} 
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="qr-description" className="font-darker-grotesque" style={{ fontSize: '16px' }}>Nội dung chuyển khoản</Label>
                <Input 
                  id="qr-description" 
                  placeholder="Nhập nội dung" 
                  value={qrDescription}
                  onChange={(e) => setQrDescription(e.target.value)}
                  className="font-darker-grotesque" 
                  style={{ fontSize: '16px' }} 
                />
              </div>
              <div className="border rounded-lg p-6 bg-slate-50 flex justify-center items-center min-h-[280px]">
                {qrUrl ? (
                  <img 
                    src={qrUrl} 
                    alt="VietQR Code" 
                    className="max-w-full h-auto"
                    style={{ maxHeight: '250px' }}
                  />
                ) : (
                  <div className="text-slate-400 font-darker-grotesque text-center" style={{ fontSize: '16px' }}>
                    <QrCode className="size-16 mx-auto mb-3 text-slate-300" />
                    <p>Nhập số tiền và nội dung để tạo QR</p>
                  </div>
                )}
              </div>
            </div>
            <DialogFooter>
              <Button 
                disabled={!qrUrl}
                className="bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 font-darker-grotesque disabled:opacity-50" 
                style={{ fontSize: '16px' }}
              >
                <Download className="size-4 mr-2" />
                Tải xuống
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Add Payment Dialog - COMPLETE FORM */}
        <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
          <DialogContent className="sm:max-w-[900px] max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="font-alata" style={{ fontSize: '24px' }}>Thêm thanh toán mới</DialogTitle>
              <DialogDescription className="font-darker-grotesque" style={{ fontSize: '16px' }}>
                Nhập thông tin giao dịch thanh toán và phân bổ vào hóa đơn
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-6 py-4">
              {/* PART A: Payment Information */}
              <div className="space-y-4">
                <h4 className="text-slate-700 font-darker-grotesque pb-2 border-b border-slate-200" style={{ fontSize: '17px', fontWeight: 600 }}>
                  I. Thông tin thanh toán
                </h4>
                
                <div className="grid grid-cols-2 gap-4">
                  {/* 1. Ngày giao dịch */}
                  <div className="space-y-2">
                    <Label htmlFor="add-date" className="font-darker-grotesque" style={{ fontSize: '16px' }}>
                      Ngày giao dịch <span className="text-red-500">*</span>
                    </Label>
                    <Input 
                      id="add-date" 
                      type="date" 
                      value={formDate}
                      onChange={(e) => setFormDate(e.target.value)}
                      className="font-darker-grotesque [&::-webkit-calendar-picker-indicator]:cursor-pointer pr-3"
                      style={{ fontSize: '16px' }} 
                    />
                  </div>
                  
                  {/* 2. Số tiền thanh toán */}
                  <div className="space-y-2">
                    <Label htmlFor="add-amount" className="font-darker-grotesque" style={{ fontSize: '16px' }}>
                      Số tiền thanh toán <span className="text-red-500">*</span>
                    </Label>
                    <Input 
                      id="add-amount" 
                      type="number"
                      placeholder="Nhập số tiền" 
                      value={formAmount}
                      onChange={(e) => setFormAmount(e.target.value)}
                      className="font-darker-grotesque" 
                      style={{ fontSize: '16px' }} 
                    />
                  </div>
                </div>

                {/* 3. Tài khoản thanh toán */}
                <div className="space-y-2">
                  <Label htmlFor="add-account" className="font-darker-grotesque" style={{ fontSize: '16px' }}>
                    Tài khoản thanh toán <span className="text-red-500">*</span>
                  </Label>
                  <Select value={formAccountId} onValueChange={setFormAccountId}>
                    <SelectTrigger id="add-account" className="font-darker-grotesque" style={{ fontSize: '16px' }}>
                      <SelectValue placeholder="Chọn tài khoản" />
                    </SelectTrigger>
                    <SelectContent>
                      {accounts.map(acc => (
                        <SelectItem key={acc.id} value={acc.id.toString()} className="font-darker-grotesque" style={{ fontSize: '16px' }}>
                          {acc.display}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  {/* 4. Phương thức */}
                  <div className="space-y-2">
                    <Label htmlFor="add-method" className="font-darker-grotesque" style={{ fontSize: '16px' }}>
                      Phương thức <span className="text-red-500">*</span>
                    </Label>
                    <Select value={formMethod} onValueChange={setFormMethod}>
                      <SelectTrigger id="add-method" className="font-darker-grotesque" style={{ fontSize: '16px' }}>
                        <SelectValue placeholder="Chọn phương thức" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="transfer" className="font-darker-grotesque">Chuyển khoản</SelectItem>
                        <SelectItem value="vietqr" className="font-darker-grotesque">VietQR</SelectItem>
                        <SelectItem value="cash" className="font-darker-grotesque">Tiền mặt</SelectItem>
                        <SelectItem value="card" className="font-darker-grotesque">Quẹt thẻ</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {/* 5. Mã tham chiếu */}
                  <div className="space-y-2">
                    <Label htmlFor="add-reference" className="font-darker-grotesque" style={{ fontSize: '16px' }}>Mã tham chiếu</Label>
                    <Input 
                      id="add-reference" 
                      placeholder="Nhập mã tham chiếu" 
                      value={formReference}
                      onChange={(e) => setFormReference(e.target.value)}
                      className="font-darker-grotesque" 
                      style={{ fontSize: '16px' }} 
                    />
                  </div>
                </div>

                {/* 6. Ghi chú */}
                <div className="space-y-2">
                  <Label htmlFor="add-memo" className="font-darker-grotesque" style={{ fontSize: '16px' }}>Ghi chú</Label>
                  <Textarea 
                    id="add-memo" 
                    placeholder="Nhập ghi chú" 
                    value={formNotes}
                    onChange={(e) => setFormNotes(e.target.value)}
                    className="font-darker-grotesque" 
                    style={{ fontSize: '16px' }} 
                    rows={3}
                  />
                </div>
              </div>

              {/* PART B: Allocations */}
              <div className="space-y-4">
                <h4 className="text-slate-700 font-darker-grotesque pb-2 border-b border-slate-200" style={{ fontSize: '17px', fontWeight: 600 }}>
                  II. Phân bổ thanh toán vào hóa đơn
                </h4>

                {/* Allocations Table */}
                <div className="border rounded-lg overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-blue-50">
                      <tr>
                        <th className="text-center p-3 font-darker-grotesque text-slate-900 border-b w-[60px]" style={{ fontSize: '15px', fontWeight: 600 }}>Chọn</th>
                        <th className="text-left p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '15px', fontWeight: 600 }}>Chứng từ</th>
                        <th className="text-left p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '15px', fontWeight: 600 }}>Mã</th>
                        <th className="text-left p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '15px', fontWeight: 600 }}>Khách/Nhà cung cấp</th>
                        <th className="text-center p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '15px', fontWeight: 600 }}>Ngày đến hạn</th>
                        <th className="text-right p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '15px', fontWeight: 600 }}>Còn nợ</th>
                        <th className="text-right p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '15px', fontWeight: 600 }}>Phân bổ</th>
                      </tr>
                    </thead>
                    <tbody>
                      {unpaidInvoices.map((inv, idx) => (
                        <tr key={inv.id} className={`border-b border-slate-100 ${idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'}`}>
                          <td className="p-3 text-center">
                            <input 
                              type="checkbox" 
                              checked={inv.selected}
                              onChange={() => toggleInvoiceSelection(inv.id)}
                              className="size-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                            />
                          </td>
                          <td className="p-3">
                            <Badge className={inv.type === 'AP' ? 'bg-purple-100 text-purple-700 border-purple-200 border' : 'bg-orange-100 text-orange-700 border-orange-200 border'} style={{ fontSize: '13px' }}>
                              {inv.type === 'AP' ? 'Hóa đơn phải trả' : 'Hóa đơn phải thu'}
                            </Badge>
                          </td>
                          <td className="p-3 font-darker-grotesque text-slate-900" style={{ fontSize: '15px', fontWeight: 500 }}>{inv.code}</td>
                          <td className="p-3 font-darker-grotesque text-slate-700" style={{ fontSize: '15px' }}>{inv.customerSupplier}</td>
                          <td className="p-3 text-center font-darker-grotesque text-slate-700" style={{ fontSize: '15px' }}>{inv.dueDate}</td>
                          <td className="p-3 text-right font-darker-grotesque text-slate-900" style={{ fontSize: '15px', fontWeight: 500 }}>
                            {formatCurrency(inv.remaining)}
                          </td>
                          <td className="p-3">
                            <Input
                              type="number"
                              disabled={!inv.selected}
                              value={inv.allocatedAmount || ''}
                              onChange={(e) => updateAllocatedAmount(inv.id, parseInt(e.target.value) || 0)}
                              className="text-right font-darker-grotesque disabled:bg-slate-100 disabled:text-slate-400"
                              style={{ fontSize: '15px' }}
                              placeholder="0"
                            />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Summary */}
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                  <div className="flex justify-between items-center">
                    <span className="text-slate-700 font-darker-grotesque" style={{ fontSize: '16px', fontWeight: 500 }}>
                      Tổng phân bổ:
                    </span>
                    <span className={`font-darker-grotesque ${totalAllocated > parseInt(formAmount || '0') ? 'text-red-600' : 'text-emerald-600'}`} style={{ fontSize: '17px', fontWeight: 600 }}>
                      {formatCurrency(totalAllocated)} / {formatCurrency(parseInt(formAmount || '0'))}
                    </span>
                  </div>
                  {totalAllocated > parseInt(formAmount || '0') && (
                    <p className="text-red-600 font-darker-grotesque mt-2" style={{ fontSize: '14px' }}>
                      ⚠️ Tổng phân bổ vượt quá số tiền thanh toán!
                    </p>
                  )}
                </div>
              </div>
            </div>
            
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsAddDialogOpen(false)} className="font-darker-grotesque" style={{ fontSize: '16px' }}>
                Hủy
              </Button>
              <Button 
                onClick={handleSubmitPayment}
                disabled={!formDate || !formAmount || !formAccountId || !formMethod || totalAllocated > parseInt(formAmount || '0')}
                className="bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 font-darker-grotesque disabled:opacity-50" 
                style={{ fontSize: '16px' }}
              >
                <CheckCircle className="size-4 mr-2" />
                Thêm giao dịch
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Detail Modal - View Payment */}
        {showDetailModal && selectedPayment && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <div className="bg-white rounded-lg shadow-2xl w-full max-w-5xl max-h-[90vh] overflow-y-auto mx-4">
              <div className="overflow-hidden">
                {/* Green Header - Sticky */}
                <div className="bg-gradient-to-r from-emerald-500 to-emerald-600 p-6 flex items-center justify-between sticky top-0 z-10">
                  <h3 className="text-white font-alata" style={{ fontSize: '28px', fontWeight: 400 }}>
                    Chi tiết thanh toán
                  </h3>
                  <Button variant="ghost" size="icon" onClick={() => setShowDetailModal(false)} className="text-white hover:bg-white/20">
                    <X className="size-6" />
                  </Button>
                </div>

                {/* White Content Area */}
                <div className="p-8 bg-white">
                  {/* 1. Thông tin thanh toán */}
                  <div className="mb-6">
                    <h4 className="text-slate-700 font-darker-grotesque mb-4 pb-2 border-b border-slate-200" style={{ fontSize: '18px', fontWeight: 600 }}>
                      Thông tin thanh toán
                    </h4>
                    <div className="grid grid-cols-2 gap-6">
                      <div>
                        <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '15px' }}>Mã thanh toán</p>
                        <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '17px', fontWeight: 600 }}>{selectedPayment.code}</p>
                      </div>
                      <div>
                        <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '15px' }}>Tài khoản</p>
                        <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '17px', fontWeight: 600 }}>
                          {selectedPayment.bankName} – {selectedPayment.accountNumber} – {selectedPayment.accountName}
                        </p>
                      </div>
                      <div>
                        <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '15px' }}>Ngày giao dịch</p>
                        <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '17px', fontWeight: 600 }}>{selectedPayment.date}</p>
                      </div>
                      <div>
                        <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '15px' }}>Số tiền thanh toán</p>
                        <p className="text-emerald-600 font-darker-grotesque" style={{ fontSize: '17px', fontWeight: 600 }}>{formatCurrency(selectedPayment.amount)}</p>
                      </div>
                      <div>
                        <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '15px' }}>Phương thức</p>
                        <div className="mt-1">{getMethodBadge(selectedPayment.method)}</div>
                      </div>
                      <div>
                        <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '15px' }}>Mã tham chiếu</p>
                        <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '17px', fontWeight: 600 }}>{selectedPayment.reference}</p>
                      </div>
                      <div className="col-span-2">
                        <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '15px' }}>Ghi chú</p>
                        <p className="text-slate-700 font-darker-grotesque bg-slate-50 p-3 rounded-lg border border-slate-200" style={{ fontSize: '16px' }}>
                          {selectedPayment.memo}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* 2. Danh sách phân bổ */}
                  <div className="mb-6">
                    <h4 className="text-slate-700 font-darker-grotesque mb-4 pb-2 border-b border-slate-200 flex items-center gap-2" style={{ fontSize: '18px', fontWeight: 600 }}>
                      <DollarSign className="size-5 text-emerald-600" />
                      Danh sách phân bổ
                    </h4>
                    <div className="border rounded-lg overflow-hidden">
                      <table className="w-full">
                        <thead className="bg-emerald-50">
                          <tr>
                            <th className="text-left p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '15px', fontWeight: 600 }}>Chứng từ</th>
                            <th className="text-left p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '15px', fontWeight: 600 }}>Mã</th>
                            <th className="text-center p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '15px', fontWeight: 600 }}>Ngày đến hạn</th>
                            <th className="text-right p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '15px', fontWeight: 600 }}>Tổng tiền</th>
                            <th className="text-right p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '15px', fontWeight: 600 }}>Đã thu/chi</th>
                            <th className="text-right p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '15px', fontWeight: 600 }}>Đã phân bổ</th>
                            <th className="text-right p-3 font-darker-grotesque text-slate-900 border-b" style={{ fontSize: '15px', fontWeight: 600 }}>Còn nợ</th>
                          </tr>
                        </thead>
                        <tbody>
                          {selectedPayment.allocations.length > 0 ? (
                            selectedPayment.allocations.map((allocation, idx) => (
                              <tr key={idx} className="bg-white border-b border-slate-100">
                                <td className="p-3 font-darker-grotesque text-slate-700" style={{ fontSize: '15px' }}>
                                  <Badge className={allocation.type === 'AP' ? 'bg-purple-100 text-purple-700 border-purple-200 border' : 'bg-orange-100 text-orange-700 border-orange-200 border'} style={{ fontSize: '13px' }}>
                                    {allocation.type === 'AP' ? 'Hóa đơn phải trả' : 'Hóa đơn phải thu'}
                                  </Badge>
                                </td>
                                <td className="p-3 font-darker-grotesque text-slate-900" style={{ fontSize: '15px', fontWeight: 500 }}>{allocation.code}</td>
                                <td className="p-3 text-center font-darker-grotesque text-slate-700" style={{ fontSize: '15px' }}>{allocation.dueDate}</td>
                                <td className="p-3 text-right font-darker-grotesque text-slate-900" style={{ fontSize: '15px', fontWeight: 500 }}>
                                  {formatCurrency(allocation.totalAmount)}
                                </td>
                                <td className="p-3 text-right font-darker-grotesque text-blue-600" style={{ fontSize: '15px', fontWeight: 500 }}>
                                  {formatCurrency(allocation.paidAmount)}
                                </td>
                                <td className="p-3 text-right font-darker-grotesque text-emerald-600" style={{ fontSize: '15px', fontWeight: 600 }}>
                                  {formatCurrency(allocation.allocated)}
                                </td>
                                <td className="p-3 text-right font-darker-grotesque text-orange-600" style={{ fontSize: '15px', fontWeight: 500 }}>
                                  {formatCurrency(allocation.remaining)}
                                </td>
                              </tr>
                            ))
                          ) : (
                            <tr>
                              <td colSpan={7} className="p-6 text-center">
                                <p className="text-slate-400 font-darker-grotesque" style={{ fontSize: '15px' }}>Chưa có phân bổ nào</p>
                              </td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* 3. Thông tin hệ thống */}
                  <div className="mb-6">
                    <h4 className="text-slate-700 font-darker-grotesque mb-4 pb-2 border-b border-slate-200" style={{ fontSize: '18px', fontWeight: 600 }}>
                      Thông tin hệ thống
                    </h4>
                    <div className="grid grid-cols-2 gap-6 bg-slate-50 p-4 rounded-lg border border-slate-200">
                      <div>
                        <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '14px' }}>Tạo lúc</p>
                        <p className="text-slate-700 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>
                          {selectedPayment.createdAt}
                        </p>
                      </div>
                      <div>
                        <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '14px' }}>Cập nhật lúc</p>
                        <p className="text-slate-700 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>
                          {selectedPayment.updatedAt}
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
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Reconcile Auto-Match Modal */}
        {showReconcileModal && selectedReconcile && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <div className="bg-white rounded-lg shadow-2xl w-full max-w-2xl mx-4">
              <div className="overflow-hidden rounded-lg">
                {/* Blue Header */}
                <div className="bg-gradient-to-r from-blue-500 to-blue-600 p-6 flex items-center justify-between rounded-t-lg">
                  <h3 className="text-white font-alata" style={{ fontSize: '24px', fontWeight: 400 }}>
                    Ghép tự động
                  </h3>
                  <Button variant="ghost" size="icon" onClick={() => setShowReconcileModal(false)} className="text-white hover:bg-white/20">
                    <X className="size-5" />
                  </Button>
                </div>

                {/* Content */}
                <div className="p-6 bg-white space-y-6 max-h-[70vh] overflow-y-auto">
                  {/* 1. Thông tin POS */}
                  <div>
                    <h4 className="text-slate-700 font-darker-grotesque mb-3 pb-2 border-b border-slate-200 flex items-center gap-2" style={{ fontSize: '17px', fontWeight: 600 }}>
                      <CreditCard className="size-4 text-blue-600" />
                      Thông tin POS
                    </h4>
                    <div className="grid grid-cols-2 gap-4 bg-blue-50 p-4 rounded-lg border border-blue-100">
                      <div>
                        <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '14px' }}>Số tiền POS</p>
                        <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '16px', fontWeight: 600 }}>
                          {selectedReconcile.posAmount > 0 ? formatCurrency(selectedReconcile.posAmount) : '0 ₫'}
                        </p>
                      </div>
                      <div>
                        <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '14px' }}>Ngày giao dịch</p>
                        <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '16px', fontWeight: 600 }}>
                          {selectedReconcile.date}
                        </p>
                      </div>
                      <div className="col-span-2">
                        <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '14px' }}>Mã tham chiếu</p>
                        <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '16px', fontWeight: 600 }}>
                          {selectedReconcile.reference}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* 2. Thông tin Bank (giả lập) */}
                  <div>
                    <h4 className="text-slate-700 font-darker-grotesque mb-3 pb-2 border-b border-slate-200 flex items-center gap-2" style={{ fontSize: '17px', fontWeight: 600 }}>
                      <DollarSign className="size-4 text-green-600" />
                      Thông tin Bank (Giả lập)
                    </h4>
                    <div className="grid grid-cols-2 gap-4 bg-green-50 p-4 rounded-lg border border-green-100">
                      <div>
                        <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '14px' }}>Số tiền Bank</p>
                        <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '16px', fontWeight: 600 }}>
                          {selectedReconcile.bankAmount > 0 ? formatCurrency(selectedReconcile.bankAmount) : formatCurrency(selectedReconcile.posAmount)}
                        </p>
                      </div>
                      <div>
                        <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '14px' }}>Ngày Bank</p>
                        <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '16px', fontWeight: 600 }}>
                          {selectedReconcile.date}
                        </p>
                      </div>
                      <div className="col-span-2">
                        <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '14px' }}>Ghi chú</p>
                        <p className="text-amber-700 font-darker-grotesque italic bg-amber-50 p-2 rounded border border-amber-200" style={{ fontSize: '14px' }}>
                          ⚠️ Dữ liệu ngân hàng mô phỏng phục vụ demo
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* 3. Kết quả đối soát */}
                  <div>
                    <h4 className="text-slate-700 font-darker-grotesque mb-3 pb-2 border-b border-slate-200 flex items-center gap-2" style={{ fontSize: '17px', fontWeight: 600 }}>
                      <CheckCircle className="size-4 text-blue-600" />
                      Kết quả đối soát
                    </h4>
                    <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '14px' }}>Trạng thái</p>
                          <div className="mt-1">
                            {(() => {
                              const posAmt = selectedReconcile.posAmount || 0;
                              const bankAmt = selectedReconcile.bankAmount || posAmt;
                              const diff = Math.abs(bankAmt - posAmt);
                              const isMatched = diff === 0;
                              
                              return isMatched ? (
                                <Badge className="bg-green-100 text-green-700 border-green-200 border font-darker-grotesque" style={{ fontSize: '15px' }}>
                                  <CheckCircle className="size-3.5 mr-1" />
                                  Khớp
                                </Badge>
                              ) : (
                                <Badge className="bg-red-100 text-red-700 border-red-200 border font-darker-grotesque" style={{ fontSize: '15px' }}>
                                  <AlertTriangle className="size-3.5 mr-1" />
                                  Lệch
                                </Badge>
                              );
                            })()}
                          </div>
                        </div>
                        <div>
                          <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '14px' }}>Số tiền chênh lệch</p>
                          <p className={`font-darker-grotesque ${(() => {
                            const posAmt = selectedReconcile.posAmount || 0;
                            const bankAmt = selectedReconcile.bankAmount || posAmt;
                            const diff = Math.abs(bankAmt - posAmt);
                            return diff === 0 ? 'text-green-600' : 'text-red-600';
                          })()}`} style={{ fontSize: '17px', fontWeight: 600 }}>
                            {(() => {
                              const posAmt = selectedReconcile.posAmount || 0;
                              const bankAmt = selectedReconcile.bankAmount || posAmt;
                              const diff = Math.abs(bankAmt - posAmt);
                              return diff === 0 ? '0 ₫' : formatCurrency(diff);
                            })()}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
                    <Button
                      variant="outline"
                      onClick={() => setShowReconcileModal(false)}
                      className="font-darker-grotesque"
                      style={{ fontSize: '16px' }}
                    >
                      Hủy
                    </Button>
                    <Button
                      onClick={() => {
                        // Auto-match all unmatched transactions
                        // Don't filter by specific date - let backend handle matching logic
                        console.log('🔄 Auto-match for transaction:', selectedReconcile);
                        
                        // Call auto-match API without date filter to match all available transactions
                        autoMatchMutation.mutate(
                          { tolerance: 1000 },
                          {
                            onSuccess: (result) => {
                              console.log('✅ Auto-match result:', result);
                              if (result.total_matched > 0) {
                                toast.success(`Đã ghép tự động ${result.total_matched} giao dịch thành công!`);
                              } else {
                                toast.info('Không có giao dịch mới cần ghép.');
                              }
                              refetchReconciliation();
                              refetchPayments();
                              setShowReconcileModal(false);
                            },
                            onError: (error: any) => {
                              console.error('❌ Auto-match error:', error);
                              const errorMsg = error?.response?.data?.detail || error?.message || 'Lỗi không xác định';
                              toast.error('Lỗi ghép tự động: ' + errorMsg);
                            }
                          }
                        );
                      }}
                      disabled={autoMatchMutation.isPending}
                      className="bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 font-darker-grotesque"
                      style={{ fontSize: '16px' }}
                    >
                      <CheckCircle className="size-4 mr-2" />
                      {autoMatchMutation.isPending ? 'Đang xử lý...' : 'Xác nhận ghép tự động'}
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
