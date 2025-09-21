import { DashboardLayout } from '@/components/layout/DashboardLayout';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Zap, CheckCircle, AlertCircle, Clock } from 'lucide-react';

export default function IntegrationsPage() {
  const integrations = [
    {
      name: 'OpenAI GPT-4',
      description: 'AI-powered content generation and analysis',
      status: 'connected',
      category: 'AI Services',
    },
    {
      name: 'D-ID Video Generation',
      description: 'AI avatar video creation platform',
      status: 'connected',
      category: 'Video AI',
    },
    {
      name: 'HeyGen',
      description: 'Advanced video generation and editing',
      status: 'connected',
      category: 'Video AI',
    },
    {
      name: 'Vapi.ai',
      description: 'Voice AI and conversation management',
      status: 'connected',
      category: 'Voice AI',
    },
    {
      name: 'Twitter API',
      description: 'Social media posting and engagement',
      status: 'pending',
      category: 'Social Media',
    },
    {
      name: 'LinkedIn API',
      description: 'Professional networking and content sharing',
      status: 'error',
      category: 'Social Media',
    },
  ];

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected':
        return <CheckCircle className='h-4 w-4 text-green-500' />;
      case 'pending':
        return <Clock className='h-4 w-4 text-yellow-500' />;
      case 'error':
        return <AlertCircle className='h-4 w-4 text-red-500' />;
      default:
        return <Zap className='h-4 w-4 text-gray-400' />;
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'connected':
        return 'Connected';
      case 'pending':
        return 'Pending';
      case 'error':
        return 'Error';
      default:
        return 'Disconnected';
    }
  };

  return (
    <DashboardLayout userRole='admin'>
      <div className='space-y-6 p-6'>
        <div className='flex items-center justify-between'>
          <div>
            <h1 className='text-3xl font-bold text-gray-900 dark:text-gray-50'>
              Integrations
            </h1>
            <p className='text-gray-600 dark:text-gray-400 mt-2'>
              Manage your AI service integrations and connections
            </p>
          </div>
          <Button>
            <Zap className='h-4 w-4 mr-2' />
            Add Integration
          </Button>
        </div>

        {/* Integration Categories */}
        <div className='grid gap-6'>
          {['AI Services', 'Video AI', 'Voice AI', 'Social Media'].map(
            category => {
              const categoryIntegrations = integrations.filter(
                integration => integration.category === category
              );

              return (
                <Card key={category}>
                  <CardHeader>
                    <CardTitle>{category}</CardTitle>
                    <CardDescription>
                      {category === 'AI Services' &&
                        'Core AI and machine learning services'}
                      {category === 'Video AI' &&
                        'Video generation and editing platforms'}
                      {category === 'Voice AI' &&
                        'Voice and conversation AI services'}
                      {category === 'Social Media' &&
                        'Social media platforms and APIs'}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className='grid gap-4 md:grid-cols-2 lg:grid-cols-3'>
                      {categoryIntegrations.map(integration => (
                        <div
                          key={integration.name}
                          className='flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors'
                        >
                          <div className='flex-1'>
                            <div className='flex items-center space-x-2 mb-1'>
                              {getStatusIcon(integration.status)}
                              <h3 className='text-sm font-medium'>
                                {integration.name}
                              </h3>
                            </div>
                            <p className='text-xs text-gray-500 mb-2'>
                              {integration.description}
                            </p>
                            <span
                              className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                                integration.status === 'connected'
                                  ? 'bg-green-100 text-green-800'
                                  : integration.status === 'pending'
                                    ? 'bg-yellow-100 text-yellow-800'
                                    : integration.status === 'error'
                                      ? 'bg-red-100 text-red-800'
                                      : 'bg-gray-100 text-gray-800'
                              }`}
                            >
                              {getStatusText(integration.status)}
                            </span>
                          </div>
                          <div className='ml-4'>
                            <Button variant='outline' size='sm'>
                              Configure
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              );
            }
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
