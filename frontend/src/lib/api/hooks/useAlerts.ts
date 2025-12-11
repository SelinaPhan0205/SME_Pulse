/**
 * Alerts React Query Hooks
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { alertsAPI, type Alert, type AlertListParams } from '../services/alerts';

const ALERTS_KEY = 'alerts';

export const useAlerts = (params?: AlertListParams) => {
  return useQuery({
    queryKey: [ALERTS_KEY, params],
    queryFn: () => alertsAPI.getAlerts(params),
  });
};

export const useAlert = (id: number) => {
  return useQuery({
    queryKey: [ALERTS_KEY, id],
    queryFn: () => alertsAPI.getAlertById(id),
    enabled: !!id,
  });
};

export const useMarkAlertRead = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => alertsAPI.markAlertRead(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: [ALERTS_KEY] });
      queryClient.invalidateQueries({ queryKey: [ALERTS_KEY, id] });
    },
  });
};

export const useDismissAlert = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => alertsAPI.dismissAlert(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: [ALERTS_KEY] });
      queryClient.invalidateQueries({ queryKey: [ALERTS_KEY, id] });
    },
  });
};
