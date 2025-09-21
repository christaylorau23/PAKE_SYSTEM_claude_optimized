'use client';

import { Moon, Sun, Monitor, Eye, Type } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useTheme } from '@/context/ThemeContext';

export function ThemeToggle() {
  const { theme, setTheme, accessibilityMode, setAccessibilityMode } =
    useTheme();

  const toggleTheme = () => {
    if (theme === 'light') {
      setTheme('dark');
    } else if (theme === 'dark') {
      setTheme('auto');
    } else {
      setTheme('light');
    }
  };

  const toggleAccessibility = () => {
    if (accessibilityMode === 'normal') {
      setAccessibilityMode('high_contrast');
    } else if (accessibilityMode === 'high_contrast') {
      setAccessibilityMode('large_text');
    } else {
      setAccessibilityMode('normal');
    }
  };

  const getThemeIcon = () => {
    switch (theme) {
      case 'light':
        return <Sun className='h-4 w-4' />;
      case 'dark':
        return <Moon className='h-4 w-4' />;
      case 'auto':
        return <Monitor className='h-4 w-4' />;
    }
  };

  const getAccessibilityIcon = () => {
    switch (accessibilityMode) {
      case 'high_contrast':
        return <Eye className='h-4 w-4' />;
      case 'large_text':
        return <Type className='h-4 w-4' />;
      default:
        return <Eye className='h-4 w-4' />;
    }
  };

  return (
    <div className='flex items-center space-x-2'>
      <Button
        variant='ghost'
        size='icon'
        onClick={toggleTheme}
        aria-label={`Switch to ${theme === 'light' ? 'dark' : theme === 'dark' ? 'auto' : 'light'} theme`}
        title={`Current: ${theme} theme`}
      >
        {getThemeIcon()}
      </Button>

      <Button
        variant='ghost'
        size='icon'
        onClick={toggleAccessibility}
        aria-label={`Switch to ${accessibilityMode === 'normal' ? 'high contrast' : accessibilityMode === 'high_contrast' ? 'large text' : 'normal'} mode`}
        title={`Current: ${accessibilityMode} mode`}
      >
        {getAccessibilityIcon()}
      </Button>
    </div>
  );
}

export function ThemeToggleDropdown() {
  const { theme, setTheme, accessibilityMode, setAccessibilityMode } =
    useTheme();

  return (
    <div className='space-y-4'>
      <div>
        <label className='text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block'>
          Theme
        </label>
        <div className='grid grid-cols-3 gap-2'>
          <Button
            variant={theme === 'light' ? 'default' : 'outline'}
            size='sm'
            onClick={() => setTheme('light')}
            className='justify-start'
          >
            <Sun className='h-4 w-4 mr-2' />
            Light
          </Button>
          <Button
            variant={theme === 'dark' ? 'default' : 'outline'}
            size='sm'
            onClick={() => setTheme('dark')}
            className='justify-start'
          >
            <Moon className='h-4 w-4 mr-2' />
            Dark
          </Button>
          <Button
            variant={theme === 'auto' ? 'default' : 'outline'}
            size='sm'
            onClick={() => setTheme('auto')}
            className='justify-start'
          >
            <Monitor className='h-4 w-4 mr-2' />
            Auto
          </Button>
        </div>
      </div>

      <div>
        <label className='text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block'>
          Accessibility
        </label>
        <div className='grid grid-cols-1 gap-2'>
          <Button
            variant={accessibilityMode === 'normal' ? 'default' : 'outline'}
            size='sm'
            onClick={() => setAccessibilityMode('normal')}
            className='justify-start'
          >
            Normal
          </Button>
          <Button
            variant={
              accessibilityMode === 'high_contrast' ? 'default' : 'outline'
            }
            size='sm'
            onClick={() => setAccessibilityMode('high_contrast')}
            className='justify-start'
          >
            <Eye className='h-4 w-4 mr-2' />
            High Contrast
          </Button>
          <Button
            variant={accessibilityMode === 'large_text' ? 'default' : 'outline'}
            size='sm'
            onClick={() => setAccessibilityMode('large_text')}
            className='justify-start'
          >
            <Type className='h-4 w-4 mr-2' />
            Large Text
          </Button>
        </div>
      </div>
    </div>
  );
}
