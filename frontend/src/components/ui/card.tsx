/* Enhanced Card Component - Advanced UI Building Block */
/* Quantum-level card system with adaptive states and micro-interactions */

'use client';

import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { motion, type Variants } from 'framer-motion';
import { cn } from '@/lib/utils';
import { useStore } from '@/lib/store';

// Card animation variants
const cardAnimationVariants: Variants = {
  initial: {
    scale: 1,
    y: 0,
    rotateX: 0,
    opacity: 1,
  },
  hover: {
    scale: 1.02,
    y: -4,
    rotateX: 2,
    transition: {
      type: 'spring',
      stiffness: 400,
      damping: 25,
      mass: 0.8,
    },
  },
  tap: {
    scale: 0.98,
    y: 0,
    rotateX: 0,
    transition: {
      type: 'spring',
      stiffness: 600,
      damping: 30,
    },
  },
  focus: {
    scale: 1.01,
    y: -2,
    transition: {
      type: 'spring',
      stiffness: 300,
      damping: 20,
    },
  },
};

const cardVariants = cva(
  'relative rounded-xl border bg-white shadow-sm transition-all duration-200 dark:bg-neutral-900 dark:border-neutral-800',
  {
    variants: {
      variant: {
        default:
          'border-neutral-200 hover:border-neutral-300 dark:border-neutral-800 dark:hover:border-neutral-700',
        outlined:
          'border-2 border-neutral-300 hover:border-brand-primary-500 dark:border-neutral-700 dark:hover:border-brand-primary-400',
        filled:
          'bg-neutral-50 border-neutral-200 hover:bg-neutral-100 dark:bg-neutral-800 dark:border-neutral-700 dark:hover:bg-neutral-750',
        gradient:
          'bg-gradient-to-br from-brand-primary-50 to-brand-secondary-50 border-brand-primary-200 hover:from-brand-primary-100 hover:to-brand-secondary-100 dark:from-brand-primary-900/20 dark:to-brand-secondary-900/20',
        glass:
          'backdrop-blur-md bg-white/80 border-white/20 shadow-lg hover:bg-white/90 dark:bg-neutral-900/80 dark:border-neutral-700/20 dark:hover:bg-neutral-900/90',
        success:
          'border-success-200 bg-success-50 hover:bg-success-100 dark:border-success-800 dark:bg-success-900/20 dark:hover:bg-success-900/30',
        warning:
          'border-warning-200 bg-warning-50 hover:bg-warning-100 dark:border-warning-800 dark:bg-warning-900/20 dark:hover:bg-warning-900/30',
        error:
          'border-error-200 bg-error-50 hover:bg-error-100 dark:border-error-800 dark:bg-error-900/20 dark:hover:bg-error-900/30',
      },
      size: {
        sm: 'p-3',
        default: 'p-4',
        lg: 'p-6',
        xl: 'p-8',
      },
      elevation: {
        none: 'shadow-none',
        sm: 'shadow-sm hover:shadow-md',
        default: 'shadow-md hover:shadow-lg',
        lg: 'shadow-lg hover:shadow-xl',
        xl: 'shadow-xl hover:shadow-2xl',
      },
      rounded: {
        none: 'rounded-none',
        sm: 'rounded-sm',
        default: 'rounded-xl',
        lg: 'rounded-2xl',
        xl: 'rounded-3xl',
        full: 'rounded-full',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
      elevation: 'default',
      rounded: 'default',
    },
  }
);

interface CardProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof cardVariants> {
  asChild?: boolean;
  interactive?: boolean;
  loading?: boolean;
  disabled?: boolean;
  href?: string;
  target?: string;
  rel?: string;
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  (
    {
      className,
      variant,
      size,
      elevation,
      rounded,
      interactive = false,
      loading = false,
      disabled = false,
      href,
      target,
      rel,
      children,
      onClick,
      ...props
    },
    ref
  ) => {
    const { user, recordInteraction } = useStore();
    const animationsEnabled = user.reducedMotion ? false : true;

    const handleClick = React.useCallback(
      (event: React.MouseEvent<HTMLDivElement>) => {
        if (disabled || loading) return;

        const startTime = performance.now();

        if (onClick) {
          onClick(event);
        }

        // Navigate if href is provided
        if (href) {
          const endTime = performance.now();
          recordInteraction(endTime - startTime);

          if (target === '_blank') {
            window.open(href, target, rel ? undefined : 'noopener,noreferrer');
          } else {
            window.location.href = href;
          }
        }
      },
      [disabled, loading, onClick, href, target, rel, recordInteraction]
    );

    return (
      <motion.div
        ref={ref}
        className={cn(
          cardVariants({ variant, size, elevation, rounded }),
          {
            'cursor-pointer': interactive || href,
            'cursor-not-allowed opacity-60': disabled,
            'overflow-hidden': loading,
          },
          className
        )}
        variants={
          interactive && animationsEnabled ? cardAnimationVariants : undefined
        }
        initial='initial'
        whileHover={
          !disabled && animationsEnabled && interactive ? 'hover' : undefined
        }
        whileTap={
          !disabled && animationsEnabled && interactive ? 'tap' : undefined
        }
        whileFocus={
          !disabled && animationsEnabled && interactive ? 'focus' : undefined
        }
        onClick={handleClick}
        tabIndex={interactive ? 0 : undefined}
        role={interactive ? 'button' : undefined}
        aria-disabled={disabled}
        data-loading={loading}
        data-testid='card'
        {...props}
      >
        {/* Loading overlay */}
        {loading && (
          <motion.div
            className='absolute inset-0 bg-white/80 dark:bg-neutral-900/80 flex items-center justify-center z-10 rounded-[inherit]'
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <motion.div
              className='w-6 h-6 border-2 border-brand-primary-600 border-t-transparent rounded-full'
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
              aria-label='Loading'
            />
          </motion.div>
        )}

        {children}
      </motion.div>
    );
  }
);
Card.displayName = 'Card';

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    data-slot='card-header'
    className={cn(
      '@container/card-header grid auto-rows-min grid-rows-[auto_auto] items-start gap-1.5 px-6 has-data-[slot=card-action]:grid-cols-[1fr_auto] [.border-b]:pb-6',
      className
    )}
    {...props}
  />
));
CardHeader.displayName = 'CardHeader';

