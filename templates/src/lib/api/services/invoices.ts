/**
 * AR Invoices API Service
 * Accounts Receivable invoices
 */

import { apiClient } from '../client';
import type { CustomerResponse } from './customers';

export interface ARInvoice {
  id: number;
  invoice_no: string;
  customer_id: number;
  customer?: CustomerResponse;
  issue_date: string;
  due_date: string;
  total_amount: number;
  paid_amount: number;
  remaining_amount: number;
  status: 'draft' | 'posted' | 'paid' | 'overdue' | 'cancelled';
  aging_days?: number;
  risk_level?: 'low' | 'normal' | 'high';
  notes: string | null;
  org_id: number;
  created_at: string;
  updated_at: string;
}

export interface ARInvoiceCreateRequest {
  invoice_no: string;
  customer_id: number;
  issue_date: string;
  due_date: string;
  total_amount: number;
  notes?: string;
}

export interface ARInvoiceUpdateRequest {
  customer_id?: number;
  issue_date?: string;
  due_date?: string;
  total_amount?: number;
  notes?: string;
}

export interface ARInvoiceListParams {
  status?: string;
  customer_id?: number;
  due_from?: string;
  due_to?: string;
  overdue_only?: boolean;
  search?: string;
  risk_level?: string;
  skip?: number;
  limit?: number;
}

export interface PaginatedInvoicesResponse {
  total: number;
  skip: number;
  limit: number;
  items: ARInvoice[];
}

export const invoicesAPI = {
  /**
   * Get list of AR invoices
   * GET /api/v1/invoices
   */
  getInvoices: async (params?: ARInvoiceListParams): Promise<PaginatedInvoicesResponse> => {
    const response = await apiClient.get<PaginatedInvoicesResponse>('/api/v1/invoices', { params });
    return response.data;
  },

  /**
   * Get invoice by ID
   * GET /api/v1/invoices/{id}
   */
  getInvoiceById: async (id: number): Promise<ARInvoice> => {
    const response = await apiClient.get<ARInvoice>(`/api/v1/invoices/${id}`);
    return response.data;
  },

  /**
   * Create new invoice
   * POST /api/v1/invoices
   */
  createInvoice: async (data: ARInvoiceCreateRequest): Promise<ARInvoice> => {
    const response = await apiClient.post<ARInvoice>('/api/v1/invoices', data);
    return response.data;
  },

  /**
   * Update invoice (only if status = draft)
   * PUT /api/v1/invoices/{id}
   */
  updateInvoice: async (id: number, data: ARInvoiceUpdateRequest): Promise<ARInvoice> => {
    const response = await apiClient.put<ARInvoice>(`/api/v1/invoices/${id}`, data);
    return response.data;
  },

  /**
   * Delete/Cancel invoice
   * DELETE /api/v1/invoices/{id}
   */
  deleteInvoice: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/v1/invoices/${id}`);
  },

  /**
   * Post invoice (change status from draft to posted)
   * POST /api/v1/invoices/{id}/post
   */
  postInvoice: async (id: number): Promise<ARInvoice> => {
    const response = await apiClient.post<ARInvoice>(`/api/v1/invoices/${id}/post`);
    return response.data;
  },
};
