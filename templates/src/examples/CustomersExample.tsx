/**
 * Example: Customer Management Component
 * Ví dụ cách dùng API hooks trong React component
 */

import { useState } from 'react';
import { Plus, Edit2, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { 
  useCustomers, 
  useCreateCustomer, 
  useUpdateCustomer, 
  useDeleteCustomer,
  type CustomerCreate,
  type CustomerUpdate,
} from '@/lib/api';

export function CustomersExample() {
  const [page, setPage] = useState(0);
  const limit = 20;

  // Fetch customers list
  const { data, isLoading, error } = useCustomers({ 
    skip: page * limit, 
    limit,
    is_active: true, // Filter chỉ lấy active customers
  });

  // Mutations
  const createMutation = useCreateCustomer();
  const updateMutation = useUpdateCustomer();
  const deleteMutation = useDeleteCustomer();

  // Handle create
  const handleCreate = () => {
    const newCustomer: CustomerCreate = {
      name: 'Công ty ABC',
      code: 'ABC001',
      email: 'abc@example.com',
      phone: '0123456789',
      credit_term: 30,
      is_active: true,
    };

    createMutation.mutate(newCustomer, {
      onSuccess: () => {
        alert('Tạo customer thành công!');
      },
      onError: (error) => {
        alert(`Lỗi: ${error.message}`);
      },
    });
  };

  // Handle update
  const handleUpdate = (customerId: number) => {
    const updates: CustomerUpdate = {
      phone: '0987654321',
      credit_term: 45,
    };

    updateMutation.mutate(
      { id: customerId, data: updates },
      {
        onSuccess: () => {
          alert('Cập nhật thành công!');
        },
      }
    );
  };

  // Handle delete
  const handleDelete = (customerId: number) => {
    if (confirm('Bạn có chắc muốn xóa?')) {
      deleteMutation.mutate(customerId, {
        onSuccess: () => {
          alert('Xóa thành công!');
        },
      });
    }
  };

  // Loading state
  if (isLoading) {
    return <div>Loading customers...</div>;
  }

  // Error state
  if (error) {
    return <div>Error: {error.message}</div>;
  }

  // Render
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Customers ({data?.total})</h1>
        <Button onClick={handleCreate} disabled={createMutation.isPending}>
          <Plus className="size-4 mr-2" />
          {createMutation.isPending ? 'Creating...' : 'Add Customer'}
        </Button>
      </div>

      {/* Table */}
      <div className="border rounded-lg">
        <table className="w-full">
          <thead>
            <tr className="border-b bg-gray-50">
              <th className="p-3 text-left">ID</th>
              <th className="p-3 text-left">Name</th>
              <th className="p-3 text-left">Code</th>
              <th className="p-3 text-left">Email</th>
              <th className="p-3 text-left">Phone</th>
              <th className="p-3 text-left">Credit Term</th>
              <th className="p-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((customer) => (
              <tr key={customer.id} className="border-b hover:bg-gray-50">
                <td className="p-3">{customer.id}</td>
                <td className="p-3 font-medium">{customer.name}</td>
                <td className="p-3">{customer.code}</td>
                <td className="p-3">{customer.email}</td>
                <td className="p-3">{customer.phone}</td>
                <td className="p-3">{customer.credit_term} days</td>
                <td className="p-3 text-right space-x-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleUpdate(customer.id)}
                    disabled={updateMutation.isPending}
                  >
                    <Edit2 className="size-4" />
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => handleDelete(customer.id)}
                    disabled={deleteMutation.isPending}
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex justify-between items-center">
        <Button 
          onClick={() => setPage(p => Math.max(0, p - 1))}
          disabled={page === 0}
        >
          Previous
        </Button>
        <span>Page {page + 1}</span>
        <Button 
          onClick={() => setPage(p => p + 1)}
          disabled={!data || data.items.length < limit}
        >
          Next
        </Button>
      </div>
    </div>
  );
}
