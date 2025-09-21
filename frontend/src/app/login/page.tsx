/* Login Page - Authentication Portal */

'use client';

import * as React from 'react';
import { motion } from 'framer-motion';
import { AuthProvider, useAuth } from '@/lib/auth/auth-context';
import { LoginForm } from '@/components/auth/login-form';

function LoginPageContent() {
  const { status, user } = useAuth();

  // Redirect if already authenticated
  React.useEffect(() => {
    if (status === 'authenticated' && user) {
      window.location.href = '/dashboard';
    }
  }, [status, user]);

  if (status === 'authenticated') {
    return (
      <div className='min-h-screen flex items-center justify-center'>
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className='text-center space-y-4'
        >
          <div className='w-16 h-16 border-4 border-brand-primary-600 border-t-transparent rounded-full mx-auto animate-spin' />
          <p className='text-neutral-600 dark:text-neutral-400'>
            Redirecting to dashboard...
          </p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className='min-h-screen bg-gradient-to-br from-neutral-50 to-neutral-100 dark:from-neutral-950 dark:to-neutral-900 flex items-center justify-center p-4'>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className='w-full'
      >
        <LoginForm
          onSuccess={() => {
            window.location.href = '/dashboard';
          }}
          showSocialLogin={true}
          showBiometric={true}
        />
      </motion.div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <AuthProvider>
      <LoginPageContent />
    </AuthProvider>
  );
}
