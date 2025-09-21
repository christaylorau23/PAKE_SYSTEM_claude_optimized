/* TanStack Query Provider - Advanced Server State Management Provider */
/* React Query integration with Suspense and error boundaries */

'use client';

import React from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { getOptimizedQueryClient } from '@/lib/api/query-client';
import { useStore } from '@/lib/store';
import { SuspenseBoundary } from '@/lib/concurrent/suspense-boundary';

interface QueryProviderProps {
  children: React.ReactNode;
  enableDevtools?: boolean;
}

// Query provider with performance monitoring
export const QueryProvider: React.FC<QueryProviderProps> = ({
  children,
  enableDevtools = process.env.NODE_ENV === 'development',
}) => {
  const [queryClient] = React.useState(() => getOptimizedQueryClient());
  const { features, updatePerformanceMetrics } = useStore();

  // Monitor query client performance
  React.useEffect(() => {
    const startTime = performance.now();

    return () => {
      const endTime = performance.now();
      updatePerformanceMetrics({
        renderTime: endTime - startTime,
      });
    };
  }, [updatePerformanceMetrics]);

  // Network status monitoring
  React.useEffect(() => {
    const handleOnline = () => {
      queryClient.resumePausedMutations();
      queryClient.refetchQueries({ type: 'active' });
    };

    const handleOffline = () => {
      // Queries will be paused automatically
      console.log('[QueryProvider] Application went offline - queries paused');
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [queryClient]);

  return (
    <QueryClientProvider client={queryClient}>
      <SuspenseBoundary
        name='Query Provider'
        level='component'
        fallback={
          <div className='flex items-center justify-center p-4'>
            <div className='animate-spin rounded-full h-8 w-8 border-b-2 border-brand-primary-600'></div>
            <span className='ml-2 text-sm text-neutral-600 dark:text-neutral-400'>
              Initializing data layer...
            </span>
          </div>
        }
      >
        {children}
      </SuspenseBoundary>

      {/* Development tools */}
      {enableDevtools && features.enableAdvancedAnalytics && (
        <ReactQueryDevtools
          initialIsOpen={false}
          position='bottom-right'
          toggleButtonProps={{
            style: {
              backgroundColor: 'oklch(0.58 0.24 240)',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              padding: '8px 12px',
              fontSize: '12px',
              fontWeight: '500',
              cursor: 'pointer',
              zIndex: 99999,
            },
          }}
        />
      )}
    </QueryClientProvider>
  );
};

// Hook for accessing query client
export const useQueryClient = () => {
  const { QueryClient } = require('@tanstack/react-query');
  return React.useContext(QueryClient);
};

// Performance monitoring hook for queries
export const useQueryPerformance = () => {
  const { updatePerformanceMetrics } = useStore();

  const trackQuery = React.useCallback(
    (queryKey: string[], startTime: number) => {
      return () => {
        const endTime = performance.now();
        const duration = endTime - startTime;

        updatePerformanceMetrics({
          renderTime: duration,
        });

        // Log slow queries in development
        if (process.env.NODE_ENV === 'development' && duration > 1000) {
          console.warn(
            `[Slow Query] ${queryKey.join(':')} took ${duration.toFixed(2)}ms`
          );
        }
      };
    },
    [updatePerformanceMetrics]
  );

  return { trackQuery };
};

export default QueryProvider;
