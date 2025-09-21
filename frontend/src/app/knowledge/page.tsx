import { DashboardLayout } from '@/components/layout/DashboardLayout';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';

export default function KnowledgePage() {
  return (
    <DashboardLayout userRole='knowledge_worker'>
      <div className='space-y-6 p-6'>
        <div>
          <h1 className='text-3xl font-bold text-gray-900 dark:text-gray-50'>
            Knowledge Base
          </h1>
          <p className='text-gray-600 dark:text-gray-400 mt-2'>
            Search and manage your knowledge repository
          </p>
        </div>

        <div className='grid gap-6 md:grid-cols-2 lg:grid-cols-3'>
          <Card>
            <CardHeader>
              <CardTitle>Quick Search</CardTitle>
              <CardDescription>
                Search across all knowledge articles
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className='text-sm text-gray-600'>
                Search functionality coming soon...
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Recent Articles</CardTitle>
              <CardDescription>Latest knowledge base updates</CardDescription>
            </CardHeader>
            <CardContent>
              <p className='text-sm text-gray-600'>
                Recent articles will appear here...
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Categories</CardTitle>
              <CardDescription>Browse by topic</CardDescription>
            </CardHeader>
            <CardContent>
              <p className='text-sm text-gray-600'>
                Knowledge categories coming soon...
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
