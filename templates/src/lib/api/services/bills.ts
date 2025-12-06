/**
 * AP Bills API Service
 * Accounts Payable bills
 */

import { apiClient } from '../client';
import type { SupplierResponse } from './suppliers';

export interface APBill {
  id: number;
  bill_no: string;
  supplier_id: number;
  supplier?: SupplierResponse;
  issue_date: string;
  due_date: string;
  total_amount: number;
  paid_amount: number;
  remaining_amount: number;
  status: 'draft' | 'posted' | 'paid' | 'overdue' | 'cancelled';
  aging_days?: number;
  notes: string | null;
  org_id: number;
  created_at: string;
  updated_at: string;
}

export interface APBillCreateRequest {
  bill_no: string;
  supplier_id: number;
  issue_date: string;
  due_date: string;
  total_amount: number;
  notes?: string;
}

export interface APBillUpdateRequest {
  supplier_id?: number;
  issue_date?: string;
  due_date?: string;
  total_amount?: number;
  notes?: string;
}

export interface APBillListParams {
  status?: string;
  supplier_id?: number;
  due_from?: string;
  due_to?: string;
  overdue_only?: boolean;
  search?: string;
  skip?: number;
  limit?: number;
}

export interface PaginatedBillsResponse {
  total: number;
  skip: number;
  limit: number;
  items: APBill[];
}

export const billsAPI = {
  /**
   * Get list of AP bills
   * GET /api/v1/bills
   */
  getBills: async (params?: APBillListParams): Promise<PaginatedBillsResponse> => {
    const response = await apiClient.get<PaginatedBillsResponse>('/api/v1/bills', { params });
    return response.data;
  },

  /**
   * Get bill by ID
   * GET /api/v1/bills/{id}
   */
  getBillById: async (id: number): Promise<APBill> => {
    const response = await apiClient.get<APBill>(`/api/v1/bills/${id}`);
    return response.data;
  },

  /**
   * Create new bill
   * POST /api/v1/bills
   */
  createBill: async (data: APBillCreateRequest): Promise<APBill> => {
    const response = await apiClient.post<APBill>('/api/v1/bills', data);
    return response.data;
  },

  /**
   * Update bill (only if status = draft)
   * PUT /api/v1/bills/{id}
   */
  updateBill: async (id: number, data: APBillUpdateRequest): Promise<APBill> => {
    const response = await apiClient.put<APBill>(`/api/v1/bills/${id}`, data);
    return response.data;
  },

  /**
   * Delete/Cancel bill
   * DELETE /api/v1/bills/{id}
   */
  deleteBill: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/v1/bills/${id}`);
  },

  /**
   * Post bill (change status from draft to posted)
   * POST /api/v1/bills/{id}/post
   */
  postBill: async (id: number): Promise<APBill> => {
    const response = await apiClient.post<APBill>(`/api/v1/bills/${id}/post`);
    return response.data;
  },
};
