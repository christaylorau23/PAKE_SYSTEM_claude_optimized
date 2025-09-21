/* Performance Dashboard Page */
'use client';

import React from 'react';
import { motion } from 'framer-motion';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  StatsCard,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useStore } from '@/lib/store';

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

export default function PerformancePage() {
  const { performance } = useStore();

  const webVitalsData = [
    {
      metric: 'First Contentful Paint',
      value: '1.2s',
      threshold: '1.8s',
      status: 'good',
      description: 'Time when first text/image appears',
    },
    {
      metric: 'Largest Contentful Paint',
      value: '2.1s',
      threshold: '2.5s',
      status: 'good',
      description: 'Time when largest element loads',
    },
    {
      metric: 'First Input Delay',
      value: '45ms',
      threshold: '100ms',
      status: 'good',
      description: 'Time to first user interaction',
    },
    {
      metric: 'Cumulative Layout Shift',
      value: '0.08',
      threshold: '0.1',
      status: 'good',
      description: 'Visual stability score',
    },
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'good':
        return 'text-success-600 bg-success-100 dark:text-success-400 dark:bg-success-900/20';
      case 'needs-improvement':
        return 'text-warning-600 bg-warning-100 dark:text-warning-400 dark:bg-warning-900/20';
      case 'poor':
        return 'text-error-600 bg-error-100 dark:text-error-400 dark:bg-error-900/20';
      default:
        return 'text-neutral-600 bg-neutral-100 dark:text-neutral-400 dark:bg-neutral-800';
    }
  };

  return (
    <div className='min-h-screen bg-gradient-to-br from-neutral-50 to-neutral-100 dark:from-neutral-950 dark:to-neutral-900 p-4 lg:p-8'>
      <motion.div
        className='max-w-7xl mx-auto space-y-8'
        variants={containerVariants}
        initial='hidden'
        animate='visible'
      >
        <motion.header variants={itemVariants}>
          <div className='flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between'>
            <div>
              <h1 className='text-3xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100 sm:text-4xl'>
                Performance Monitoring
              </h1>
              <p className='text-neutral-600 dark:text-neutral-400 mt-2'>
                Real-time performance metrics and Web Vitals monitoring
              </p>
            </div>
            <div className='flex items-center gap-3'>
              <Button variant='outline' size='sm'>
                Run Audit
              </Button>
              <Button size='sm'>Optimize</Button>
            </div>
          </div>
        </motion.header>

        {/* Real-time Performance Stats */}
        <motion.section variants={itemVariants}>
          <div className='grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4'>
            <StatsCard
              title='Render Time'
              value={`${performance.renderTime.toFixed(2)}ms`}
              change='-12%'
              trend='down'
              icon='🎨'
              description='Component render time'
              variant='success'
            />
            <StatsCard
              title='Memory Usage'
              value={
                performance.memoryUsage
                  ? `${(performance.memoryUsage.used / 1024 / 1024).toFixed(1)}MB`
                  : 'N/A'
              }
              change='+5%'
              trend='up'
              icon='💾'
              description='JavaScript heap size'
            />
            <StatsCard
              title='Bundle Size'
              value={
                performance.bundleSize
                  ? `${(performance.bundleSize / 1024).toFixed(1)}KB`
                  : 'N/A'
              }
              change='0%'
              trend='neutral'
              icon='📦'
              description='Total bundle size'
            />
            <StatsCard
              title='Interaction Latency'
              value={`${performance.interactionLatency.toFixed(2)}ms`}
              change='-8%'
              trend='down'
              icon='⚡'
              description='User interaction delay'
              variant='success'
            />
          </div>
        </motion.section>

        {/* Web Vitals */}
        <motion.section variants={itemVariants}>
          <Card>
            <CardHeader>
              <CardTitle className='flex items-center gap-2'>
                🚀 Core Web Vitals
                <span className='text-xs bg-success-100 text-success-800 px-2 py-1 rounded-full dark:bg-success-900/20 dark:text-success-400'>
                  All Good
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className='grid grid-cols-1 gap-6 lg:grid-cols-2'>
                {webVitalsData.map((vital, index) => (
                  <motion.div
                    key={vital.metric}
                    className='p-4 border border-neutral-200 dark:border-neutral-700 rounded-lg'
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
                  >
                    <div className='flex items-center justify-between mb-2'>
                      <h3 className='font-medium text-neutral-900 dark:text-neutral-100'>
                        {vital.metric}
                      </h3>
                      <span
                        className={`px-2 py-1 text-xs rounded-full ${getStatusColor(vital.status)}`}
                      >
                        {vital.status}
                      </span>
                    </div>
                    <div className='flex items-center justify-between mb-3'>
                      <span className='text-2xl font-bold text-neutral-900 dark:text-neutral-100'>
                        {vital.value}
                      </span>
                      <span className='text-sm text-neutral-500 dark:text-neutral-400'>
                        Threshold: {vital.threshold}
                      </span>
                    </div>
                    <p className='text-sm text-neutral-600 dark:text-neutral-400'>
                      {vital.description}
                    </p>
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.section>

        {/* Performance Timeline */}
        <motion.section variants={itemVariants}>
          <Card>
            <CardHeader>
              <CardTitle>Performance Timeline</CardTitle>
            </CardHeader>
            <CardContent>
              <div className='space-y-4'>
                {[
                  { phase: 'DNS Resolution', time: '12ms', percentage: 5 },
                  { phase: 'Initial Connection', time: '45ms', percentage: 18 },
                  { phase: 'SSL Handshake', time: '28ms', percentage: 11 },
                  { phase: 'Request', time: '8ms', percentage: 3 },
                  { phase: 'Response', time: '89ms', percentage: 35 },
                  { phase: 'DOM Processing', time: '67ms', percentage: 26 },
                  { phase: 'Resource Loading', time: '156ms', percentage: 62 },
                ].map((phase, index) => (
                  <div key={phase.phase} className='flex items-center gap-4'>
                    <div className='w-32 text-sm font-medium text-neutral-600 dark:text-neutral-400'>
                      {phase.phase}
                    </div>
                    <div className='flex-1'>
                      <div className='flex items-center justify-between mb-1'>
                        <div className='w-full bg-neutral-200 dark:bg-neutral-700 rounded-full h-2'>
                          <motion.div
                            className='h-2 bg-brand-primary-500 rounded-full'
                            initial={{ width: 0 }}
                            animate={{
                              width: `${Math.min(phase.percentage, 100)}%`,
                            }}
                            transition={{ duration: 1, delay: index * 0.1 }}
                          />
                        </div>
                        <span className='text-sm text-neutral-600 dark:text-neutral-400 ml-4 w-12'>
                          {phase.time}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.section>
      </motion.div>
    </div>
  );
}
