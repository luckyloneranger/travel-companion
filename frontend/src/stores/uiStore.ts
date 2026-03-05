import { create } from 'zustand';
import type { ProgressEvent } from '@/types';

type AppPhase = 'input' | 'planning' | 'preview' | 'day-plans';

interface UIState {
  // Phase
  phase: AppPhase;
  setPhase: (phase: AppPhase) => void;

  // Planning progress
  progress: ProgressEvent | null;
  setProgress: (event: ProgressEvent | null) => void;

  // Loading / error
  isLoading: boolean;
  error: string | null;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;

  // Map toggles
  showJourneyMap: boolean;
  toggleJourneyMap: () => void;
  dayMapVisible: Record<number, boolean>;
  toggleDayMap: (dayNumber: number) => void;

  // Chat
  isChatOpen: boolean;
  chatContext: 'journey' | 'day_plans';
  openChat: (context?: 'journey' | 'day_plans') => void;
  closeChat: () => void;

  // Wizard
  wizardStep: number;
  setWizardStep: (step: number) => void;

  // Sign in modal
  showSignIn: boolean;
  openSignIn: () => void;
  closeSignIn: () => void;

  // Day plans background generation
  dayPlansGenerating: boolean;
  setDayPlansGenerating: (generating: boolean) => void;

  // Reset
  resetUI: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  phase: 'input',
  setPhase: (phase) => {
    set({ phase });
    if (phase !== 'planning') {
      sessionStorage.setItem('tc_phase', phase);
      // Push browser history state so back/forward buttons navigate phases
      const currentState = history.state?.phase;
      if (currentState !== phase) {
        history.pushState({ phase }, '', undefined);
      }
    }
  },

  progress: null,
  setProgress: (event) => set({ progress: event }),

  isLoading: false,
  error: null,
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),

  showJourneyMap: false,
  toggleJourneyMap: () => set((s) => ({ showJourneyMap: !s.showJourneyMap })),
  dayMapVisible: {},
  toggleDayMap: (dayNumber) =>
    set((s) => ({
      dayMapVisible: {
        ...s.dayMapVisible,
        [dayNumber]: !s.dayMapVisible[dayNumber],
      },
    })),

  isChatOpen: false,
  chatContext: 'journey',
  openChat: (context = 'journey') =>
    set({ isChatOpen: true, chatContext: context }),
  closeChat: () => set({ isChatOpen: false }),

  wizardStep: 1,
  setWizardStep: (step) => set({ wizardStep: step }),

  showSignIn: false,
  openSignIn: () => set({ showSignIn: true }),
  closeSignIn: () => set({ showSignIn: false }),

  dayPlansGenerating: false,
  setDayPlansGenerating: (generating) => set({ dayPlansGenerating: generating }),

  resetUI: () => {
    set({
      phase: 'input',
      progress: null,
      isLoading: false,
      error: null,
      showJourneyMap: false,
      dayMapVisible: {},
      isChatOpen: false,
      wizardStep: 1,
      dayPlansGenerating: false,
      showSignIn: false,
    });
    sessionStorage.removeItem('tc_phase');
    sessionStorage.removeItem('tc_tripId');
  },
}));
