'use client';

import {
  TrendingUp,
  Users,
  BookOpen,
  Shield,
  ArrowUpIcon,
  ArrowDownIcon,
} from 'lucide-react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';

interface MetricCardProps {
  title: string;
  value: string;
  trend: number;
  description: string;
  icon: React.ElementType;
  color: 'success' | 'primary' | 'info' | 'warning';
}

function MetricCard({
  title,
  value,
  trend,
  description,
  icon: Icon,
  color,
}: MetricCardProps) {
  const colorClasses = {
    success: 'text-primary bg-secondary',
    primary: 'text-primary bg-accent',
    info: 'text-primary bg-muted',
    warning: 'text-destructive bg-destructive/10',
  };

  const trendColorClasses = trend >= 0 ? 'text-primary' : 'text-destructive';
  const TrendIcon = trend >= 0 ? ArrowUpIcon : ArrowDownIcon;

  return (
    <Card>
      <CardHeader className='flex flex-row items-center justify-between space-y-0 pb-2'>
        <CardTitle className='text-sm font-medium'>{title}</CardTitle>
        <div
          className={`h-8 w-8 rounded-full flex items-center justify-center ${colorClasses[color]}`}
        >
          <Icon className='h-4 w-4' />
        </div>
      </CardHeader>
      <CardContent>
        <div className='text-2xl font-bold'>{value}</div>
        <div className='flex items-center mt-1'>
          <TrendIcon className={`h-4 w-4 mr-1 ${trendColorClasses}`} />
          <span className={`text-sm ${trendColorClasses}`}>
            {Math.abs(trend)}% from last month
          </span>
        </div>
        <p className='text-xs text-muted-foreground mt-1'>{description}</p>
      </CardContent>
    </Card>
  );
}

function ComplianceStatus() {
  const complianceItems = [
    { name: 'WCAG 2.1 AA', status: 'compliant', score: '100%' },
    { name: 'SOC 2 Type II', status: 'compliant', score: '100%' },
    { name: 'GDPR', status: 'compliant', score: '98%' },
    { name: 'ISO 27001', status: 'pending', score: '95%' },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Compliance Status</CardTitle>
        <CardDescription>
          Current compliance scores and certifications
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className='space-y-4'>
          {complianceItems.map(item => (
            <div key={item.name} className='flex items-center justify-between'>
              <div className='flex items-center space-x-3'>
                <div
                  className={`w-3 h-3 rounded-full ${
                    item.status === 'compliant'
                      ? 'bg-primary'
                      : item.status === 'pending'
                        ? 'bg-destructive/70'
                        : 'bg-destructive'
                  }`}
                />
                <span className='text-sm font-medium'>{item.name}</span>
              </div>
              <span className='text-sm text-muted-foreground'>
                {item.score}
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function SystemPerformanceChart() {
  // This would typically use Recharts for real charts
  return (
    <Card>
      <CardHeader>
        <CardTitle>System Performance</CardTitle>
        <CardDescription>
          Key performance indicators and system health
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className='h-80 flex items-center justify-center border-2 border-dashed border-border rounded-lg'>
          <div className='text-center'>
            <TrendingUp className='h-12 w-12 text-muted-foreground mx-auto mb-4' />
            <p className='text-muted-foreground'>Performance Chart</p>
            <p className='text-sm text-muted-foreground/70'>
              ROI trending +340% YoY
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function UserEngagementChart() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>User Engagement</CardTitle>
        <CardDescription>Active users and engagement patterns</CardDescription>
      </CardHeader>
      <CardContent>
        <div className='h-80 flex items-center justify-center border-2 border-dashed border-border rounded-lg'>
          <div className='text-center'>
            <Users className='h-12 w-12 text-muted-foreground mx-auto mb-4' />
            <p className='text-muted-foreground'>Engagement Chart</p>
            <p className='text-sm text-muted-foreground/70'>
              87% active user rate
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function ExecutiveDashboard() {
  return (
    <div className='space-y-8 p-8'>
      {/* Page Header */}
      <div>
        <h1 className='text-3xl font-bold text-foreground'>
          Executive Dashboard
        </h1>
        <p className='text-muted-foreground mt-2'>
          Strategic insights and key performance indicators
        </p>
      </div>

      {/* Key Metrics Grid */}
      <div className='grid gap-6 md:grid-cols-2 lg:grid-cols-4'>
        <MetricCard
          title='System ROI'
          value='340%'
          trend={12.5}
          description='Return on investment since implementation'
          icon={TrendingUp}
          color='success'
        />
        <MetricCard
          title='User Adoption'
          value='87%'
          trend={8.3}
          description='Active users vs. licensed seats'
          icon={Users}
          color='primary'
        />
        <MetricCard
          title='Knowledge Growth'
          value='24.3k'
          trend={15.7}
          description='Total knowledge articles'
          icon={BookOpen}
          color='info'
        />
        <MetricCard
          title='Compliance Score'
          value='99.2%'
          trend={2.1}
          description='Security and compliance rating'
          icon={Shield}
          color='success'
        />
      </div>

      {/* Main Content Grid */}
      <div className='grid gap-6 md:grid-cols-2'>
        <SystemPerformanceChart />
        <UserEngagementChart />
      </div>

      {/* Compliance Section */}
      <div className='grid gap-6 md:grid-cols-3'>
        <div className='md:col-span-2'>
          <ComplianceStatus />
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className='space-y-4'>
            <button className='w-full text-left p-3 rounded-lg border border-border hover:bg-accent transition-colors'>
              <div className='font-medium text-foreground'>
                Generate Executive Report
              </div>
              <div className='text-sm text-muted-foreground'>
                Weekly performance summary
              </div>
            </button>
            <button className='w-full text-left p-3 rounded-lg border border-border hover:bg-accent transition-colors'>
              <div className='font-medium text-foreground'>
                Review Compliance
              </div>
              <div className='text-sm text-muted-foreground'>
                Audit trail and certifications
              </div>
            </button>
            <button className='w-full text-left p-3 rounded-lg border border-border hover:bg-accent transition-colors'>
              <div className='font-medium text-foreground'>
                Export Analytics
              </div>
              <div className='text-sm text-muted-foreground'>
                Download data for presentations
              </div>
            </button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
