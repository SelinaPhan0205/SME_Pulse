/**
 * Payments API Service
 * Payments and allocations to invoices/bills
 */

import { apiClient } from '../client';
import type { ARInvoice } from './invoices';
import type { APBill } from './bills';
import type { Account } from './accounts';

export interface PaymentAllocation {
  id: number;
  payment_id: number;
  ar_invoice_id: number | null;
  ap_bill_id: number | null;
  allocated_amount: number;
  notes: string | null;
  ar_invoice?: ARInvoice;
  ap_bill?: APBill;
}

export interface Payment {
  id: number;
  account_id: number;
  account?: Account;
  transaction_date: string;
  amount: number;
  payment_method: string | null;
  reference_code: string | null;
  notes: string | null;
  allocations: PaymentAllocation[];
  org_id: number;
  created_at: string;
  updated_at: string;
}

export interface AllocationInput {
  ar_invoice_id?: number;
  ap_bill_id?: number;
  allocated_amount: number;
  notes?: string;
}

export interface PaymentCreateRequest {
  account_id: number;
  transaction_date: string;
  amount: number;
  payment_method?: string;
  reference_code?: string;
  notes?: string;
  allocations: AllocationInput[];
}

export interface PaymentUpdateRequest {
  notes?: string;
  reference_code?: string;
}

export interface PaymentListParams {
  date_from?: string;
  date_to?: string;
  customer_id?: number;
  account_id?: number;
  has_allocations?: boolean;
  skip?: number;
  limit?: number;
}

export interface PaginatedPaymentsResponse {
  total: number;
  skip: number;
  limit: number;
  items: Payment[];
}

export const paymentsAPI = {
  /**
   * Get list of payments
   * GET /api/v1/payments
   */
  getPayments: async (params?: PaymentListParams): Promise<PaginatedPaymentsResponse> => {
    const response = await apiClient.get<PaginatedPaymentsResponse>('/api/v1/payments', { params });
    return response.data;
  },

  /**
   * Get payment by ID with allocations
   * GET /api/v1/payments/{id}
   */
  getPaymentById: async (id: number): Promise<Payment> => {
    const response = await apiClient.get<Payment>(`/api/v1/payments/${id}`);
    return response.data;
  },

  /**
   * Create payment with allocations
   * POST /api/v1/payments
   */
  createPayment: async (data: PaymentCreateRequest): Promise<Payment> => {
    const response = await apiClient.post<Payment>('/api/v1/payments', data);
    return response.data;
  },

  /**
   * Update payment metadata (notes, reference_code only)
   * PUT /api/v1/payments/{id}
   */
  updatePayment: async (id: number, data: PaymentUpdateRequest): Promise<Payment> => {
    const response = await apiClient.put<Payment>(`/api/v1/payments/${id}`, data);
    return response.data;
  },
};
