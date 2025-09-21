/* Advanced Input Component - Transcendent Form Building Block */
/* Quantum-level input system with adaptive states and cognitive ergonomics */

'use client';

import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { motion, type Variants } from 'framer-motion';
import { cn } from '@/lib/utils';
import { useStore } from '@/lib/store';

const inputAnimationVariants: Variants = {
  rest: {
    scale: 1,
    borderColor: 'currentColor',
    transition: {
      type: 'spring',
      stiffness: 400,
      damping: 25,
    },
  },
  focus: {
    scale: 1.01,
    borderColor: 'rgb(var(--brand-primary-500))',
    transition: {
      type: 'spring',
      stiffness: 400,
      damping: 20,
    },
  },
  error: {
    scale: 1.01,
    borderColor: 'rgb(var(--error-500))',
    x: [0, -4],
    transition: {
      x: {
        type: 'spring',
        stiffness: 600,
        damping: 10,
        duration: 0.6,
      },
    },
  },
  success: {
    scale: 1.01,
    borderColor: 'rgb(var(--success-500))',
    transition: {
      type: 'spring',
      stiffness: 400,
      damping: 20,
    },
  },
};

const inputVariants = cva(
  'flex w-full rounded-md border bg-white px-3 py-2 text-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-neutral-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-neutral-950 dark:placeholder:text-neutral-400',
  {
    variants: {
      variant: {
        default:
          'border-neutral-300 dark:border-neutral-700 focus:border-brand-primary-500 dark:focus:border-brand-primary-400',
        outlined:
          'border-2 border-neutral-300 dark:border-neutral-700 focus:border-brand-primary-500 dark:focus:border-brand-primary-400',
        filled:
          'border-transparent bg-neutral-100 dark:bg-neutral-800 focus:bg-white dark:focus:bg-neutral-900 focus:border-brand-primary-500',
        underlined:
          'border-0 border-b-2 rounded-none border-neutral-300 dark:border-neutral-700 focus:border-brand-primary-500 bg-transparent px-0',
        ghost:
          'border-transparent bg-transparent hover:bg-neutral-50 dark:hover:bg-neutral-900/50 focus:bg-white dark:focus:bg-neutral-900',
      },
      size: {
        sm: 'h-8 px-2 text-xs',
        default: 'h-10 px-3 text-sm',
        lg: 'h-12 px-4 text-base',
        xl: 'h-14 px-5 text-lg',
      },
      state: {
        default: '',
        error:
          'border-error-500 focus:border-error-500 focus:ring-error-500/20 text-error-900 dark:text-error-100',
        success:
          'border-success-500 focus:border-success-500 focus:ring-success-500/20 text-success-900 dark:text-success-100',
        warning:
          'border-warning-500 focus:border-warning-500 focus:ring-warning-500/20 text-warning-900 dark:text-warning-100',
      },
      rounded: {
        none: 'rounded-none',
        sm: 'rounded-sm',
        default: 'rounded-md',
        lg: 'rounded-lg',
        xl: 'rounded-xl',
        full: 'rounded-full',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
      state: 'default',
      rounded: 'default',
    },
  }
);

interface InputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'>,
    VariantProps<typeof inputVariants> {
  label?: string;
  description?: string;
  error?: string;
  success?: string;
  warning?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  clearable?: boolean;
  showPasswordToggle?: boolean;
  loading?: boolean;
  counter?: boolean;
  maxLength?: number;
  onClear?: () => void;
  containerClassName?: string;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    {
      className,
      containerClassName,
      variant,
      size,
      state: stateProp,
      rounded,
      type: typeProp = 'text',
      label,
      description,
      error,
      success,
      warning,
      leftIcon,
      rightIcon,
      clearable,
      showPasswordToggle,
      loading = false,
      counter = false,
      maxLength,
      value,
      onChange,
      onClear,
      disabled,
      id,
      ...props
    },
    ref
  ) => {
    const { user, recordInteraction } = useStore();
    const animationsEnabled = user.reducedMotion ? false : true;

    const [isFocused, setIsFocused] = React.useState(false);
    const [showPassword, setShowPassword] = React.useState(false);
    const [internalValue, setInternalValue] = React.useState(value || '');
    const [interactionStart, setInteractionStart] = React.useState(0);

    const inputId = id || React.useId();
    const descriptionId = description ? `${inputId}-description` : undefined;
    const errorId = error ? `${inputId}-error` : undefined;

    const currentValue = value !== undefined ? value : internalValue;
    const isControlled = value !== undefined;
    const type = showPassword ? 'text' : typeProp;

    // Determine current state
    const currentState = React.useMemo(() => {
      if (stateProp && stateProp !== 'default') return stateProp;
      if (error) return 'error';
      if (success) return 'success';
      if (warning) return 'warning';
      return 'default';
    }, [stateProp, error, success, warning]);

    // Handle value changes
    const handleChange = React.useCallback(
      (event: React.ChangeEvent<HTMLInputElement>) => {
        const newValue = event.target.value;

        if (!isControlled) {
          setInternalValue(newValue);
        }

        onChange?.(event);
      },
      [isControlled, onChange]
    );

    // Handle focus events
    const handleFocus = React.useCallback(
      (event: React.FocusEvent<HTMLInputElement>) => {
        setIsFocused(true);
        setInteractionStart(performance.now());
        props.onFocus?.(event);
      },
      [props]
    );

    const handleBlur = React.useCallback(
      (event: React.FocusEvent<HTMLInputElement>) => {
        setIsFocused(false);

        const endTime = performance.now();
        const interactionTime = endTime - interactionStart;
        recordInteraction(interactionTime);

        props.onBlur?.(event);
      },
      [interactionStart, recordInteraction, props]
    );

    // Handle clear
    const handleClear = React.useCallback(() => {
      if (!isControlled) {
        setInternalValue('');
      }

      onClear?.();

      // Trigger onChange with empty value
      if (onChange) {
        const fakeEvent = {
          target: { value: '' },
          currentTarget: { value: '' },
        } as React.ChangeEvent<HTMLInputElement>;
        onChange(fakeEvent);
      }
    }, [isControlled, onClear, onChange]);

    // Handle REDACTED_SECRET toggle
    const handlePasswordToggle = React.useCallback(() => {
      setShowPassword(prev => !prev);
    }, []);

    // Animation variant based on current state
    const animationVariant = React.useMemo(() => {
      if (!animationsEnabled) return undefined;
      if (currentState === 'error') return 'error';
      if (currentState === 'success') return 'success';
      if (isFocused) return 'focus';
      return 'rest';
    }, [animationsEnabled, currentState, isFocused]);

    const showClearButton = clearable && currentValue && !disabled;
    const showPasswordButton =
      showPasswordToggle && typeProp === 'REDACTED_SECRET' && !disabled;
    const hasRightContent =
      rightIcon || showClearButton || showPasswordButton || loading;

    return (
      <div className={cn('space-y-2', containerClassName)}>
        {/* Label */}
        {label && (
          <label
            htmlFor={inputId}
            className='text-sm font-medium leading-none text-neutral-900 dark:text-neutral-100 peer-disabled:cursor-not-allowed peer-disabled:opacity-70'
          >
            {label}
            {props.required && (
              <span className='text-error-500 ml-1' aria-label='required'>
                *
              </span>
            )}
          </label>
        )}

        {/* Input Container */}
        <div className='relative'>
          {/* Left Icon */}
          {leftIcon && (
            <div className='absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500 dark:text-neutral-400 pointer-events-none'>
              {leftIcon}
            </div>
          )}

          {/* Input Field */}
          <motion.input
            ref={ref}
            id={inputId}
            type={type}
            value={currentValue}
            onChange={handleChange}
            onFocus={handleFocus}
            onBlur={handleBlur}
            disabled={disabled || loading}
            maxLength={maxLength}
            className={cn(
              inputVariants({ variant, size, state: currentState, rounded }),
              {
                'pl-10': leftIcon,
                'pr-10': hasRightContent,
                'pr-20': showClearButton && showPasswordButton,
              },
              className
            )}
            variants={animationsEnabled ? inputAnimationVariants : undefined}
            animate={animationVariant}
            aria-describedby={cn(descriptionId, errorId)}
            aria-invalid={currentState === 'error'}
            data-testid='input'
            {...props}
          />

          {/* Right Content */}
          {hasRightContent && (
            <div className='absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1'>
              {/* Loading Spinner */}
              {loading && (
                <motion.div
                  className='w-4 h-4 border-2 border-brand-primary-600 border-t-transparent rounded-full'
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                  aria-label='Loading'
                />
              )}

              {/* Clear Button */}
              {showClearButton && (
                <motion.button
                  type='button'
                  onClick={handleClear}
                  className='w-4 h-4 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 transition-colors'
                  whileHover={animationsEnabled ? { scale: 1.1 } : undefined}
                  whileTap={animationsEnabled ? { scale: 0.9 } : undefined}
                  aria-label='Clear input'
                >
                  ✕
                </motion.button>
              )}

              {/* Password Toggle */}
              {showPasswordButton && (
                <motion.button
                  type='button'
                  onClick={handlePasswordToggle}
                  className='w-4 h-4 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 transition-colors'
                  whileHover={animationsEnabled ? { scale: 1.1 } : undefined}
                  whileTap={animationsEnabled ? { scale: 0.9 } : undefined}
                  aria-label={showPassword ? 'Hide REDACTED_SECRET' : 'Show REDACTED_SECRET'}
                >
                  {showPassword ? '🙈' : '👁️'}
                </motion.button>
              )}

              {/* Custom Right Icon */}
              {rightIcon && !loading && (
                <div className='text-neutral-500 dark:text-neutral-400'>
                  {rightIcon}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Description */}
        {description && !error && !success && !warning && (
          <p
            id={descriptionId}
            className='text-xs text-neutral-600 dark:text-neutral-400'
          >
            {description}
          </p>
        )}

        {/* Error Message */}
        {error && (
          <motion.p
            id={errorId}
            className='text-xs text-error-600 dark:text-error-400 flex items-center gap-1'
            initial={animationsEnabled ? { opacity: 0, y: -4 } : undefined}
            animate={animationsEnabled ? { opacity: 1, y: 0 } : undefined}
            transition={{ duration: 0.2 }}
          >
            <span>⚠️</span>
            {error}
          </motion.p>
        )}

        {/* Success Message */}
        {success && !error && (
          <motion.p
            className='text-xs text-success-600 dark:text-success-400 flex items-center gap-1'
            initial={animationsEnabled ? { opacity: 0, y: -4 } : undefined}
            animate={animationsEnabled ? { opacity: 1, y: 0 } : undefined}
            transition={{ duration: 0.2 }}
          >
            <span>✅</span>
            {success}
          </motion.p>
        )}

        {/* Warning Message */}
        {warning && !error && !success && (
          <motion.p
            className='text-xs text-warning-600 dark:text-warning-400 flex items-center gap-1'
            initial={animationsEnabled ? { opacity: 0, y: -4 } : undefined}
            animate={animationsEnabled ? { opacity: 1, y: 0 } : undefined}
            transition={{ duration: 0.2 }}
          >
            <span>⚠️</span>
            {warning}
          </motion.p>
        )}

        {/* Character Counter */}
        {counter && maxLength && (
          <div className='text-xs text-neutral-500 dark:text-neutral-400 text-right'>
            {String(currentValue).length} / {maxLength}
          </div>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export { Input, inputVariants };
export type { InputProps };
