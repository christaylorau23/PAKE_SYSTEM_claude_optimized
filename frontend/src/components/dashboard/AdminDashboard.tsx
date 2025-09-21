'use client';

import {
  CheckCircle,
  AlertTriangle,
  XCircle,
  Activity,
  Server,
  Database,
  Wifi,
  Shield,
  RefreshCw,
  Settings,
  Download,
} from 'lucide-react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface SystemHealthCardProps {
  title: string;
  status: 'healthy' | 'warning' | 'critical';
  value: string;
  description: string;
  icon: React.ElementType;
}

function SystemHealthCard({
  title,
  status,
  value,
  description,
  icon: Icon,
}: SystemHealthCardProps) {
  const statusStyles = {
    healthy: {
      bg: 'bg-green-50 border-green-200',
      icon: 'text-green-600',
      status: 'text-green-800',
      badge: 'bg-green-100 text-green-800',
    },
    warning: {
      bg: 'bg-yellow-50 border-yellow-200',
      icon: 'text-yellow-600',
      status: 'text-yellow-800',
      badge: 'bg-yellow-100 text-yellow-800',
    },
    critical: {
      bg: 'bg-red-50 border-red-200',
      icon: 'text-red-600',
      status: 'text-red-800',
      badge: 'bg-red-100 text-red-800',
    },
  };

  const styles = statusStyles[status];
  const StatusIcon =
    status === 'healthy'
      ? CheckCircle
      : status === 'warning'
        ? AlertTriangle
        : XCircle;

  return (
    <Card className={`${styles.bg} border`}>
      <CardHeader className='flex flex-row items-center justify-between space-y-0 pb-2'>
        <CardTitle className='text-sm font-medium'>{title}</CardTitle>
        <div className='flex items-center space-x-2'>
          <Icon className={`h-5 w-5 ${styles.icon}`} />
          <StatusIcon className={`h-4 w-4 ${styles.icon}`} />
        </div>
      </CardHeader>
      <CardContent>
        <div className='text-2xl font-bold'>{value}</div>
        <div
          className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium mt-2 ${styles.badge}`}
        >
          {status.charAt(0).toUpperCase() + status.slice(1)}
        </div>
        <p className='text-xs text-gray-600 mt-2'>{description}</p>
      </CardContent>
    </Card>
  );
}

function QuickActions() {
  const actions = [
    {
      icon: RefreshCw,
      label: 'Refresh Services',
      action: () => console.log('Refresh'),
    },
    {
      icon: Settings,
      label: 'System Config',
      action: () => console.log('Config'),
    },
    {
      icon: Download,
      label: 'Export Logs',
      action: () => console.log('Export'),
    },
    { icon: Shield, label: 'Security Scan', action: () => console.log('Scan') },
  ];

  return (
    <div className='flex flex-wrap gap-2'>
      {actions.map(action => (
        <Button
          key={action.label}
          variant='outline'
          size='sm'
          onClick={action.action}
          className='flex items-center space-x-2'
        >
          <action.icon className='h-4 w-4' />
          <span>{action.label}</span>
        </Button>
      ))}
    </div>
  );
}

function ServiceStatus() {
  const services = [
    {
      name: 'Voice Agents Service',
      status: 'healthy',
      uptime: '99.9%',
      lastCheck: '2 min ago',
    },
    {
      name: 'Video Generation Pipeline',
      status: 'healthy',
      uptime: '99.7%',
      lastCheck: '1 min ago',
    },
    {
      name: 'Social Media Automation',
      status: 'warning',
      uptime: '98.5%',
      lastCheck: '5 min ago',
    },
    {
      name: 'Knowledge Graph Service',
      status: 'healthy',
      uptime: '100%',
      lastCheck: '1 min ago',
    },
    {
      name: 'Authentication Service',
      status: 'healthy',
      uptime: '99.9%',
      lastCheck: '2 min ago',
    },
    {
      name: 'Analytics Engine',
      status: 'critical',
      uptime: '95.2%',
      lastCheck: '10 min ago',
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Service Status</CardTitle>
        <CardDescription>Real-time status of all AI services</CardDescription>
      </CardHeader>
      <CardContent>
        <div className='space-y-4'>
          {services.map(service => (
            <div
              key={service.name}
              className='flex items-center justify-between p-3 rounded-lg border border-gray-100'
            >
              <div className='flex items-center space-x-3'>
                {service.status === 'healthy' && (
                  <CheckCircle className='h-5 w-5 text-green-500' />
                )}
                {service.status === 'warning' && (
                  <AlertTriangle className='h-5 w-5 text-yellow-500' />
                )}
                {service.status === 'critical' && (
                  <XCircle className='h-5 w-5 text-red-500' />
                )}
                <div>
                  <div className='font-medium text-sm'>{service.name}</div>
                  <div className='text-xs text-gray-500'>
                    Uptime: {service.uptime}
                  </div>
                </div>
              </div>
              <div className='text-right'>
                <div
                  className={`text-xs px-2 py-1 rounded-full ${
                    service.status === 'healthy'
                      ? 'bg-green-100 text-green-800'
                      : service.status === 'warning'
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-red-100 text-red-800'
                  }`}
                >
                  {service.status.charAt(0).toUpperCase() +
                    service.status.slice(1)}
                </div>
                <div className='text-xs text-gray-500 mt-1'>
                  {service.lastCheck}
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function AlertsPanel() {
  const alerts = [
    {
      id: 1,
      type: 'warning',
      title: 'High Memory Usage',
      description: 'Social Media service memory usage at 85%',
      timestamp: '5 minutes ago',
    },
    {
      id: 2,
      type: 'critical',
      title: 'Analytics Engine Offline',
      description: 'Analytics service not responding to health checks',
      timestamp: '10 minutes ago',
    },
    {
      id: 3,
      type: 'info',
      title: 'Scheduled Maintenance',
      description:
        'Video generation service maintenance window starts in 2 hours',
      timestamp: '1 hour ago',
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Alerts</CardTitle>
        <CardDescription>System alerts and notifications</CardDescription>
      </CardHeader>
      <CardContent>
        <div className='space-y-4'>
          {alerts.map(alert => (
            <div
              key={alert.id}
              className='flex space-x-3 p-3 rounded-lg border border-gray-100'
            >
              <div className='flex-shrink-0'>
                {alert.type === 'critical' && (
                  <XCircle className='h-5 w-5 text-red-500' />
                )}
                {alert.type === 'warning' && (
                  <AlertTriangle className='h-5 w-5 text-yellow-500' />
                )}
                {alert.type === 'info' && (
                  <CheckCircle className='h-5 w-5 text-blue-500' />
                )}
              </div>
              <div className='flex-1 min-w-0'>
                <p className='text-sm font-medium text-gray-900'>
                  {alert.title}
                </p>
                <p className='text-sm text-gray-500'>{alert.description}</p>
                <p className='text-xs text-gray-400 mt-1'>{alert.timestamp}</p>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export function AdminDashboard() {
  return (
    <div className='space-y-6 p-6'>
      {/* System Status Banner */}
      <div className='bg-green-50 border border-green-200 rounded-lg p-4'>
        <div className='flex items-center'>
          <CheckCircle className='h-5 w-5 text-green-600 mr-3' />
          <div>
            <h3 className='text-sm font-medium text-green-800'>
              System Status: Operational
            </h3>
            <p className='text-sm text-green-700'>
              All core services running normally. Last check: 2 minutes ago
            </p>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className='text-lg font-semibold text-gray-900 mb-4'>
          Quick Actions
        </h2>
        <QuickActions />
      </div>

      {/* System Health Grid */}
      <div className='grid gap-6 md:grid-cols-2 lg:grid-cols-4'>
        <SystemHealthCard
          title='API Gateway'
          status='healthy'
          value='99.9%'
          description='Request success rate'
          icon={Wifi}
        />
        <SystemHealthCard
          title='Database'
          status='healthy'
          value='2.3ms'
          description='Average response time'
          icon={Database}
        />
        <SystemHealthCard
          title='CPU Usage'
          status='warning'
          value='72%'
          description='Across all services'
          icon={Activity}
        />
        <SystemHealthCard
          title='Storage'
          status='healthy'
          value='67GB'
          description='Available space'
          icon={Server}
        />
      </div>

      {/* Main Content Grid */}
      <div className='grid gap-6 lg:grid-cols-3'>
        {/* Service Status */}
        <div className='lg:col-span-2'>
          <ServiceStatus />
        </div>

        {/* System Resources */}
        <Card>
          <CardHeader>
            <CardTitle>System Resources</CardTitle>
          </CardHeader>
          <CardContent className='space-y-4'>
            <div className='space-y-2'>
              <div className='flex items-center justify-between'>
                <span className='text-sm font-medium'>CPU Usage</span>
                <span className='text-sm text-gray-500'>72%</span>
              </div>
              <div className='w-full bg-gray-200 rounded-full h-2'>
                <div
                  className='bg-yellow-500 h-2 rounded-full'
                  style={{ width: '72%' }}
                ></div>
              </div>
            </div>

            <div className='space-y-2'>
              <div className='flex items-center justify-between'>
                <span className='text-sm font-medium'>Memory</span>
                <span className='text-sm text-gray-500'>67%</span>
              </div>
              <div className='w-full bg-gray-200 rounded-full h-2'>
                <div
                  className='bg-yellow-500 h-2 rounded-full'
                  style={{ width: '67%' }}
                ></div>
              </div>
            </div>

            <div className='space-y-2'>
              <div className='flex items-center justify-between'>
                <span className='text-sm font-medium'>Storage</span>
                <span className='text-sm text-gray-500'>23%</span>
              </div>
              <div className='w-full bg-gray-200 rounded-full h-2'>
                <div
                  className='bg-green-500 h-2 rounded-full'
                  style={{ width: '23%' }}
                ></div>
              </div>
            </div>

            <div className='space-y-2'>
              <div className='flex items-center justify-between'>
                <span className='text-sm font-medium'>Network I/O</span>
                <span className='text-sm text-gray-500'>34%</span>
              </div>
              <div className='w-full bg-gray-200 rounded-full h-2'>
                <div
                  className='bg-blue-500 h-2 rounded-full'
                  style={{ width: '34%' }}
                ></div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Alerts Panel */}
      <AlertsPanel />
    </div>
  );
}
