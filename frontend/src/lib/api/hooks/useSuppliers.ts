/**
 * Suppliers Hooks - React Query
 * CRUD operations cho Suppliers với React Query
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { suppliersAPI } from '../services';
import { getErrorMessage } from '../client';
import type { SupplierCreate, SupplierUpdate, PaginationParams } from '../types';

/**
 * Hook để list suppliers với pagination
 */
export function useSuppliers(params?: PaginationParams & { is_active?: boolean }) {
  return useQuery({
    queryKey: ['suppliers', params],
    queryFn: () => suppliersAPI.list(params),
    staleTime: 30 * 1000,
  });
}

/**
 * Hook để get supplier by ID
 */
export function useSupplier(id: number) {
  return useQuery({
    queryKey: ['suppliers', id],
    queryFn: () => suppliersAPI.getById(id),
    enabled: !!id,
  });
}

/**
 * Hook để create supplier
 */
export function useCreateSupplier() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: SupplierCreate) => suppliersAPI.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['suppliers'] });
    },
    onError: (error) => {
      console.error('Create supplier failed:', getErrorMessage(error));
    },
  });
}

/**
 * Hook để update supplier
 */
export function useUpdateSupplier() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: SupplierUpdate }) => 
      suppliersAPI.update(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['suppliers', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['suppliers'] });
    },
    onError: (error) => {
      console.error('Update supplier failed:', getErrorMessage(error));
    },
  });
}

/**
 * Hook để delete supplier
 */
export function useDeleteSupplier() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => suppliersAPI.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['suppliers'] });
    },
    onError: (error) => {
      console.error('Delete supplier failed:', getErrorMessage(error));
    },
  });
}
