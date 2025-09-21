'use client';

import { useEffect } from 'react';
import { initializeTelemetry, PerformanceTracker } from '@/lib/telemetry';

export default function TelemetryProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  useEffect(() => {
    // Initialize OpenTelemetry
    const tracerProvider = initializeTelemetry();

    // Start performance tracking
    const performanceTracker = PerformanceTracker.getInstance();
    performanceTracker.startTracking();

    // Cleanup on unmount
    return () => {
      performanceTracker.stopTracking();
    };
  }, []);

  return <>{children}</>;
}
