'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { usePerformanceMetrics } from '@/lib/hooks/usePhase3Data';

interface PerformanceData {
  timestamp: string;
  cpu_usage: number;
  memory_usage: number;
  response_time: number;
  active_connections: number;
  error_rate: number;
  cache_hit_rate: number;
  task_queue_size: number;
  system_health: 'healthy' | 'warning' | 'error';
}

interface MetricCardProps {
  title: string;
  value: string | number;
  unit?: string;
  status?: 'healthy' | 'warning' | 'error';
  trend?: 'up' | 'down' | 'stable';
}

function MetricCard({
  title,
  value,
  unit,
  status = 'healthy',
  trend = 'stable',
}: MetricCardProps) {
  const statusColors = {
    healthy: 'text-green-600 border-green-200 bg-green-50',
    warning: 'text-yellow-600 border-yellow-200 bg-yellow-50',
    error: 'text-red-600 border-red-200 bg-red-50',
  };

  const trendIcons = {
    up: '↗️',
    down: '↘️',
    stable: '➡️',
  };

  return (
    <div
      className={`p-4 rounded-lg border-2 transition-all duration-200 ${statusColors[status]}`}
    >
      <div className='flex justify-between items-start'>
        <div>
          <p className='text-sm font-medium opacity-75'>{title}</p>
          <p className='text-2xl font-bold'>
            {value}
            {unit && <span className='text-sm opacity-75'>{unit}</span>}
          </p>
        </div>
        <span className='text-lg'>{trendIcons[trend]}</span>
      </div>
    </div>
  );
}

export default function PerformanceMetrics() {
  const { data: metrics, loading, error } = usePerformanceMetrics();

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Performance Metrics</CardTitle>
        </CardHeader>
        <CardContent>
          <div className='flex items-center justify-center h-64 text-muted-foreground'>
            Loading performance metrics...
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error || !metrics) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Performance Metrics</CardTitle>
        </CardHeader>
        <CardContent>
          <div className='flex items-center justify-center h-64 text-muted-foreground'>
            {error || 'Failed to load performance metrics'}
          </div>
        </CardContent>
      </Card>
    );
  }

  const getHealthStatus = (
    value: number,
    thresholds: { warning: number; error: number }
  ) => {
    if (value >= thresholds.error) return 'error';
    if (value >= thresholds.warning) return 'warning';
    return 'healthy';
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className='flex items-center gap-2'>
          Performance Metrics
          <div
            className={`w-3 h-3 rounded-full ${
              metrics.system_health === 'healthy'
                ? 'bg-green-500'
                : metrics.system_health === 'warning'
                  ? 'bg-yellow-500'
                  : 'bg-red-500'
            }`}
          />
        </CardTitle>
        <p className='text-sm text-muted-foreground'>
          Last updated: {new Date(metrics.timestamp).toLocaleTimeString()}
        </p>
      </CardHeader>
      <CardContent>
        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4'>
          <MetricCard
            title='CPU Usage'
            value={metrics.cpu_usage.toFixed(1)}
            unit='%'
            status={getHealthStatus(metrics.cpu_usage, {
              warning: 70,
              error: 85,
            })}
            trend={
              metrics.cpu_usage > 70
                ? 'up'
                : metrics.cpu_usage < 30
                  ? 'down'
                  : 'stable'
            }
          />
          <MetricCard
            title='Memory Usage'
            value={metrics.memory_usage.toFixed(1)}
            unit='%'
            status={getHealthStatus(metrics.memory_usage, {
              warning: 75,
              error: 90,
            })}
            trend={metrics.memory_usage > 75 ? 'up' : 'stable'}
          />
          <MetricCard
            title='Response Time'
            value={metrics.response_time.toFixed(0)}
            unit='ms'
            status={getHealthStatus(metrics.response_time, {
              warning: 500,
              error: 1000,
            })}
            trend={metrics.response_time > 500 ? 'up' : 'down'}
          />
          <MetricCard
            title='Active Connections'
            value={metrics.active_connections}
            status={getHealthStatus(metrics.active_connections, {
              warning: 300,
              error: 400,
            })}
            trend='stable'
          />
          <MetricCard
            title='Error Rate'
            value={metrics.error_rate.toFixed(2)}
            unit='%'
            status={getHealthStatus(metrics.error_rate, {
              warning: 2,
              error: 5,
            })}
            trend={metrics.error_rate > 2 ? 'up' : 'down'}
          />
          <MetricCard
            title='Cache Hit Rate'
            value={metrics.cache_hit_rate.toFixed(1)}
            unit='%'
            status={metrics.cache_hit_rate < 80 ? 'warning' : 'healthy'}
            trend={metrics.cache_hit_rate > 90 ? 'up' : 'stable'}
          />
          <MetricCard
            title='Task Queue'
            value={metrics.task_queue_size}
            unit=' tasks'
            status={getHealthStatus(metrics.task_queue_size, {
              warning: 20,
              error: 40,
            })}
            trend={metrics.task_queue_size > 20 ? 'up' : 'stable'}
          />
          <MetricCard
            title='System Health'
            value={
              metrics.system_health.charAt(0).toUpperCase() +
              metrics.system_health.slice(1)
            }
            status={metrics.system_health}
            trend='stable'
          />
        </div>
      </CardContent>
    </Card>
  );
}
