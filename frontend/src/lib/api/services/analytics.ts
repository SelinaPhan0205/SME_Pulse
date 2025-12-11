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
  ForecastResponse,
  AnomalyResponse,
  MetabaseTokenResponse,
  ReconciliationKPI,
  ReconciliationAutoMatchResponse,
  ReconciliationActionResponse,
  PendingReconciliationsResponse,
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
   * GET /api/v1/analytics/aging/ar
   */
  getARAging: async (): Promise<ARAgingResponse> => {
    const response = await apiClient.get<ARAgingResponse>('/api/v1/analytics/aging/ar');
    return response.data;
  },

  /**
   * Get AP Aging - Phân tích công nợ phải trả
   * GET /api/v1/analytics/aging/ap
   */
  getAPAging: async (): Promise<APAgingResponse> => {
    const response = await apiClient.get<APAgingResponse>('/api/v1/analytics/aging/ap');
    return response.data;
  },

  /**
   * Get daily revenue - Doanh thu theo ngày
   * GET /api/v1/analytics/kpi/daily-revenue
   */
  getDailyRevenue: async (params?: DateRangeParams): Promise<DailyRevenueResponse> => {
    const response = await apiClient.get<DailyRevenueResponse>('/api/v1/analytics/kpi/daily-revenue', {
      params,
    });
    return response.data;
  },

  /**
   * Get payment success rate - Tỷ lệ thanh toán thành công
   * GET /api/v1/analytics/kpi/payment-success-rate
   */
  getPaymentSuccessRate: async (params?: DateRangeParams): Promise<PaymentSuccessRateResponse> => {
    const response = await apiClient.get<PaymentSuccessRateResponse>('/api/v1/analytics/kpi/payment-success-rate', {
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
   * Get revenue forecast data (UC09 - Prophet Cashflow Forecasting)
   * GET /api/v1/analytics/forecast/revenue
   * Query params: start_date (YYYY-MM-DD), end_date (YYYY-MM-DD)
   */
  getRevenueForecast: async (params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<ForecastResponse> => {
    const response = await apiClient.get<ForecastResponse>('/api/v1/analytics/forecast/revenue', { params });
    return response.data;
  },

  /**
   * Get revenue anomalies (UC10 - Isolation Forest Anomaly Detection)
   * GET /api/v1/analytics/anomalies/revenue
   * Query params: start_date, end_date, severity (CRITICAL|HIGH|MEDIUM|LOW)
   */
  getRevenueAnomalies: async (params?: {
    start_date?: string;
    end_date?: string;
    severity?: string;
  }): Promise<AnomalyResponse> => {
    const response = await apiClient.get<AnomalyResponse>('/api/v1/analytics/anomalies/revenue', { params });
    return response.data;
  },

  // ============================================================
  // RECONCILIATION ACTION APIS
  // ============================================================

  /**
   * Auto-match bank transactions with system payments
   * POST /api/v1/analytics/reconciliation/auto-match
   */
  autoMatchReconciliation: async (params?: {
    reconcile_date?: string;
    tolerance?: number;
  }): Promise<ReconciliationAutoMatchResponse> => {
    const response = await apiClient.post<ReconciliationAutoMatchResponse>(
      '/api/v1/analytics/reconciliation/auto-match',
      null,
      { params }
    );
    return response.data;
  },

  /**
   * Confirm a reconciliation match
   * POST /api/v1/analytics/reconciliation/{transaction_id}/confirm
   */
  confirmReconciliation: async (
    transactionId: number,
    data: { bank_transaction_id: number; payment_id: number; notes?: string }
  ): Promise<ReconciliationActionResponse> => {
    const response = await apiClient.post<ReconciliationActionResponse>(
      `/api/v1/analytics/reconciliation/${transactionId}/confirm`,
      data
    );
    return response.data;
  },

  /**
   * Reject a reconciliation match suggestion
   * POST /api/v1/analytics/reconciliation/{transaction_id}/reject
   */
  rejectReconciliation: async (transactionId: number): Promise<ReconciliationActionResponse> => {
    const response = await apiClient.post<ReconciliationActionResponse>(
      `/api/v1/analytics/reconciliation/${transactionId}/reject`
    );
    return response.data;
  },

  /**
   * Get pending reconciliation transactions
   * GET /api/v1/analytics/reconciliation/pending
   */
  getPendingReconciliations: async (params?: {
    reconcile_date?: string;
  }): Promise<PendingReconciliationsResponse> => {
    const response = await apiClient.get<PendingReconciliationsResponse>(
      '/api/v1/analytics/reconciliation/pending',
      { params }
    );
    return response.data;
  },
};

// Note: Types moved to ../types.ts for centralized type definitions
