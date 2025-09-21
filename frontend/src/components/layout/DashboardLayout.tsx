'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  Menu,
  X,
  Search,
  Bell,
  User,
  Home,
  BookOpen,
  Zap,
  BarChart3,
  Settings,
  Mic,
  Video,
  Share2,
  Brain,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useScreenReader } from '@/hooks/useScreenReader';
import { ThemeToggle } from '@/components/ui/theme-toggle';

interface DashboardLayoutProps {
  children: React.ReactNode;
  userRole?: 'admin' | 'knowledge_worker' | 'executive';
}

export function DashboardLayout({
  children,
  userRole = 'admin',
}: DashboardLayoutProps) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const { announce, announcementRef } = useScreenReader();

  const navigationItems = [
    { href: '/dashboard', icon: Home, label: 'Dashboard' },
    { href: '/knowledge', icon: BookOpen, label: 'Knowledge Base' },
    { href: '/ai-showcase', icon: Brain, label: 'AI Showcase' },
    { href: '/voice-agents', icon: Mic, label: 'Voice Agents' },
    { href: '/video-generation', icon: Video, label: 'Video Generation' },
    { href: '/social-media', icon: Share2, label: 'Social Media' },
    { href: '/integrations', icon: Zap, label: 'Integrations' },
    { href: '/analytics', icon: BarChart3, label: 'Analytics' },
    { href: '/settings', icon: Settings, label: 'Settings' },
  ];

  const handleSearch = (query: string) => {
    if (query.trim()) {
      announce(`Searching for: ${query}`, 'assertive');
      // Implement search logic here
      console.log('Searching for:', query);
    }
  };

  return (
    <div className='min-h-screen bg-gray-50 dark:bg-gray-900'>
      <div
        ref={announcementRef}
        aria-live='polite'
        aria-atomic='true'
        className='sr-only'
      />

      {/* Desktop Sidebar */}
      <div className='hidden lg:flex lg:w-64 lg:flex-col lg:fixed lg:inset-y-0'>
        <div className='flex-1 flex flex-col min-h-0 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700'>
          <div className='flex-1 flex flex-col pt-5 pb-4 overflow-y-auto'>
            {/* Logo */}
            <div className='flex items-center flex-shrink-0 px-6'>
              <h1 className='text-xl font-bold text-gray-900 dark:text-white'>
                PAKE System
              </h1>
            </div>

            {/* Navigation */}
            <nav
              className='mt-8 flex-1 px-4 space-y-1'
              aria-label='Main navigation'
            >
              {navigationItems.map(item => (
                <Link
                  key={item.href}
                  href={item.href}
                  className='group flex items-center px-2 py-2 text-sm font-medium rounded-md text-foreground hover:text-foreground hover:bg-accent transition-colors'
                  aria-current={item.href === '/dashboard' ? 'page' : undefined}
                >
                  <item.icon
                    className='mr-3 flex-shrink-0 h-5 w-5 text-gray-400 group-hover:text-gray-500 dark:text-gray-500 dark:group-hover:text-gray-300'
                    aria-hidden='true'
                  />
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>

          {/* User Profile */}
          <div className='flex-shrink-0 p-4 border-t border-gray-200 dark:border-gray-700'>
            <div className='flex items-center space-x-3'>
              <div className='w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center'>
                <User className='h-4 w-4 text-white' />
              </div>
              <div>
                <p className='text-sm font-medium text-gray-700 dark:text-gray-300'>
                  {userRole === 'admin'
                    ? 'Sarah Admin'
                    : userRole === 'executive'
                      ? 'Dr. Elena CTO'
                      : 'Marcus Worker'}
                </p>
                <p className='text-xs text-gray-500 dark:text-gray-400'>
                  {userRole === 'admin'
                    ? 'System Administrator'
                    : userRole === 'executive'
                      ? 'Chief Technology Officer'
                      : 'Knowledge Worker'}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Mobile menu overlay */}
      {isMobileMenuOpen && (
        <div
          className='lg:hidden fixed inset-0 z-40 bg-black bg-opacity-50'
          aria-hidden='true'
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}

      {/* Mobile menu */}
      <div
        className={`lg:hidden fixed inset-y-0 left-0 z-50 w-64 bg-background border-r border-border transform ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'} transition-transform duration-300 ease-in-out`}
      >
        <div className='flex items-center justify-between p-4 border-b border-border'>
          <h2 className='text-lg font-semibold text-foreground'>PAKE System</h2>
          <Button
            variant='ghost'
            size='icon'
            onClick={() => setIsMobileMenuOpen(false)}
            aria-label='Close menu'
          >
            <X className='h-6 w-6' />
          </Button>
        </div>

        <nav className='mt-8 px-4 space-y-1' aria-label='Mobile navigation'>
          {navigationItems.map(item => (
            <Link
              key={item.href}
              href={item.href}
              className='group flex items-center px-2 py-2 text-sm font-medium rounded-md text-foreground hover:text-foreground hover:bg-accent transition-colors'
              onClick={() => setIsMobileMenuOpen(false)}
            >
              <item.icon className='mr-3 h-5 w-5 text-muted-foreground group-hover:text-foreground' />
              {item.label}
            </Link>
          ))}
        </nav>
      </div>

      {/* Main content */}
      <div className='lg:pl-64 flex flex-col flex-1'>
        {/* Top navigation */}
        <header className='bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700'>
          <div className='px-4 sm:px-6 lg:px-8'>
            <div className='flex items-center justify-between h-16'>
              {/* Mobile menu button */}
              <Button
                variant='ghost'
                size='icon'
                className='lg:hidden'
                onClick={() => setIsMobileMenuOpen(true)}
                aria-label='Open menu'
              >
                <Menu className='h-6 w-6' />
              </Button>

              {/* Search */}
              <div className='flex-1 flex items-center justify-center px-2 lg:ml-6 lg:justify-start'>
                <div className='max-w-lg w-full lg:max-w-xs'>
                  <label htmlFor='search' className='sr-only'>
                    Search
                  </label>
                  <div className='relative'>
                    <div className='absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none'>
                      <Search
                        className='h-5 w-5 text-gray-400'
                        aria-hidden='true'
                      />
                    </div>
                    <Input
                      id='search'
                      value={searchQuery}
                      onChange={e => setSearchQuery(e.target.value)}
                      onKeyDown={e =>
                        e.key === 'Enter' && handleSearch(searchQuery)
                      }
                      className='block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white dark:bg-gray-700 placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm'
                      placeholder='Search knowledge base...'
                    />
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className='flex items-center space-x-4'>
                <ThemeToggle />

                <Button variant='ghost' size='icon' aria-label='Notifications'>
                  <Bell className='h-5 w-5' />
                </Button>

                <Button variant='ghost' size='icon' aria-label='User menu'>
                  <User className='h-5 w-5' />
                </Button>
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className='flex-1'>{children}</main>
      </div>
    </div>
  );
}
