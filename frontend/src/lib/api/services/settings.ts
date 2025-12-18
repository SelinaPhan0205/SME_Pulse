/**
 * Settings API Service
 * AI/System settings management
 */

import { apiClient } from '../client';

export interface AISettings {
  forecast_window: number;
  forecast_confidence: number;
  seasonality_mode: string;
  anomaly_threshold: number;
  min_anomaly_amount: number;
  alert_severity: string;
  job_schedule: {
    frequency: string;
    time: string;
    auto_retry: boolean;
  };
}

export interface SettingResponse {
  id: number;
  key: string;
  value_json: Record<string, any>;
  description: string | null;
  org_id: number;
  created_at: string;
  updated_at: string;
}

export interface SettingUpdateRequest {
  value_json: Record<string, any>;
}

export const settingsAPI = {
  /**
   * Get AI system settings
   * GET /api/v1/settings/ai
   */
  getAISystemSettings: async (): Promise<AISettings> => {
    const response = await apiClient.get<SettingResponse>('/api/v1/settings/ai');
    return response.data.value_json as AISettings;
  },

  /**
   * Update AI system settings
   * PUT /api/v1/settings/ai
   */
  updateAISystemSettings: async (data: Partial<AISettings>): Promise<AISettings> => {
    const response = await apiClient.put<SettingResponse>('/api/v1/settings/ai', {
      value_json: data,
    });
    return response.data.value_json as AISettings;
  },
};
