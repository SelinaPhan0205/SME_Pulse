/**
 * Users API Service
 * User Management - CRUD operations for users
 */

import { apiClient } from '../client';

export interface User {
  id: number;
  email: string;
  full_name: string | null;
  status: string;
  org_id: number;
  roles: string[];
  created_at: string;
  updated_at: string;
  last_login?: string;
}

export interface UserCreateRequest {
  email: string;
  full_name?: string;
  password: string;
  role: 'owner' | 'admin' | 'accountant' | 'cashier';
}

export interface UserUpdateRequest {
  full_name?: string;
  status?: 'active' | 'inactive';
  role?: 'owner' | 'admin' | 'accountant' | 'cashier';
}

export interface UserListParams {
  search?: string;
  role?: string;
  status?: string;
  skip?: number;
  limit?: number;
}

export interface PaginatedUsersResponse {
  total: number;
  skip: number;
  limit: number;
  items: User[];
}

export const usersAPI = {
  /**
   * Get list of users with filters
   * GET /api/v1/users
   */
  getUsers: async (params?: UserListParams): Promise<PaginatedUsersResponse> => {
    const response = await apiClient.get<PaginatedUsersResponse>('/api/v1/users', { params });
    return response.data;
  },

  /**
   * Get user by ID
   * GET /api/v1/users/{id}
   */
  getUserById: async (id: number): Promise<User> => {
    const response = await apiClient.get<User>(`/api/v1/users/${id}`);
    return response.data;
  },

  /**
   * Create new user
   * POST /api/v1/users/
   */
  createUser: async (data: UserCreateRequest): Promise<User> => {
    const response = await apiClient.post<User>('/api/v1/users/', data);
    return response.data;
  },

  /**
   * Update user
   * PUT /api/v1/users/{id}
   */
  updateUser: async (id: number, data: UserUpdateRequest): Promise<User> => {
    const response = await apiClient.put<User>(`/api/v1/users/${id}`, data);
    return response.data;
  },

  /**
   * Delete/Deactivate user (soft delete)
   * DELETE /api/v1/users/{id}
   */
  deleteUser: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/v1/users/${id}`);
  },

  /**
   * Reset user password (Admin only)
   * POST /api/v1/users/{id}/reset-password
   */
  resetUserPassword: async (id: number): Promise<{ temporary_password: string }> => {
    const response = await apiClient.post<{ temporary_password: string }>(
      `/api/v1/users/${id}/reset-password`
    );
    return response.data;
  },
};
