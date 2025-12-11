/**
 * Analytics Hooks - React Query
 * Fetch analytics data với React Query
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { analyticsAPI } from '../services';
import type { DateRangeParams } from '../types';

/**
 * Hook để get dashboard summary
 * 
 * @example
 * const { data, isLoading, error } = useDashboardSummary();
 * 
 * if (isLoading) return <Skeleton />;
 * 
 * return (
 *   <div>
 *     <KPICard title="Total Revenue" value={data.total_revenue} />
 *     <KPICard title="Receivables" value={data.total_receivables} />
 *   </div>
 * );
 */
export function useDashboardSummary() {
  return useQuery({
    queryKey: ['analytics', 'dashboard-summary'],
    queryFn: async () => {
      console.log('🔵 [API CALL] Fetching dashboard summary...');
      const data = await analyticsAPI.getDashboardSummary();
      console.log('✅ [REAL DATA] Dashboard Summary:', {
        total_revenue: data.total_revenue,
        total_receivables: data.total_receivables,
        dso: data.dso,
        source: 'BACKEND API /api/v1/analytics/summary'
      });
      return data;
    },
    staleTime: 60 * 1000, // Cache 1 phút
    refetchInterval: 5 * 60 * 1000, // Auto refetch mỗi 5 phút
  });
}

/**
 * Hook để get AR Aging
 */
export function useARAging() {
  return useQuery({
    queryKey: ['analytics', 'ar-aging'],
    queryFn: () => analyticsAPI.getARAging(),
    staleTime: 60 * 1000,
  });
}

/**
 * Hook để get AP Aging
 */
export function useAPAging() {
  return useQuery({
    queryKey: ['analytics', 'ap-aging'],
    queryFn: () => analyticsAPI.getAPAging(),
    staleTime: 60 * 1000,
  });
}

/**
 * Hook để get daily revenue với date range
 * 
 * @example
 * const { data } = useDailyRevenue({
 *   start_date: '2024-01-01',
 *   end_date: '2024-12-31',
 * });
 */
export function useDailyRevenue(params?: DateRangeParams) {
  return useQuery({
    queryKey: ['analytics', 'daily-revenue', params],
    queryFn: () => analyticsAPI.getDailyRevenue(params),
    staleTime: 5 * 60 * 1000, // Cache 5 phút
  });
}

/**
 * Hook để get payment success rate
 */
export function usePaymentSuccessRate(params?: DateRangeParams) {
  return useQuery({
    queryKey: ['analytics', 'payment-success-rate', params],
    queryFn: () => analyticsAPI.getPaymentSuccessRate(params),
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Hook để get reconciliation KPI
 */
export function useReconciliationKPI() {
  return useQuery({
    queryKey: ['analytics', 'reconciliation-kpi'],
    queryFn: () => analyticsAPI.getReconciliationKPI(),
    staleTime: 60 * 1000,
  });
}

/**
 * Hook để get Metabase embed token
 * 
 * @example
 * const { data } = useMetabaseToken({ resource_id: 2, resource_type: 'dashboard' });
 */
export function useMetabaseToken(params: { resource_id: number; resource_type: 'dashboard' | 'question' }) {
  return useQuery({
    queryKey: ['analytics', 'metabase-token', params],
    queryFn: () => analyticsAPI.getMetabaseToken(params),
    staleTime: 10 * 60 * 1000, // Cache 10 phút
    enabled: !!params.resource_id,
  });
}

/**
 * Hook để get revenue forecast
 */
export function useRevenueForecast(params?: DateRangeParams) {
  return useQuery({
    queryKey: ['analytics', 'revenue-forecast', params],
    queryFn: async () => {
      console.log('🔵 [API CALL] Fetching revenue forecast...', params);
      const data = await analyticsAPI.getRevenueForecast(params);
      console.log('✅ [REAL DATA] Revenue Forecast:', {
        model: data.model_name,
        total_days: data.total_days,
        first_forecast: data.data[0],
        last_forecast: data.data[data.data.length - 1],
        source: 'BACKEND API /api/v1/analytics/forecast/revenue',
        timestamp: data.timestamp
      });
      return data;
    },
    staleTime: 30 * 60 * 1000, // Cache 30 phút (forecast ít thay đổi)
  });
}

/**
 * Hook để get revenue anomalies
 */
export function useRevenueAnomalies(params?: DateRangeParams) {
  return useQuery({
    queryKey: ['analytics', 'revenue-anomalies', params],
    queryFn: async () => {
      console.log('🔵 [API CALL] Fetching revenue anomalies...', params);
      const data = await analyticsAPI.getRevenueAnomalies(params);
      console.log('✅ [REAL DATA] Revenue Anomalies:', {
        total_anomalies: data.total_anomalies,
        severity_breakdown: data.severity_breakdown,
        sample_anomaly: data.data[0],
        source: 'BACKEND API /api/v1/analytics/anomalies/revenue',
        timestamp: data.timestamp
      });
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
}

// ============================================================
// RECONCILIATION ACTION HOOKS
// ============================================================

/**
 * Hook để auto-match reconciliation
 */
export function useAutoMatchReconciliation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params?: { reconcile_date?: string; tolerance?: number }) =>
      analyticsAPI.autoMatchReconciliation(params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['analytics', 'reconciliation'] });
    },
  });
}

/**
 * Hook để confirm reconciliation match
 */
export function useConfirmReconciliation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ transactionId, data }: {
      transactionId: number;
      data: { bank_transaction_id: number; payment_id: number; notes?: string };
    }) => analyticsAPI.confirmReconciliation(transactionId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['analytics', 'reconciliation'] });
    },
  });
}

/**
 * Hook để reject reconciliation match
 */
export function useRejectReconciliation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (transactionId: number) => analyticsAPI.rejectReconciliation(transactionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['analytics', 'reconciliation'] });
    },
  });
}

/**
 * Hook để get pending reconciliations
 */
export function usePendingReconciliations(params?: { reconcile_date?: string }) {
  return useQuery({
    queryKey: ['analytics', 'reconciliation', 'pending', params],
    queryFn: () => analyticsAPI.getPendingReconciliations(params),
    staleTime: 60 * 1000,
  });
}
