import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { AdminDashboard } from '@/components/dashboard/AdminDashboard';

export default function AdminPage() {
  return (
    <DashboardLayout userRole='admin'>
      <AdminDashboard />
    </DashboardLayout>
  );
}
