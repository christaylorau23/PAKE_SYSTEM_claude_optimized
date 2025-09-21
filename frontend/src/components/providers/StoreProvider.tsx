/* Zustand Store Provider - Global State Management Provider */
/* React context wrapper for Zustand store with SSR support */

'use client';

import React, { createContext, useContext, useRef } from 'react';
import { useStore as useZustandStore } from 'zustand';
import { AppStore, createAppStore } from '@/lib/store';

interface StoreProviderProps {
  children: React.ReactNode;
  initialState?: Partial<ReturnType<AppStore['getState']>>;
}

// Create store context
const StoreContext = createContext<AppStore | null>(null);

export const StoreProvider: React.FC<StoreProviderProps> = ({
  children,
  initialState,
}) => {
  const storeRef = useRef<AppStore>();

  if (!storeRef.current) {
    storeRef.current = createAppStore();

    // Apply initial state if provided
    if (initialState) {
      storeRef.current.setState(initialState as unknown);
    }
  }

  return (
    <StoreContext.Provider value={storeRef.current}>
      {children}
    </StoreContext.Provider>
  );
};

// Hook to use the store from context
export const useAppStore = <T,>(
  selector: (state: ReturnType<AppStore['getState']>) => T
): T => {
  const store = useContext(StoreContext);

  if (!store) {
    throw new Error('useAppStore must be used within a StoreProvider');
  }

  return useZustandStore(store, selector);
};

// Hook to get the raw store instance
export const useStoreApi = (): AppStore => {
  const store = useContext(StoreContext);

  if (!store) {
    throw new Error('useStoreApi must be used within a StoreProvider');
  }

  return store;
};

export default StoreProvider;
