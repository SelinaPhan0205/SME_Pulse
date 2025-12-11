import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Dashboard } from './components/Dashboard';
import { Forecast } from './components/Forecast';
import { AnomalyDetection } from './components/AnomalyDetection';
import { Reports } from './components/Reports';
import { Payments } from './components/Payments';
import { AccountsReceivable } from './components/AccountsReceivable';
import { AccountsPayable } from './components/AccountsPayable';
import { UserManagement } from './components/UserManagement';
import { Settings } from './components/Settings';
import { APITestPage } from './components/APITestPage';
import LandingPage from './components/LandingPage';
import Login from './components/Login';
import DashboardLayout from './pages/DashboardLayout';
import { ProtectedRoute } from './components/ProtectedRoute';
import { QueryProvider } from './providers/QueryProvider';
import { Toaster } from './components/ui/sonner';
import { DevAPIMonitor } from './components/DevAPIMonitor';

export default function App() {
  return (
    <QueryProvider>
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<Login />} />
          
          {/* API Test Route (Development only) */}
          <Route path="/api-test" element={<APITestPage />} />
          
          {/* Protected dashboard routes with role-based access control */}
          <Route path="/dashboard" element={<DashboardLayout />}>
            {/* Dashboard - Owner, Accountant only */}
            <Route index element={
              <ProtectedRoute requiredPermission="dashboard">
                <Dashboard />
              </ProtectedRoute>
            } />
            
            {/* Forecast - Owner, Accountant only */}
            <Route path="forecast" element={
              <ProtectedRoute requiredPermission="forecast">
                <Forecast />
              </ProtectedRoute>
            } />
            
            {/* Anomaly Detection - Owner, Accountant only */}
            <Route path="anomaly" element={
              <ProtectedRoute requiredPermission="anomaly">
                <AnomalyDetection />
              </ProtectedRoute>
            } />
            
            {/* Reports - Owner, Accountant only */}
            <Route path="reports" element={
              <ProtectedRoute requiredPermission="report">
                <Reports />
              </ProtectedRoute>
            } />
            
            {/* Payments - Owner, Accountant, Cashier */}
            <Route path="payments" element={
              <ProtectedRoute requiredPermission="payment">
                <Payments />
              </ProtectedRoute>
            } />
            
            {/* AR - Owner, Accountant, Cashier */}
            <Route path="ar" element={
              <ProtectedRoute requiredPermission="ar">
                <AccountsReceivable />
              </ProtectedRoute>
            } />
            
            {/* AP - Owner, Accountant only */}
            <Route path="ap" element={
              <ProtectedRoute requiredPermission="ap">
                <AccountsPayable />
              </ProtectedRoute>
            } />
            
            {/* User Management - Admin only */}
            <Route path="users" element={
              <ProtectedRoute requiredPermission="user">
                <UserManagement />
              </ProtectedRoute>
            } />
            
            {/* Settings - Admin only */}
            <Route path="settings" element={
              <ProtectedRoute requiredPermission="settings">
                <Settings />
              </ProtectedRoute>
            } />
          </Route>

          {/* Redirect unknown routes to landing */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster />
      {/* 🔍 Dev API Monitor - Only shows in development */}
      <DevAPIMonitor />
    </QueryProvider>
  );
}