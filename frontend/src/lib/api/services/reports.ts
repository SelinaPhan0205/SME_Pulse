/**
 * Reports & Export Jobs API Service
 * 
 * Backend API:
 * - POST /api/v1/analytics/reports/export?report_type=ar_aging|ap_aging|cashflow&format=xlsx
 * - GET /api/v1/analytics/reports/jobs/{job_id}
 */

import { apiClient } from '../client';

export interface ReportTemplate {
  slug: string;
  name: string;
  description: string;
  supported_formats: string[];
}

// Match backend ExportJobResponse schema
export interface ExportJob {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  report_type: string;
  format: string;
  file_url: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

// Backend only supports these report types
export type BackendReportType = 'ar_aging' | 'ap_aging' | 'cashflow';

export interface ExportJobCreateRequest {
  report_type: BackendReportType;
  format?: 'xlsx';
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
   * Create export job - sends as query params per backend API
   * POST /api/v1/analytics/reports/export?report_type=...&format=xlsx
   */
  createExportJob: async (data: ExportJobCreateRequest): Promise<ExportJob> => {
    const params = new URLSearchParams();
    params.append('report_type', data.report_type);
    params.append('format', data.format || 'xlsx');
    
    const response = await apiClient.post<ExportJob>(
      `/api/v1/analytics/reports/export?${params.toString()}`
    );
    return response.data;
  },

  /**
   * Get export job status by job_id
   * GET /api/v1/analytics/reports/jobs/{job_id}
   */
  getExportJobStatus: async (jobId: string): Promise<ExportJob> => {
    const response = await apiClient.get<ExportJob>(`/api/v1/analytics/reports/jobs/${jobId}`);
    return response.data;
  },

  /**
   * Get export jobs history (if backend supports it)
   * GET /api/v1/analytics/reports/export-jobs
   */
  getExportJobs: async (params?: { skip?: number; limit?: number }): Promise<PaginatedExportJobsResponse> => {
    const response = await apiClient.get<PaginatedExportJobsResponse>('/api/v1/analytics/reports/export-jobs', { params });
    return response.data;
  },

  /**
   * Get export job by ID (legacy)
   * @deprecated Use getExportJobStatus instead
   */
  getExportJobById: async (id: number): Promise<ExportJob> => {
    const response = await apiClient.get<ExportJob>(`/api/v1/analytics/reports/export-jobs/${id}`);
    return response.data;
  },
};
