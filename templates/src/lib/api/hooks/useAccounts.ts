/**
 * Accounts React Query Hooks
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { accountsAPI, type Account, type AccountCreateRequest, type AccountUpdateRequest } from '../services/accounts';

const ACCOUNTS_KEY = 'accounts';

export const useAccounts = (params?: { skip?: number; limit?: number }) => {
  return useQuery({
    queryKey: [ACCOUNTS_KEY, params],
    queryFn: () => accountsAPI.getAccounts(params),
  });
};

export const useAccount = (id: number) => {
  return useQuery({
    queryKey: [ACCOUNTS_KEY, id],
    queryFn: () => accountsAPI.getAccountById(id),
    enabled: !!id,
  });
};

export const useCreateAccount = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AccountCreateRequest) => accountsAPI.createAccount(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [ACCOUNTS_KEY] });
    },
  });
};

export const useUpdateAccount = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: AccountUpdateRequest }) =>
      accountsAPI.updateAccount(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [ACCOUNTS_KEY] });
      queryClient.invalidateQueries({ queryKey: [ACCOUNTS_KEY, variables.id] });
    },
  });
};

export const useDeleteAccount = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => accountsAPI.deleteAccount(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [ACCOUNTS_KEY] });
    },
  });
};
