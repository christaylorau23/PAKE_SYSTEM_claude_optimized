import { DashboardLayout } from '@/components/layout/DashboardLayout';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { ThemeToggleDropdown } from '@/components/ui/theme-toggle';

export default function SettingsPage() {
  return (
    <DashboardLayout userRole='admin'>
      <div className='space-y-6 p-6'>
        <div>
          <h1 className='text-3xl font-bold text-gray-900 dark:text-gray-50'>
            Settings
          </h1>
          <p className='text-gray-600 dark:text-gray-400 mt-2'>
            Configure your PAKE System preferences
          </p>
        </div>

        <div className='grid gap-6 md:grid-cols-2'>
          <Card>
            <CardHeader>
              <CardTitle>Appearance</CardTitle>
              <CardDescription>
                Customize your interface theme and accessibility options
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ThemeToggleDropdown />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Notifications</CardTitle>
              <CardDescription>
                Manage your notification preferences
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className='text-sm text-gray-600'>
                Notification settings coming soon...
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Account</CardTitle>
              <CardDescription>Manage your account settings</CardDescription>
            </CardHeader>
            <CardContent>
              <p className='text-sm text-gray-600'>
                Account management coming soon...
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>System</CardTitle>
              <CardDescription>
                System-wide configuration options
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className='text-sm text-gray-600'>
                System settings coming soon...
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
