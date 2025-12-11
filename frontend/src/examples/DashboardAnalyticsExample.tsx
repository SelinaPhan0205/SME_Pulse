/**
 * Example: Dashboard Analytics
 * Ví dụ cách dùng Analytics hooks
 */

import { useDashboardSummary, useARAging, useDailyRevenue } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { ArrowUpIcon, ArrowDownIcon } from 'lucide-react';

export function DashboardAnalyticsExample() {
  // Fetch dashboard summary
  const { data: summary, isLoading: summaryLoading } = useDashboardSummary();

  // Fetch AR Aging
  const { data: arAging, isLoading: arLoading } = useARAging();

  // Fetch daily revenue (last 30 days)
  const today = new Date();
  const thirtyDaysAgo = new Date(today);
  thirtyDaysAgo.setDate(today.getDate() - 30);

  const { data: revenue } = useDailyRevenue({
    start_date: thirtyDaysAgo.toISOString().split('T')[0],
    end_date: today.toISOString().split('T')[0],
  });

  if (summaryLoading) {
    return <div>Loading dashboard...</div>;
  }

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-6">
          <div className="text-sm text-gray-600 mb-2">Total Revenue</div>
          <div className="text-3xl font-bold">
            ${summary?.total_revenue.toLocaleString()}
          </div>
          <div className="flex items-center text-sm text-green-600 mt-2">
            <ArrowUpIcon className="size-4 mr-1" />
            <span>12% vs last month</span>
          </div>
        </Card>

        <Card className="p-6">
          <div className="text-sm text-gray-600 mb-2">Accounts Receivable</div>
          <div className="text-3xl font-bold">
            ${summary?.total_receivables.toLocaleString()}
          </div>
          <div className="text-sm text-gray-500 mt-2">
            {summary?.overdue_invoices_count} overdue
          </div>
        </Card>

        <Card className="p-6">
          <div className="text-sm text-gray-600 mb-2">Accounts Payable</div>
          <div className="text-3xl font-bold">
            ${summary?.total_payables.toLocaleString()}
          </div>
          <div className="text-sm text-gray-500 mt-2">
            {summary?.pending_payments_count} pending
          </div>
        </Card>

        <Card className="p-6">
          <div className="text-sm text-gray-600 mb-2">Payment Success Rate</div>
          <div className="text-3xl font-bold">
            {summary?.payment_success_rate.toFixed(1)}%
          </div>
          <div className="flex items-center text-sm text-red-600 mt-2">
            <ArrowDownIcon className="size-4 mr-1" />
            <span>2% vs last month</span>
          </div>
        </Card>
      </div>

      {/* AR Aging Chart */}
      {!arLoading && arAging && (
        <Card className="p-6">
          <h2 className="text-xl font-bold mb-4">AR Aging Analysis</h2>
          <div className="space-y-3">
            {arAging.buckets.map((bucket) => (
              <div key={bucket.bucket} className="flex items-center justify-between">
                <div>
                  <div className="font-medium">{bucket.bucket}</div>
                  <div className="text-sm text-gray-500">{bucket.count} invoices</div>
                </div>
                <div className="text-lg font-semibold">
                  ${bucket.amount.toLocaleString()}
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 pt-4 border-t flex justify-between items-center">
            <span className="font-bold">Total AR</span>
            <span className="text-xl font-bold">
              ${arAging.total_ar.toLocaleString()}
            </span>
          </div>
        </Card>
      )}

      {/* Daily Revenue */}
      {revenue && (
        <Card className="p-6">
          <h2 className="text-xl font-bold mb-4">Daily Revenue (Last 30 Days)</h2>
          <div className="text-sm text-gray-600">
            {revenue.data.length} data points
          </div>
          {/* Có thể dùng chart library như recharts để vẽ biểu đồ */}
        </Card>
      )}
    </div>
  );
}
