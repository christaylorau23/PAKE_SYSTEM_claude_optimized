'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';

type Theme = 'light' | 'dark' | 'auto';
type AccessibilityMode = 'normal' | 'high_contrast' | 'large_text';

interface ThemeContextType {
  theme: Theme;
  accessibilityMode: AccessibilityMode;
  setTheme: (theme: Theme) => void;
  setAccessibilityMode: (mode: AccessibilityMode) => void;
  isDark: boolean;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}

interface ThemeProviderProps {
  children: React.ReactNode;
  defaultTheme?: Theme;
  defaultAccessibilityMode?: AccessibilityMode;
}

export function ThemeProvider({
  children,
  defaultTheme = 'auto',
  defaultAccessibilityMode = 'normal',
}: ThemeProviderProps) {
  const [theme, setTheme] = useState<Theme>(defaultTheme);
  const [accessibilityMode, setAccessibilityMode] = useState<AccessibilityMode>(
    defaultAccessibilityMode
  );
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    // Load theme from localStorage
    const savedTheme = localStorage.getItem('theme') as Theme;
    const savedAccessibility = localStorage.getItem(
      'accessibility-mode'
    ) as AccessibilityMode;

    if (savedTheme) {
      setTheme(savedTheme);
    }

    if (savedAccessibility) {
      setAccessibilityMode(savedAccessibility);
    }
  }, []);

  useEffect(() => {
    const root = window.document.documentElement;

    // Remove all theme classes
    root.classList.remove('light', 'dark');

    // Determine if dark mode should be active
    let shouldBeDark = false;

    if (theme === 'dark') {
      shouldBeDark = true;
    } else if (theme === 'auto') {
      shouldBeDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    }

    setIsDark(shouldBeDark);

    if (shouldBeDark) {
      root.classList.add('dark');
    } else {
      root.classList.add('light');
    }

    // Save to localStorage
    localStorage.setItem('theme', theme);
  }, [theme]);

  useEffect(() => {
    const root = window.document.documentElement;

    // Remove all accessibility classes
    root.classList.remove('high-contrast', 'large-text');

    // Add accessibility class if needed
    if (accessibilityMode === 'high_contrast') {
      root.classList.add('high-contrast');
    } else if (accessibilityMode === 'large_text') {
      root.classList.add('large-text');
    }

    // Save to localStorage
    localStorage.setItem('accessibility-mode', accessibilityMode);
  }, [accessibilityMode]);

  useEffect(() => {
    // Listen for system theme changes when using auto mode
    if (theme === 'auto') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

      const handleChange = () => {
        setIsDark(mediaQuery.matches);
        const root = window.document.documentElement;
        root.classList.remove('light', 'dark');
        root.classList.add(mediaQuery.matches ? 'dark' : 'light');
      };

      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }
  }, [theme]);

  const value = {
    theme,
    accessibilityMode,
    setTheme: (newTheme: Theme) => setTheme(newTheme),
    setAccessibilityMode: (mode: AccessibilityMode) =>
      setAccessibilityMode(mode),
    isDark,
  };

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}
