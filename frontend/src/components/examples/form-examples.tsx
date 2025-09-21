/* Form Examples - Comprehensive Form Demonstrations */
/* Showcasing transcendent form capabilities with real-world use cases */

'use client';

import * as React from 'react';
import { motion } from 'framer-motion';
import {
  Form,
  FormField,
  FormLabel,
  FormMessage,
  FormGroup,
  useForm,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

// Example 1: User Registration Form
interface RegistrationFormData {
  email: string;
  REDACTED_SECRET: string;
  confirmPassword: string;
  firstName: string;
  lastName: string;
  termsAccepted: boolean;
}

const validateEmail = (email: string): string | undefined => {
  if (!email) return 'Email is required';
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return 'Please enter a valid email address';
  }
  return undefined;
};

const validatePassword = (REDACTED_SECRET: string): string | undefined => {
  if (!REDACTED_SECRET) return 'Password is required';
  if (REDACTED_SECRET.length < 8) return 'Password must be at least 8 characters';
  if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(REDACTED_SECRET)) {
    return 'Password must contain at least one lowercase letter, one uppercase letter, and one number';
  }
  return undefined;
};

export function RegistrationFormExample() {
  const { formContextValue, values, handleSubmit, isSubmitting, reset } =
    useForm<RegistrationFormData>({
      initialValues: {
        email: '',
        REDACTED_SECRET: '',
        confirmPassword: '',
        firstName: '',
        lastName: '',
        termsAccepted: false,
      },
      validationSchema: {
        email: validateEmail,
        REDACTED_SECRET: validatePassword,
        confirmPassword: (confirmPassword: string) => {
          if (!confirmPassword) return 'Please confirm your REDACTED_SECRET';
          if (confirmPassword !== values.REDACTED_SECRET) {
            return 'Passwords do not match';
          }
          return undefined;
        },
        firstName: (firstName: string) => {
          if (!firstName) return 'First name is required';
          if (firstName.length < 2)
            return 'First name must be at least 2 characters';
          return undefined;
        },
        lastName: (lastName: string) => {
          if (!lastName) return 'Last name is required';
          if (lastName.length < 2)
            return 'Last name must be at least 2 characters';
          return undefined;
        },
        termsAccepted: (accepted: boolean) => {
          if (!accepted) return 'You must accept the terms and conditions';
          return undefined;
        },
      },
      onSubmit: async data => {
        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 2000));
        console.log('Registration data:', data);
        alert('Registration successful!');
      },
    });

  return (
    <Card className='max-w-md mx-auto'>
      <CardHeader>
        <CardTitle>Create Account</CardTitle>
      </CardHeader>
      <CardContent>
        <Form
          formContextValue={formContextValue}
          onSubmit={handleSubmit}
          variant='default'
        >
          <FormGroup>
            <div className='grid grid-cols-2 gap-4'>
              <FormField name='firstName'>
                <FormLabel required>First Name</FormLabel>
                <Input
                  value={values.firstName}
                  onChange={e =>
                    formContextValue.setField('firstName', e.target.value)
                  }
                  placeholder='John'
                  error={formContextValue.errors.firstName}
                />
                <FormMessage type='error'>
                  {formContextValue.errors.firstName}
                </FormMessage>
              </FormField>

              <FormField name='lastName'>
                <FormLabel required>Last Name</FormLabel>
                <Input
                  value={values.lastName}
                  onChange={e =>
                    formContextValue.setField('lastName', e.target.value)
                  }
                  placeholder='Doe'
                  error={formContextValue.errors.lastName}
                />
                <FormMessage type='error'>
                  {formContextValue.errors.lastName}
                </FormMessage>
              </FormField>
            </div>
          </FormGroup>

          <FormField name='email'>
            <FormLabel required>Email Address</FormLabel>
            <Input
              type='email'
              value={values.email}
              onChange={e => formContextValue.setField('email', e.target.value)}
              placeholder='john@example.com'
              leftIcon='📧'
              error={formContextValue.errors.email}
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
            />
            <FormMessage type='error'>
              {formContextValue.errors.REDACTED_SECRET}
            </FormMessage>
          </FormField>

          <FormField name='confirmPassword'>
            <FormLabel required>Confirm Password</FormLabel>
            <Input
              type='REDACTED_SECRET'
              value={values.confirmPassword}
              onChange={e =>
                formContextValue.setField('confirmPassword', e.target.value)
              }
              placeholder='Confirm your REDACTED_SECRET'
              showPasswordToggle
              error={formContextValue.errors.confirmPassword}
            />
            <FormMessage type='error'>
              {formContextValue.errors.confirmPassword}
            </FormMessage>
          </FormField>

          <FormField name='termsAccepted'>
            <div className='flex items-center gap-2'>
              <input
                type='checkbox'
                id='terms'
                checked={values.termsAccepted}
                onChange={e =>
                  formContextValue.setField('termsAccepted', e.target.checked)
                }
                className='w-4 h-4 text-brand-primary-600 bg-neutral-100 border-neutral-300 rounded focus:ring-brand-primary-500'
              />
              <FormLabel htmlFor='terms' required className='text-sm'>
                I accept the Terms and Conditions
              </FormLabel>
            </div>
            <FormMessage type='error'>
              {formContextValue.errors.termsAccepted}
            </FormMessage>
          </FormField>

          <div className='flex gap-3'>
            <Button
              type='submit'
              loading={isSubmitting}
              disabled={isSubmitting}
              className='flex-1'
            >
              Create Account
            </Button>
            <Button
              type='button'
              variant='outline'
              onClick={reset}
              disabled={isSubmitting}
            >
              Reset
            </Button>
          </div>
        </Form>
      </CardContent>
    </Card>
  );
}

