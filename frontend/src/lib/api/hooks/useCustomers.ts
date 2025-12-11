/**
 * Customers Hooks - React Query
 * CRUD operations cho Customers với React Query
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { customersAPI } from '../services';
import { getErrorMessage } from '../client';
import type { CustomerCreate, CustomerUpdate, PaginationParams } from '../types';

/**
 * Hook để list customers với pagination
 * 
 * @example
 * const { data, isLoading, error } = useCustomers({ skip: 0, limit: 100 });
 * 
 * if (isLoading) return <Spinner />;
 * if (error) return <Error message={error.message} />;
 * 
 * return (
 *   <div>
 *     <p>Total: {data.total}</p>
 *     {data.items.map(customer => <CustomerCard key={customer.id} data={customer} />)}
 *   </div>
 * );
 */
export function useCustomers(params?: PaginationParams & { is_active?: boolean }) {
  return useQuery({
    queryKey: ['customers', params],
    queryFn: () => customersAPI.list(params),
    staleTime: 30 * 1000, // Cache 30 giây
  });
}

/**
 * Hook để get customer by ID
 * 
 * @example
 * const { data: customer, isLoading } = useCustomer(customerId);
 */
export function useCustomer(id: number) {
  return useQuery({
    queryKey: ['customers', id],
    queryFn: () => customersAPI.getById(id),
    enabled: !!id, // Chỉ fetch nếu có id
  });
}

/**
 * Hook để create customer
 * 
 * @example
 * const createMutation = useCreateCustomer();
 * 
 * const handleSubmit = (formData) => {
 *   createMutation.mutate(formData, {
 *     onSuccess: () => {
 *       toast.success('Customer created!');
 *       closeDialog();
 *     },
 *     onError: (error) => toast.error(error.message),
 *   });
 * };
 */
export function useCreateCustomer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CustomerCreate) => customersAPI.create(data),
    onSuccess: () => {
      // Invalidate customers list để refetch
      queryClient.invalidateQueries({ queryKey: ['customers'] });
    },
    onError: (error) => {
      console.error('Create customer failed:', getErrorMessage(error));
    },
  });
}

/**
 * Hook để update customer
 * 
 * @example
 * const updateMutation = useUpdateCustomer();
 * 
 * const handleUpdate = (id, changes) => {
 *   updateMutation.mutate({ id, data: changes }, {
 *     onSuccess: () => toast.success('Updated!'),
 *   });
 * };
 */
export function useUpdateCustomer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: CustomerUpdate }) => 
      customersAPI.update(id, data),
    onSuccess: (_, variables) => {
      // Invalidate specific customer và list
      queryClient.invalidateQueries({ queryKey: ['customers', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['customers'] });
    },
    onError: (error) => {
      console.error('Update customer failed:', getErrorMessage(error));
    },
  });
}

/**
 * Hook để delete customer
 * 
 * @example
 * const deleteMutation = useDeleteCustomer();
 * 
 * const handleDelete = (id) => {
 *   if (confirm('Are you sure?')) {
 *     deleteMutation.mutate(id, {
 *       onSuccess: () => toast.success('Deleted!'),
 *     });
 *   }
 * };
 */
export function useDeleteCustomer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => customersAPI.delete(id),
    onSuccess: () => {
      // Invalidate customers list
      queryClient.invalidateQueries({ queryKey: ['customers'] });
    },
    onError: (error) => {
      console.error('Delete customer failed:', getErrorMessage(error));
    },
  });
}
