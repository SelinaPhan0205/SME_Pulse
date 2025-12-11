/**
 * API Module - Central Export
 * Import API client, services, hooks, types từ đây
 */

// Client
export { apiClient, getErrorMessage } from './client';

// Services - Dùng khi cần gọi API trực tiếp (không qua React Query)
export { authAPI, customersAPI, suppliersAPI, analyticsAPI } from './services';

// Hooks - Dùng trong React components
export * from './hooks';

// Types
export type * from './types';
