/**
 * AR Invoices React Query Hooks
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  invoicesAPI,
  type ARInvoice,
  type ARInvoiceCreateRequest,
  type ARInvoiceUpdateRequest,
  type ARInvoiceListParams,
  type BulkImportRequest,
} from '../services/invoices';

const INVOICES_KEY = 'invoices';

export const useInvoices = (params?: ARInvoiceListParams) => {
  return useQuery({
    queryKey: [INVOICES_KEY, params],
    queryFn: () => invoicesAPI.getInvoices(params),
  });
};

export const useInvoice = (id: number) => {
  return useQuery({
    queryKey: [INVOICES_KEY, id],
    queryFn: () => invoicesAPI.getInvoiceById(id),
    enabled: !!id,
  });
};

export const useCreateInvoice = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ARInvoiceCreateRequest) => invoicesAPI.createInvoice(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [INVOICES_KEY] });
    },
  });
};

export const useUpdateInvoice = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ARInvoiceUpdateRequest }) =>
      invoicesAPI.updateInvoice(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [INVOICES_KEY] });
      queryClient.invalidateQueries({ queryKey: [INVOICES_KEY, variables.id] });
    },
  });
};

export const useDeleteInvoice = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => invoicesAPI.deleteInvoice(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [INVOICES_KEY] });
    },
  });
};

export const usePostInvoice = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => invoicesAPI.postInvoice(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: [INVOICES_KEY] });
      queryClient.invalidateQueries({ queryKey: [INVOICES_KEY, id] });
    },
  });
};

/**
 * Bulk import invoices from Excel/CSV
 */
export const useBulkImportInvoices = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: BulkImportRequest) => invoicesAPI.bulkImport(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [INVOICES_KEY] });
    },
  });
};