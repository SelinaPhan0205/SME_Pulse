/**
 * Settings React Query Hooks
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { settingsAPI, type AISettings } from '../services/settings';

const SETTINGS_KEY = 'settings';

export const useAISettings = () => {
  return useQuery({
    queryKey: [SETTINGS_KEY, 'ai'],
    queryFn: () => settingsAPI.getAISystemSettings(),
  });
};

export const useUpdateAISettings = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<AISettings>) => settingsAPI.updateAISystemSettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SETTINGS_KEY, 'ai'] });
    },
  });
};