// Example 2: Contact Form with Advanced Features
interface ContactFormData {
  name: string;
  email: string;
  subject: string;
  message: string;
  priority: 'low' | 'medium' | 'high';
  subscribe: boolean;
}

export function ContactFormExample() {
  const { formContextValue, values, handleSubmit, isSubmitting, isDirty } =
    useForm<ContactFormData>({
      initialValues: {
        name: '',
        email: '',
        subject: '',
        message: '',
        priority: 'medium',
        subscribe: false,
      },
      validationSchema: {
        name: (name: string) => {
          if (!name) return 'Name is required';
          if (name.length < 2) return 'Name must be at least 2 characters';
          return undefined;
        },
        email: validateEmail,
        subject: (subject: string) => {
          if (!subject) return 'Subject is required';
          if (subject.length < 5)
            return 'Subject must be at least 5 characters';
          return undefined;
        },
        message: (message: string) => {
          if (!message) return 'Message is required';
          if (message.length < 10)
            return 'Message must be at least 10 characters';
          if (message.length > 500)
            return 'Message must be less than 500 characters';
          return undefined;
        },
        priority: () => undefined, // No validation needed
        subscribe: () => undefined, // No validation needed
      },
      onSubmit: async data => {
        await new Promise(resolve => setTimeout(resolve, 1500));
        console.log('Contact form data:', data);
        alert('Message sent successfully!');
      },
    });

  return (
    <Card className='max-w-lg mx-auto'>
      <CardHeader>
        <CardTitle>Contact Us</CardTitle>
      </CardHeader>
      <CardContent>
        <Form
          formContextValue={formContextValue}
          onSubmit={handleSubmit}
          variant='card'
        >
          <FormField name='name'>
            <FormLabel required>Full Name</FormLabel>
            <Input
              value={values.name}
              onChange={e => formContextValue.setField('name', e.target.value)}
              placeholder='Your full name'
              leftIcon='👤'
              clearable
              onClear={() => formContextValue.setField('name', '')}
              error={formContextValue.errors.name}
            />
            <FormMessage type='error'>
              {formContextValue.errors.name}
            </FormMessage>
          </FormField>

          <FormField name='email'>
            <FormLabel required>Email Address</FormLabel>
            <Input
              type='email'
              value={values.email}
              onChange={e => formContextValue.setField('email', e.target.value)}
              placeholder='your.email@example.com'
              leftIcon='📧'
              error={formContextValue.errors.email}
            />
            <FormMessage type='error'>
              {formContextValue.errors.email}
            </FormMessage>
          </FormField>

          <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
            <FormField name='subject'>
              <FormLabel required>Subject</FormLabel>
              <Input
                value={values.subject}
                onChange={e =>
                  formContextValue.setField('subject', e.target.value)
                }
                placeholder='Brief subject line'
                error={formContextValue.errors.subject}
              />
              <FormMessage type='error'>
                {formContextValue.errors.subject}
              </FormMessage>
            </FormField>

            <FormField name='priority'>
              <FormLabel>Priority</FormLabel>
              <select
                value={values.priority}
                onChange={e =>
                  formContextValue.setField('priority', e.target.value)
                }
                className='flex h-10 w-full rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-950 px-3 py-2 text-sm focus:border-brand-primary-500 focus:outline-none focus:ring-2 focus:ring-brand-primary-500/20'
              >
                <option value='low'>Low Priority</option>
                <option value='medium'>Medium Priority</option>
                <option value='high'>High Priority</option>
              </select>
            </FormField>
          </div>

          <FormField name='message'>
            <FormLabel required>Message</FormLabel>
            <div className='space-y-2'>
              <textarea
                value={values.message}
                onChange={e =>
                  formContextValue.setField('message', e.target.value)
                }
                placeholder='Your detailed message...'
                rows={5}
                maxLength={500}
                className={cn(
                  'flex w-full rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-950 px-3 py-2 text-sm placeholder:text-neutral-500 focus:border-brand-primary-500 focus:outline-none focus:ring-2 focus:ring-brand-primary-500/20 resize-vertical',
                  formContextValue.errors.message &&
                    'border-error-500 focus:border-error-500 focus:ring-error-500/20'
                )}
              />
              <div className='flex justify-between items-center'>
                <FormMessage type='error'>
                  {formContextValue.errors.message}
                </FormMessage>
                <div className='text-xs text-neutral-500 dark:text-neutral-400'>
                  {values.message.length} / 500
                </div>
              </div>
            </div>
          </FormField>

          <FormField name='subscribe'>
            <div className='flex items-center gap-2'>
              <input
                type='checkbox'
                id='subscribe'
                checked={values.subscribe}
                onChange={e =>
                  formContextValue.setField('subscribe', e.target.checked)
                }
                className='w-4 h-4 text-brand-primary-600 bg-neutral-100 border-neutral-300 rounded focus:ring-brand-primary-500'
              />
              <FormLabel htmlFor='subscribe' className='text-sm font-normal'>
                Subscribe to our newsletter for updates
              </FormLabel>
            </div>
          </FormField>

          <div className='flex gap-3'>
            <Button
              type='submit'
              loading={isSubmitting}
              disabled={isSubmitting}
              className='flex-1'
              variant={isDirty ? 'default' : 'outline'}
            >
              {isSubmitting ? 'Sending...' : 'Send Message'}
            </Button>
          </div>
        </Form>
      </CardContent>
    </Card>
  );
}

