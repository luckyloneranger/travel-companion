import { create } from "zustand";

interface UIStore {
  loading: boolean;
  darkMode: boolean;
  setLoading: (loading: boolean) => void;
  toggleDarkMode: () => void;
}

export const useUIStore = create<UIStore>((set) => ({
  loading: false,
  darkMode: window.matchMedia("(prefers-color-scheme: dark)").matches,
  setLoading: (loading) => set({ loading }),
  toggleDarkMode: () => set((s) => ({ darkMode: !s.darkMode })),
}));
