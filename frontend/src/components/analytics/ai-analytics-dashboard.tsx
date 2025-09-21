/* AI Analytics Dashboard - Intelligent Behavioral Analytics */
/* Advanced analytics with ML-powered insights and predictions */

'use client';

import * as React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  StatsCard,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useAIService } from '@/lib/ai/ai-service';
import { useStore } from '@/lib/store';
import { cn } from '@/lib/utils';

// Behavioral Prediction Types
interface UserBehaviorPattern {
  id: string;
  pattern:
    | 'engagement'
    | 'conversion'
    | 'churn'
    | 'feature_adoption'
    | 'performance';
  confidence: number;
  prediction: string;
  recommendation: string;
  impact: 'high' | 'medium' | 'low';
  timeframe: string;
  data: Record<string, unknown>;
}

interface AnalyticsInsight {
  type: 'optimization' | 'anomaly' | 'trend' | 'opportunity';
  title: string;
  description: string;
  confidence: number;
  action: string;
  impact: number; // 0-100
  urgency: 'critical' | 'high' | 'medium' | 'low';
  createdAt: Date;
}

interface PredictiveMetric {
  name: string;
  currentValue: number;
  predictedValue: number;
  change: number;
  changeType: 'improvement' | 'decline' | 'stable';
  confidence: number;
  timeframe: '1h' | '1d' | '7d' | '30d';
}

// Real-time User Analytics
interface UserAnalytics {
  totalUsers: number;
  activeUsers: number;
  engagementScore: number;
  conversionRate: number;
  retentionRate: number;
  satisfactionScore: number;
  cognitiveLoadIndex: number;
  aiAssistanceUsage: number;
}

// Component Props
interface AIAnalyticsDashboardProps {
  timeRange?: '1h' | '1d' | '7d' | '30d';
  enablePredictions?: boolean;
  enableRealTimeUpdates?: boolean;
  className?: string;
}

// Mock Data Generator (replace with real analytics API)
const generateMockAnalytics = (): UserAnalytics => ({
  totalUsers: 12847 + Math.floor(Math.random() * 100),
  activeUsers: 3247 + Math.floor(Math.random() * 50),
  engagementScore: 0.78 + (Math.random() * 0.2 - 0.1),
  conversionRate: 0.045 + (Math.random() * 0.01 - 0.005),
  retentionRate: 0.89 + (Math.random() * 0.1 - 0.05),
  satisfactionScore: 4.2 + (Math.random() * 0.6 - 0.3),
  cognitiveLoadIndex: 0.35 + (Math.random() * 0.2 - 0.1),
  aiAssistanceUsage: 0.67 + (Math.random() * 0.2 - 0.1),
});

const generateMockBehaviorPatterns = (): UserBehaviorPattern[] => [
  {
    id: 'pattern_1',
    pattern: 'engagement',
    confidence: 0.89,
    prediction: 'User engagement expected to increase by 23% in next 7 days',
    recommendation: 'Focus on promoting new AI-powered features',
    impact: 'high',
    timeframe: '7 days',
    data: { engagementTrend: 'increasing', newFeatureAdoption: 0.45 },
  },
  {
    id: 'pattern_2',
    pattern: 'churn',
    confidence: 0.76,
    prediction: '12% of inactive users likely to churn within 30 days',
    recommendation:
      'Implement re-engagement campaign with personalized content',
    impact: 'medium',
    timeframe: '30 days',
    data: { inactivityDays: 14, lastEngagementScore: 0.23 },
  },
  {
    id: 'pattern_3',
    pattern: 'feature_adoption',
    confidence: 0.92,
    prediction:
      'AI form assistant adoption expected to reach 85% by next month',
    recommendation: 'Prepare infrastructure scaling for increased AI usage',
    impact: 'high',
    timeframe: '30 days',
    data: { currentAdoption: 0.67, growthRate: 0.12 },
  },
];

const generateMockInsights = (): AnalyticsInsight[] => [
  {
    type: 'optimization',
    title: 'Form Completion Rate Optimization',
    description:
      'AI analysis suggests 34% improvement possible with smart field completion',
    confidence: 0.87,
    action: 'Enable smart completion for address and payment fields',
    impact: 85,
    urgency: 'high',
    createdAt: new Date(),
  },
  {
    type: 'anomaly',
    title: 'Unusual Error Pattern Detected',
    description:
      'Increased validation errors in mobile form submissions (+23%)',
    confidence: 0.94,
    action: 'Investigate mobile keyboard input handling',
    impact: 70,
    urgency: 'medium',
    createdAt: new Date(),
  },
  {
    type: 'opportunity',
    title: 'Voice Input Adoption Potential',
    description:
      'Users spending 40% more time on forms without voice input enabled',
    confidence: 0.78,
    action: 'Promote voice input feature with contextual hints',
    impact: 60,
    urgency: 'medium',
    createdAt: new Date(),
  },
];

