import { create } from 'zustand';
import type { User } from '@/types';
import { api } from '@/services/api';

import { AUTH_TOKEN_KEY } from '@/constants';

const TOKEN_KEY = AUTH_TOKEN_KEY;

/** Capture token from OAuth redirect URL (#token=xxx or ?token=xxx) and store it. */
function captureTokenFromUrl(): void {
  // Read token from hash fragment (OAuth redirect) or query params (legacy)
  const hash = window.location.hash;
  const hashToken = hash.startsWith('#token=') ? hash.slice(7) : null;
  const searchToken = new URLSearchParams(window.location.search).get('token');
  const token = hashToken || searchToken;
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
    // Remove token from URL without reload
    window.history.replaceState({}, '', window.location.pathname);
  }
}

// Run once on module load
captureTokenFromUrl();

interface AuthState {
  user: User | null;
  isLoading: boolean;
  fetchUser: () => Promise<void>;
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: true,

  fetchUser: async () => {
    set({ isLoading: true });
    try {
      const data = await api.getMe();
      set({ user: data.user, isLoading: false });
    } catch {
      set({ user: null, isLoading: false });
    }
  },

  logout: async () => {
    try {
      await api.logout();
    } catch {
      // ignore
    }
    localStorage.removeItem(TOKEN_KEY);
    set({ user: null });
    // Clear trip and UI state so stale data doesn't linger
    const { useTripStore } = await import('./tripStore');
    const { useUIStore } = await import('./uiStore');
    useTripStore.getState().reset();
    useUIStore.getState().resetUI();
  },
}));
