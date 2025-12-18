import { useQuery } from '@tanstack/react-query';
import { getCashflowForecast, getAnomalyResult } from '../services/metabase';

export function useCashflowForecast() {
  return useQuery({
    queryKey: ['cashflow-forecast'],
    queryFn: getCashflowForecast,
    staleTime: 1000 * 60 * 5,
  });
}

export function useAnomalyResult() {
  return useQuery({
    queryKey: ['anomaly-result'],
    queryFn: getAnomalyResult,
    staleTime: 1000 * 60 * 5,
  });
}
