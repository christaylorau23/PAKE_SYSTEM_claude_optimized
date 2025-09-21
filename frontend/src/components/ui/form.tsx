/* Advanced Form Components - Transcendent Form Management System */
/* Quantum-level form validation with cognitive ergonomics */

'use client';

import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { useStore } from '@/lib/store';

// Form animation variants
const formAnimationVariants = {
  hidden: {
    opacity: 0,
    y: 20,
    transition: { duration: 0.2 },
  },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.3,
      ease: 'easeOut',
    },
  },
  exit: {
    opacity: 0,
    y: -20,
    transition: { duration: 0.2 },
  },
};

const fieldAnimationVariants = {
  hidden: { opacity: 0, x: -10 },
  visible: {
    opacity: 1,
    x: 0,
    transition: {
      type: 'spring',
      stiffness: 400,
      damping: 25,
    },
  },
  error: {
    x: [0, -4],
    transition: {
      type: 'spring',
      stiffness: 600,
      damping: 10,
      duration: 0.6,
    },
  },
};

// Form variants
const formVariants = cva(
  'space-y-6 p-6 bg-white dark:bg-neutral-900 rounded-lg border border-neutral-200 dark:border-neutral-800 shadow-sm',
  {
    variants: {
      variant: {
        default: '',
        card: 'shadow-lg border-2',
        inline: 'p-4 space-y-4',
        compact: 'p-3 space-y-3 text-sm',
        floating:
          'shadow-xl border-0 bg-white/95 dark:bg-neutral-900/95 backdrop-blur-sm',
      },
      size: {
        sm: 'max-w-sm',
        default: 'max-w-md',
        lg: 'max-w-lg',
        xl: 'max-w-xl',
        full: 'w-full',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

// Form field validation state
export interface FormFieldState {
  value: unknown;
  error?: string;
  touched: boolean;
  validating: boolean;
}

// Form validation function type
export type FormValidator<T> = (
  value: T
) => string | undefined | Promise<string | undefined>;

// Form field configuration
export interface FormFieldConfig<T = unknown> {
  name: string;
  label?: string;
  required?: boolean;
  validator?: FormValidator<T>;
  initialValue?: T;
  dependencies?: string[];
}

// Form context
interface FormContextValue {
  fields: Record<string, FormFieldState>;
  setField: (name: string, value: unknown) => void;
  validateField: (name: string) => Promise<void>;
  validateForm: () => Promise<boolean>;
  isSubmitting: boolean;
  errors: Record<string, string>;
  touched: Record<string, boolean>;
  reset: () => void;
}

const FormContext = React.createContext<FormContextValue | null>(null);

export const useFormContext = () => {
  const context = React.useContext(FormContext);
  if (!context) {
    throw new Error('useFormContext must be used within a Form component');
  }
  return context;
};

// Form hook
export interface UseFormOptions<T extends Record<string, unknown>> {
  initialValues?: Partial<T>;
  validationSchema?: Record<keyof T, FormValidator<T[keyof T]>>;
  onSubmit?: (values: T) => void | Promise<void>;
  validateOnChange?: boolean;
  validateOnBlur?: boolean;
}

export function useForm<T extends Record<string, unknown>>(
  options: UseFormOptions<T> = {}
) {
  const { user } = useStore();
  const {
    initialValues = {},
    validationSchema = {},
    onSubmit,
    validateOnChange = true,
    validateOnBlur = true,
  } = options;

  const [fields, setFields] = React.useState<Record<string, FormFieldState>>(
    () => {
      const initialFields: Record<string, FormFieldState> = {};
      Object.entries(initialValues).forEach(([name, value]) => {
        initialFields[name] = {
          value,
          touched: false,
          validating: false,
        };
      });
      return initialFields;
    }
  );

  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [submitCount, setSubmitCount] = React.useState(0);

  // Set field value
  const setField = React.useCallback(
    (name: string, value: unknown) => {
      setFields(prev => ({
        ...prev,
        [name]: {
          ...prev[name],
          value,
          touched: true,
        },
      }));

      if (validateOnChange && validationSchema[name]) {
        validateField(name);
      }
    },
    [validateOnChange, validationSchema]
  );

  // Validate single field
  const validateField = React.useCallback(
    async (name: string) => {
      const validator = validationSchema[name];
      if (!validator) return;

      setFields(prev => ({
        ...prev,
        [name]: { ...prev[name], validating: true },
      }));

      try {
        const fieldValue = fields[name]?.value;
        const error = await validator(fieldValue);

        setFields(prev => ({
          ...prev,
          [name]: {
            ...prev[name],
            error,
            validating: false,
          },
        }));
      } catch (validationError) {
        setFields(prev => ({
          ...prev,
          [name]: {
            ...prev[name],
            error: 'Validation failed',
            validating: false,
          },
        }));
      }
    },
    [validationSchema, fields]
  );

  // Validate entire form
  const validateForm = React.useCallback(async (): Promise<boolean> => {
    const validationPromises = Object.keys(validationSchema).map(name =>
      validateField(name)
    );

    await Promise.all(validationPromises);

    // Check if any fields have errors
    const hasErrors = Object.values(fields).some(field => field.error);
    return !hasErrors;
  }, [validationSchema, validateField, fields]);

  // Submit form
  const handleSubmit = React.useCallback(
    async (event?: React.FormEvent) => {
      if (event) {
        event.preventDefault();
      }

      setIsSubmitting(true);
      setSubmitCount(prev => prev + 1);

      try {
        const isValid = await validateForm();
        if (!isValid) {
          user.hapticFeedback?.('error');
          return;
        }

        const values = Object.entries(fields).reduce(
          (acc, [name, field]) => {
            acc[name] = field.value;
            return acc;
          },
          {} as Record<string, unknown>
        ) as T;

        await onSubmit?.(values);
        user.hapticFeedback?.('success');
      } catch (error) {
        console.error('Form submission error:', error);
        user.hapticFeedback?.('error');
      } finally {
        setIsSubmitting(false);
      }
    },
    [validateForm, fields, onSubmit, user]
  );

  // Reset form
  const reset = React.useCallback(() => {
    setFields(() => {
      const resetFields: Record<string, FormFieldState> = {};
      Object.entries(initialValues).forEach(([name, value]) => {
        resetFields[name] = {
          value,
          touched: false,
          validating: false,
        };
      });
      return resetFields;
    });
    setIsSubmitting(false);
    setSubmitCount(0);
  }, [initialValues]);

  // Computed values
  const errors = React.useMemo(() => {
    return Object.entries(fields).reduce(
      (acc, [name, field]) => {
        if (field.error) {
          acc[name] = field.error;
        }
        return acc;
      },
      {} as Record<string, string>
    );
  }, [fields]);

  const touched = React.useMemo(() => {
    return Object.entries(fields).reduce(
      (acc, [name, field]) => {
        acc[name] = field.touched;
        return acc;
      },
      {} as Record<string, boolean>
    );
  }, [fields]);

  const values = React.useMemo(() => {
    return Object.entries(fields).reduce(
      (acc, [name, field]) => {
        acc[name] = field.value;
        return acc;
      },
      {} as Record<string, unknown>
    ) as T;
  }, [fields]);

  const isValid = React.useMemo(() => {
    return Object.values(fields).every(field => !field.error);
  }, [fields]);

  const isDirty = React.useMemo(() => {
    return Object.values(fields).some(field => field.touched);
  }, [fields]);

  return {
    fields,
    values,
    errors,
    touched,
    isSubmitting,
    isValid,
    isDirty,
    submitCount,
    setField,
    validateField,
    validateForm,
    handleSubmit,
    reset,
    // Form context value
    formContextValue: {
      fields,
      setField,
      validateField,
      validateForm,
      isSubmitting,
      errors,
      touched,
      reset,
    } as FormContextValue,
  };
}

// Form component props
interface FormProps
  extends React.FormHTMLAttributes<HTMLFormElement>,
    VariantProps<typeof formVariants> {
  children: React.ReactNode;
  formContextValue?: FormContextValue;
  loading?: boolean;
  disabled?: boolean;
}

// Form component
const Form = React.forwardRef<HTMLFormElement, FormProps>(
  (
    {
      className,
      variant,
      size,
      children,
      formContextValue,
      loading = false,
      disabled = false,
      onSubmit,
      ...props
    },
    ref
  ) => {
    const { user } = useStore();
    const animationsEnabled = !user.reducedMotion;

    const handleSubmit = React.useCallback(
      (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (formContextValue) {
          formContextValue.validateForm();
        }
        onSubmit?.(event);
      },
      [formContextValue, onSubmit]
    );

    const formContent = (
      <motion.form
        ref={ref}
        className={cn(formVariants({ variant, size }), className)}
        onSubmit={handleSubmit}
        variants={animationsEnabled ? formAnimationVariants : undefined}
        initial='hidden'
        animate='visible'
        exit='exit'
        noValidate
        aria-busy={loading || formContextValue?.isSubmitting}
        data-testid='form'
        {...props}
      >
        {loading && (
          <motion.div
            className='absolute inset-0 bg-white/80 dark:bg-neutral-900/80 flex items-center justify-center z-10 rounded-[inherit]'
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className='w-8 h-8 border-2 border-brand-primary-600 border-t-transparent rounded-full'
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
              aria-label='Loading form'
            />
          </motion.div>
        )}

        <fieldset
          disabled={disabled || loading || formContextValue?.isSubmitting}
        >
          {children}
        </fieldset>
      </motion.form>
    );

    if (formContextValue) {
      return (
        <FormContext.Provider value={formContextValue}>
          {formContent}
        </FormContext.Provider>
      );
    }

    return formContent;
  }
);
Form.displayName = 'Form';

// Form field component
interface FormFieldProps {
  name: string;
  children: React.ReactNode;
  className?: string;
}

const FormField = React.forwardRef<HTMLDivElement, FormFieldProps>(
  ({ name, children, className }, ref) => {
    const { user } = useStore();
    const animationsEnabled = !user.reducedMotion;
    const { fields } = useFormContext();

    const field = fields[name];
    const hasError = field?.error && field?.touched;

    return (
      <motion.div
        ref={ref}
        className={cn('space-y-2', className)}
        variants={animationsEnabled ? fieldAnimationVariants : undefined}
        animate={hasError ? 'error' : 'visible'}
        initial='hidden'
        data-testid={`form-field-${name}`}
      >
        {children}
      </motion.div>
    );
  }
);
FormField.displayName = 'FormField';

// Form label component
interface FormLabelProps extends React.LabelHTMLAttributes<HTMLLabelElement> {
  required?: boolean;
}

const FormLabel = React.forwardRef<HTMLLabelElement, FormLabelProps>(
  ({ className, required, children, ...props }, ref) => (
    <label
      ref={ref}
      className={cn(
        'text-sm font-medium leading-none text-neutral-900 dark:text-neutral-100 peer-disabled:cursor-not-allowed peer-disabled:opacity-70',
        className
      )}
      {...props}
    >
      {children}
      {required && (
        <span className='text-error-500 ml-1' aria-label='required'>
          *
        </span>
      )}
    </label>
  )
);
FormLabel.displayName = 'FormLabel';

// Form message component
interface FormMessageProps extends React.HTMLAttributes<HTMLParagraphElement> {
  type?: 'error' | 'success' | 'warning' | 'info';
}

const FormMessage = React.forwardRef<HTMLParagraphElement, FormMessageProps>(
  ({ className, type = 'error', children, ...props }, ref) => {
    const { user } = useStore();
    const animationsEnabled = !user.reducedMotion;

    const getTypeStyles = () => {
      switch (type) {
        case 'error':
          return 'text-error-600 dark:text-error-400';
        case 'success':
          return 'text-success-600 dark:text-success-400';
        case 'warning':
          return 'text-warning-600 dark:text-warning-400';
        case 'info':
          return 'text-brand-primary-600 dark:text-brand-primary-400';
        default:
          return 'text-neutral-600 dark:text-neutral-400';
      }
    };

    const getIcon = () => {
      switch (type) {
        case 'error':
          return '⚠️';
        case 'success':
          return '✅';
        case 'warning':
          return '⚠️';
        case 'info':
          return 'ℹ️';
        default:
          return '';
      }
    };

    if (!children) return null;

    return (
      <motion.p
        ref={ref}
        className={cn(
          'text-xs flex items-center gap-1',
          getTypeStyles(),
          className
        )}
        initial={animationsEnabled ? { opacity: 0, y: -4 } : undefined}
        animate={animationsEnabled ? { opacity: 1, y: 0 } : undefined}
        exit={animationsEnabled ? { opacity: 0, y: -4 } : undefined}
        transition={{ duration: 0.2 }}
        role={type === 'error' ? 'alert' : undefined}
        {...props}
      >
        {getIcon() && <span>{getIcon()}</span>}
        {children}
      </motion.p>
    );
  }
);
FormMessage.displayName = 'FormMessage';

// Form group component for grouping related fields
interface FormGroupProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  description?: string;
}

const FormGroup = React.forwardRef<HTMLDivElement, FormGroupProps>(
  ({ className, title, description, children, ...props }, ref) => (
    <div ref={ref} className={cn('space-y-4', className)} {...props}>
      {title && (
        <div className='space-y-1'>
          <h3 className='text-base font-semibold text-neutral-900 dark:text-neutral-100'>
            {title}
          </h3>
          {description && (
            <p className='text-sm text-neutral-600 dark:text-neutral-400'>
              {description}
            </p>
          )}
        </div>
      )}
      <div className='space-y-4'>{children}</div>
    </div>
  )
);
FormGroup.displayName = 'FormGroup';

export {
  Form,
  FormField,
  FormLabel,
  FormMessage,
  FormGroup,
  FormContext,
  formVariants,
  type FormFieldState,
  type FormValidator,
  type FormFieldConfig,
};
