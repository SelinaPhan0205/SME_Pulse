/**
 * MSW Mock Handlers
 * Mock tất cả API endpoints cho development
 */

import { http, HttpResponse, delay } from 'msw';

const BASE_URL = 'http://localhost:8000';

// Helper: generate mock data
const generateMockUsers = (count = 10) => {
  const roles = ['owner', 'admin', 'accountant', 'cashier'];
  return Array.from({ length: count }, (_, i) => ({
    id: i + 1,
    email: `user${i + 1}@company.com`,
    full_name: `User ${i + 1}`,
    status: i < 8 ? 'active' : 'inactive',
    org_id: 1,
    roles: [roles[i % roles.length]],
    created_at: new Date(2024, 0, i + 1).toISOString(),
    updated_at: new Date(2024, 0, i + 1).toISOString(),
  }));
};

const generateMockCustomers = (count = 20) => {
  return Array.from({ length: count }, (_, i) => ({
    id: i + 1,
    code: `CUS${String(i + 1).padStart(3, '0')}`,
    name: `Customer ${i + 1}`,
    tax_code: `TAX${i + 1}`,
    email: `customer${i + 1}@example.com`,
    phone: `090${String(i + 1).padStart(7, '0')}`,
    address: `Address ${i + 1}`,
    credit_term: 30,
    is_active: true,
    org_id: 1,
    created_at: new Date(2024, 0, i + 1).toISOString(),
    updated_at: new Date(2024, 0, i + 1).toISOString(),
  }));
};

const generateMockSuppliers = (count = 15) => {
  return Array.from({ length: count }, (_, i) => ({
    id: i + 1,
    code: `SUP${String(i + 1).padStart(3, '0')}`,
    name: `Supplier ${i + 1}`,
    tax_code: `TAX${i + 1}`,
    email: `supplier${i + 1}@example.com`,
    phone: `091${String(i + 1).padStart(7, '0')}`,
    address: `Address ${i + 1}`,
    payment_term: 30,
    is_active: true,
    org_id: 1,
    created_at: new Date(2024, 0, i + 1).toISOString(),
    updated_at: new Date(2024, 0, i + 1).toISOString(),
  }));
};

