import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { VideoGenerationStudio } from '@/components/dynamic';

export default function VideoGenerationPage() {
  return (
    <DashboardLayout userRole='admin'>
      <VideoGenerationStudio />
    </DashboardLayout>
  );
}
