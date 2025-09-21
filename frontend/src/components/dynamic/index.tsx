'use client';

import dynamic from 'next/dynamic';
import { ComponentLoading } from '@/components/ui/loading';

// Dashboard Components - Lazy loaded for better performance
export const ExecutiveDashboard = dynamic(
  () =>
    import('@/components/dashboard/ExecutiveDashboard').then(mod => ({
      default: mod.ExecutiveDashboard,
    })),
  {
    loading: () => <ComponentLoading />,
    ssr: false, // Executive dashboard has real-time data, disable SSR
  }
);

export const AdminDashboard = dynamic(
  () =>
    import('@/components/dashboard/AdminDashboard').then(mod => ({
      default: mod.AdminDashboard,
    })),
  {
    loading: () => <ComponentLoading />,
  }
);

// AI Service Components - Heavy components, perfect for code splitting
export const VoiceAgentDashboard = dynamic(
  () =>
    import('@/components/voice/VoiceAgentDashboard').then(mod => ({
      default: mod.VoiceAgentDashboard,
    })),
  {
    loading: () => <ComponentLoading />,
    ssr: false, // Voice agents have real-time WebSocket connections
  }
);

export const VideoGenerationStudio = dynamic(
  () =>
    import('@/components/video/VideoGenerationStudio').then(mod => ({
      default: mod.VideoGenerationStudio,
    })),
  {
    loading: () => <ComponentLoading />,
    ssr: false, // Video generation has file uploads and real-time status
  }
);

export const SocialMediaDashboard = dynamic(
  () =>
    import('@/components/social/SocialMediaDashboard').then(mod => ({
      default: mod.SocialMediaDashboard,
    })),
  {
    loading: () => <ComponentLoading />,
    ssr: false, // Social media has real-time feeds and interactions
  }
);

// Charts and Analytics - Heavy recharts library
export const AnalyticsCharts = dynamic(
  () => import('@/components/analytics/AnalyticsCharts'),
  {
    loading: () => <ComponentLoading />,
    ssr: false, // Charts don't need SSR and can be heavy
  }
);

export const PerformanceMetrics = dynamic(
  () => import('@/components/analytics/PerformanceMetrics'),
  {
    loading: () => <ComponentLoading />,
    ssr: false,
  }
);

// Settings and Configuration - Rarely used, perfect for splitting
export const SettingsPanel = dynamic(
  () => import('@/components/settings/SettingsPanel'),
  {
    loading: () => <ComponentLoading />,
  }
);

export const IntegrationsManager = dynamic(
  () => import('@/components/integrations/IntegrationsManager'),
  {
    loading: () => <ComponentLoading />,
  }
);

// Knowledge Vault - Text-heavy component
export const KnowledgeVault = dynamic(
  () => import('@/components/knowledge/KnowledgeVault'),
  {
    loading: () => <ComponentLoading />,
  }
);
