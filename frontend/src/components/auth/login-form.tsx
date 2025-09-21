/* Advanced Login Form - Enterprise Authentication */

'use client';

import * as React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '@/lib/auth/auth-context';
import {
  Form,
  FormField,
  FormLabel,
  FormMessage,
  useForm,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface LoginFormData {
  email: string;
  REDACTED_SECRET: string;
  rememberMe: boolean;
  mfaCode?: string;
}

interface LoginFormProps {
  onSuccess?: () => void;
  redirectTo?: string;
  showSocialLogin?: boolean;
  showBiometric?: boolean;
  className?: string;
}

export function LoginForm({
  onSuccess,
  redirectTo,
  showSocialLogin = true,
  showBiometric = true,
  className,
}: LoginFormProps) {
  const {
    signIn,
    signInWithGoogle,
    signInWithGithub,
    signInWithMicrosoft,
    authenticateWithBiometric,
    isLoading,
    error: authError,
    status,
  } = useAuth();

  const [showMFA, setShowMFA] = React.useState(false);
  const [socialLoading, setSocialLoading] = React.useState<string | null>(null);

  const { formContextValue, values, handleSubmit, isSubmitting, reset } =
    useForm<LoginFormData>({
      initialValues: {
        email: '',
        REDACTED_SECRET: '',
        rememberMe: false,
        mfaCode: '',
      },
      validationSchema: {
        email: (email: string) => {
          if (!email) return 'Email is required';
          if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            return 'Please enter a valid email address';
          }
          return undefined;
        },
        REDACTED_SECRET: (REDACTED_SECRET: string) => {
          if (!REDACTED_SECRET) return 'Password is required';
          if (REDACTED_SECRET.length < 6)
            return 'Password must be at least 6 characters';
          return undefined;
        },
        mfaCode: (code?: string) => {
          if (showMFA && !code) return 'MFA code is required';
          if (showMFA && code && !/^\d{6}$/.test(code)) {
            return 'MFA code must be 6 digits';
          }
          return undefined;
        },
        rememberMe: () => undefined,
      },
      onSubmit: async data => {
        try {
          await signIn(data.email, data.REDACTED_SECRET, {
            rememberMe: data.rememberMe,
            mfaCode: data.mfaCode,
          });

          if (status === 'authenticated') {
            onSuccess?.();
            if (redirectTo) {
              window.location.href = redirectTo;
            }
          }
        } catch (loginError) {
          console.error('Login failed:', loginError);
        }
      },
    });

  // Handle social login
  const handleSocialLogin = async (
    provider: 'google' | 'github' | 'microsoft'
  ) => {
    setSocialLoading(provider);

    try {
      switch (provider) {
        case 'google':
          await signInWithGoogle();
          break;
        case 'github':
          await signInWithGithub();
          break;
        case 'microsoft':
          await signInWithMicrosoft();
          break;
      }

      onSuccess?.();
      if (redirectTo) {
        window.location.href = redirectTo;
      }
    } catch (socialError) {
      console.error('Social login failed:', socialError);
    } finally {
      setSocialLoading(null);
    }
  };

  // Handle biometric authentication
  const handleBiometricLogin = async () => {
    try {
      await authenticateWithBiometric();
      onSuccess?.();
      if (redirectTo) {
        window.location.href = redirectTo;
      }
    } catch (biometricError) {
      console.error('Biometric login failed:', biometricError);
    }
  };

  // Show MFA field if login succeeds but MFA is required
  React.useEffect(() => {
    if (authError?.includes('MFA') || authError?.includes('Two-factor')) {
      setShowMFA(true);
    }
  }, [authError]);

  return (
    <Card className={cn('w-full max-w-md mx-auto', className)}>
      <CardHeader className='text-center'>
        <div className='w-16 h-16 bg-brand-primary-600 rounded-2xl flex items-center justify-center mx-auto mb-4'>
          <span className='text-2xl text-white font-bold'>P</span>
        </div>
        <CardTitle className='text-2xl'>Welcome Back</CardTitle>
        <p className='text-sm text-neutral-600 dark:text-neutral-400'>
          Sign in to your PAKE System account
        </p>
      </CardHeader>

      <CardContent className='space-y-6'>
        <Form
          formContextValue={formContextValue}
          onSubmit={handleSubmit}
          className='space-y-4'
        >
          <FormField name='email'>
            <FormLabel required>Email Address</FormLabel>
            <Input
              type='email'
              value={values.email}
              onChange={e => formContextValue.setField('email', e.target.value)}
              placeholder='Enter your email'
              leftIcon='📧'
              error={formContextValue.errors.email}
              disabled={isSubmitting}
            />
            <FormMessage type='error'>
              {formContextValue.errors.email}
            </FormMessage>
          </FormField>

          <FormField name='REDACTED_SECRET'>
            <FormLabel required>Password</FormLabel>
            <Input
              type='REDACTED_SECRET'
              value={values.REDACTED_SECRET}
              onChange={e =>
                formContextValue.setField('REDACTED_SECRET', e.target.value)
              }
              placeholder='Enter your REDACTED_SECRET'
              showPasswordToggle
              error={formContextValue.errors.REDACTED_SECRET}
              disabled={isSubmitting}
            />
            <FormMessage type='error'>
              {formContextValue.errors.REDACTED_SECRET}
            </FormMessage>
          </FormField>

          <AnimatePresence>
            {showMFA && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
              >
                <FormField name='mfaCode'>
                  <FormLabel required>Two-Factor Code</FormLabel>
                  <Input
                    value={values.mfaCode || ''}
                    onChange={e =>
                      formContextValue.setField('mfaCode', e.target.value)
                    }
                    placeholder='Enter 6-digit code'
                    maxLength={6}
                    error={formContextValue.errors.mfaCode}
                    disabled={isSubmitting}
                    leftIcon='🔐'
                  />
                  <FormMessage type='error'>
                    {formContextValue.errors.mfaCode}
                  </FormMessage>
                </FormField>
              </motion.div>
            )}
          </AnimatePresence>

          <div className='flex items-center justify-between'>
            <FormField name='rememberMe'>
              <div className='flex items-center gap-2'>
                <input
                  type='checkbox'
                  id='rememberMe'
                  checked={values.rememberMe}
                  onChange={e =>
                    formContextValue.setField('rememberMe', e.target.checked)
                  }
                  className='w-4 h-4 text-brand-primary-600 bg-neutral-100 border-neutral-300 rounded focus:ring-brand-primary-500'
                  disabled={isSubmitting}
                />
                <FormLabel htmlFor='rememberMe' className='text-sm font-normal'>
                  Remember me
                </FormLabel>
              </div>
            </FormField>

            <button
              type='button'
              className='text-sm text-brand-primary-600 hover:text-brand-primary-700 dark:text-brand-primary-400 transition-colors'
              disabled={isSubmitting}
            >
              Forgot REDACTED_SECRET?
            </button>
          </div>

          {authError && <FormMessage type='error'>{authError}</FormMessage>}

          <Button
            type='submit'
            loading={isSubmitting}
            disabled={isSubmitting}
            className='w-full'
            size='lg'
          >
            {isSubmitting ? 'Signing In...' : 'Sign In'}
          </Button>
        </Form>

        {/* Biometric Authentication */}
        {showBiometric && (
          <div className='space-y-3'>
            <div className='relative'>
              <div className='absolute inset-0 flex items-center'>
                <div className='w-full border-t border-neutral-200 dark:border-neutral-800' />
              </div>
              <div className='relative flex justify-center text-xs uppercase'>
                <span className='bg-white dark:bg-neutral-900 px-2 text-neutral-500'>
                  Or continue with
                </span>
              </div>
            </div>

            <Button
              variant='outline'
              onClick={handleBiometricLogin}
              disabled={isLoading}
              className='w-full'
            >
              <span className='mr-2'>👆</span>
              Use Biometric
            </Button>
          </div>
        )}

        {/* Social Login */}
        {showSocialLogin && (
          <div className='space-y-3'>
            {!showBiometric && (
              <div className='relative'>
                <div className='absolute inset-0 flex items-center'>
                  <div className='w-full border-t border-neutral-200 dark:border-neutral-800' />
                </div>
                <div className='relative flex justify-center text-xs uppercase'>
                  <span className='bg-white dark:bg-neutral-900 px-2 text-neutral-500'>
                    Or continue with
                  </span>
                </div>
              </div>
            )}

            <div className='grid grid-cols-1 gap-3'>
              <Button
                variant='outline'
                onClick={() => handleSocialLogin('google')}
                disabled={isLoading}
                loading={socialLoading === 'google'}
                className='w-full'
              >
                <span className='mr-2'>🔵</span>
                Google
              </Button>

              <div className='grid grid-cols-2 gap-3'>
                <Button
                  variant='outline'
                  onClick={() => handleSocialLogin('github')}
                  disabled={isLoading}
                  loading={socialLoading === 'github'}
                >
                  <span className='mr-2'>⚫</span>
                  GitHub
                </Button>

                <Button
                  variant='outline'
                  onClick={() => handleSocialLogin('microsoft')}
                  disabled={isLoading}
                  loading={socialLoading === 'microsoft'}
                >
                  <span className='mr-2'>🔷</span>
                  Microsoft
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Sign Up Link */}
        <div className='text-center text-sm'>
          <span className='text-neutral-600 dark:text-neutral-400'>
            Don't have an account?{' '}
          </span>
          <button
            type='button'
            className='text-brand-primary-600 hover:text-brand-primary-700 dark:text-brand-primary-400 font-medium transition-colors'
          >
            Sign up
          </button>
        </div>
      </CardContent>
    </Card>
  );
}
