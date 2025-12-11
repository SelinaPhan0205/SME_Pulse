/**
 * API Hooks - Central export
 * Import tất cả hooks từ đây
 */

// Auth hooks
export { useLogin, useLogout, useCurrentUser, useChangePassword, useUserRoles } from './useAuth';

// Users hooks
export {
  useUsers,
  useUser,
  useCreateUser,
  useUpdateUser,
  useDeleteUser,
  useResetUserPassword,
} from './useUsers';

// Customers hooks
export {
  useCustomers,
  useCustomer,
  useCreateCustomer,
  useUpdateCustomer,
  useDeleteCustomer,
} from './useCustomers';

// Suppliers hooks
export {
  useSuppliers,
  useSupplier,
  useCreateSupplier,
  useUpdateSupplier,
  useDeleteSupplier,
} from './useSuppliers';

// Accounts hooks
export {
  useAccounts,
  useAccount,
  useCreateAccount,
  useUpdateAccount,
  useDeleteAccount,
} from './useAccounts';

// Invoices hooks
export {
  useInvoices,
  useInvoice,
  useCreateInvoice,
  useUpdateInvoice,
  useDeleteInvoice,
  usePostInvoice,
  useBulkImportInvoices,
} from './useInvoices';

// Bills hooks
export {
  useBills,
  useBill,
  useCreateBill,
  useUpdateBill,
  useDeleteBill,
  usePostBill,
} from './useBills';

// Payments hooks
export {
  usePayments,
  usePayment,
  useCreatePayment,
  useUpdatePayment,
} from './usePayments';

// Analytics hooks
export {
  useDashboardSummary,
  useARAging,
  useAPAging,
  useDailyRevenue,
  usePaymentSuccessRate,
  useReconciliationKPI,
  useMetabaseToken,
  useRevenueForecast,
  useRevenueAnomalies,
  // Reconciliation action hooks
  useAutoMatchReconciliation,
  useConfirmReconciliation,
  useRejectReconciliation,
  usePendingReconciliations,
} from './useAnalytics';

// Reports hooks
export {
  useReportTemplates,
  useExportJobs,
  useExportJob,
  useCreateExportJob,
} from './useReports';

// Settings hooks
export {
  useAISettings,
  useUpdateAISettings,
} from './useSettings';

// Alerts hooks
export {
  useAlerts,
  useAlert,
  useMarkAlertRead,
  useDismissAlert,
} from './useAlerts';