const CardTitle = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, children, ...props }, ref) => (
  <div
    ref={ref}
    data-slot='card-title'
    className={cn(
      'text-lg font-semibold leading-none tracking-tight text-neutral-900 dark:text-neutral-100',
      className
    )}
    {...props}
  >
    {children}
  </div>
));
CardTitle.displayName = 'CardTitle';

const CardDescription = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    data-slot='card-description'
    className={cn('text-sm text-neutral-600 dark:text-neutral-400', className)}
    {...props}
  />
));
CardDescription.displayName = 'CardDescription';

const CardAction = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    data-slot='card-action'
    className={cn(
      'col-start-2 row-span-2 row-start-1 self-start justify-self-end',
      className
    )}
    {...props}
  />
));
CardAction.displayName = 'CardAction';

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    data-slot='card-content'
    className={cn('px-6 pt-0', className)}
    {...props}
  />
));
CardContent.displayName = 'CardContent';

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    data-slot='card-footer'
    className={cn('flex items-center px-6 pt-4 [.border-t]:pt-6', className)}
    {...props}
  />
));
CardFooter.displayName = 'CardFooter';

// Specialized Card Components
interface StatsCardProps extends Omit<CardProps, 'children'> {
  title: string;
  value: string | number;
  change?: string;
  trend?: 'up' | 'down' | 'neutral';
  icon?: React.ReactNode;
  description?: string;
}

const StatsCard = React.forwardRef<HTMLDivElement, StatsCardProps>(
  (
    { title, value, change, trend = 'neutral', icon, description, ...props },
    ref
  ) => {
    const getTrendColor = () => {
      switch (trend) {
        case 'up':
          return 'text-success-600 dark:text-success-400';
        case 'down':
          return 'text-error-600 dark:text-error-400';
        default:
          return 'text-neutral-600 dark:text-neutral-400';
      }
    };

    const getTrendIcon = () => {
      switch (trend) {
        case 'up':
          return '↗';
        case 'down':
          return '↘';
        default:
          return '→';
      }
    };

    return (
      <Card ref={ref} interactive {...props}>
        <CardContent className='p-6'>
          <div className='flex items-center justify-between'>
            <div className='flex-1'>
              <p className='text-sm font-medium text-neutral-600 dark:text-neutral-400'>
                {title}
              </p>
              <p className='text-2xl font-bold text-neutral-900 dark:text-neutral-100'>
                {value}
              </p>
              {change && (
                <p
                  className={cn(
                    'text-sm flex items-center gap-1 mt-1',
                    getTrendColor()
                  )}
                >
                  <span>{getTrendIcon()}</span>
                  {change}
                </p>
              )}
              {description && (
                <p className='text-xs text-neutral-500 dark:text-neutral-500 mt-2'>
                  {description}
                </p>
              )}
            </div>
            {icon && (
              <div className='text-2xl text-neutral-400 dark:text-neutral-600'>
                {icon}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }
);
StatsCard.displayName = 'StatsCard';

interface MetricCardProps extends Omit<CardProps, 'children'> {
  title: string;
  metrics: Array<{
    label: string;
    value: string | number;
    unit?: string;
    trend?: 'up' | 'down' | 'neutral';
  }>;
  timeRange?: string;
}

const MetricCard = React.forwardRef<HTMLDivElement, MetricCardProps>(
  ({ title, metrics, timeRange, ...props }, ref) => (
    <Card ref={ref} {...props}>
      <CardHeader>
        <div className='flex items-center justify-between'>
          <CardTitle>{title}</CardTitle>
          {timeRange && (
            <span className='text-xs text-neutral-500 dark:text-neutral-500'>
              {timeRange}
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className='grid grid-cols-1 gap-4'>
          {metrics.map((metric, index) => (
            <div key={index} className='flex items-center justify-between'>
              <span className='text-sm text-neutral-600 dark:text-neutral-400'>
                {metric.label}
              </span>
              <div className='flex items-center gap-1'>
                <span className='text-sm font-medium text-neutral-900 dark:text-neutral-100'>
                  {metric.value}
                  {metric.unit && ` ${metric.unit}`}
                </span>
                {metric.trend && metric.trend !== 'neutral' && (
                  <span
                    className={cn(
                      'text-xs',
                      metric.trend === 'up'
                        ? 'text-success-600 dark:text-success-400'
                        : 'text-error-600 dark:text-error-400'
                    )}
                  >
                    {metric.trend === 'up' ? '↗' : '↘'}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
);
MetricCard.displayName = 'MetricCard';

export {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardAction,
  CardDescription,
  CardContent,
  StatsCard,
  MetricCard,
  cardVariants,
};
