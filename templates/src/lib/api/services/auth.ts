/**
 * Auth API Service
 * Xử lý authentication: login, logout, get current user
 */

import { apiClient } from '../client';
import type { LoginRequest, LoginResponse, UserResponse } from '../types';

export interface ChangePasswordRequest {
  old_password: string;
  new_password: string;
}

export const authAPI = {
  /**
   * Login - Đăng nhập
   * POST /auth/login
   */
  login: async (credentials: LoginRequest): Promise<LoginResponse> => {
    const response = await apiClient.post<LoginResponse>('/auth/login', credentials);
    return response.data;
  },

  /**
   * Get current user info
   * GET /auth/me
   */
  getCurrentUser: async (): Promise<UserResponse> => {
    const response = await apiClient.get<UserResponse>('/auth/me');
    return response.data;
  },

  /**
   * Change password
   * POST /api/v1/auth/change-password
   */
  changePassword: async (data: ChangePasswordRequest): Promise<void> => {
    await apiClient.post('/api/v1/auth/change-password', data);
  },

  /**
   * Logout - Xóa token khỏi localStorage
   */
  logout: () => {
    localStorage.removeItem('token');
  },
};
