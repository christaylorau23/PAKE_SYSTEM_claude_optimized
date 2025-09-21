import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { VoiceAgentDashboard } from '@/components/dynamic';

export default function VoiceAgentsPage() {
  return (
    <DashboardLayout userRole='admin'>
      <VoiceAgentDashboard />
    </DashboardLayout>
  );
}
