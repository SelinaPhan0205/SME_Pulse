/**
 * Auth Hooks - React Query
 * Quản lý authentication state với React Query
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { authAPI } from '../services';
import { getErrorMessage } from '../client';
import type { LoginRequest } from '../types';

/**
 * Hook để login
 * 
 * @example
 * const loginMutation = useLogin();
 * 
 * const handleSubmit = (data) => {
 *   loginMutation.mutate(data, {
 *     onSuccess: () => navigate('/dashboard'),
 *     onError: (error) => alert(error.message),
 *   });
 * };
 */
export function useLogin() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (credentials: LoginRequest) => authAPI.login(credentials),
    onSuccess: (data) => {
      // Lưu token vào localStorage
      localStorage.setItem('token', data.access_token);
      
      // Cache user data vào React Query
      queryClient.setQueryData(['currentUser'], data.user);
      
      // Navigate to dashboard
      navigate('/dashboard');
    },
    onError: (error) => {
      console.error('Login failed:', getErrorMessage(error));
    },
  });
}

/**
 * Hook để get current user
 * 
 * @example
 * const { data: user, isLoading } = useCurrentUser();
 * 
 * if (isLoading) return <Spinner />;
 * return <div>Welcome {user.full_name}</div>;
 */
export function useCurrentUser() {
  return useQuery({
    queryKey: ['currentUser'],
    queryFn: () => authAPI.getCurrentUser(),
    enabled: !!localStorage.getItem('token'), // Chỉ fetch nếu có token
    staleTime: 5 * 60 * 1000, // Cache 5 phút
    retry: false, // Không retry nếu 401
  });
}

/**
 * Hook để change password
 * 
 * @example
 * const changePasswordMutation = useChangePassword();
 * 
 * const handleChangePassword = (data) => {
 *   changePasswordMutation.mutate(data);
 * };
 */
export function useChangePassword() {
  return useMutation({
    mutationFn: (data: { old_password: string; new_password: string }) => 
      authAPI.changePassword(data),
  });
}

/**
 * Hook để logout
 * 
 * @example
 * const logoutMutation = useLogout();
 * 
 * const handleLogout = () => {
 *   logoutMutation.mutate();
 * };
 */
export function useLogout() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => {
      authAPI.logout();
      return Promise.resolve();
    },
    onSuccess: () => {
      // Clear tất cả cache
      queryClient.clear();
      
      // Navigate về landing page
      navigate('/');
    },
  });
}
