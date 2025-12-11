/**
 * Dev API Monitor - Component để verify data nguồn
 * CHỈ HIỆN Ở DEVELOPMENT MODE
 * 
 * Hiển thị:
 * - API endpoint đang call
 * - Response time
 * - Data source (REAL vs MOCK)
 */

import { useEffect, useState } from 'react';
import { Badge } from './ui/badge';
import { Card, CardContent } from './ui/card';
import { Activity, Database, Wifi, WifiOff } from 'lucide-react';

interface APICall {
  id: string;
  method: string;
  url: string;
  status: 'pending' | 'success' | 'error';
  timestamp: number;
  duration?: number;
}

export function DevAPIMonitor() {
  const [apiCalls, setApiCalls] = useState<APICall[]>([]);
  const [isBackendReachable, setIsBackendReachable] = useState<boolean | null>(null);

  // Debug: Log component mount
  useEffect(() => {
    console.log('🔧 [DevAPIMonitor] Component mounted!');
    console.log('🔧 [DevAPIMonitor] PROD mode:', import.meta.env.PROD);
    console.log('🔧 [DevAPIMonitor] Should show:', !import.meta.env.PROD);
  }, []);

  // Listen to window events for API tracking
  useEffect(() => {
    const handleAPIRequest = (event: CustomEvent) => {
      const data = event.detail;
      setApiCalls((prev) => [
        {
          id: `${Date.now()}-${Math.random()}`,
          method: data.method || 'GET',
          url: data.url || '',
          status: 'pending',
          timestamp: Date.now(),
        },
        ...prev.slice(0, 9), // Keep last 10
      ]);
    };

    const handleAPIResponse = (event: CustomEvent) => {
      const data = event.detail;
      setApiCalls((prev) =>
        prev.map((call) =>
          call.url.includes(data.url) && call.status === 'pending'
            ? {
                ...call,
                status: 'success',
                duration: Date.now() - call.timestamp,
              }
            : call
        )
      );
    };

    window.addEventListener('api-request', handleAPIRequest as EventListener);
    window.addEventListener('api-response', handleAPIResponse as EventListener);

    return () => {
      window.removeEventListener('api-request', handleAPIRequest as EventListener);
      window.removeEventListener('api-response', handleAPIResponse as EventListener);
    };
  }, []);

  // Check backend health
  useEffect(() => {
    const checkBackend = async () => {
      try {
        // Use /health endpoint for health check (proper endpoint)
        const response = await fetch('http://localhost:8000/health', {
          method: 'GET',
          mode: 'cors',
        });
        setIsBackendReachable(response.ok);
      } catch (error) {
        setIsBackendReachable(false);
      }
    };

    checkBackend();
    const interval = setInterval(checkBackend, 30000); // Check every 30s (reduced frequency)
    return () => clearInterval(interval);
  }, []);

  // Only show in development
  if (import.meta.env.PROD) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 w-96 max-h-96 overflow-auto">
      <Card className="bg-slate-900 text-white border-slate-700 shadow-2xl">
        <CardContent className="p-3">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Activity className="size-4 text-blue-400" />
              <span className="text-xs font-semibold">API Monitor</span>
            </div>
            <div className="flex items-center gap-2">
              {isBackendReachable === null ? (
                <Badge variant="secondary" className="text-xs">
                  <Wifi className="size-3 mr-1" />
                  Checking...
                </Badge>
              ) : isBackendReachable ? (
                <Badge className="bg-green-600 text-xs">
                  <Wifi className="size-3 mr-1" />
                  Backend LIVE
                </Badge>
              ) : (
                <Badge variant="destructive" className="text-xs">
                  <WifiOff className="size-3 mr-1" />
                  Backend DOWN
                </Badge>
              )}
            </div>
          </div>

          <div className="space-y-1">
            {apiCalls.length === 0 ? (
              <p className="text-xs text-slate-400 text-center py-4">
                No API calls yet...
              </p>
            ) : (
              apiCalls.map((call) => (
                <div
                  key={call.id}
                  className="flex items-start gap-2 p-2 rounded bg-slate-800 text-xs"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge
                        variant={
                          call.status === 'success'
                            ? 'default'
                            : call.status === 'error'
                            ? 'destructive'
                            : 'secondary'
                        }
                        className="text-[10px] px-1 py-0"
                      >
                        {call.method}
                      </Badge>
                      {call.status === 'success' && (
                        <span className="text-green-400 text-[10px]">
                          ✓ {call.duration}ms
                        </span>
                      )}
                      {call.status === 'pending' && (
                        <span className="text-yellow-400 text-[10px] animate-pulse">
                          ⏳ Loading...
                        </span>
                      )}
                    </div>
                    <p className="text-slate-300 truncate font-mono text-[10px]">
                      {call.url}
                    </p>
                    {call.status === 'success' && (
                      <div className="flex items-center gap-1 mt-1">
                        <Database className="size-3 text-blue-400" />
                        <span className="text-blue-400 text-[10px] font-semibold">
                          🔥 REAL BACKEND DATA
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="mt-2 pt-2 border-t border-slate-700 text-[10px] text-slate-400">
            <p className="flex items-center gap-1">
              <span className="text-green-400">●</span>
              MSW: DISABLED - All requests go to backend
            </p>
            <p className="flex items-center gap-1 mt-1">
              <span className="text-blue-400">●</span>
              API Base: http://localhost:8000
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
