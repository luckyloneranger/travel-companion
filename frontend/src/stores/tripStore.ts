import { create } from 'zustand';
import type { JourneyPlan, DayPlan, TripSummary } from '@/types';
import { api, type TipsResponse } from '@/services/api';

interface TripState {
  // Data
  journey: JourneyPlan | null;
  dayPlans: DayPlan[] | null;
  tripId: string | null;
  savedTrips: TripSummary[];
  tips: Record<string, string>;
  tipsLoading: boolean;

  // Actions
  setJourney: (journey: JourneyPlan, tripId?: string) => void;
  setDayPlans: (plans: DayPlan[]) => void;
  updateJourney: (journey: JourneyPlan) => void;
  updateDayPlans: (plans: DayPlan[]) => void;
  reset: () => void;

  // Async actions
  loadTrips: () => Promise<void>;
  loadTrip: (id: string) => Promise<void>;
  deleteTrip: (id: string) => Promise<void>;
  fetchTips: (activities: DayPlan['activities']) => Promise<void>;
}

export const useTripStore = create<TripState>((set, get) => ({
  journey: null,
  dayPlans: null,
  tripId: null,
  savedTrips: [],
  tips: {},
  tipsLoading: false,

  setJourney: (journey, tripId) => set({ journey, tripId: tripId ?? null }),
  setDayPlans: (plans) => set({ dayPlans: plans }),
  updateJourney: (journey) => set({ journey }),
  updateDayPlans: (plans) => set({ dayPlans: plans }),
  reset: () => set({ journey: null, dayPlans: null, tripId: null, tips: {} }),

  loadTrips: async () => {
    try {
      const trips = await api.listTrips();
      set({ savedTrips: trips });
    } catch (e) {
      console.error('Failed to load trips:', e);
    }
  },

  loadTrip: async (id) => {
    try {
      const trip = await api.getTrip(id);
      set({
        journey: trip.journey,
        dayPlans: trip.day_plans,
        tripId: trip.id,
      });
    } catch (e) {
      console.error('Failed to load trip:', e);
    }
  },

  deleteTrip: async (id) => {
    try {
      await api.deleteTrip(id);
      set((state) => ({
        savedTrips: state.savedTrips.filter((t) => t.id !== id),
        ...(state.tripId === id
          ? { journey: null, dayPlans: null, tripId: null, tips: {} }
          : {}),
      }));
    } catch (e) {
      console.error('Failed to delete trip:', e);
    }
  },

  fetchTips: async (activities) => {
    const { tripId } = get();
    if (!tripId) return;
    set({ tipsLoading: true });
    try {
      const result: TipsResponse = await api.generateTips(tripId, activities);
      set((state) => ({ tips: { ...state.tips, ...result.tips } }));
    } catch (e) {
      console.error('Failed to fetch tips:', e);
    } finally {
      set({ tipsLoading: false });
    }
  },
}));
