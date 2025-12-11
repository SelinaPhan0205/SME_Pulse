/**
 * Protected Route Component
 * 
 * Wraps routes to enforce authentication and role-based access control.
 * Redirects to login if not authenticated, or shows 403 if unauthorized.
 */

import { Navigate, useLocation } from 'react-router-dom';
import { hasMenuAccess, getUserRoles } from '../lib/permissions';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredPermission?: string; // Menu ID that maps to permission
}

/**
 * Check if user is authenticated (has valid token)
 */
function isAuthenticated(): boolean {
  const token = localStorage.getItem('token');
  return !!token;
}

/**
 * ProtectedRoute component
 * 
 * Usage:
 * <ProtectedRoute requiredPermission="dashboard">
 *   <Dashboard />
 * </ProtectedRoute>
 */
export function ProtectedRoute({ children, requiredPermission }: ProtectedRouteProps) {
  const location = useLocation();
  
  // Check authentication first
  if (!isAuthenticated()) {
    // Redirect to login, preserving the intended destination
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  
  // If no specific permission required, just check authentication
  if (!requiredPermission) {
    return <>{children}</>;
  }
  
  // Check role-based permission
  const userRoles = getUserRoles();
  if (!hasMenuAccess(userRoles, requiredPermission)) {
    // User doesn't have permission - show 403 or redirect
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <h1 className="text-6xl font-bold text-gray-300 mb-4">403</h1>
          <h2 className="text-2xl font-semibold text-gray-700 mb-2">Không có quyền truy cập</h2>
          <p className="text-gray-500 mb-6">
            Bạn không có quyền truy cập trang này. Vui lòng liên hệ quản trị viên.
          </p>
          <button
            onClick={() => window.history.back()}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          >
            Quay lại
          </button>
        </div>
      </div>
    );
  }
  
  return <>{children}</>;
}

/**
 * Hook to check if current user has permission
 */
export function useHasPermission(permissionId: string): boolean {
  const userRoles = getUserRoles();
  return hasMenuAccess(userRoles, permissionId);
}
