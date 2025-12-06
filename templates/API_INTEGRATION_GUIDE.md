# API Integration Guide

## 📁 Cấu trúc thư mục

```
src/
├── lib/
│   └── api/
│       ├── client.ts              # Axios instance + interceptors
│       ├── types.ts               # TypeScript interfaces
│       ├── index.ts               # Central export
│       ├── services/              # API service functions
│       │   ├── auth.ts
│       │   ├── customers.ts
│       │   ├── suppliers.ts
│       │   ├── analytics.ts
│       │   └── index.ts
│       └── hooks/                 # React Query hooks
│           ├── useAuth.ts
│           ├── useCustomers.ts
│           ├── useSuppliers.ts
│           ├── useAnalytics.ts
│           └── index.ts
├── providers/
│   └── QueryProvider.tsx          # React Query Provider
└── examples/                      # Ví dụ cách dùng
    ├── LoginExample.tsx
    ├── CustomersExample.tsx
    └── DashboardAnalyticsExample.tsx
```

---

## 🚀 Setup

### 1. Cài đặt dependencies

```bash
npm install @tanstack/react-query @tanstack/react-query-devtools axios
```

### 2. Cấu hình environment variables

Tạo file `.env`:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

### 3. Wrap App với QueryProvider

File `App.tsx` đã được setup:

```tsx
import { QueryProvider } from './providers/QueryProvider';

export default function App() {
  return (
    <QueryProvider>
      <BrowserRouter>
        {/* Routes */}
      </BrowserRouter>
    </QueryProvider>
  );
}
```

---

## 📖 Cách sử dụng

### 1. Authentication

#### Login

```tsx
import { useLogin, getErrorMessage } from '@/lib/api';

function LoginPage() {
  const loginMutation = useLogin();

  const handleLogin = () => {
    loginMutation.mutate(
      { email: 'user@example.com', password: 'password123' },
      {
        onSuccess: () => {
          // Tự động navigate to /dashboard
          console.log('Login successful!');
        },
        onError: (error) => {
          alert(getErrorMessage(error));
        },
      }
    );
  };

  return (
    <button 
      onClick={handleLogin}
      disabled={loginMutation.isPending}
    >
      {loginMutation.isPending ? 'Logging in...' : 'Login'}
    </button>
  );
}
```

#### Get Current User

```tsx
import { useCurrentUser } from '@/lib/api';

function Profile() {
  const { data: user, isLoading } = useCurrentUser();

  if (isLoading) return <div>Loading...</div>;

  return <div>Welcome, {user?.full_name}</div>;
}
```

#### Logout

```tsx
import { useLogout } from '@/lib/api';

function LogoutButton() {
  const logoutMutation = useLogout();

  return (
    <button onClick={() => logoutMutation.mutate()}>
      Logout
    </button>
  );
}
```

---

### 2. CRUD Operations - Customers

#### List Customers (với pagination)

```tsx
import { useCustomers } from '@/lib/api';

function CustomersList() {
  const { data, isLoading, error } = useCustomers({
    skip: 0,
    limit: 20,
    is_active: true,
  });

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      <p>Total: {data.total}</p>
      {data.items.map(customer => (
        <div key={customer.id}>
          {customer.name} - {customer.email}
        </div>
      ))}
    </div>
  );
}
```

#### Get Customer by ID

```tsx
import { useCustomer } from '@/lib/api';

function CustomerDetail({ customerId }: { customerId: number }) {
  const { data: customer, isLoading } = useCustomer(customerId);

  if (isLoading) return <div>Loading...</div>;

  return (
    <div>
      <h1>{customer?.name}</h1>
      <p>Email: {customer?.email}</p>
      <p>Phone: {customer?.phone}</p>
    </div>
  );
}
```

#### Create Customer

