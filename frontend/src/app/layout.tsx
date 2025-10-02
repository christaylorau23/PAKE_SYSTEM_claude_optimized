import type { Metadata } from 'next';
import { Inter } from 'next/font/google';

// Import design tokens
import '@/design-tokens/colors.css';
import '@/design-tokens/typography.css';
import '@/design-tokens/spacing.css';
import '@/design-tokens/motion.css';
import './globals.css';

// Enhanced providers
import { ThemeProvider } from '@/context/ThemeContext';
import TelemetryProvider from '@/components/providers/TelemetryProvider';
import { QueryProvider } from '@/components/providers/QueryProvider';
import { StoreProvider } from '@/components/providers/StoreProvider';
import { AuthProvider } from '@/lib/auth/auth-context';

// Performance monitoring
import { PerformanceMonitor } from '@/lib/performance/performance-monitor';

const inter = Inter({
  variable: '--font-inter',
  subsets: ['latin'],
  display: 'swap',
  preload: true,
});

export const metadata: Metadata = {
  title: {
    template: '%s | PAKE System',
    default: 'PAKE System - Transcendent Web Application',
  },
  description:
    'A transcendent web application with quantum-level responsiveness and cognitive ergonomics.',
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'
  ),
  keywords: [
    'PAKE System',
    'Web Application',
    'React',
    'Next.js',
    'TypeScript',
    'Performance',
    'Accessibility',
    'Real-time',
  ],
  authors: [{ name: 'PAKE System Team' }],
  creator: 'PAKE System',
  publisher: 'PAKE System',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang='en' className={inter.variable} suppressHydrationWarning>
      <head>
        {/* Critical CSS for performance */}
        <style
          dangerouslySetInnerHTML={{
            __html: `
              html {
                font-family: 'Inter', system-ui, sans-serif;
                scroll-behavior: smooth;
              }
              body {
                margin: 0;
                background: oklch(0.985 0.002 240);
                color: oklch(0.15 0.005 240);
                -webkit-font-smoothing: antialiased;
                -moz-osx-font-smoothing: grayscale;
              }
            `,
          }}
        />
      </head>
      <body className={`${inter.variable} font-sans antialiased`}>
        {/* Performance monitoring */}
        <PerformanceMonitor />

        {/* Enhanced provider hierarchy */}
        <StoreProvider>
          <TelemetryProvider>
            <ThemeProvider>
              <QueryProvider>
                <AuthProvider>
                  {/* Skip to main content for accessibility */}
                  <a
                    href='#main-content'
                    className='sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-brand-primary-600 focus:text-white focus:rounded-lg'
                  >
                    Skip to main content
                  </a>

                  <div id='app-root' className='min-h-screen'>
                    <main id='main-content'>{children}</main>
                  </div>
                </AuthProvider>
              </QueryProvider>
            </ThemeProvider>
          </TelemetryProvider>
        </StoreProvider>
      </body>
    </html>
  );
}
