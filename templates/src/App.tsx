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
import { QueryProvider } from './providers/QueryProvider';
import { Toaster } from './components/ui/sonner';

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
          
          {/* Protected dashboard routes */}
          <Route path="/dashboard" element={<DashboardLayout />}>
            <Route index element={<Dashboard />} />
            <Route path="forecast" element={<Forecast />} />
            <Route path="anomaly" element={<AnomalyDetection />} />
            <Route path="reports" element={<Reports />} />
            <Route path="payments" element={<Payments />} />
            <Route path="ar" element={<AccountsReceivable />} />
            <Route path="ap" element={<AccountsPayable />} />
            <Route path="users" element={<UserManagement />} />
            <Route path="settings" element={<Settings />} />
          </Route>

          {/* Redirect unknown routes to landing */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster />
    </QueryProvider>
  );
}