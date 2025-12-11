/**
 * Accounts API Service
 * Bank and Cash accounts for payments
 */

import { apiClient } from '../client';

export interface Account {
  id: number;
  name: string;
  type: 'cash' | 'bank';
  account_number: string | null;
  bank_name: string | null;
  is_active: boolean;
  org_id: number;
  created_at: string;
  updated_at: string;
}

export interface AccountCreateRequest {
  name: string;
  type: 'cash' | 'bank';
  account_number?: string;
  bank_name?: string;
}

export interface AccountUpdateRequest {
  name?: string;
  type?: 'cash' | 'bank';
  account_number?: string;
  bank_name?: string;
  is_active?: boolean;
}

export interface PaginatedAccountsResponse {
  total: number;
  skip: number;
  limit: number;
  items: Account[];
}

export const accountsAPI = {
  /**
   * Get list of accounts
   * GET /api/v1/accounts
   */
  getAccounts: async (params?: { skip?: number; limit?: number }): Promise<PaginatedAccountsResponse> => {
    const response = await apiClient.get<PaginatedAccountsResponse>('/api/v1/accounts', { params });
    return response.data;
  },

  /**
   * Get account by ID
   * GET /api/v1/accounts/{id}
   */
  getAccountById: async (id: number): Promise<Account> => {
    const response = await apiClient.get<Account>(`/api/v1/accounts/${id}`);
    return response.data;
  },

  /**
   * Create new account
   * POST /api/v1/accounts
   */
  createAccount: async (data: AccountCreateRequest): Promise<Account> => {
    const response = await apiClient.post<Account>('/api/v1/accounts', data);
    return response.data;
  },

  /**
   * Update account
   * PUT /api/v1/accounts/{id}
   */
  updateAccount: async (id: number, data: AccountUpdateRequest): Promise<Account> => {
    const response = await apiClient.put<Account>(`/api/v1/accounts/${id}`, data);
    return response.data;
  },

  /**
   * Delete account
   * DELETE /api/v1/accounts/{id}
   */
  deleteAccount: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/v1/accounts/${id}`);
  },
};
