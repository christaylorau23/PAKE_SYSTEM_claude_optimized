/* AI Showcase Page - Demonstrating AI-Powered Features */

'use client';

import * as React from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AIInput } from '@/components/ai/ai-input';
import { AIAnalyticsDashboard } from '@/components/analytics/ai-analytics-dashboard';
import {
  Form,
  FormField,
  FormLabel,
  FormMessage,
  useForm,
} from '@/components/ui/form';

// Showcase form data
interface ShowcaseFormData {
  name: string;
  email: string;
  company: string;
  message: string;
  preferences: string;
}

export default function AIShowcasePage() {
  const [activeDemo, setActiveDemo] = React.useState<
    'forms' | 'analytics' | 'predictions'
  >('forms');
  const [aiEvents, setAIEvents] = React.useState<
    Array<{ type: string; data: unknown; timestamp: number }>
  >([]);

  // Form with AI integration
  const { formContextValue, values, handleSubmit, isSubmitting } =
    useForm<ShowcaseFormData>({
      initialValues: {
        name: '',
        email: '',
        company: '',
        message: '',
        preferences: '',
      },
      validationSchema: {
        name: (name: string) => {
          if (!name) return 'Name is required';
          if (name.length < 2) return 'Name must be at least 2 characters';
          return undefined;
        },
        email: (email: string) => {
          if (!email) return 'Email is required';
          if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            return 'Please enter a valid email address';
          }
          return undefined;
        },
        company: (company: string) => {
          if (!company) return 'Company name is required';
          return undefined;
        },
        message: (message: string) => {
          if (!message) return 'Message is required';
          if (message.length < 10)
            return 'Message must be at least 10 characters';
          return undefined;
        },
        preferences: () => undefined,
      },
      onSubmit: async data => {
        await new Promise(resolve => setTimeout(resolve, 2000));
        console.log('AI Showcase form submitted:', data);
        alert('Form submitted successfully with AI assistance!');
      },
    });

  // Handle AI events from components
  const handleAIEvent = React.useCallback(
    (event: { type: string; data: unknown; timestamp: number }) => {
      setAIEvents(prev => [event, ...prev].slice(0, 10)); // Keep last 10 events
    },
    []
  );

  // Container animation
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        delayChildren: 0.1,
        staggerChildren: 0.1,
      },
    },
  };

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: {
        type: 'spring',
        stiffness: 300,
        damping: 24,
      },
    },
  };

  return (
    <div className='min-h-screen bg-gradient-to-br from-neutral-50 to-neutral-100 dark:from-neutral-950 dark:to-neutral-900 p-4 lg:p-8'>
      <motion.div
        className='max-w-7xl mx-auto space-y-8'
        variants={containerVariants}
        initial='hidden'
        animate='visible'
      >
        {/* Header */}
        <motion.header variants={itemVariants}>
          <div className='text-center space-y-4'>
            <h1 className='text-4xl font-bold text-neutral-900 dark:text-neutral-100 sm:text-5xl'>
              🧠 AI-Powered PAKE System
            </h1>
            <p className='text-lg text-neutral-600 dark:text-neutral-400 max-w-3xl mx-auto'>
              Experience the future of web applications with intelligent form
              assistance, predictive analytics, and cognitive user experience
              optimization.
            </p>
          </div>
        </motion.header>

        {/* Demo Navigation */}
        <motion.nav variants={itemVariants}>
          <div className='flex justify-center'>
            <div className='bg-white dark:bg-neutral-900 p-2 rounded-lg border border-neutral-200 dark:border-neutral-800 shadow-sm'>
              <div className='flex space-x-2'>
                <Button
                  variant={activeDemo === 'forms' ? 'default' : 'ghost'}
                  onClick={() => setActiveDemo('forms')}
                  size='sm'
                >
                  🤖 Smart Forms
                </Button>
                <Button
                  variant={activeDemo === 'analytics' ? 'default' : 'ghost'}
                  onClick={() => setActiveDemo('analytics')}
                  size='sm'
                >
                  📊 AI Analytics
                </Button>
                <Button
                  variant={activeDemo === 'predictions' ? 'default' : 'ghost'}
                  onClick={() => setActiveDemo('predictions')}
                  size='sm'
                >
                  🔮 Predictions
                </Button>
              </div>
            </div>
          </div>
        </motion.nav>

        {/* Demo Content */}
        <motion.div variants={itemVariants}>
          {activeDemo === 'forms' && (
            <div className='grid grid-cols-1 lg:grid-cols-2 gap-8'>
              {/* AI-Powered Form */}
              <Card className='lg:col-span-1'>
                <CardHeader>
                  <CardTitle className='flex items-center gap-2'>
                    🤖 AI-Enhanced Form
                    <span className='text-xs bg-brand-primary-100 text-brand-primary-800 px-2 py-1 rounded-full dark:bg-brand-primary-900/20 dark:text-brand-primary-400'>
                      Live Demo
                    </span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <Form
                    formContextValue={formContextValue}
                    onSubmit={handleSubmit}
                  >
                    <div className='space-y-4'>
                      <FormField name='name'>
                        <FormLabel required>Full Name</FormLabel>
                        <AIInput
                          name='name'
                          value={values.name}
                          onValueChange={value =>
                            formContextValue.setField('name', value)
                          }
                          placeholder='Enter your full name'
                          formContext={values}
                          onAIEvent={handleAIEvent}
                          aiConfig={{
                            enableSmartCompletion: true,
                            enableVoiceInput: true,
                            enableAccessibilityAI: true,
                          }}
                        />
                        <FormMessage type='error'>
                          {formContextValue.errors.name}
                        </FormMessage>
                      </FormField>

                      <FormField name='email'>
                        <FormLabel required>Email Address</FormLabel>
                        <AIInput
                          name='email'
                          type='email'
                          value={values.email}
                          onValueChange={value =>
                            formContextValue.setField('email', value)
                          }
                          placeholder='your.email@company.com'
                          formContext={values}
                          onAIEvent={handleAIEvent}
                          leftIcon='📧'
                          aiConfig={{
                            enableSmartCompletion: true,
                            enablePredictiveValidation: true,
                          }}
                        />
                        <FormMessage type='error'>
                          {formContextValue.errors.email}
                        </FormMessage>
                      </FormField>

                      <FormField name='company'>
                        <FormLabel required>Company</FormLabel>
                        <AIInput
                          name='company'
                          value={values.company}
                          onValueChange={value =>
                            formContextValue.setField('company', value)
                          }
                          placeholder='Your company name'
                          formContext={values}
                          onAIEvent={handleAIEvent}
                          leftIcon='🏢'
                          aiConfig={{
                            enableSmartCompletion: true,
                            completionDelay: 300,
                          }}
                        />
                        <FormMessage type='error'>
                          {formContextValue.errors.company}
                        </FormMessage>
                      </FormField>

                      <FormField name='message'>
                        <FormLabel required>Message</FormLabel>
                        <textarea
                          value={values.message}
                          onChange={e =>
                            formContextValue.setField('message', e.target.value)
                          }
                          placeholder='Tell us about your AI experience needs...'
                          rows={4}
                          className='flex w-full rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-950 px-3 py-2 text-sm placeholder:text-neutral-500 focus:border-brand-primary-500 focus:outline-none focus:ring-2 focus:ring-brand-primary-500/20 resize-vertical'
                        />
                        <FormMessage type='error'>
                          {formContextValue.errors.message}
                        </FormMessage>
                      </FormField>

                      <Button
                        type='submit'
                        loading={isSubmitting}
                        disabled={isSubmitting}
                        className='w-full'
                        size='lg'
                      >
                        {isSubmitting
                          ? 'Processing with AI...'
                          : '🚀 Submit with AI Enhancement'}
                      </Button>
                    </div>
                  </Form>
                </CardContent>
              </Card>

              {/* AI Events Log */}
              <Card className='lg:col-span-1'>
                <CardHeader>
                  <CardTitle>🎯 Real-Time AI Events</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className='space-y-3 max-h-96 overflow-y-auto'>
                    {aiEvents.length === 0 ? (
                      <p className='text-neutral-500 text-center py-8'>
                        Start typing in the form to see AI events...
                      </p>
                    ) : (
                      aiEvents.map((event, index) => (
                        <motion.div
                          key={index}
                          className='p-3 bg-neutral-50 dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700'
                          initial={{ opacity: 0, x: 20 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ duration: 0.3 }}
                        >
                          <div className='flex items-center justify-between mb-1'>
                            <span className='font-medium text-sm'>
                              {event.type === 'completion'
                                ? '🤖 Smart Completion'
                                : event.type === 'validation'
                                  ? '✅ AI Validation'
                                  : event.type === 'voice'
                                    ? '🎤 Voice Input'
                                    : '🧠 AI Analysis'}
                            </span>
                            <span className='text-xs text-neutral-500'>
                              {new Date(event.timestamp).toLocaleTimeString()}
                            </span>
                          </div>
                          <div className='text-xs text-neutral-600 dark:text-neutral-400'>
                            {JSON.stringify(event.data, null, 2).substring(
                              0,
                              100
                            )}
                            ...
                          </div>
                        </motion.div>
                      ))
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {activeDemo === 'analytics' && (
            <AIAnalyticsDashboard
              timeRange='1d'
              enablePredictions={true}
              enableRealTimeUpdates={true}
            />
          )}

          {activeDemo === 'predictions' && (
            <div className='grid grid-cols-1 gap-8'>
              {/* Predictive Insights */}
              <Card>
                <CardHeader>
                  <CardTitle>🔮 AI Predictive Insights</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'>
                    <motion.div
                      className='p-6 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg border border-blue-200 dark:border-blue-800'
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.1 }}
                    >
                      <div className='text-2xl mb-2'>📈</div>
                      <h4 className='font-semibold mb-2'>
                        User Engagement Prediction
                      </h4>
                      <p className='text-sm text-neutral-600 dark:text-neutral-400 mb-3'>
                        AI predicts 23% increase in user engagement over the
                        next 7 days
                      </p>
                      <div className='flex items-center text-xs text-blue-600 dark:text-blue-400'>
                        <div className='w-2 h-2 bg-blue-500 rounded-full mr-2'></div>
                        89% confidence
                      </div>
                    </motion.div>

                    <motion.div
                      className='p-6 bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-lg border border-green-200 dark:border-green-800'
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.2 }}
                    >
                      <div className='text-2xl mb-2'>⚡</div>
                      <h4 className='font-semibold mb-2'>
                        Performance Optimization
                      </h4>
                      <p className='text-sm text-neutral-600 dark:text-neutral-400 mb-3'>
                        AI suggests 34% form completion improvement with smart
                        assistance
                      </p>
                      <div className='flex items-center text-xs text-green-600 dark:text-green-400'>
                        <div className='w-2 h-2 bg-green-500 rounded-full mr-2'></div>
                        92% confidence
                      </div>
                    </motion.div>

                    <motion.div
                      className='p-6 bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 rounded-lg border border-purple-200 dark:border-purple-800'
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.3 }}
                    >
                      <div className='text-2xl mb-2'>🎯</div>
                      <h4 className='font-semibold mb-2'>Feature Adoption</h4>
                      <p className='text-sm text-neutral-600 dark:text-neutral-400 mb-3'>
                        Voice input adoption expected to reach 85% within 30
                        days
                      </p>
                      <div className='flex items-center text-xs text-purple-600 dark:text-purple-400'>
                        <div className='w-2 h-2 bg-purple-500 rounded-full mr-2'></div>
                        76% confidence
                      </div>
                    </motion.div>
                  </div>
                </CardContent>
              </Card>

              {/* AI Capabilities Showcase */}
              <Card>
                <CardHeader>
                  <CardTitle>🧠 AI Capabilities Overview</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className='grid grid-cols-1 md:grid-cols-2 gap-6'>
                    <div className='space-y-4'>
                      <h4 className='font-semibold text-neutral-900 dark:text-neutral-100'>
                        🤖 Smart Form Features
                      </h4>
                      <ul className='space-y-2 text-sm text-neutral-600 dark:text-neutral-400'>
                        <li className='flex items-center gap-2'>
                          <div className='w-1.5 h-1.5 bg-brand-primary-500 rounded-full'></div>
                          Intelligent field completion based on context
                        </li>
                        <li className='flex items-center gap-2'>
                          <div className='w-1.5 h-1.5 bg-brand-primary-500 rounded-full'></div>
                          Predictive validation before submission
                        </li>
                        <li className='flex items-center gap-2'>
                          <div className='w-1.5 h-1.5 bg-brand-primary-500 rounded-full'></div>
                          Voice input with speech recognition
                        </li>
                        <li className='flex items-center gap-2'>
                          <div className='w-1.5 h-1.5 bg-brand-primary-500 rounded-full'></div>
                          AI-enhanced accessibility features
                        </li>
                        <li className='flex items-center gap-2'>
                          <div className='w-1.5 h-1.5 bg-brand-primary-500 rounded-full'></div>
                          Multi-language translation support
                        </li>
                      </ul>
                    </div>

                    <div className='space-y-4'>
                      <h4 className='font-semibold text-neutral-900 dark:text-neutral-100'>
                        📊 Analytics Intelligence
                      </h4>
                      <ul className='space-y-2 text-sm text-neutral-600 dark:text-neutral-400'>
                        <li className='flex items-center gap-2'>
                          <div className='w-1.5 h-1.5 bg-success-500 rounded-full'></div>
                          Real-time behavioral pattern recognition
                        </li>
                        <li className='flex items-center gap-2'>
                          <div className='w-1.5 h-1.5 bg-success-500 rounded-full'></div>
                          Predictive user engagement modeling
                        </li>
                        <li className='flex items-center gap-2'>
                          <div className='w-1.5 h-1.5 bg-success-500 rounded-full'></div>
                          Anomaly detection and alerting
                        </li>
                        <li className='flex items-center gap-2'>
                          <div className='w-1.5 h-1.5 bg-success-500 rounded-full'></div>
                          Cognitive load measurement
                        </li>
                        <li className='flex items-center gap-2'>
                          <div className='w-1.5 h-1.5 bg-success-500 rounded-full'></div>
                          Automated performance optimization
                        </li>
                      </ul>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </motion.div>

        {/* Footer */}
        <motion.footer variants={itemVariants}>
          <div className='text-center py-8 border-t border-neutral-200 dark:border-neutral-800'>
            <p className='text-neutral-500 dark:text-neutral-400 text-sm'>
              🧠 AI-Powered PAKE System - The Future of Intelligent Web
              Applications
            </p>
            <p className='text-xs text-neutral-400 dark:text-neutral-500 mt-2'>
              Experience transcendent user interactions with privacy-first AI
              processing
            </p>
          </div>
        </motion.footer>
      </motion.div>
    </div>
  );
}
