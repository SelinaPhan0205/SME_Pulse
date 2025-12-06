/**
 * API Client Configuration
 * Axios instance với interceptors cho authentication và error handling
 */

import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

// Base URL từ environment variable hoặc default
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Tạo axios instance
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - Tự động thêm token vào header
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - Xử lý lỗi global
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail: string; error_code?: string }>) => {
    // Xử lý các lỗi phổ biến
    if (error.response) {
      const { status, data } = error.response;

      switch (status) {
        case 401:
          // Token hết hạn hoặc không hợp lệ -> redirect về login
          localStorage.removeItem('token');
          if (window.location.pathname !== '/login') {
            window.location.href = '/login';
          }
          break;

        case 403:
          // Không có quyền truy cập
          console.error('Access denied:', data.detail);
          break;

        case 404:
          console.error('Resource not found:', data.detail);
          break;

        case 422:
          // Validation error
          console.error('Validation error:', data);
          break;

        case 500:
          console.error('Server error:', data.detail);
          break;

        default:
          console.error('API error:', data.detail || error.message);
      }
    } else if (error.request) {
      // Request được gửi nhưng không nhận được response
      console.error('Network error: No response from server');
    } else {
      // Lỗi khi setup request
      console.error('Request error:', error.message);
    }

    return Promise.reject(error);
  }
);

// Helper function để extract error message
export const getErrorMessage = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.detail || error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'An unexpected error occurred';
};