const generatePredictiveMetrics = (): PredictiveMetric[] => [
  {
    name: 'User Engagement',
    currentValue: 78.5,
    predictedValue: 82.3,
    change: 3.8,
    changeType: 'improvement',
    confidence: 0.89,
    timeframe: '7d',
  },
  {
    name: 'Conversion Rate',
    currentValue: 4.5,
    predictedValue: 5.2,
    change: 0.7,
    changeType: 'improvement',
    confidence: 0.76,
    timeframe: '7d',
  },
  {
    name: 'Cognitive Load',
    currentValue: 35.2,
    predictedValue: 28.7,
    change: -6.5,
    changeType: 'improvement',
    confidence: 0.83,
    timeframe: '7d',
  },
];

// Insight Card Component
function InsightCard({ insight }: { insight: AnalyticsInsight }) {
  const getUrgencyColor = (urgency: AnalyticsInsight['urgency']) => {
    switch (urgency) {
      case 'critical':
        return 'text-error-600 bg-error-50 border-error-200';
      case 'high':
        return 'text-warning-600 bg-warning-50 border-warning-200';
      case 'medium':
        return 'text-brand-primary-600 bg-brand-primary-50 border-brand-primary-200';
      case 'low':
        return 'text-success-600 bg-success-50 border-success-200';
    }
  };

  const getTypeIcon = (type: AnalyticsInsight['type']) => {
    switch (type) {
      case 'optimization':
        return '⚡';
      case 'anomaly':
        return '⚠️';
      case 'trend':
        return '📈';
      case 'opportunity':
        return '💡';
    }
  };

  return (
    <motion.div
      className={cn(
        'p-4 rounded-lg border-2 transition-all cursor-pointer hover:shadow-md',
        getUrgencyColor(insight.urgency)
      )}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      whileHover={{ scale: 1.02 }}
    >
      <div className='flex items-start justify-between mb-2'>
        <div className='flex items-center gap-2'>
          <span className='text-lg'>{getTypeIcon(insight.type)}</span>
          <h4 className='font-semibold text-neutral-900 dark:text-neutral-100'>
            {insight.title}
          </h4>
        </div>
        <span className='text-xs px-2 py-1 rounded-full bg-neutral-200 dark:bg-neutral-700'>
          {Math.round(insight.confidence * 100)}% sure
        </span>
      </div>

      <p className='text-sm text-neutral-600 dark:text-neutral-400 mb-3'>
        {insight.description}
      </p>

      <div className='flex items-center justify-between'>
        <span className='text-sm font-medium text-neutral-900 dark:text-neutral-100'>
          {insight.action}
        </span>
        <div className='flex items-center gap-2'>
          <div className='w-16 bg-neutral-200 dark:bg-neutral-700 rounded-full h-2'>
            <div
              className='h-2 bg-current rounded-full transition-all duration-500'
              style={{ width: `${insight.impact}%` }}
            />
          </div>
          <span className='text-xs text-neutral-500'>
            {insight.impact}% impact
          </span>
        </div>
      </div>
    </motion.div>
  );
}