```tsx
import { useCreateCustomer, type CustomerCreate } from '@/lib/api';

function CreateCustomerForm() {
  const createMutation = useCreateCustomer();

  const handleSubmit = (formData: CustomerCreate) => {
    createMutation.mutate(formData, {
      onSuccess: (newCustomer) => {
        alert(`Customer ${newCustomer.name} created!`);
      },
      onError: (error) => {
        alert(`Error: ${error.message}`);
      },
    });
  };

  return (
    <form onSubmit={(e) => {
      e.preventDefault();
      handleSubmit({
        name: 'Công ty ABC',
        email: 'abc@example.com',
        phone: '0123456789',
        credit_term: 30,
        is_active: true,
      });
    }}>
      <button type="submit" disabled={createMutation.isPending}>
        {createMutation.isPending ? 'Creating...' : 'Create Customer'}
      </button>
    </form>
  );
}
```

#### Update Customer

```tsx
import { useUpdateCustomer, type CustomerUpdate } from '@/lib/api';

function EditCustomerButton({ customerId }: { customerId: number }) {
  const updateMutation = useUpdateCustomer();

  const handleUpdate = () => {
    const updates: CustomerUpdate = {
      phone: '0987654321',
      credit_term: 45,
    };

    updateMutation.mutate(
      { id: customerId, data: updates },
      {
        onSuccess: () => {
          alert('Updated successfully!');
        },
      }
    );
  };

  return (
    <button onClick={handleUpdate} disabled={updateMutation.isPending}>
      Update
    </button>
  );
}
```

#### Delete Customer

```tsx
import { useDeleteCustomer } from '@/lib/api';

function DeleteCustomerButton({ customerId }: { customerId: number }) {
  const deleteMutation = useDeleteCustomer();

  const handleDelete = () => {
    if (confirm('Are you sure?')) {
      deleteMutation.mutate(customerId, {
        onSuccess: () => {
          alert('Deleted successfully!');
        },
      });
    }
  };

  return (
    <button onClick={handleDelete} disabled={deleteMutation.isPending}>
      Delete
    </button>
  );
}
```

---

### 3. Analytics & KPIs

#### Dashboard Summary

```tsx
import { useDashboardSummary } from '@/lib/api';

function DashboardKPIs() {
  const { data, isLoading } = useDashboardSummary();

  if (isLoading) return <div>Loading KPIs...</div>;

  return (
    <div className="grid grid-cols-4 gap-4">
      <div>
        <h3>Total Revenue</h3>
        <p>${data?.total_revenue.toLocaleString()}</p>
      </div>
      <div>
        <h3>Accounts Receivable</h3>
        <p>${data?.total_receivables.toLocaleString()}</p>
      </div>
      <div>
        <h3>Accounts Payable</h3>
        <p>${data?.total_payables.toLocaleString()}</p>
      </div>
      <div>
        <h3>Payment Success Rate</h3>
        <p>{data?.payment_success_rate.toFixed(1)}%</p>
      </div>
    </div>
  );
}
```

#### AR Aging

```tsx
import { useARAging } from '@/lib/api';

function ARAgingChart() {
  const { data, isLoading } = useARAging();

  if (isLoading) return <div>Loading AR Aging...</div>;

  return (
    <div>
      <h2>AR Aging Analysis</h2>
      <p>Total AR: ${data?.total_ar.toLocaleString()}</p>
      {data?.buckets.map(bucket => (
        <div key={bucket.bucket}>
          <span>{bucket.bucket}:</span>
          <span>${bucket.amount.toLocaleString()}</span>
          <span>({bucket.count} invoices)</span>
        </div>
      ))}
    </div>
  );
}
```

#### Daily Revenue (với date range)

```tsx
import { useDailyRevenue } from '@/lib/api';

function RevenueChart() {
  const { data } = useDailyRevenue({
    start_date: '2024-01-01',
    end_date: '2024-12-31',
  });

  return (
    <div>
      <h2>Daily Revenue</h2>
      {data?.data.map(point => (
        <div key={point.date}>
          {point.date}: ${point.revenue.toLocaleString()}
        </div>
      ))}
    </div>
  );
}
```

---

## 🛠️ Advanced Usage

