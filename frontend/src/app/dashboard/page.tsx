/* Advanced Dashboard - Real-time Data Visualization & Analytics */
/* Transcendent dashboard with quantum-level responsiveness and adaptive layouts */

'use client';

import React from 'react';
import { motion } from 'framer-motion';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  StatsCard,
  MetricCard,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useStore } from '@/lib/store';

// Dashboard animation variants
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      delayChildren: 0.1,
      staggerChildren: 0.1,
    },
  },
};

const itemVariants = {
  hidden: { y: 20, opacity: 0 },
  visible: {
    y: 0,
    opacity: 1,
    transition: {
      type: 'spring',
      stiffness: 300,
      damping: 24,
    },
  },
};

export default function DashboardPage() {
  const { user, performance, device, errors, features } = useStore();

  // Safe state access with fallbacks for SSR
  const safePerformance = performance || {
    renderTime: 0,
    memoryUsage: null,
    bundleSize: null,
    interactionLatency: 0,
  };
  
  const safeDevice = device || {
    connectionType: null,
    batteryLevel: null,
    screenWidth: 1920,
    screenHeight: 1080,
    platform: null,
  };
  
  const safeErrors = errors || { errors: [] };
  const safeFeatures = features || {
    enableAdvancedAnalytics: true,
    enableVoiceCommands: false,
    enableDarkMode: true,
    enableNotifications: true,
    enableOfflineMode: false,
  };

  // Simulate real-time data updates
  const [realTimeData, setRealTimeData] = React.useState({
    activeUsers: 1247,
    totalRequests: 98432,
    avgResponseTime: 145,
    errorRate: 0.3,
    uptime: 99.9,
  });

  // Update real-time data periodically
  React.useEffect(() => {
    const interval = setInterval(() => {
      setRealTimeData(prev => ({
        activeUsers: prev.activeUsers + Math.floor(Math.random() * 20 - 10),
        totalRequests: prev.totalRequests + Math.floor(Math.random() * 100),
        avgResponseTime:
          prev.avgResponseTime + Math.floor(Math.random() * 20 - 10),
        errorRate: Math.max(0, prev.errorRate + (Math.random() * 0.2 - 0.1)),
        uptime: Math.min(100, prev.uptime + Math.random() * 0.01),
      }));
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  // Dashboard ready effect
  React.useEffect(() => {
    // Dashboard loaded with real-time analytics
  }, []);

  const performanceMetrics = [
    {
      label: 'Render Time',
      value: safePerformance.renderTime.toFixed(2),
      unit: 'ms',
      trend: 'down' as const,
    },
    {
      label: 'Memory Usage',
      value: safePerformance.memoryUsage
        ? (safePerformance.memoryUsage.used / 1024 / 1024).toFixed(1)
        : '0',
      unit: 'MB',
      trend: 'up' as const,
    },
    {
      label: 'Bundle Size',
      value: safePerformance.bundleSize
        ? (safePerformance.bundleSize / 1024).toFixed(1)
        : '0',
      unit: 'KB',
      trend: 'neutral' as const,
    },
    {
      label: 'Interaction Latency',
      value: safePerformance.interactionLatency.toFixed(2),
      unit: 'ms',
      trend: 'down' as const,
    },
  ];

  const deviceMetrics = [
    {
      label: 'Connection',
      value: safeDevice.connectionType || 'Unknown',
      trend: 'neutral' as const,
    },
    {
      label: 'Battery Level',
      value: safeDevice.batteryLevel
        ? `${(safeDevice.batteryLevel * 100).toFixed(0)}%`
        : 'N/A',
      trend: 'neutral' as const,
    },
    {
      label: 'Screen Size',
      value: `${safeDevice.screenWidth}×${safeDevice.screenHeight}`,
      trend: 'neutral' as const,
    },
    {
      label: 'Platform',
      value: safeDevice.platform || 'Unknown',
      trend: 'neutral' as const,
    },
  ];

  return (
    <div className='min-h-screen bg-gradient-to-br from-neutral-50 to-neutral-100 dark:from-neutral-950 dark:to-neutral-900 p-4 lg:p-8'>
      <motion.div
        className='max-w-7xl mx-auto space-y-8'
        variants={containerVariants}
        initial='hidden'
        animate='visible'
      >
        {/* Header */}
        <motion.header
          className='flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between'
          variants={itemVariants}
        >
          <div>
            <h1 className='text-3xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100 sm:text-4xl'>
              Analytics Dashboard
            </h1>
            <p className='text-neutral-600 dark:text-neutral-400 mt-2'>
              Real-time insights and performance metrics for your application
            </p>
          </div>
          <div className='flex items-center gap-3'>
            <Button variant='outline' size='sm'>
              Export Data
            </Button>
            <Button size='sm'>Refresh</Button>
          </div>
        </motion.header>

        {/* Real-time Stats Grid */}
        <motion.section variants={itemVariants}>
          <div className='grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-5'>
            <StatsCard
              title='Active Users'
              value={realTimeData.activeUsers.toLocaleString()}
              change='+12.5%'
              trend='up'
              icon='👥'
              description='Currently online'
            />
            <StatsCard
              title='Total Requests'
              value={realTimeData.totalRequests.toLocaleString()}
              change='+8.2%'
              trend='up'
              icon='📊'
              description='Last 24 hours'
            />
            <StatsCard
              title='Avg Response'
              value={`${realTimeData.avgResponseTime}ms`}
              change='-5.3%'
              trend='down'
              icon='⚡'
              description='Server response time'
            />
            <StatsCard
              title='Error Rate'
              value={`${realTimeData.errorRate.toFixed(2)}%`}
              change='+0.1%'
              trend='up'
              icon='⚠️'
              description='Error percentage'
              variant='warning'
            />
            <StatsCard
              title='Uptime'
              value={`${realTimeData.uptime.toFixed(1)}%`}
              change='+0.1%'
              trend='up'
              icon='✅'
              description='Service availability'
              variant='success'
            />
          </div>
        </motion.section>

        {/* Charts and Analytics Row */}
        <motion.section
          className='grid grid-cols-1 gap-6 lg:grid-cols-2 xl:grid-cols-3'
          variants={itemVariants}
        >
          {/* Performance Metrics */}
          <MetricCard
            title='Performance Metrics'
            metrics={performanceMetrics}
            timeRange='Last 5 minutes'
            variant='gradient'
          />

          {/* Device Information */}
          <MetricCard
            title='Device Information'
            metrics={deviceMetrics}
            variant='outlined'
          />

          {/* System Health */}
          <Card className='col-span-1 xl:col-span-1'>
            <CardHeader>
              <CardTitle className='flex items-center gap-2'>
                🔧 System Health
                <span className='text-xs bg-success-100 text-success-800 px-2 py-1 rounded-full dark:bg-success-900/20 dark:text-success-400'>
                  Healthy
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className='space-y-4'>
                <div className='flex items-center justify-between'>
                  <span className='text-sm text-neutral-600 dark:text-neutral-400'>
                    Features Enabled
                  </span>
                  <span className='text-sm font-medium'>
                    {Object.values(safeFeatures).filter(Boolean).length}/
                    {Object.keys(safeFeatures).length}
                  </span>
                </div>
                <div className='flex items-center justify-between'>
                  <span className='text-sm text-neutral-600 dark:text-neutral-400'>
                    Active Errors
                  </span>
                  <span
                    className={`text-sm font-medium ${safeErrors.errors.length > 0 ? 'text-error-600' : 'text-success-600'}`}
                  >
                    {safeErrors.errors.length}
                  </span>
                </div>
                <div className='flex items-center justify-between'>
                  <span className='text-sm text-neutral-600 dark:text-neutral-400'>
                    Theme
                  </span>
                  <span className='text-sm font-medium capitalize'>
                    {user?.theme || 'system'}
                  </span>
                </div>
                <div className='flex items-center justify-between'>
                  <span className='text-sm text-neutral-600 dark:text-neutral-400'>
                    Reduced Motion
                  </span>
                  <span className='text-sm font-medium'>
                    {user?.reducedMotion ? 'Enabled' : 'Disabled'}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.section>

        {/* Feature Flags & Configuration */}
        <motion.section variants={itemVariants}>
          <Card>
            <CardHeader>
              <CardTitle>Feature Configuration</CardTitle>
            </CardHeader>
            <CardContent>
              <div className='grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4'>
                {Object.entries(safeFeatures).map(([feature, enabled]) => (
                  <div
                    key={feature}
                    className='flex items-center justify-between p-3 bg-neutral-50 dark:bg-neutral-800 rounded-lg'
                  >
                    <span className='text-sm font-medium capitalize'>
                      {feature.replace(/([A-Z])/g, ' $1').trim()}
                    </span>
                    <div
                      className={`w-3 h-3 rounded-full ${
                        enabled
                          ? 'bg-success-500'
                          : 'bg-neutral-300 dark:bg-neutral-600'
                      }`}
                      title={enabled ? 'Enabled' : 'Disabled'}
                    />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.section>

        {/* Real-time Activity Feed */}
        <motion.section variants={itemVariants}>
          <Card>
            <CardHeader>
              <CardTitle>Real-time Activity</CardTitle>
            </CardHeader>
            <CardContent>
              <div className='space-y-3'>
                <div className='flex items-center gap-3 p-3 bg-brand-primary-50 dark:bg-brand-primary-900/20 rounded-lg'>
                  <div className='w-2 h-2 bg-brand-primary-500 rounded-full animate-pulse' />
                  <span className='text-sm'>
                    New user session started from San Francisco
                  </span>
                  <span className='text-xs text-neutral-500 ml-auto'>
                    2s ago
                  </span>
                </div>
                <div className='flex items-center gap-3 p-3 bg-success-50 dark:bg-success-900/20 rounded-lg'>
                  <div className='w-2 h-2 bg-success-500 rounded-full animate-pulse' />
                  <span className='text-sm'>
                    API response time improved by 15ms
                  </span>
                  <span className='text-xs text-neutral-500 ml-auto'>
                    15s ago
                  </span>
                </div>
                <div className='flex items-center gap-3 p-3 bg-warning-50 dark:bg-warning-900/20 rounded-lg'>
                  <div className='w-2 h-2 bg-warning-500 rounded-full animate-pulse' />
                  <span className='text-sm'>Memory usage increased to 78%</span>
                  <span className='text-xs text-neutral-500 ml-auto'>
                    1m ago
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.section>
      </motion.div>
    </div>
  );
}
