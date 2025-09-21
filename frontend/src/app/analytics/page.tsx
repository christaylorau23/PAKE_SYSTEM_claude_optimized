import { DashboardLayout } from '@/components/layout/DashboardLayout';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { BarChart3, TrendingUp, Users, Activity } from 'lucide-react';

export default function AnalyticsPage() {
  return (
    <DashboardLayout userRole='executive'>
      <div className='space-y-6 p-6'>
        <div>
          <h1 className='text-3xl font-bold text-gray-900 dark:text-gray-50'>
            Analytics Dashboard
          </h1>
          <p className='text-gray-600 dark:text-gray-400 mt-2'>
            View comprehensive analytics and insights across all AI services
          </p>
        </div>

        {/* Analytics Metrics */}
        <div className='grid gap-6 md:grid-cols-2 lg:grid-cols-4'>
          <Card>
            <CardHeader className='flex flex-row items-center justify-between space-y-0 pb-2'>
              <CardTitle className='text-sm font-medium'>Total Usage</CardTitle>
              <Activity className='h-4 w-4 text-muted-foreground' />
            </CardHeader>
            <CardContent>
              <div className='text-2xl font-bold'>2.4M</div>
              <p className='text-xs text-muted-foreground'>
                +15% from last month
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className='flex flex-row items-center justify-between space-y-0 pb-2'>
              <CardTitle className='text-sm font-medium'>
                Active Users
              </CardTitle>
              <Users className='h-4 w-4 text-muted-foreground' />
            </CardHeader>
            <CardContent>
              <div className='text-2xl font-bold'>1.2k</div>
              <p className='text-xs text-muted-foreground'>
                +8% from last month
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className='flex flex-row items-center justify-between space-y-0 pb-2'>
              <CardTitle className='text-sm font-medium'>Growth Rate</CardTitle>
              <TrendingUp className='h-4 w-4 text-muted-foreground' />
            </CardHeader>
            <CardContent>
              <div className='text-2xl font-bold'>23.1%</div>
              <p className='text-xs text-muted-foreground'>
                +2.1% from last month
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className='flex flex-row items-center justify-between space-y-0 pb-2'>
              <CardTitle className='text-sm font-medium'>
                AI Efficiency
              </CardTitle>
              <BarChart3 className='h-4 w-4 text-muted-foreground' />
            </CardHeader>
            <CardContent>
              <div className='text-2xl font-bold'>94.7%</div>
              <p className='text-xs text-muted-foreground'>
                +1.2% from last month
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Analytics Charts */}
        <div className='grid gap-6 md:grid-cols-2'>
          <Card>
            <CardHeader>
              <CardTitle>Usage Trends</CardTitle>
              <CardDescription>AI service usage over time</CardDescription>
            </CardHeader>
            <CardContent>
              <div className='h-80 flex items-center justify-center border-2 border-dashed border-gray-200 rounded-lg'>
                <div className='text-center'>
                  <BarChart3 className='h-12 w-12 text-gray-400 mx-auto mb-4' />
                  <p className='text-gray-500'>Usage trends chart</p>
                  <p className='text-sm text-gray-400'>
                    Real-time analytics coming soon
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Service Performance</CardTitle>
              <CardDescription>
                Performance metrics by AI service
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className='h-80 flex items-center justify-center border-2 border-dashed border-gray-200 rounded-lg'>
                <div className='text-center'>
                  <TrendingUp className='h-12 w-12 text-gray-400 mx-auto mb-4' />
                  <p className='text-gray-500'>Performance metrics</p>
                  <p className='text-sm text-gray-400'>
                    Detailed analytics coming soon
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
