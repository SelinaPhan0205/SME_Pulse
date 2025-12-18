/**
 * AP Bills React Query Hooks
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  billsAPI,
  type APBill,
  type APBillCreateRequest,
  type APBillUpdateRequest,
  type APBillListParams,
} from '../services/bills';

const BILLS_KEY = 'bills';

export const useBills = (params?: APBillListParams) => {
  return useQuery({
    queryKey: [BILLS_KEY, params],
    queryFn: () => billsAPI.getBills(params),
  });
};

export const useBill = (id: number) => {
  return useQuery({
    queryKey: [BILLS_KEY, id],
    queryFn: () => billsAPI.getBillById(id),
    enabled: !!id,
  });
};

export const useCreateBill = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: APBillCreateRequest) => billsAPI.createBill(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [BILLS_KEY] });
    },
  });
};

export const useUpdateBill = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: APBillUpdateRequest }) =>
      billsAPI.updateBill(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [BILLS_KEY] });
      queryClient.invalidateQueries({ queryKey: [BILLS_KEY, variables.id] });
    },
  });
};

export const useDeleteBill = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => billsAPI.deleteBill(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [BILLS_KEY] });
    },
  });
};

export const usePostBill = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => billsAPI.postBill(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: [BILLS_KEY] });
      queryClient.invalidateQueries({ queryKey: [BILLS_KEY, id] });
      queryClient.invalidateQueries({ queryKey: ['bills-all-kpi'] });
    },
  });
};

/**
 * Hook to fetch ALL bills for KPI calculation
 * Uses separate query key to avoid cache conflicts with paginated data
 */
export const useAllBillsForKPI = () => {
  return useQuery({
    queryKey: ['bills-all-kpi'],
    queryFn: () => billsAPI.getBills({ limit: 500 }),
    staleTime: 30 * 1000, // Cache 30 seconds
  });
};
