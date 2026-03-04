import { create } from 'zustand';
import type { JourneyPlan, DayPlan, TripSummary, CostBreakdown } from '@/types';
import { api, type TipsResponse } from '@/services/api';

interface TripState {
  // Data
  journey: JourneyPlan | null;
  dayPlans: DayPlan[] | null;
  tripId: string | null;
  savedTrips: TripSummary[];
  tips: Record<string, string>;
  tipsLoading: boolean;
  costBreakdown: CostBreakdown | null;

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
  costBreakdown: null,

  setJourney: (journey, tripId) => set({ journey, tripId: tripId ?? null }),
  setDayPlans: (plans) => {
    // Compute cost breakdown from plans
    let total = 0, dining = 0, activities = 0;
    for (const dp of plans) {
      for (const a of dp.activities) {
        if (a.estimated_cost_usd) {
          total += a.estimated_cost_usd;
          const cat = (a.place.category || '').toLowerCase();
          if (cat.includes('restaurant') || cat.includes('cafe') || cat.includes('bakery') || cat.includes('food') || cat.includes('bistro')) {
            dining += a.estimated_cost_usd;
          } else {
            activities += a.estimated_cost_usd;
          }
        }
      }
    }
    const breakdown = total > 0 ? { accommodation_usd: 0, transport_usd: 0, activities_usd: activities, dining_usd: dining, total_usd: total } : null;
    set({ dayPlans: plans, costBreakdown: breakdown });
  },
  updateJourney: (journey) => set({ journey }),
  updateDayPlans: (plans) => set({ dayPlans: plans }),
  reset: () => set({ journey: null, dayPlans: null, tripId: null, tips: {}, costBreakdown: null }),

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
        costBreakdown: trip.cost_breakdown ?? null,
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
