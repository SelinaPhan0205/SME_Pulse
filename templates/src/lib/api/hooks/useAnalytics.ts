/**
 * Analytics Hooks - React Query
 * Fetch analytics data với React Query
 */

import { useQuery } from '@tanstack/react-query';
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
    queryFn: () => analyticsAPI.getDashboardSummary(),
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
    queryFn: () => analyticsAPI.getRevenueForecast(params),
    staleTime: 30 * 60 * 1000, // Cache 30 phút (forecast ít thay đổi)
  });
}

/**
 * Hook để get revenue anomalies
 */
export function useRevenueAnomalies(params?: DateRangeParams) {
  return useQuery({
    queryKey: ['analytics', 'revenue-anomalies', params],
    queryFn: () => analyticsAPI.getRevenueAnomalies(params),
    staleTime: 5 * 60 * 1000,
  });
}
