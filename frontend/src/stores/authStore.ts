import { create } from 'zustand';
import type { User } from '@/types';
import { api } from '@/services/api';

const TOKEN_KEY = 'tc_auth_token';

/** Capture token from OAuth redirect URL (?token=xxx) and store it. */
function captureTokenFromUrl(): void {
  const params = new URLSearchParams(window.location.search);
  const token = params.get('token');
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
    // Remove token from URL without reload
    params.delete('token');
    const clean = params.toString();
    const newUrl = window.location.pathname + (clean ? `?${clean}` : '') + window.location.hash;
    window.history.replaceState({}, '', newUrl);
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
  },
}));