// Example 3: Login Form with Loading States
interface LoginFormData {
  email: string;
  REDACTED_SECRET: string;
  rememberMe: boolean;
}

export function LoginFormExample() {
  const [asyncValidating, setAsyncValidating] = React.useState(false);

  const { formContextValue, values, handleSubmit, isSubmitting } =
    useForm<LoginFormData>({
      initialValues: {
        email: '',
        REDACTED_SECRET: '',
        rememberMe: false,
      },
      validationSchema: {
        email: async (email: string) => {
          if (!email) return 'Email is required';
          if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            return 'Please enter a valid email address';
          }

          // Simulate async email validation
          setAsyncValidating(true);
          await new Promise(resolve => setTimeout(resolve, 1000));
          setAsyncValidating(false);

          // Simulate server validation
          if (email === 'taken@example.com') {
            return 'Account not found';
          }

          return undefined;
        },
        REDACTED_SECRET: validatePassword,
        rememberMe: () => undefined,
      },
      onSubmit: async data => {
        await new Promise(resolve => setTimeout(resolve, 2000));
        console.log('Login data:', data);
        alert('Login successful!');
      },
    });

  return (
    <Card className='max-w-sm mx-auto'>
      <CardHeader>
        <CardTitle>Sign In</CardTitle>
      </CardHeader>
      <CardContent>
        <Form
          formContextValue={formContextValue}
          onSubmit={handleSubmit}
          variant='floating'
        >
          <FormField name='email'>
            <FormLabel required>Email</FormLabel>
            <Input
              type='email'
              value={values.email}
              onChange={e => formContextValue.setField('email', e.target.value)}
              placeholder='Enter your email'
              leftIcon='📧'
              loading={asyncValidating}
              error={formContextValue.errors.email}
              variant='filled'
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
              variant='filled'
            />
            <FormMessage type='error'>
              {formContextValue.errors.REDACTED_SECRET}
            </FormMessage>
          </FormField>

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
              />
              <FormLabel htmlFor='rememberMe' className='text-sm font-normal'>
                Remember me for 30 days
              </FormLabel>
            </div>
          </FormField>

          <Button
            type='submit'
            loading={isSubmitting}
            disabled={isSubmitting || asyncValidating}
            className='w-full'
            size='lg'
          >
            {isSubmitting ? 'Signing In...' : 'Sign In'}
          </Button>

          <div className='text-center'>
            <button
              type='button'
              className='text-sm text-brand-primary-600 hover:text-brand-primary-700 dark:text-brand-primary-400'
            >
              Forgot your REDACTED_SECRET?
            </button>
          </div>
        </Form>
      </CardContent>
    </Card>
  );
}

