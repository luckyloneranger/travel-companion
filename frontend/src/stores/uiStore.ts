import { create } from "zustand";

type Phase = "input" | "planning" | "preview" | "day-plans" | "live";

interface ProgressState {
  phase: string;
  message: string;
  progress: number;
  data?: Record<string, unknown>;
}

interface UIStore {
  loading: boolean;
  darkMode: boolean;
  error: string | null;
  phase: Phase;
  progress: ProgressState | null;
  wizardStep: number;
  dayPlansGenerating: boolean;
  isChatOpen: boolean;
  chatContext: string | null;
  chatPrefill: string | null;
  signInOpen: boolean;

  setLoading: (loading: boolean) => void;
  toggleDarkMode: () => void;
  setError: (error: string | null) => void;
  setPhase: (phase: Phase) => void;
  setProgress: (progress: ProgressState | null) => void;
  setWizardStep: (step: number) => void;
  setDayPlansGenerating: (generating: boolean) => void;
  openChat: (context?: string, prefill?: string) => void;
  closeChat: () => void;
  openSignIn: () => void;
  closeSignIn: () => void;
  resetUI: () => void;
}

export const useUIStore = create<UIStore>((set) => ({
  loading: false,
  darkMode: window.matchMedia("(prefers-color-scheme: dark)").matches,
  error: null,
  phase: "input",
  progress: null,
  wizardStep: 0,
  dayPlansGenerating: false,
  isChatOpen: false,
  chatContext: null,
  chatPrefill: null,
  signInOpen: false,

  setLoading: (loading) => set({ loading }),
  toggleDarkMode: () => set((s) => ({ darkMode: !s.darkMode })),
  setError: (error) => set({ error }),
  setPhase: (phase) => set({ phase }),
  setProgress: (progress) => set({ progress }),
  setWizardStep: (step) => set({ wizardStep: step }),
  setDayPlansGenerating: (generating) => set({ dayPlansGenerating: generating }),
  openChat: (context, prefill) => set({ isChatOpen: true, chatContext: context ?? null, chatPrefill: prefill ?? null }),
  closeChat: () => set({ isChatOpen: false, chatContext: null, chatPrefill: null }),
  openSignIn: () => set({ signInOpen: true }),
  closeSignIn: () => set({ signInOpen: false }),
  resetUI: () => set({
    error: null,
    phase: "input",
    progress: null,
    wizardStep: 0,
    dayPlansGenerating: false,
    isChatOpen: false,
    chatContext: null,
    chatPrefill: null,
    signInOpen: false,
  }),
}));
