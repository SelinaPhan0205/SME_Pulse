/**
 * Reports & Export Jobs React Query Hooks
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  reportsAPI,
  type ReportTemplate,
  type ExportJob,
  type ExportJobCreateRequest,
} from '../services/reports';

const REPORTS_KEY = 'reports';
const EXPORT_JOBS_KEY = 'export-jobs';

export const useReportTemplates = () => {
  return useQuery({
    queryKey: [REPORTS_KEY, 'templates'],
    queryFn: () => reportsAPI.getReportTemplates(),
  });
};

export const useExportJobs = (params?: { skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: [EXPORT_JOBS_KEY, params],
    queryFn: () => reportsAPI.getExportJobs(params),
  });
};

export const useExportJob = (id: number) => {
  return useQuery({
    queryKey: [EXPORT_JOBS_KEY, id],
    queryFn: () => reportsAPI.getExportJobById(id),
    enabled: !!id,
    refetchInterval: (query) => {
      // Auto-refetch every 2s if status is pending or running
      const data = query.state.data;
      if (data && (data.status === 'pending' || data.status === 'running')) {
        return 2000;
      }
      return false;
    },
  });
};

export const useCreateExportJob = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ExportJobCreateRequest) => reportsAPI.createExportJob(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [EXPORT_JOBS_KEY] });
    },
  });
};
