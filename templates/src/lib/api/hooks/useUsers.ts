/**
 * Users React Query Hooks
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { usersAPI, type User, type UserCreateRequest, type UserUpdateRequest, type UserListParams } from '../services/users';

const USERS_KEY = 'users';

export const useUsers = (params?: UserListParams) => {
  return useQuery({
    queryKey: [USERS_KEY, params],
    queryFn: () => usersAPI.getUsers(params),
  });
};

export const useUser = (id: number) => {
  return useQuery({
    queryKey: [USERS_KEY, id],
    queryFn: () => usersAPI.getUserById(id),
    enabled: !!id,
  });
};

export const useCreateUser = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: UserCreateRequest) => usersAPI.createUser(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [USERS_KEY] });
    },
  });
};

export const useUpdateUser = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: UserUpdateRequest }) =>
      usersAPI.updateUser(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [USERS_KEY] });
      queryClient.invalidateQueries({ queryKey: [USERS_KEY, variables.id] });
    },
  });
};

export const useDeleteUser = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => usersAPI.deleteUser(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [USERS_KEY] });
    },
  });
};

export const useResetUserPassword = () => {
  return useMutation({
    mutationFn: (id: number) => usersAPI.resetUserPassword(id),
  });
};