// Behavior Pattern Card Component
function BehaviorPatternCard({ pattern }: { pattern: UserBehaviorPattern }) {
  const getPatternIcon = (patternType: UserBehaviorPattern['pattern']) => {
    switch (patternType) {
      case 'engagement':
        return '💝';
      case 'conversion':
        return '🎯';
      case 'churn':
        return '👋';
      case 'feature_adoption':
        return '🚀';
      case 'performance':
        return '⚡';
    }
  };

  const getImpactColor = (impact: UserBehaviorPattern['impact']) => {
    switch (impact) {
      case 'high':
        return 'text-error-600 dark:text-error-400';
      case 'medium':
        return 'text-warning-600 dark:text-warning-400';
      case 'low':
        return 'text-success-600 dark:text-success-400';
    }
  };

  return (
    <motion.div
      className='p-4 bg-neutral-50 dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700'
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
    >
      <div className='flex items-center justify-between mb-3'>
        <div className='flex items-center gap-2'>
          <span className='text-xl'>{getPatternIcon(pattern.pattern)}</span>
          <span className='font-semibold capitalize text-neutral-900 dark:text-neutral-100'>
            {pattern.pattern.replace('_', ' ')}
          </span>
        </div>
        <span
          className={cn(
            'text-xs font-medium uppercase',
            getImpactColor(pattern.impact)
          )}
        >
          {pattern.impact} Impact
        </span>
      </div>

      <p className='text-sm text-neutral-700 dark:text-neutral-300 mb-2'>
        {pattern.prediction}
      </p>

      <p className='text-xs text-brand-primary-600 dark:text-brand-primary-400 mb-3'>
        💡 {pattern.recommendation}
      </p>

      <div className='flex items-center justify-between text-xs text-neutral-500'>
        <span>Confidence: {Math.round(pattern.confidence * 100)}%</span>
        <span>Timeframe: {pattern.timeframe}</span>
      </div>
    </motion.div>
  );
}

