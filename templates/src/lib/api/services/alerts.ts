/**
 * Alerts API Service
 * System notifications and anomaly alerts
 */

import { apiClient } from '../client';

export interface Alert {
  id: number;
  kind: string;
  title: string | null;
  message: string | null;
  severity: 'info' | 'warning' | 'error' | 'critical';
  status: 'new' | 'read' | 'dismissed';
  alert_metadata: Record<string, any> | null;
  org_id: number;
  created_at: string;
  updated_at: string;
}

export interface AlertListParams {
  kind?: string;
  severity?: string;
  status?: string;
  skip?: number;
  limit?: number;
}

export interface PaginatedAlertsResponse {
  total: number;
  skip: number;
  limit: number;
  items: Alert[];
}

export const alertsAPI = {
  /**
   * Get list of alerts
   * GET /api/v1/alerts
   */
  getAlerts: async (params?: AlertListParams): Promise<PaginatedAlertsResponse> => {
    const response = await apiClient.get<PaginatedAlertsResponse>('/api/v1/alerts', { params });
    return response.data;
  },

  /**
   * Get alert by ID
   * GET /api/v1/alerts/{id}
   */
  getAlertById: async (id: number): Promise<Alert> => {
    const response = await apiClient.get<Alert>(`/api/v1/alerts/${id}`);
    return response.data;
  },

  /**
   * Mark alert as read
   * PUT /api/v1/alerts/{id}
   */
  markAlertRead: async (id: number): Promise<Alert> => {
    const response = await apiClient.put<Alert>(`/api/v1/alerts/${id}`, {
      status: 'read',
    });
    return response.data;
  },

  /**
   * Dismiss alert
   * PUT /api/v1/alerts/{id}
   */
  dismissAlert: async (id: number): Promise<Alert> => {
    const response = await apiClient.put<Alert>(`/api/v1/alerts/${id}`, {
      status: 'dismissed',
    });
    return response.data;
  },
};
