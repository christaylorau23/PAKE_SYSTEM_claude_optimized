/* Dashboard Layout - Advanced Nested Layout System */
/* Responsive dashboard shell with navigation and contextual sidebars */

'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useStore } from '@/lib/store';
import { cn } from '@/lib/utils';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

const sidebarVariants = {
  open: {
    width: 280,
    transition: {
      type: 'spring',
      stiffness: 300,
      damping: 30,
    },
  },
  closed: {
    width: 64,
    transition: {
      type: 'spring',
      stiffness: 300,
      damping: 30,
    },
  },
};

const menuItems = [
  {
    id: 'overview',
    label: 'Overview',
    icon: '📊',
    href: '/dashboard',
    description: 'System overview and key metrics',
  },
  {
    id: 'analytics',
    label: 'Analytics',
    icon: '📈',
    href: '/dashboard/analytics',
    description: 'Detailed analytics and reports',
  },
  {
    id: 'performance',
    label: 'Performance',
    icon: '⚡',
    href: '/dashboard/performance',
    description: 'Performance monitoring',
  },
  {
    id: 'forms',
    label: 'Forms',
    icon: '📝',
    href: '/forms',
    description: 'Advanced form components',
  },
  {
    id: 'users',
    label: 'Users',
    icon: '👥',
    href: '/dashboard/users',
    description: 'User management',
  },
  {
    id: 'settings',
    label: 'Settings',
    icon: '⚙️',
    href: '/dashboard/settings',
    description: 'System configuration',
  },
];

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const { ui, user } = useStore();
  const [activeItem, setActiveItem] = React.useState('overview');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false);

  const isSidebarCollapsed = ui.sidebarCollapsed;
  const animationsEnabled = !user.reducedMotion;

  // Handle navigation
  const handleNavigation = (item: (typeof menuItems)[0]) => {
    setActiveItem(item.id);
    setIsMobileMenuOpen(false);

    // Navigate (in a real app, you'd use Next.js router)
    if (typeof window !== 'undefined') {
      window.history.pushState({}, '', item.href);
    }
  };

  // Toggle sidebar
  const toggleSidebar = () => {
    useStore.getState().toggleSidebar();
  };

  return (
    <div className='min-h-screen bg-neutral-50 dark:bg-neutral-950 flex'>
      {/* Desktop Sidebar */}
      <motion.aside
        className={cn(
          'hidden lg:flex flex-col bg-white dark:bg-neutral-900 border-r border-neutral-200 dark:border-neutral-800 relative z-10',
          'shadow-sm'
        )}
        variants={animationsEnabled ? sidebarVariants : undefined}
        animate={isSidebarCollapsed ? 'closed' : 'open'}
        initial={false}
      >
        {/* Sidebar Header */}
        <div className='p-6 border-b border-neutral-200 dark:border-neutral-800'>
          <div className='flex items-center gap-3'>
            <motion.div
              className='w-8 h-8 bg-brand-primary-600 rounded-lg flex items-center justify-center text-white font-bold'
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
            >
              P
            </motion.div>
            <AnimatePresence>
              {!isSidebarCollapsed && (
                <motion.div
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -10 }}
                  transition={{ duration: 0.2 }}
                  className='flex flex-col'
                >
                  <h1 className='text-lg font-semibold text-neutral-900 dark:text-neutral-100'>
                    PAKE System
                  </h1>
                  <p className='text-xs text-neutral-500 dark:text-neutral-400'>
                    Admin Dashboard
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Navigation */}
        <nav className='flex-1 p-4 space-y-2'>
          {menuItems.map(item => (
            <motion.button
              key={item.id}
              className={cn(
                'w-full flex items-center gap-3 px-3 py-3 rounded-lg text-left transition-all',
                'hover:bg-neutral-100 dark:hover:bg-neutral-800',
                activeItem === item.id
                  ? 'bg-brand-primary-50 dark:bg-brand-primary-900/20 text-brand-primary-700 dark:text-brand-primary-400 border border-brand-primary-200 dark:border-brand-primary-800'
                  : 'text-neutral-600 dark:text-neutral-400'
              )}
              onClick={() => handleNavigation(item)}
              whileHover={animationsEnabled ? { scale: 1.02 } : undefined}
              whileTap={animationsEnabled ? { scale: 0.98 } : undefined}
              title={isSidebarCollapsed ? item.label : undefined}
            >
              <span className='text-xl flex-shrink-0'>{item.icon}</span>
              <AnimatePresence>
                {!isSidebarCollapsed && (
                  <motion.div
                    initial={{ opacity: 0, width: 0 }}
                    animate={{ opacity: 1, width: 'auto' }}
                    exit={{ opacity: 0, width: 0 }}
                    transition={{ duration: 0.2 }}
                    className='flex flex-col overflow-hidden'
                  >
                    <span className='font-medium'>{item.label}</span>
                    <span className='text-xs text-neutral-500 dark:text-neutral-400'>
                      {item.description}
                    </span>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.button>
          ))}
        </nav>

        {/* Sidebar Toggle */}
        <div className='p-4 border-t border-neutral-200 dark:border-neutral-800'>
          <Button
            variant='ghost'
            size='icon'
            onClick={toggleSidebar}
            className='w-full'
            title={isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isSidebarCollapsed ? '→' : '←'}
          </Button>
        </div>
      </motion.aside>

      {/* Mobile Menu Overlay */}
      <AnimatePresence>
        {isMobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className='lg:hidden fixed inset-0 bg-black/50 z-50'
            onClick={() => setIsMobileMenuOpen(false)}
          >
            <motion.aside
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              className='w-80 h-full bg-white dark:bg-neutral-900 shadow-xl'
              onClick={e => e.stopPropagation()}
            >
              <div className='p-6 border-b border-neutral-200 dark:border-neutral-800'>
                <div className='flex items-center justify-between'>
                  <div className='flex items-center gap-3'>
                    <div className='w-8 h-8 bg-brand-primary-600 rounded-lg flex items-center justify-center text-white font-bold'>
                      P
                    </div>
                    <div>
                      <h1 className='text-lg font-semibold text-neutral-900 dark:text-neutral-100'>
                        PAKE System
                      </h1>
                      <p className='text-xs text-neutral-500 dark:text-neutral-400'>
                        Admin Dashboard
                      </p>
                    </div>
                  </div>
                  <Button
                    variant='ghost'
                    size='icon'
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    ✕
                  </Button>
                </div>
              </div>

              <nav className='p-4 space-y-2'>
                {menuItems.map(item => (
                  <button
                    key={item.id}
                    className={cn(
                      'w-full flex items-center gap-3 px-3 py-3 rounded-lg text-left transition-all',
                      'hover:bg-neutral-100 dark:hover:bg-neutral-800',
                      activeItem === item.id
                        ? 'bg-brand-primary-50 dark:bg-brand-primary-900/20 text-brand-primary-700 dark:text-brand-primary-400 border border-brand-primary-200 dark:border-brand-primary-800'
                        : 'text-neutral-600 dark:text-neutral-400'
                    )}
                    onClick={() => handleNavigation(item)}
                  >
                    <span className='text-xl'>{item.icon}</span>
                    <div>
                      <div className='font-medium'>{item.label}</div>
                      <div className='text-xs text-neutral-500 dark:text-neutral-400'>
                        {item.description}
                      </div>
                    </div>
                  </button>
                ))}
              </nav>
            </motion.aside>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content Area */}
      <main className='flex-1 flex flex-col min-w-0'>
        {/* Top Navigation Bar */}
        <header className='lg:hidden bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800 p-4'>
          <div className='flex items-center justify-between'>
            <div className='flex items-center gap-3'>
              <Button
                variant='ghost'
                size='icon'
                onClick={() => setIsMobileMenuOpen(true)}
                className='lg:hidden'
              >
                ☰
              </Button>
              <h1 className='text-lg font-semibold text-neutral-900 dark:text-neutral-100'>
                Dashboard
              </h1>
            </div>
            <div className='flex items-center gap-2'>
              <Button variant='ghost' size='sm'>
                Settings
              </Button>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div className='flex-1 overflow-auto'>
          <motion.div
            key={activeItem}
            initial={animationsEnabled ? { opacity: 0, y: 10 } : undefined}
            animate={animationsEnabled ? { opacity: 1, y: 0 } : undefined}
            transition={{ duration: 0.2 }}
            className='h-full'
          >
            {children}
          </motion.div>
        </div>
      </main>
    </div>
  );
}