### Gọi API trực tiếp (không dùng hooks)

```tsx
import { customersAPI, authAPI } from '@/lib/api';

// Login
const response = await authAPI.login({ email, password });
console.log(response.access_token);

// Create customer
const newCustomer = await customersAPI.create({
  name: 'Test Company',
  email: 'test@example.com',
  credit_term: 30,
  is_active: true,
});
```

### Invalidate cache manually

```tsx
import { useQueryClient } from '@tanstack/react-query';

function RefreshButton() {
  const queryClient = useQueryClient();

  const handleRefresh = () => {
    // Invalidate tất cả customers queries
    queryClient.invalidateQueries({ queryKey: ['customers'] });
  };

  return <button onClick={handleRefresh}>Refresh</button>;
}
```

### Custom error handling

```tsx
import { getErrorMessage } from '@/lib/api';

const createMutation = useCreateCustomer();

createMutation.mutate(data, {
  onError: (error) => {
    const message = getErrorMessage(error);
    
    // Custom UI notification
    toast.error(message);
    
    // Log to analytics
    analytics.track('Customer Create Failed', { error: message });
  },
});
```

---

## 🔧 Configuration

### Thay đổi base URL

Edit `.env`:

```bash
VITE_API_BASE_URL=https://api.production.com
```

### Timeout configuration

Edit `src/lib/api/client.ts`:

```typescript
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60 seconds
  headers: {
    'Content-Type': 'application/json',
  },
});
```

### Query cache configuration

Edit `src/providers/QueryProvider.tsx`:

```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: true,  // Auto refetch khi focus window
      retry: 3,                    // Retry 3 lần
      staleTime: 5 * 60 * 1000,   // Cache 5 phút
    },
  },
});
```

---

## 📚 API Reference

### Available Hooks

#### Auth
- `useLogin()` - Login mutation
- `useLogout()` - Logout mutation
- `useCurrentUser()` - Get current user query

#### Customers
- `useCustomers(params)` - List customers query
- `useCustomer(id)` - Get customer by ID query
- `useCreateCustomer()` - Create customer mutation
- `useUpdateCustomer()` - Update customer mutation
- `useDeleteCustomer()` - Delete customer mutation

#### Suppliers
- `useSuppliers(params)` - List suppliers query
- `useSupplier(id)` - Get supplier by ID query
- `useCreateSupplier()` - Create supplier mutation
- `useUpdateSupplier()` - Update supplier mutation
- `useDeleteSupplier()` - Delete supplier mutation

#### Analytics
- `useDashboardSummary()` - Get dashboard KPIs
- `useARAging()` - Get AR aging analysis
- `useAPAging()` - Get AP aging analysis
- `useDailyRevenue(params)` - Get daily revenue
- `usePaymentSuccessRate(params)` - Get payment success rate

---

## 🐛 Troubleshooting

### Token expired / 401 errors

Token expired được handle tự động bởi response interceptor. User sẽ được redirect về `/login`.

### CORS errors

Đảm bảo backend config CORS cho phép origin của frontend:

```python
# backend/app/main.py
cors_origins = ["http://localhost:5173", "http://localhost:3000"]
app.add_middleware(CORSMiddleware, allow_origins=cors_origins, ...)
```

### Type errors

Import types từ `@/lib/api`:

```tsx
import type { CustomerCreate, CustomerResponse } from '@/lib/api';
```

---

## ✅ Best Practices

1. **Luôn dùng hooks trong components** - Không gọi API trực tiếp trong components
2. **Handle loading states** - Hiển thị spinner khi `isLoading === true`
3. **Handle errors** - Hiển thị error message khi có lỗi
4. **Optimistic updates** - Update UI trước khi API response (advanced)
5. **Type safety** - Dùng TypeScript types để tránh lỗi runtime

---

## 📝 Examples

Xem thêm ví dụ chi tiết trong:
- `src/examples/LoginExample.tsx`
- `src/examples/CustomersExample.tsx`
- `src/examples/DashboardAnalyticsExample.tsx`
