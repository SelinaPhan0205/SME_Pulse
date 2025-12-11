/**
 * Customers API Service
 * CRUD operations cho Customers
 */

import { apiClient } from '../client';
import type {
  CustomerCreate,
  CustomerUpdate,
  CustomerResponse,
  PaginatedCustomersResponse,
  PaginationParams,
} from '../types';

export type { CustomerResponse };

export const customersAPI = {
  /**
   * List customers - Lấy danh sách customers có phân trang
   * GET /api/v1/customers
   */
  list: async (params?: PaginationParams & { is_active?: boolean }): Promise<PaginatedCustomersResponse> => {
    const response = await apiClient.get<PaginatedCustomersResponse>('/api/v1/customers', {
      params,
    });
    return response.data;
  },

  /**
   * Get customer by ID - Lấy chi tiết 1 customer
   * GET /api/v1/customers/{id}
   */
  getById: async (id: number): Promise<CustomerResponse> => {
    const response = await apiClient.get<CustomerResponse>(`/api/v1/customers/${id}`);
    return response.data;
  },

  /**
   * Create customer - Tạo customer mới
   * POST /api/v1/customers
   */
  create: async (data: CustomerCreate): Promise<CustomerResponse> => {
    const response = await apiClient.post<CustomerResponse>('/api/v1/customers', data);
    return response.data;
  },

  /**
   * Update customer - Cập nhật customer
   * PUT /api/v1/customers/{id}
   */
  update: async (id: number, data: CustomerUpdate): Promise<CustomerResponse> => {
    const response = await apiClient.put<CustomerResponse>(`/api/v1/customers/${id}`, data);
    return response.data;
  },

  /**
   * Delete customer - Xóa customer
   * DELETE /api/v1/customers/{id}
   */
  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/v1/customers/${id}`);
  },
};