const generateMockAccounts = () => [
  { id: 1, name: 'Tiền mặt', type: 'cash', account_number: null, bank_name: null, is_active: true, org_id: 1, created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
  { id: 2, name: 'TK Vietcombank', type: 'bank', account_number: '1234567890', bank_name: 'Vietcombank', is_active: true, org_id: 1, created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
  { id: 3, name: 'TK Techcombank', type: 'bank', account_number: '9876543210', bank_name: 'Techcombank', is_active: true, org_id: 1, created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
];

const generateMockInvoices = (count = 30) => {
  const statuses = ['draft', 'posted', 'paid', 'overdue'];
  const customers = generateMockCustomers(20);
  
  return Array.from({ length: count }, (_, i) => {
    const issueDate = new Date(2024, 10, i + 1);
    const dueDate = new Date(issueDate);
    dueDate.setDate(dueDate.getDate() + 30);
    const totalAmount = (i + 1) * 1000000;
    const paidAmount = i % 4 === 2 ? totalAmount : (i % 4 === 1 ? totalAmount / 2 : 0);
    const status = statuses[i % 4];
    const customer = customers[i % customers.length];

    return {
      id: i + 1,
      invoice_no: `INV${new Date().getFullYear()}${String(i + 1).padStart(4, '0')}`,
      customer_id: customer.id,
      customer,
      issue_date: issueDate.toISOString().split('T')[0],
      due_date: dueDate.toISOString().split('T')[0],
      total_amount: totalAmount,
      paid_amount: paidAmount,
      remaining_amount: totalAmount - paidAmount,
      status,
      aging_days: status === 'overdue' ? Math.floor(Math.random() * 60) + 1 : 0,
      risk_level: status === 'overdue' ? 'high' : (i % 3 === 0 ? 'normal' : 'low'),
      notes: i % 3 === 0 ? `Note for invoice ${i + 1}` : null,
      org_id: 1,
      created_at: issueDate.toISOString(),
      updated_at: issueDate.toISOString(),
    };
  });
};

const generateMockBills = (count = 25) => {
  const statuses = ['draft', 'posted', 'paid', 'overdue'];
  const suppliers = generateMockSuppliers(15);
  
  return Array.from({ length: count }, (_, i) => {
    const issueDate = new Date(2024, 10, i + 1);
    const dueDate = new Date(issueDate);
    dueDate.setDate(dueDate.getDate() + 30);
    const totalAmount = (i + 1) * 800000;
    const paidAmount = i % 4 === 2 ? totalAmount : (i % 4 === 1 ? totalAmount / 2 : 0);
    const supplier = suppliers[i % suppliers.length];

    return {
      id: i + 1,
      bill_no: `BILL${new Date().getFullYear()}${String(i + 1).padStart(4, '0')}`,
      supplier_id: supplier.id,
      supplier,
      issue_date: issueDate.toISOString().split('T')[0],
      due_date: dueDate.toISOString().split('T')[0],
      total_amount: totalAmount,
      paid_amount: paidAmount,
      remaining_amount: totalAmount - paidAmount,
      status: statuses[i % 4],
      aging_days: i % 4 === 3 ? Math.floor(Math.random() * 50) + 1 : 0,
      notes: i % 3 === 0 ? `Note for bill ${i + 1}` : null,
      org_id: 1,
      created_at: issueDate.toISOString(),
      updated_at: issueDate.toISOString(),
    };
  });
};

const generateMockPayments = (count = 20) => {
  const accounts = generateMockAccounts();
  const invoices = generateMockInvoices(30);
  
  return Array.from({ length: count }, (_, i) => ({
    id: i + 1,
    account_id: accounts[i % accounts.length].id,
    account: accounts[i % accounts.length],
    transaction_date: new Date(2024, 10, i + 1).toISOString().split('T')[0],
    amount: (i + 1) * 500000,
    payment_method: ['cash', 'transfer', 'vietqr'][i % 3],
    reference_code: i % 2 === 0 ? `REF${i + 1}` : null,
    notes: i % 3 === 0 ? `Payment note ${i + 1}` : null,
    allocations: [
      {
        id: i * 10 + 1,
        payment_id: i + 1,
        ar_invoice_id: invoices[i % invoices.length].id,
        ap_bill_id: null,
        allocated_amount: (i + 1) * 500000,
        notes: null,
        ar_invoice: invoices[i % invoices.length],
      },
    ],
    org_id: 1,
    created_at: new Date(2024, 10, i + 1).toISOString(),
    updated_at: new Date(2024, 10, i + 1).toISOString(),
  }));
};

// Store data in memory
let mockData = {
  users: generateMockUsers(),
  customers: generateMockCustomers(),
  suppliers: generateMockSuppliers(),
  accounts: generateMockAccounts(),
  invoices: generateMockInvoices(),
  bills: generateMockBills(),
  payments: generateMockPayments(),
  exportJobs: [],
  alerts: [],
};

export const handlers = [
  // ==================== AUTH ====================
  http.post(`${BASE_URL}/auth/login`, async () => {
    await delay(500);
    return HttpResponse.json({
      access_token: 'mock_token_12345',
      token_type: 'bearer',
      expires_in: 3600,
      user: mockData.users[0],
      roles: ['owner'],
    });
  }),

  http.get(`${BASE_URL}/auth/me`, async () => {
    await delay(300);
    return HttpResponse.json(mockData.users[0]);
  }),

  http.post(`${BASE_URL}/api/v1/auth/change-password`, async () => {
    await delay(500);
    return HttpResponse.json({ message: 'Password changed successfully' });
  }),

  // ==================== USERS ====================
  http.get(`${BASE_URL}/api/v1/users`, async ({ request }) => {
    await delay(400);
    const url = new URL(request.url);
    const skip = parseInt(url.searchParams.get('skip') || '0');
    const limit = parseInt(url.searchParams.get('limit') || '10');
    const search = url.searchParams.get('search') || '';
    
    let filtered = mockData.users;
    if (search) {
      filtered = filtered.filter(u => 
        u.full_name.toLowerCase().includes(search.toLowerCase()) ||
        u.email.toLowerCase().includes(search.toLowerCase())
      );
    }
    
    return HttpResponse.json({
      total: filtered.length,
      skip,
      limit,
      items: filtered.slice(skip, skip + limit),
    });
  }),

  http.get(`${BASE_URL}/api/v1/users/:id`, async ({ params }) => {
    await delay(300);
    const user = mockData.users.find(u => u.id === parseInt(params.id as string));
    return user ? HttpResponse.json(user) : new HttpResponse(null, { status: 404 });
  }),

  http.post(`${BASE_URL}/api/v1/users`, async ({ request }) => {
    await delay(500);
    const body = await request.json();
    const newUser = {
      id: mockData.users.length + 1,
      ...body,
      org_id: 1,
      roles: [body.role],
      status: 'active',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    mockData.users.push(newUser);
    return HttpResponse.json(newUser, { status: 201 });
  }),

  http.put(`${BASE_URL}/api/v1/users/:id`, async ({ params, request }) => {
    await delay(500);
    const body = await request.json();
    const index = mockData.users.findIndex(u => u.id === parseInt(params.id as string));
    if (index !== -1) {
      mockData.users[index] = { ...mockData.users[index], ...body, updated_at: new Date().toISOString() };
      return HttpResponse.json(mockData.users[index]);
    }
    return new HttpResponse(null, { status: 404 });
  }),

  http.delete(`${BASE_URL}/api/v1/users/:id`, async ({ params }) => {
    await delay(500);
    mockData.users = mockData.users.filter(u => u.id !== parseInt(params.id as string));
    return new HttpResponse(null, { status: 204 });
  }),

  // ==================== CUSTOMERS ====================
  http.get(`${BASE_URL}/api/v1/customers`, async ({ request }) => {
    await delay(400);
    const url = new URL(request.url);
    const skip = parseInt(url.searchParams.get('skip') || '0');
    const limit = parseInt(url.searchParams.get('limit') || '10');
    
    return HttpResponse.json({
      total: mockData.customers.length,
      skip,
      limit,
      items: mockData.customers.slice(skip, skip + limit),
    });
  }),

  http.get(`${BASE_URL}/api/v1/customers/:id`, async ({ params }) => {
    await delay(300);
    const customer = mockData.customers.find(c => c.id === parseInt(params.id as string));
    return customer ? HttpResponse.json(customer) : new HttpResponse(null, { status: 404 });
  }),

  http.post(`${BASE_URL}/api/v1/customers`, async ({ request }) => {
    await delay(500);
    const body = await request.json();
    const newCustomer = {
      id: mockData.customers.length + 1,
      ...body,
      org_id: 1,
      is_active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    mockData.customers.push(newCustomer);
    return HttpResponse.json(newCustomer, { status: 201 });
  }),

  // ==================== SUPPLIERS ====================
  http.get(`${BASE_URL}/api/v1/suppliers`, async ({ request }) => {
    await delay(400);
    const url = new URL(request.url);
    const skip = parseInt(url.searchParams.get('skip') || '0');
    const limit = parseInt(url.searchParams.get('limit') || '10');
    
    return HttpResponse.json({
      total: mockData.suppliers.length,
      skip,
      limit,
      items: mockData.suppliers.slice(skip, skip + limit),
    });
  }),

  // ==================== ACCOUNTS ====================
  http.get(`${BASE_URL}/api/v1/accounts`, async () => {
    await delay(300);
    return HttpResponse.json({
      total: mockData.accounts.length,
      skip: 0,
      limit: 10,
      items: mockData.accounts,
    });
  }),

  // ==================== INVOICES ====================
  http.get(`${BASE_URL}/api/v1/invoices`, async ({ request }) => {
    await delay(500);
    const url = new URL(request.url);
    const skip = parseInt(url.searchParams.get('skip') || '0');
    const limit = parseInt(url.searchParams.get('limit') || '10');
    const status = url.searchParams.get('status');
    
    let filtered = mockData.invoices;
    if (status) {
      filtered = filtered.filter(inv => inv.status === status);
    }
    
    return HttpResponse.json({
      total: filtered.length,
      skip,
      limit,
      items: filtered.slice(skip, skip + limit),
    });
  }),

  http.get(`${BASE_URL}/api/v1/invoices/:id`, async ({ params }) => {
    await delay(300);
    const invoice = mockData.invoices.find(i => i.id === parseInt(params.id as string));
    return invoice ? HttpResponse.json(invoice) : new HttpResponse(null, { status: 404 });
  }),

  http.post(`${BASE_URL}/api/v1/invoices`, async ({ request }) => {
    await delay(500);
    const body = await request.json();
    const customer = mockData.customers.find(c => c.id === body.customer_id);
    const newInvoice = {
      id: mockData.invoices.length + 1,
      ...body,
      customer,
      paid_amount: 0,
      remaining_amount: body.total_amount,
      status: 'draft',
      aging_days: 0,
      org_id: 1,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    mockData.invoices.push(newInvoice);
    return HttpResponse.json(newInvoice, { status: 201 });
  }),

  http.post(`${BASE_URL}/api/v1/invoices/:id/post`, async ({ params }) => {
    await delay(500);
    const index = mockData.invoices.findIndex(i => i.id === parseInt(params.id as string));
    if (index !== -1) {
      mockData.invoices[index].status = 'posted';
      return HttpResponse.json(mockData.invoices[index]);
    }
    return new HttpResponse(null, { status: 404 });
  }),

  // ==================== BILLS ====================
  http.get(`${BASE_URL}/api/v1/bills`, async ({ request }) => {
    await delay(500);
    const url = new URL(request.url);
    const skip = parseInt(url.searchParams.get('skip') || '0');
    const limit = parseInt(url.searchParams.get('limit') || '10');
    
    return HttpResponse.json({
      total: mockData.bills.length,
      skip,
      limit,
      items: mockData.bills.slice(skip, skip + limit),
    });
  }),

  // ==================== PAYMENTS ====================
  http.get(`${BASE_URL}/api/v1/payments`, async ({ request }) => {
    await delay(500);
    const url = new URL(request.url);
    const skip = parseInt(url.searchParams.get('skip') || '0');
    const limit = parseInt(url.searchParams.get('limit') || '10');
    
    return HttpResponse.json({
      total: mockData.payments.length,
      skip,
      limit,
      items: mockData.payments.slice(skip, skip + limit),
    });
  }),

  http.post(`${BASE_URL}/api/v1/payments`, async ({ request }) => {
    await delay(500);
    const body = await request.json();
    const account = mockData.accounts.find(a => a.id === body.account_id);
    const newPayment = {
      id: mockData.payments.length + 1,
      ...body,
      account,
      org_id: 1,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    mockData.payments.push(newPayment);
    return HttpResponse.json(newPayment, { status: 201 });
  }),

  // ==================== ANALYTICS ====================
  http.get(`${BASE_URL}/api/v1/analytics/summary`, async () => {
    await delay(400);
    return HttpResponse.json({
      total_revenue: 150000000,
      total_receivables: 85000000,
      total_payables: 45000000,
      payment_success_rate: 0.87,
      overdue_invoices_count: 8,
      pending_payments_count: 12,
    });
  }),

  http.get(`${BASE_URL}/api/v1/analytics/ar-aging`, async () => {
    await delay(400);
    return HttpResponse.json({
      total_ar: 85000000,
      buckets: [
        { bucket: '0-30', amount: 45000000, count: 25 },
        { bucket: '31-60', amount: 20000000, count: 12 },
        { bucket: '61-90', amount: 12000000, count: 8 },
        { bucket: '90+', amount: 8000000, count: 5 },
      ],
    });
  }),

  http.get(`${BASE_URL}/api/v1/analytics/ap-aging`, async () => {
    await delay(400);
    return HttpResponse.json({
      total_ap: 45000000,
      buckets: [
        { bucket: '0-30', amount: 25000000, count: 15 },
        { bucket: '31-60', amount: 12000000, count: 8 },
        { bucket: '61-90', amount: 5000000, count: 4 },
        { bucket: '90+', amount: 3000000, count: 2 },
      ],
    });
  }),

  http.get(`${BASE_URL}/api/v1/analytics/daily-revenue`, async () => {
    await delay(400);
    const data = Array.from({ length: 30 }, (_, i) => ({
      date: new Date(2024, 10, i + 1).toISOString().split('T')[0],
      revenue: Math.floor(Math.random() * 10000000) + 5000000,
    }));
    return HttpResponse.json({ data });
  }),

  http.get(`${BASE_URL}/api/v1/analytics/payment-success-rate`, async () => {
    await delay(400);
    return HttpResponse.json({
      success_rate: 0.87,
      total_payments: 150,
      successful_payments: 130,
    });
  }),

  http.get(`${BASE_URL}/api/v1/analytics/kpi/reconciliation`, async () => {
    await delay(400);
    return HttpResponse.json({
      total_transactions: 200,
      matched_transactions: 180,
      pending_transactions: 20,
      matched_rate: 0.9,
    });
  }),

  http.get(`${BASE_URL}/api/v1/analytics/metabase-token`, async () => {
    await delay(500);
    return HttpResponse.json({
      embed_url: 'https://metabase.example.com/embed/dashboard/mock',
    });
  }),

  http.get(`${BASE_URL}/api/v1/analytics/forecast/revenue`, async () => {
    await delay(600);
    const data = Array.from({ length: 60 }, (_, i) => ({
      date: new Date(2024, 10, i + 1).toISOString().split('T')[0],
      actual: i < 30 ? Math.floor(Math.random() * 10000000) + 5000000 : null,
      forecast: Math.floor(Math.random() * 10000000) + 6000000,
      lower_bound: Math.floor(Math.random() * 8000000) + 4000000,
      upper_bound: Math.floor(Math.random() * 12000000) + 8000000,
    }));
    return HttpResponse.json({ data });
  }),

  http.get(`${BASE_URL}/api/v1/analytics/anomalies/revenue`, async () => {
    await delay(500);
    const data = Array.from({ length: 5 }, (_, i) => ({
      date: new Date(2024, 10, i * 6 + 1).toISOString().split('T')[0],
      amount: Math.floor(Math.random() * 5000000) + 2000000,
      expected: 7000000,
      deviation: Math.random() * 0.5 + 0.3,
      severity: ['low', 'medium', 'high'][i % 3] as 'low' | 'medium' | 'high',
    }));
    return HttpResponse.json({ data });
  }),

  // ==================== REPORTS ====================
  http.get(`${BASE_URL}/api/v1/analytics/reports/templates`, async () => {
    await delay(300);
    return HttpResponse.json([
      { slug: 'ar_aging', name: 'AR Aging Report', description: 'Báo cáo phân tích công nợ phải thu', supported_formats: ['xlsx', 'pdf'] },
      { slug: 'ap_aging', name: 'AP Aging Report', description: 'Báo cáo phân tích công nợ phải trả', supported_formats: ['xlsx', 'pdf'] },
      { slug: 'payments', name: 'Payments Report', description: 'Báo cáo thanh toán', supported_formats: ['xlsx', 'pdf'] },
    ]);
  }),

  http.post(`${BASE_URL}/api/v1/analytics/reports/export`, async ({ request }) => {
    await delay(1000);
    const body = await request.json();
    const newJob = {
      id: mockData.exportJobs.length + 1,
      job_id: `exp_${Date.now()}`,
      job_type: body.report_type,
      status: 'pending' as const,
      file_url: null,
      error_log: null,
      job_metadata: body.filters || {},
      org_id: 1,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    mockData.exportJobs.push(newJob);
    
    // Simulate job completion after 3 seconds
    setTimeout(() => {
      newJob.status = 'completed';
      newJob.file_url = `https://example.com/files/${newJob.job_id}.${body.format}`;
      newJob.updated_at = new Date().toISOString();
    }, 3000);
    
    return HttpResponse.json(newJob, { status: 201 });
  }),

  http.get(`${BASE_URL}/api/v1/analytics/reports/export-jobs`, async () => {
    await delay(300);
    return HttpResponse.json({
      total: mockData.exportJobs.length,
      skip: 0,
      limit: 10,
      items: mockData.exportJobs,
    });
  }),

  http.get(`${BASE_URL}/api/v1/analytics/reports/export-jobs/:id`, async ({ params }) => {
    await delay(300);
    const job = mockData.exportJobs.find(j => j.id === parseInt(params.id as string));
    return job ? HttpResponse.json(job) : new HttpResponse(null, { status: 404 });
  }),

  // ==================== SETTINGS ====================
  http.get(`${BASE_URL}/api/v1/settings/ai`, async () => {
    await delay(300);
    return HttpResponse.json({
      id: 1,
      key: 'ai_settings',
      value_json: {
        forecast_window: 30,
        forecast_confidence: 0.95,
        seasonality_mode: 'multiplicative',
        anomaly_threshold: 0.85,
        min_anomaly_amount: 1000000,
        alert_severity: 'medium',
        job_schedule: {
          frequency: 'daily',
          time: '02:00',
          auto_retry: true,
        },
      },
      description: 'AI system settings',
      org_id: 1,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });
  }),

  http.put(`${BASE_URL}/api/v1/settings/ai`, async ({ request }) => {
    await delay(500);
    const body = await request.json();
    return HttpResponse.json({
      id: 1,
      key: 'ai_settings',
      value_json: body.value_json,
      description: 'AI system settings',
      org_id: 1,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });
  }),

  // ==================== ALERTS ====================
  http.get(`${BASE_URL}/api/v1/alerts`, async () => {
    await delay(400);
    const alerts = [
      { id: 1, kind: 'overdue_invoice', title: 'Hoá đơn quá hạn', message: 'Invoice #1234 quá hạn 15 ngày', severity: 'high' as const, status: 'new' as const, alert_metadata: {}, org_id: 1, created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
      { id: 2, kind: 'abnormal_payment', title: 'Thanh toán bất thường', message: 'Phát hiện thanh toán không bình thường', severity: 'medium' as const, status: 'new' as const, alert_metadata: {}, org_id: 1, created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
    ];
    return HttpResponse.json({
      total: alerts.length,
      skip: 0,
      limit: 10,
      items: alerts,
    });
  }),
];
