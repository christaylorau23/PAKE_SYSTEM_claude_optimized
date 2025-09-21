import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { SocialMediaDashboard } from '@/components/social/SocialMediaDashboard';

export default function SocialMediaPage() {
  return (
    <DashboardLayout userRole='admin'>
      <SocialMediaDashboard />
    </DashboardLayout>
  );
}
