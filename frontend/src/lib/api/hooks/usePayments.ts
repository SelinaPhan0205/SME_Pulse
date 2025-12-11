/**
 * Payments React Query Hooks
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  paymentsAPI,
  type Payment,
  type PaymentCreateRequest,
  type PaymentUpdateRequest,
  type PaymentListParams,
} from '../services/payments';

const PAYMENTS_KEY = 'payments';

export const usePayments = (params?: PaymentListParams) => {
  return useQuery({
    queryKey: [PAYMENTS_KEY, params],
    queryFn: () => paymentsAPI.getPayments(params),
  });
};

export const usePayment = (id: number) => {
  return useQuery({
    queryKey: [PAYMENTS_KEY, id],
    queryFn: () => paymentsAPI.getPaymentById(id),
    enabled: !!id,
  });
};

export const useCreatePayment = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: PaymentCreateRequest) => paymentsAPI.createPayment(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PAYMENTS_KEY] });
      // Also invalidate invoices/bills as their paid_amount changed
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      queryClient.invalidateQueries({ queryKey: ['bills'] });
    },
  });
};

export const useUpdatePayment = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: PaymentUpdateRequest }) =>
      paymentsAPI.updatePayment(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PAYMENTS_KEY] });
    },
  });
};
