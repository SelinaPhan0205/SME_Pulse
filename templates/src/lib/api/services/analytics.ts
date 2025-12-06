/**
 * Analytics API Service
 * Lấy dữ liệu analytics, KPIs, reports
 */

import { apiClient } from '../client';
import type {
  DashboardSummary,
  ARAgingResponse,
  APAgingResponse,
  DailyRevenueResponse,
  PaymentSuccessRateResponse,
  DateRangeParams,
} from '../types';

export const analyticsAPI = {
  /**
   * Get dashboard summary - Lấy tổng quan KPIs
   * GET /api/v1/analytics/summary
   */
  getDashboardSummary: async (): Promise<DashboardSummary> => {
    const response = await apiClient.get<DashboardSummary>('/api/v1/analytics/summary');
    return response.data;
  },

  /**
   * Get AR Aging - Phân tích công nợ phải thu
   * GET /api/v1/analytics/ar-aging
   */
  getARAging: async (): Promise<ARAgingResponse> => {
    const response = await apiClient.get<ARAgingResponse>('/api/v1/analytics/ar-aging');
    return response.data;
  },

  /**
   * Get AP Aging - Phân tích công nợ phải trả
   * GET /api/v1/analytics/ap-aging
   */
  getAPAging: async (): Promise<APAgingResponse> => {
    const response = await apiClient.get<APAgingResponse>('/api/v1/analytics/ap-aging');
    return response.data;
  },

  /**
   * Get daily revenue - Doanh thu theo ngày
   * GET /api/v1/analytics/daily-revenue
   */
  getDailyRevenue: async (params?: DateRangeParams): Promise<DailyRevenueResponse> => {
    const response = await apiClient.get<DailyRevenueResponse>('/api/v1/analytics/daily-revenue', {
      params,
    });
    return response.data;
  },

  /**
   * Get payment success rate - Tỷ lệ thanh toán thành công
   * GET /api/v1/analytics/payment-success-rate
   */
  getPaymentSuccessRate: async (params?: DateRangeParams): Promise<PaymentSuccessRateResponse> => {
    const response = await apiClient.get<PaymentSuccessRateResponse>('/api/v1/analytics/payment-success-rate', {
      params,
    });
    return response.data;
  },

  /**
   * Get reconciliation KPI
   * GET /api/v1/analytics/kpi/reconciliation
   */
  getReconciliationKPI: async (): Promise<ReconciliationKPI> => {
    const response = await apiClient.get<ReconciliationKPI>('/api/v1/analytics/kpi/reconciliation');
    return response.data;
  },

  /**
   * Get Metabase embed token for dashboards
   * GET /api/v1/analytics/metabase-token
   */
  getMetabaseToken: async (params: { resource_id: number; resource_type: 'dashboard' | 'question' }): Promise<MetabaseTokenResponse> => {
    const response = await apiClient.get<MetabaseTokenResponse>('/api/v1/analytics/metabase-token', { params });
    return response.data;
  },

  /**
   * Get revenue forecast data
   * GET /api/v1/analytics/forecast/revenue
   */
  getRevenueForecast: async (params?: DateRangeParams): Promise<ForecastResponse> => {
    const response = await apiClient.get<ForecastResponse>('/api/v1/analytics/forecast/revenue', { params });
    return response.data;
  },

  /**
   * Get revenue anomalies
   * GET /api/v1/analytics/anomalies/revenue
   */
  getRevenueAnomalies: async (params?: DateRangeParams): Promise<AnomalyResponse> => {
    const response = await apiClient.get<AnomalyResponse>('/api/v1/analytics/anomalies/revenue', { params });
    return response.data;
  },
};

// Extended types for new analytics endpoints
export interface ReconciliationKPI {
  total_transactions: number;
  matched_transactions: number;
  pending_transactions: number;
  matched_rate: number;
}

export interface MetabaseTokenResponse {
  embed_url: string;
}

export interface ForecastPoint {
  date: string;
  actual: number | null;
  forecast: number;
  lower_bound: number;
  upper_bound: number;
}

export interface ForecastResponse {
  data: ForecastPoint[];
}

export interface AnomalyPoint {
  date: string;
  amount: number;
  expected: number;
  deviation: number;
  severity: 'low' | 'medium' | 'high';
}

export interface AnomalyResponse {
  data: AnomalyPoint[];
};