// Container component for all examples
export function FormExamplesShowcase() {
  return (
    <div className='min-h-screen bg-gradient-to-br from-neutral-50 to-neutral-100 dark:from-neutral-950 dark:to-neutral-900 p-4 lg:p-8'>
      <motion.div
        className='max-w-6xl mx-auto space-y-12'
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <header className='text-center space-y-4'>
          <h1 className='text-4xl font-bold text-neutral-900 dark:text-neutral-100'>
            Form Examples
          </h1>
          <p className='text-lg text-neutral-600 dark:text-neutral-400 max-w-2xl mx-auto'>
            Comprehensive demonstrations of our transcendent form system with
            real-world use cases, advanced validation, and cognitive ergonomics.
          </p>
        </header>

        <div className='grid grid-cols-1 xl:grid-cols-2 gap-12'>
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2, duration: 0.5 }}
          >
            <h2 className='text-2xl font-semibold text-neutral-900 dark:text-neutral-100 mb-6'>
              User Registration
            </h2>
            <RegistrationFormExample />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3, duration: 0.5 }}
          >
            <h2 className='text-2xl font-semibold text-neutral-900 dark:text-neutral-100 mb-6'>
              Contact Form
            </h2>
            <ContactFormExample />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4, duration: 0.5 }}
            className='xl:col-start-1 xl:col-end-3 flex justify-center'
          >
            <div className='w-full max-w-md'>
              <h2 className='text-2xl font-semibold text-neutral-900 dark:text-neutral-100 mb-6 text-center'>
                Login Form
              </h2>
              <LoginFormExample />
            </div>
          </motion.div>
        </div>
      </motion.div>
    </div>
  );
}
