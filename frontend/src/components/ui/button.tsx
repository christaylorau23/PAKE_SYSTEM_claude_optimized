'use client';

import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { motion, type Variants } from 'framer-motion';

import { cn } from '@/lib/utils';
import { useStore } from '@/lib/store';
import { useScreenReader } from '@/lib/accessibility/screen-reader';

const buttonVariants = cva(
  "relative inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          'bg-brand-primary-600 text-white shadow-sm hover:bg-brand-primary-700 focus-visible:ring-brand-primary-500 active:bg-brand-primary-800',
        destructive:
          'bg-error-600 text-white shadow-sm hover:bg-error-700 focus-visible:ring-error-500 active:bg-error-800',
        outline:
          'border border-neutral-300 bg-white shadow-sm hover:bg-neutral-50 hover:text-neutral-900 focus-visible:ring-brand-primary-500 active:bg-neutral-100 dark:border-neutral-700 dark:bg-neutral-900 dark:hover:bg-neutral-800 dark:hover:text-neutral-50',
        secondary:
          'bg-neutral-100 text-neutral-900 shadow-sm hover:bg-neutral-200 focus-visible:ring-brand-primary-500 active:bg-neutral-300 dark:bg-neutral-800 dark:text-neutral-50 dark:hover:bg-neutral-700',
        ghost:
          'hover:bg-neutral-100 hover:text-neutral-900 focus-visible:ring-brand-primary-500 active:bg-neutral-200 dark:hover:bg-neutral-800 dark:hover:text-neutral-50',
        link: 'text-brand-primary-600 underline-offset-4 hover:underline focus-visible:ring-brand-primary-500 dark:text-brand-primary-400',
        success:
          'bg-success-600 text-white shadow-sm hover:bg-success-700 focus-visible:ring-success-500 active:bg-success-800',
        warning:
          'bg-warning-600 text-white shadow-sm hover:bg-warning-700 focus-visible:ring-warning-500 active:bg-warning-800',
      },
      size: {
        xs: 'h-7 px-2 text-xs gap-1 rounded-md',
        sm: 'h-8 px-3 text-sm gap-1.5 rounded-md',
        default: 'h-9 px-4 py-2 gap-2',
        lg: 'h-10 px-6 text-base gap-2',
        xl: 'h-12 px-8 text-lg gap-3 rounded-xl',
        icon: 'size-9',
        'icon-sm': 'size-8',
        'icon-lg': 'size-10',
        'icon-xl': 'size-12',
      },
      elevation: {
        flat: '',
        raised: 'shadow-sm hover:shadow-md',
        floating: 'shadow-lg hover:shadow-xl',
      },
      rounded: {
        none: 'rounded-none',
        sm: 'rounded-sm',
        md: 'rounded-md',
        lg: 'rounded-lg',
        xl: 'rounded-xl',
        full: 'rounded-full',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
      elevation: 'flat',
      rounded: 'lg',
    },
  }
);

// Animation variants for micro-interactions (keeping for future extensions)
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const buttonAnimationVariants: Variants = {
  initial: {
    scale: 1,
    y: 0,
  },
  hover: {
    scale: 1.02,
    y: -1,
    transition: {
      type: 'spring',
      stiffness: 400,
      damping: 17,
      mass: 0.8,
    },
  },
  tap: {
    scale: 0.98,
    y: 0,
    transition: {
      type: 'spring',
      stiffness: 600,
      damping: 20,
      mass: 0.6,
    },
  },
  loading: {
    scale: 0.95,
    transition: {
      type: 'spring',
      stiffness: 300,
      damping: 15,
    },
  },
  disabled: {
    scale: 1,
    opacity: 0.5,
    transition: {
      type: 'tween',
      duration: 0.2,
    },
  },
};

const pulseVariants: Variants = {
  pulse: {
    scale: [1, 1.05, 1],
    transition: {
      duration: 2,
      repeat: Infinity,
      repeatType: 'reverse',
      ease: 'easeInOut',
    },
  },
};

const loadingSpinnerVariants: Variants = {
  spin: {
    rotate: 360,
    transition: {
      duration: 1,
      repeat: Infinity,
      ease: 'linear',
    },
  },
};

