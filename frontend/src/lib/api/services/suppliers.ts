/**
 * Suppliers API Service
 * CRUD operations cho Suppliers
 */

import { apiClient } from '../client';
import type {
  SupplierCreate,
  SupplierUpdate,
  SupplierResponse,
  PaginatedSuppliersResponse,
  PaginationParams,
} from '../types';

export type { SupplierResponse };

export const suppliersAPI = {
  /**
   * List suppliers - Lấy danh sách suppliers có phân trang
   * GET /api/v1/suppliers
   */
  list: async (params?: PaginationParams & { is_active?: boolean }): Promise<PaginatedSuppliersResponse> => {
    const response = await apiClient.get<PaginatedSuppliersResponse>('/api/v1/suppliers', {
      params,
    });
    return response.data;
  },

  /**
   * Get supplier by ID - Lấy chi tiết 1 supplier
   * GET /api/v1/suppliers/{id}
   */
  getById: async (id: number): Promise<SupplierResponse> => {
    const response = await apiClient.get<SupplierResponse>(`/api/v1/suppliers/${id}`);
    return response.data;
  },

  /**
   * Create supplier - Tạo supplier mới
   * POST /api/v1/suppliers
   */
  create: async (data: SupplierCreate): Promise<SupplierResponse> => {
    const response = await apiClient.post<SupplierResponse>('/api/v1/suppliers', data);
    return response.data;
  },

  /**
   * Update supplier - Cập nhật supplier
   * PUT /api/v1/suppliers/{id}
   */
  update: async (id: number, data: SupplierUpdate): Promise<SupplierResponse> => {
    const response = await apiClient.put<SupplierResponse>(`/api/v1/suppliers/${id}`, data);
    return response.data;
  },

  /**
   * Delete supplier - Xóa supplier
   * DELETE /api/v1/suppliers/{id}
   */
  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/v1/suppliers/${id}`);
  },
};
