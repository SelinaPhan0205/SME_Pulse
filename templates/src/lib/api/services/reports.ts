/**
 * Reports & Export Jobs API Service
 */

import { apiClient } from '../client';

export interface ReportTemplate {
  slug: string;
  name: string;
  description: string;
  supported_formats: string[];
}

export interface ExportJob {
  id: number;
  job_id: string;
  job_type: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  file_url: string | null;
  error_log: string | null;
  job_metadata: Record<string, any> | null;
  org_id: number;
  created_at: string;
  updated_at: string;
}

export interface ExportJobCreateRequest {
  report_type: string;
  format: 'xlsx' | 'pdf';
  filters?: Record<string, any>;
}

export interface PaginatedExportJobsResponse {
  total: number;
  skip: number;
  limit: number;
  items: ExportJob[];
}

export const reportsAPI = {
  /**
   * Get available report templates
   * GET /api/v1/analytics/reports/templates
   */
  getReportTemplates: async (): Promise<ReportTemplate[]> => {
    const response = await apiClient.get<ReportTemplate[]>('/api/v1/analytics/reports/templates');
    return response.data;
  },

  /**
   * Create export job
   * POST /api/v1/analytics/reports/export
   */
  createExportJob: async (data: ExportJobCreateRequest): Promise<ExportJob> => {
    const response = await apiClient.post<ExportJob>('/api/v1/analytics/reports/export', data);
    return response.data;
  },

  /**
   * Get export jobs history
   * GET /api/v1/analytics/reports/export-jobs
   */
  getExportJobs: async (params?: { skip?: number; limit?: number }): Promise<PaginatedExportJobsResponse> => {
    const response = await apiClient.get<PaginatedExportJobsResponse>('/api/v1/analytics/reports/export-jobs', { params });
    return response.data;
  },

  /**
   * Get export job by ID
   * GET /api/v1/analytics/reports/export-jobs/{id}
   */
  getExportJobById: async (id: number): Promise<ExportJob> => {
    const response = await apiClient.get<ExportJob>(`/api/v1/analytics/reports/export-jobs/${id}`);
    return response.data;
  },
};
