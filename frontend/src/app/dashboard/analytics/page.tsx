/* Analytics Dashboard Page */
'use client';

import React from 'react';
import { motion } from 'framer-motion';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  MetricCard,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';

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

export default function AnalyticsPage() {
  const trafficMetrics = [
    { label: 'Page Views', value: '2.4M', unit: '', trend: 'up' as const },
    { label: 'Unique Visitors', value: '180K', unit: '', trend: 'up' as const },
    { label: 'Bounce Rate', value: '34.2', unit: '%', trend: 'down' as const },
    { label: 'Avg. Session', value: '4.2', unit: 'min', trend: 'up' as const },
  ];

  const conversionMetrics = [
    { label: 'Conversion Rate', value: '3.8', unit: '%', trend: 'up' as const },
    {
      label: 'Total Conversions',
      value: '1,247',
      unit: '',
      trend: 'up' as const,
    },
    { label: 'Revenue', value: '$24,300', unit: '', trend: 'up' as const },
    { label: 'AOV', value: '$19.48', unit: '', trend: 'neutral' as const },
  ];

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
                Advanced Analytics
              </h1>
              <p className='text-neutral-600 dark:text-neutral-400 mt-2'>
                Deep dive into user behavior and conversion patterns
              </p>
            </div>
            <div className='flex items-center gap-3'>
              <Button variant='outline' size='sm'>
                Export Report
              </Button>
              <Button size='sm'>Customize View</Button>
            </div>
          </div>
        </motion.header>

        <motion.section
          className='grid grid-cols-1 gap-6 lg:grid-cols-2'
          variants={itemVariants}
        >
          <MetricCard
            title='Traffic Analytics'
            metrics={trafficMetrics}
            timeRange='Last 30 days'
            variant='gradient'
          />

          <MetricCard
            title='Conversion Metrics'
            metrics={conversionMetrics}
            timeRange='Last 30 days'
            variant='outlined'
          />
        </motion.section>

        <motion.section variants={itemVariants}>
          <Card>
            <CardHeader>
              <CardTitle>Traffic Sources</CardTitle>
            </CardHeader>
            <CardContent>
              <div className='space-y-4'>
                {[
                  {
                    source: 'Organic Search',
                    percentage: 45,
                    visitors: '81K',
                    color: 'bg-brand-primary-500',
                  },
                  {
                    source: 'Direct',
                    percentage: 28,
                    visitors: '50.4K',
                    color: 'bg-success-500',
                  },
                  {
                    source: 'Social Media',
                    percentage: 15,
                    visitors: '27K',
                    color: 'bg-warning-500',
                  },
                  {
                    source: 'Email',
                    percentage: 12,
                    visitors: '21.6K',
                    color: 'bg-error-500',
                  },
                ].map((item, index) => (
                  <div key={index} className='flex items-center gap-4'>
                    <div className='w-12 text-sm font-medium text-neutral-600 dark:text-neutral-400'>
                      {item.percentage}%
                    </div>
                    <div className='flex-1'>
                      <div className='flex items-center justify-between mb-1'>
                        <span className='text-sm font-medium text-neutral-900 dark:text-neutral-100'>
                          {item.source}
                        </span>
                        <span className='text-sm text-neutral-600 dark:text-neutral-400'>
                          {item.visitors}
                        </span>
                      </div>
                      <div className='w-full bg-neutral-200 dark:bg-neutral-700 rounded-full h-2'>
                        <motion.div
                          className={`h-2 rounded-full ${item.color}`}
                          initial={{ width: 0 }}
                          animate={{ width: `${item.percentage}%` }}
                          transition={{ duration: 1, delay: index * 0.1 }}
                        />
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
