'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

interface TimeSeriesData {
  time: string;
  cpu: number;
  memory: number;
  responseTime: number;
  activeConnections: number;
}

interface TaskQueueData {
  name: string;
  pending: number;
  processing: number;
  completed: number;
  failed: number;
}

interface SystemHealthData {
  name: string;
  value: number;
  color: string;
}

export default function AnalyticsCharts() {
  const [timeSeriesData, setTimeSeriesData] = useState<TimeSeriesData[]>([]);
  const [taskQueueData, setTaskQueueData] = useState<TaskQueueData[]>([]);
  const [systemHealthData, setSystemHealthData] = useState<SystemHealthData[]>(
    []
  );
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const generateMockData = () => {
      // Generate time series data for the last 24 data points (5 min intervals)
      const now = new Date();
      const timeSeries: TimeSeriesData[] = Array.from(
        { length: 24 },
        (_, i) => {
          const time = new Date(now.getTime() - (23 - i) * 5 * 60 * 1000);
          return {
            time: time.toLocaleTimeString('en-US', {
              hour: '2-digit',
              minute: '2-digit',
            }),
            cpu: Math.max(
              10,
              Math.min(90, 50 + Math.sin(i / 4) * 20 + Math.random() * 10)
            ),
            memory: Math.max(
              20,
              Math.min(85, 60 + Math.cos(i / 3) * 15 + Math.random() * 8)
            ),
            responseTime: Math.max(
              50,
              Math.min(800, 200 + Math.sin(i / 6) * 100 + Math.random() * 50)
            ),
            activeConnections: Math.max(
              50,
              Math.min(400, 150 + Math.sin(i / 5) * 75 + Math.random() * 30)
            ),
          };
        }
      );

      // Generate task queue data
      const taskQueues: TaskQueueData[] = [
        {
          name: 'Video Processing',
          pending: 12,
          processing: 3,
          completed: 245,
          failed: 2,
        },
        {
          name: 'AI Analysis',
          pending: 8,
          processing: 5,
          completed: 189,
          failed: 1,
        },
        {
          name: 'Data Sync',
          pending: 4,
          processing: 2,
          completed: 567,
          failed: 3,
        },
        {
          name: 'Social Media',
          pending: 15,
          processing: 4,
          completed: 334,
          failed: 5,
        },
        {
          name: 'Knowledge Vault',
          pending: 6,
          processing: 1,
          completed: 678,
          failed: 2,
        },
      ];

      // Generate system health data
      const healthData: SystemHealthData[] = [
        { name: 'Healthy', value: 78, color: '#10b981' },
        { name: 'Warning', value: 18, color: '#f59e0b' },
        { name: 'Critical', value: 4, color: '#ef4444' },
      ];

      setTimeSeriesData(timeSeries);
      setTaskQueueData(taskQueues);
      setSystemHealthData(healthData);
      setLoading(false);
    };

    generateMockData();
    const interval = setInterval(generateMockData, 30000); // Update every 30 seconds

    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i}>
            <CardHeader>
              <CardTitle>Loading...</CardTitle>
            </CardHeader>
            <CardContent>
              <div className='flex items-center justify-center h-64 text-muted-foreground'>
                Loading chart data...
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
      {/* System Performance Over Time */}
      <Card className='lg:col-span-2'>
        <CardHeader>
          <CardTitle>System Performance Trends</CardTitle>
          <p className='text-sm text-muted-foreground'>
            Real-time system metrics over the last 2 hours
          </p>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width='100%' height={300}>
            <LineChart data={timeSeriesData}>
              <CartesianGrid strokeDasharray='3 3' />
              <XAxis dataKey='time' />
              <YAxis yAxisId='left' />
              <YAxis yAxisId='right' orientation='right' />
              <Tooltip />
              <Legend />
              <Line
                yAxisId='left'
                type='monotone'
                dataKey='cpu'
                stroke='#ef4444'
                name='CPU %'
                strokeWidth={2}
              />
              <Line
                yAxisId='left'
                type='monotone'
                dataKey='memory'
                stroke='#3b82f6'
                name='Memory %'
                strokeWidth={2}
              />
              <Line
                yAxisId='right'
                type='monotone'
                dataKey='responseTime'
                stroke='#10b981'
                name='Response Time (ms)'
                strokeWidth={2}
              />
              <Line
                yAxisId='right'
                type='monotone'
                dataKey='activeConnections'
                stroke='#f59e0b'
                name='Active Connections'
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Task Queue Status */}
      <Card>
        <CardHeader>
          <CardTitle>Task Queue Status</CardTitle>
          <p className='text-sm text-muted-foreground'>
            Current status of all task queues
          </p>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width='100%' height={300}>
            <BarChart data={taskQueueData} layout='horizontal'>
              <CartesianGrid strokeDasharray='3 3' />
              <XAxis type='number' />
              <YAxis dataKey='name' type='category' width={100} />
              <Tooltip />
              <Legend />
              <Bar
                dataKey='pending'
                stackId='a'
                fill='#f59e0b'
                name='Pending'
              />
              <Bar
                dataKey='processing'
                stackId='a'
                fill='#3b82f6'
                name='Processing'
              />
              <Bar
                dataKey='completed'
                stackId='b'
                fill='#10b981'
                name='Completed'
              />
              <Bar dataKey='failed' stackId='b' fill='#ef4444' name='Failed' />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* System Health Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>System Health Overview</CardTitle>
          <p className='text-sm text-muted-foreground'>
            Distribution of system component health
          </p>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width='100%' height={300}>
            <PieChart>
              <Pie
                data={systemHealthData}
                cx='50%'
                cy='50%'
                innerRadius={60}
                outerRadius={100}
                paddingAngle={5}
                dataKey='value'
                label={({ name, value }) => `${name}: ${value}%`}
              >
                {systemHealthData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip formatter={value => [`${value}%`, 'Percentage']} />
            </PieChart>
          </ResponsiveContainer>
          <div className='mt-4 flex justify-center'>
            <div className='flex gap-4'>
              {systemHealthData.map(entry => (
                <div key={entry.name} className='flex items-center gap-2'>
                  <div
                    className='w-3 h-3 rounded-full'
                    style={{ backgroundColor: entry.color }}
                  />
                  <span className='text-sm'>
                    {entry.name} ({entry.value}%)
                  </span>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Real-time Activity Feed */}
      <Card className='lg:col-span-2'>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
          <p className='text-sm text-muted-foreground'>
            Live feed of system events and alerts
          </p>
        </CardHeader>
        <CardContent>
          <div className='space-y-3 max-h-64 overflow-y-auto'>
            {[
              {
                time: '12:45 PM',
                type: 'success',
                message: 'Video processing task completed successfully',
                id: 'task-1234',
              },
              {
                time: '12:44 PM',
                type: 'info',
                message: 'New AI analysis job started',
                id: 'task-1235',
              },
              {
                time: '12:43 PM',
                type: 'warning',
                message: 'High memory usage detected on server-02',
                threshold: '85%',
              },
              {
                time: '12:42 PM',
                type: 'success',
                message: 'Cache warming completed',
                duration: '2.3s',
              },
              {
                time: '12:41 PM',
                type: 'error',
                message: 'Failed to connect to external API',
                retry: 'in 30s',
              },
              {
                time: '12:40 PM',
                type: 'info',
                message: 'Database backup initiated',
                size: '1.2GB',
              },
              {
                time: '12:39 PM',
                type: 'success',
                message: 'Social media sync completed',
                count: '324 posts',
              },
            ].map((activity, i) => (
              <div
                key={i}
                className='flex items-center gap-3 p-3 rounded-lg bg-muted/50'
              >
                <div
                  className={`w-2 h-2 rounded-full ${
                    activity.type === 'success'
                      ? 'bg-green-500'
                      : activity.type === 'warning'
                        ? 'bg-yellow-500'
                        : activity.type === 'error'
                          ? 'bg-red-500'
                          : 'bg-blue-500'
                  }`}
                />
                <span className='text-sm text-muted-foreground min-w-16'>
                  {activity.time}
                </span>
                <span className='text-sm flex-1'>{activity.message}</span>
                {(activity as any).id && (
                  <span className='text-xs text-muted-foreground bg-muted px-2 py-1 rounded'>
                    {(activity as any).id}
                  </span>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