interface ButtonProps
  extends Omit<
      React.ComponentProps<typeof motion.button>,
      'whileHover' | 'whileTap'
    >,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
  pulse?: boolean;
  ripple?: boolean;
  hapticFeedback?: boolean;
  loadingText?: string;
  successState?: boolean;
  errorState?: boolean;
  tooltip?: string;
  kbd?: string; // Keyboard shortcut display
  onSuccess?: () => void;
  onError?: () => void;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
      elevation,
      rounded,
      asChild = false,
      loading = false,
      pulse = false,
      ripple = true,
      hapticFeedback = false,
      loadingText,
      successState = false,
      errorState = false,
      tooltip,
      kbd,
      disabled,
      children,
      onClick,
      onFocus,
      onBlur,
      onSuccess,
      onError,
      ...props
    },
    ref
  ) => {
    const {
      user,
      recordInteraction,
      addPendingAnimation,
      markAnimationComplete,
    } = useStore();
    const { announce } = useScreenReader();

    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const [isPressed, setIsPressed] = React.useState(false);
    const [ripples, setRipples] = React.useState<
      Array<{ id: string; x: number; y: number }>
    >([]);
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const [interactionStart, setInteractionStart] = React.useState<number>(0);

    const buttonRef = React.useRef<HTMLButtonElement>(null);
    const animationsEnabled = user.reducedMotion ? false : true;

    // Combine refs
    React.useImperativeHandle(ref, () => buttonRef.current!);

    // Handle click with performance tracking and haptic feedback
    const handleClick = React.useCallback(
      (event: React.MouseEvent<HTMLButtonElement>) => {
        if (loading || disabled) return;

        const startTime = performance.now();
        setInteractionStart(startTime);

        // Create ripple effect
        if (ripple && animationsEnabled && buttonRef.current) {
          const rect = buttonRef.current.getBoundingClientRect();
          const x = event.clientX - rect.left;
          const y = event.clientY - rect.top;
          const rippleId = `ripple-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

          setRipples(prev => [...prev, { id: rippleId, x, y }]);

          // Remove ripple after animation
          setTimeout(() => {
            setRipples(prev => prev.filter(r => r.id !== rippleId));
          }, 600);
        }

        // Haptic feedback for supported devices
        if (hapticFeedback && 'vibrate' in navigator) {
          navigator.vibrate(10); // Short, subtle vibration
        }

        // Track interaction latency
        addPendingAnimation('button-click');

        // Call original onClick handler
        if (onClick) {
          Promise.resolve(onClick(event))
            .then(() => {
              const endTime = performance.now();
              const latency = endTime - startTime;
              recordInteraction(latency);
              markAnimationComplete('button-click');

              if (onSuccess) {
                onSuccess();
              }
            })
            .catch(() => {
              if (onError) {
                onError();
              }
            });
        }
      },
      [
        loading,
        disabled,
        ripple,
        animationsEnabled,
        hapticFeedback,
        onClick,
        recordInteraction,
        addPendingAnimation,
        markAnimationComplete,
        onSuccess,
        onError,
      ]
    );

    // Handle focus with screen reader announcements
    const handleFocus = React.useCallback(
      (event: React.FocusEvent<HTMLButtonElement>) => {
        if (tooltip) {
          announce(tooltip, { priority: 'polite' });
        }

        if (kbd) {
          announce(`Keyboard shortcut: ${kbd}`, {
            priority: 'polite',
            delay: 500,
          });
        }

        if (onFocus) {
          onFocus(event);
        }
      },
      [tooltip, kbd, announce, onFocus]
    );

    // Handle blur
    const handleBlur = React.useCallback(
      (event: React.FocusEvent<HTMLButtonElement>) => {
        setIsPressed(false);

        if (onBlur) {
          onBlur(event);
        }
      },
      [onBlur]
    );

    // Determine current state
    const currentVariant = successState
      ? 'success'
      : errorState
        ? 'destructive'
        : variant;
    const isDisabled = disabled || loading;

    // Animation variants based on state
    const getAnimationState = () => {
      if (!animationsEnabled) return 'initial';
      if (loading) return 'loading';
      if (isDisabled) return 'disabled';
      return 'initial';
    };

    const MotionComp = asChild ? motion(Slot) : motion.button;

    return (
      <MotionComp
        ref={buttonRef}
        className={cn(
          buttonVariants({
            variant: currentVariant,
            size,
            elevation,
            rounded,
            className,
          }),
          'overflow-hidden',
          {
            'cursor-not-allowed': isDisabled,
            'cursor-pointer': !isDisabled,
          }
        )}
        disabled={isDisabled}
        aria-disabled={isDisabled}
        aria-busy={loading}
        aria-describedby={
          tooltip ? `${props.id || 'button'}-tooltip` : undefined
        }
        data-state={successState ? 'success' : errorState ? 'error' : 'default'}
        data-loading={loading}
        data-testid='enhanced-button'
        variants={pulse ? pulseVariants : buttonVariants}
        initial='initial'
        animate={pulse ? 'pulse' : getAnimationState()}
        whileHover={!isDisabled && animationsEnabled ? 'hover' : undefined}
        whileTap={!isDisabled && animationsEnabled ? 'tap' : undefined}
        whileFocus={
          !isDisabled && animationsEnabled ? { scale: 1.01 } : undefined
        }
        layout={animationsEnabled}
        onClick={handleClick}
        onFocus={handleFocus}
        onBlur={handleBlur}
        onMouseDown={() => setIsPressed(true)}
        onMouseUp={() => setIsPressed(false)}
        onMouseLeave={() => setIsPressed(false)}
        {...props}
      >
        {/* Ripple effect overlay */}
        {ripple && animationsEnabled && (
          <div className='absolute inset-0 overflow-hidden pointer-events-none rounded-[inherit]'>
            {ripples.map(({ id, x, y }) => (
              <motion.div
                key={id}
                className='absolute bg-white/30 rounded-full pointer-events-none'
                style={{
                  left: x - 10,
                  top: y - 10,
                  width: 20,
                  height: 20,
                }}
                initial={{ scale: 0, opacity: 0.8 }}
                animate={{
                  scale: 4,
                  opacity: 0,
                  transition: {
                    duration: 0.6,
                    ease: 'easeOut',
                  },
                }}
              />
            ))}
          </div>
        )}

        {/* Loading spinner */}
        {loading && (
          <motion.div
            className='flex items-center gap-2'
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 10 }}
            transition={{ duration: 0.2 }}
          >
            <motion.div
              className='w-4 h-4 border-2 border-current border-t-transparent rounded-full'
              variants={loadingSpinnerVariants}
              animate='spin'
              aria-hidden='true'
              data-testid='loading-spinner'
            />
            {loadingText && <span className='text-sm'>{loadingText}</span>}
          </motion.div>
        )}

        {/* Button content */}
        {!loading && (
          <motion.div
            className='flex items-center gap-2'
            initial={false}
            animate={{
              opacity: loading ? 0 : 1,
              scale: loading ? 0.8 : 1,
            }}
            transition={{ duration: 0.2 }}
          >
            {children}
            {kbd && (
              <span
                className='ml-2 px-1.5 py-0.5 text-xs font-mono bg-black/10 rounded border dark:bg-white/10'
                aria-label={`Keyboard shortcut ${kbd}`}
              >
                {kbd}
              </span>
            )}
          </motion.div>
        )}

        {/* Success/Error state indicators */}
        {(successState || errorState) && (
          <motion.div
            className='absolute inset-0 flex items-center justify-center bg-inherit rounded-[inherit]'
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ duration: 0.3 }}
          >
            {successState && (
              <motion.svg
                className='w-5 h-5'
                fill='none'
                stroke='currentColor'
                viewBox='0 0 24 24'
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 0.5, delay: 0.2 }}
              >
                <motion.path
                  strokeLinecap='round'
                  strokeLinejoin='round'
                  strokeWidth={2}
                  d='M5 13l4 4L19 7'
                />
              </motion.svg>
            )}
            {errorState && (
              <motion.svg
                className='w-5 h-5'
                fill='none'
                stroke='currentColor'
                viewBox='0 0 24 24'
                initial={{ rotate: 0 }}
                animate={{ rotate: 360 }}
                transition={{ duration: 0.3 }}
              >
                <path
                  strokeLinecap='round'
                  strokeLinejoin='round'
                  strokeWidth={2}
                  d='M6 18L18 6M6 6l12 12'
                />
              </motion.svg>
            )}
          </motion.div>
        )}
      </MotionComp>
    );
  }
);

Button.displayName = 'Button';

export { Button, buttonVariants };
