/* PAKE System - Main Navigation Hub */
'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import Link from 'next/link';

const dashboards = [
  {
    title: '🔍 Interactive Research',
    description:
      'Multi-source research dashboard with real-time querying across Web, ArXiv, and PubMed',
    href: '/research',
    color: 'bg-blue-500',
    status: 'NEW',
  },
  {
    title: '📊 Analytics Dashboard',
    description: 'Real-time system analytics and performance monitoring',
    href: '/dashboard',
    color: 'bg-purple-500',
    status: 'ACTIVE',
  },
  {
    title: '🏢 Admin Dashboard',
    description: 'System administration and configuration management',
    href: '/admin',
    color: 'bg-green-500',
    status: 'ACTIVE',
  },
  {
    title: '🎯 Knowledge Vault',
    description: 'Obsidian knowledge management and vault operations',
    href: '/knowledge',
    color: 'bg-orange-500',
    status: 'ACTIVE',
  },
  {
    title: '⚙️ Settings',
    description: 'System configuration and preferences',
    href: '/settings',
    color: 'bg-gray-500',
    status: 'ACTIVE',
  },
  {
    title: '🔗 Integrations',
    description: 'External service integrations and API management',
    href: '/integrations',
    color: 'bg-teal-500',
    status: 'ACTIVE',
  },
];

const systemStats = {
  bridgeStatus: 'Online',
  apiConnections: 3,
  activeServices: 6,
  lastUpdate: 'Loading...',
};

export default function HomePage() {
  const [stats, setStats] = React.useState(systemStats);
  const [mounted, setMounted] = React.useState(false);

  // Set mounted state and initial time on client side
  React.useEffect(() => {
    setMounted(true);
    setStats(prev => ({
      ...prev,
      lastUpdate: new Date().toLocaleTimeString(),
    }));
  }, []);

  // Update stats periodically
  React.useEffect(() => {
    if (!mounted) return;

    const interval = setInterval(() => {
      setStats(prev => ({
        ...prev,
        lastUpdate: new Date().toLocaleTimeString(),
      }));
    }, 30000);

    return () => clearInterval(interval);
  }, [mounted]);

  return (
    <div className='min-h-screen bg-gradient-to-br from-neutral-50 to-neutral-100 dark:from-neutral-950 dark:to-neutral-900 p-4 lg:p-8'>
      <div className='max-w-7xl mx-auto space-y-8'>
        {/* Header */}
        <motion.header
          className='text-center space-y-4'
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <h1 className='text-4xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100 sm:text-6xl'>
            🚀 PAKE System
          </h1>
          <p className='text-xl text-neutral-600 dark:text-neutral-400 max-w-3xl mx-auto'>
            Production-Ready, Enterprise-Grade Knowledge Management & AI
            Research System
          </p>
          <div className='flex justify-center items-center gap-4 text-sm'>
            <div className='flex items-center gap-2'>
              <div className='w-2 h-2 bg-green-500 rounded-full animate-pulse'></div>
              <span>Bridge: {stats.bridgeStatus}</span>
            </div>
            <span>•</span>
            <span>APIs: {stats.apiConnections}</span>
            <span>•</span>
            <span>Services: {stats.activeServices}</span>
            <span>•</span>
            <span>Updated: {stats.lastUpdate}</span>
          </div>
        </motion.header>

        {/* Dashboard Grid */}
        <motion.section
          className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          {dashboards.map((dashboard, index) => (
            <motion.div
              key={dashboard.href}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: index * 0.1 }}
            >
              <Link href={dashboard.href}>
                <Card className='h-full hover:shadow-lg transition-all duration-200 hover:scale-105 cursor-pointer group'>
                  <CardHeader className='pb-4'>
                    <div className='flex items-center justify-between'>
                      <CardTitle className='text-lg group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors'>
                        {dashboard.title}
                      </CardTitle>
                      <div className='flex items-center gap-2'>
                        {dashboard.status === 'NEW' && (
                          <span className='px-2 py-1 bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400 text-xs font-medium rounded-full'>
                            NEW
                          </span>
                        )}
                        <div
                          className={`w-3 h-3 rounded-full ${dashboard.color}`}
                        ></div>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className='text-neutral-600 dark:text-neutral-400 text-sm leading-relaxed'>
                      {dashboard.description}
                    </p>
                  </CardContent>
                </Card>
              </Link>
            </motion.div>
          ))}
        </motion.section>

        {/* System Status */}
        <motion.section
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
        >
          <Card>
            <CardHeader>
              <CardTitle className='flex items-center gap-2'>
                ⚡ System Status
                <span className='text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full dark:bg-green-900/20 dark:text-green-400'>
                  Operational
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className='grid grid-cols-1 md:grid-cols-4 gap-4 text-center'>
                <div className='space-y-1'>
                  <div className='text-2xl font-bold text-green-600 dark:text-green-400'>
                    99.9%
                  </div>
                  <div className='text-xs text-neutral-600 dark:text-neutral-400'>
                    Uptime
                  </div>
                </div>
                <div className='space-y-1'>
                  <div className='text-2xl font-bold text-blue-600 dark:text-blue-400'>
                    0.11s
                  </div>
                  <div className='text-xs text-neutral-600 dark:text-neutral-400'>
                    Avg Response
                  </div>
                </div>
                <div className='space-y-1'>
                  <div className='text-2xl font-bold text-purple-600 dark:text-purple-400'>
                    3
                  </div>
                  <div className='text-xs text-neutral-600 dark:text-neutral-400'>
                    Data Sources
                  </div>
                </div>
                <div className='space-y-1'>
                  <div className='text-2xl font-bold text-orange-600 dark:text-orange-400'>
                    Active
                  </div>
                  <div className='text-xs text-neutral-600 dark:text-neutral-400'>
                    Phase 3
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.section>

        {/* Quick Actions */}
        <motion.section
          className='text-center space-y-4'
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.6 }}
        >
          <h2 className='text-2xl font-semibold text-neutral-900 dark:text-neutral-100'>
            Quick Actions
          </h2>
          <div className='flex justify-center gap-4 flex-wrap'>
            <Link href='/research'>
              <button className='px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors'>
                🔍 Start Research
              </button>
            </Link>
            <Link href='/dashboard'>
              <button className='px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors'>
                📊 View Analytics
              </button>
            </Link>
            <a
              href='http://localhost:3001/health'
              target='_blank'
              rel='noopener noreferrer'
              className='px-6 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors inline-block'
            >
              🔗 API Status
            </a>
          </div>
        </motion.section>

        {/* Footer */}
        <motion.footer
          className='text-center text-sm text-neutral-500 dark:text-neutral-400'
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.8 }}
        >
          <p>PAKE System v2.0 - Phase 3 Development Environment</p>
          <p>
            Enterprise-Grade Knowledge Management & Multi-Source Research
            Platform
          </p>
        </motion.footer>
      </div>
    </div>
  );
}