// Main Dashboard Component
export function AIAnalyticsDashboard({
  timeRange = '1d',
  enablePredictions = true,
  enableRealTimeUpdates = true,
  className,
}: AIAnalyticsDashboardProps) {
  const { user } = useStore();
  const aiService = useAIService();
  const animationsEnabled = !user.reducedMotion;

  // State Management
  const [analytics, setAnalytics] = React.useState<UserAnalytics>(
    generateMockAnalytics()
  );
  const [behaviorPatterns, setBehaviorPatterns] = React.useState<
    UserBehaviorPattern[]
  >(generateMockBehaviorPatterns());
  const [insights, setInsights] = React.useState<AnalyticsInsight[]>(
    generateMockInsights()
  );
  const [predictiveMetrics, setPredictiveMetrics] = React.useState<
    PredictiveMetric[]
  >(generatePredictiveMetrics());
  const [isLoading, setIsLoading] = React.useState(false);
  const [lastUpdated, setLastUpdated] = React.useState(new Date());

  // Real-time updates
  React.useEffect(() => {
    if (!enableRealTimeUpdates) return;

    const interval = setInterval(() => {
      setAnalytics(generateMockAnalytics());
      setLastUpdated(new Date());
    }, 10000); // Update every 10 seconds

    return () => clearInterval(interval);
  }, [enableRealTimeUpdates]);

  // Generate AI insights
  const generateAIInsights = React.useCallback(async () => {
    setIsLoading(true);

    try {
      const response = await aiService.complete({
        prompt: `Analyze this user analytics data and provide actionable insights:
        
Analytics Data:
${JSON.stringify(analytics, null, 2)}

Behavior Patterns:
${JSON.stringify(behaviorPatterns, null, 2)}

Please provide:
1. Key opportunities for improvement
2. Potential risks or anomalies
3. Optimization recommendations
4. Predicted trends and outcomes

Focus on actionable insights that can improve user experience and business metrics.`,
        systemPrompt:
          'You are an expert data analyst specializing in user experience analytics and behavioral prediction.',
        maxTokens: 500,
        temperature: 0.3,
      });

      // In a real implementation, parse AI response and update insights
      console.log('AI Insights Generated:', response.content);
    } catch (error) {
      console.error('AI insights generation error:', error);
    } finally {
      setIsLoading(false);
    }
  }, [analytics, behaviorPatterns, aiService]);

  // Container animation variants
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
    <div className={cn('space-y-8', className)}>
      {/* Header */}
      <motion.div
        className='flex items-center justify-between'
        variants={itemVariants}
        initial='hidden'
        animate='visible'
      >
        <div>
          <h2 className='text-3xl font-bold text-neutral-900 dark:text-neutral-100'>
            AI Analytics Dashboard
          </h2>
          <p className='text-neutral-600 dark:text-neutral-400 mt-1'>
            Intelligent behavioral analytics with predictive insights
          </p>
        </div>

        <div className='flex items-center gap-3'>
          <div className='text-xs text-neutral-500 flex items-center gap-1'>
            <div className='w-2 h-2 bg-success-500 rounded-full animate-pulse' />
            Last updated: {lastUpdated.toLocaleTimeString()}
          </div>

          <Button
            onClick={generateAIInsights}
            loading={isLoading}
            disabled={isLoading}
            size='sm'
          >
            🧠 Generate AI Insights
          </Button>
        </div>
      </motion.div>

      {/* Key Metrics */}
      <motion.div
        className='grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4'
        variants={containerVariants}
        initial='hidden'
        animate='visible'
      >
        <motion.div variants={itemVariants}>
          <StatsCard
            title='Active Users'
            value={analytics.activeUsers.toLocaleString()}
            change='+12.5%'
            trend='up'
            icon='👥'
            description='Currently online'
            variant='success'
          />
        </motion.div>

        <motion.div variants={itemVariants}>
          <StatsCard
            title='Engagement Score'
            value={`${Math.round(analytics.engagementScore * 100)}%`}
            change='+8.2%'
            trend='up'
            icon='💝'
            description='AI-calculated engagement'
          />
        </motion.div>

        <motion.div variants={itemVariants}>
          <StatsCard
            title='AI Assistance Usage'
            value={`${Math.round(analytics.aiAssistanceUsage * 100)}%`}
            change='+15.3%'
            trend='up'
            icon='🤖'
            description='Users using AI features'
            variant='success'
          />
        </motion.div>

        <motion.div variants={itemVariants}>
          <StatsCard
            title='Cognitive Load'
            value={`${Math.round(analytics.cognitiveLoadIndex * 100)}%`}
            change='-5.1%'
            trend='down'
            icon='🧠'
            description='User mental effort score'
            variant='success'
          />
        </motion.div>
      </motion.div>

      {/* Predictive Metrics */}
      {enablePredictions && (
        <motion.section
          variants={itemVariants}
          initial='hidden'
          animate='visible'
        >
          <Card>
            <CardHeader>
              <CardTitle className='flex items-center gap-2'>
                🔮 Predictive Analytics
                <span className='text-xs bg-brand-primary-100 text-brand-primary-800 px-2 py-1 rounded-full dark:bg-brand-primary-900/20 dark:text-brand-primary-400'>
                  ML Powered
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className='grid grid-cols-1 gap-4 md:grid-cols-3'>
                {predictiveMetrics.map((metric, index) => (
                  <motion.div
                    key={metric.name}
                    className='p-4 border border-neutral-200 dark:border-neutral-700 rounded-lg'
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
                  >
                    <div className='flex items-center justify-between mb-2'>
                      <span className='font-medium text-neutral-900 dark:text-neutral-100'>
                        {metric.name}
                      </span>
                      <span className='text-xs text-neutral-500'>
                        {Math.round(metric.confidence * 100)}% confident
                      </span>
                    </div>

                    <div className='flex items-center gap-4'>
                      <div className='text-2xl font-bold text-neutral-900 dark:text-neutral-100'>
                        {metric.currentValue}%
                      </div>
                      <div className='flex items-center'>
                        <span className='text-sm text-neutral-500 mr-1'>→</span>
                        <span
                          className={cn(
                            'text-lg font-semibold',
                            metric.changeType === 'improvement'
                              ? 'text-success-600'
                              : metric.changeType === 'decline'
                                ? 'text-error-600'
                                : 'text-neutral-600'
                          )}
                        >
                          {metric.predictedValue}%
                        </span>
                      </div>
                    </div>

                    <div className='mt-2 text-xs text-neutral-500'>
                      Predicted for next {metric.timeframe}
                    </div>
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.section>
      )}

      {/* Behavior Patterns */}
      <motion.section
        variants={itemVariants}
        initial='hidden'
        animate='visible'
      >
        <Card>
          <CardHeader>
            <CardTitle>🧩 Behavioral Pattern Recognition</CardTitle>
          </CardHeader>
          <CardContent>
            <div className='grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3'>
              {behaviorPatterns.map(pattern => (
                <BehaviorPatternCard key={pattern.id} pattern={pattern} />
              ))}
            </div>
          </CardContent>
        </Card>
      </motion.section>

      {/* AI Insights */}
      <motion.section
        variants={itemVariants}
        initial='hidden'
        animate='visible'
      >
        <Card>
          <CardHeader>
            <CardTitle className='flex items-center gap-2'>
              🎯 AI-Generated Insights
              {isLoading && (
                <motion.div
                  className='w-4 h-4 border-2 border-brand-primary-600 border-t-transparent rounded-full'
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                />
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className='grid grid-cols-1 gap-4 lg:grid-cols-2'>
              <AnimatePresence mode='popLayout'>
                {insights.map(insight => (
                  <InsightCard key={insight.title} insight={insight} />
                ))}
              </AnimatePresence>
            </div>
          </CardContent>
        </Card>
      </motion.section>
    </div>
  );
}
