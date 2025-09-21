import { useEffect, useCallback } from 'react';

interface KeyboardNavigationOptions {
  enableArrowKeys?: boolean;
  enableTabTrapping?: boolean;
  enableEscapeKey?: boolean;
  onEscape?: () => void;
}

export function useKeyboardNavigation(
  containerRef: React.RefObject<HTMLElement>,
  options: KeyboardNavigationOptions = {}
) {
  const {
    enableArrowKeys = true,
    enableTabTrapping = false,
    enableEscapeKey = true,
    onEscape,
  } = options;

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      const container = containerRef.current;
      if (!container) return;

      const focusableElements = container.querySelectorAll(
        'button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])'
      );

      const focusableArray = Array.from(focusableElements) as HTMLElement[];
      const currentIndex = focusableArray.indexOf(
        document.activeElement as HTMLElement
      );

      switch (event.key) {
        case 'ArrowDown':
          if (enableArrowKeys && currentIndex < focusableArray.length - 1) {
            event.preventDefault();
            focusableArray[currentIndex + 1]?.focus();
          }
          break;

        case 'ArrowUp':
          if (enableArrowKeys && currentIndex > 0) {
            event.preventDefault();
            focusableArray[currentIndex - 1]?.focus();
          }
          break;

        case 'Home':
          if (enableArrowKeys) {
            event.preventDefault();
            focusableArray[0]?.focus();
          }
          break;

        case 'End':
          if (enableArrowKeys) {
            event.preventDefault();
            focusableArray[focusableArray.length - 1]?.focus();
          }
          break;

        case 'Tab':
          if (enableTabTrapping) {
            if (event.shiftKey && currentIndex === 0) {
              event.preventDefault();
              focusableArray[focusableArray.length - 1]?.focus();
            } else if (
              !event.shiftKey &&
              currentIndex === focusableArray.length - 1
            ) {
              event.preventDefault();
              focusableArray[0]?.focus();
            }
          }
          break;

        case 'Escape':
          if (enableEscapeKey && onEscape) {
            event.preventDefault();
            onEscape();
          }
          break;
      }
    },
    [
      containerRef,
      enableArrowKeys,
      enableTabTrapping,
      enableEscapeKey,
      onEscape,
    ]
  );

  useEffect(() => {
    const container = containerRef.current;
    if (container) {
      container.addEventListener('keydown', handleKeyDown);
      return () => container.removeEventListener('keydown', handleKeyDown);
    }
  }, [handleKeyDown]);
}
