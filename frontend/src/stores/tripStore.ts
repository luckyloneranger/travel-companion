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

  setJourney: (journey, tripId) => {
    set({ journey, tripId: tripId ?? null });
    if (tripId) sessionStorage.setItem('tc_tripId', tripId);
  },
  setDayPlans: (plans) => {
    if (plans.length === 0) {
      set({ dayPlans: plans, costBreakdown: null });
      return;
    }
    const { journey } = get();

    // Activity costs from day plans
    let dining = 0, activitiesCost = 0;
    for (const dp of plans) {
      for (const a of dp.activities) {
        if (a.estimated_cost_usd) {
          const cat = (a.place.category || '').toLowerCase();
          if (cat.includes('restaurant') || cat.includes('cafe') || cat.includes('bakery') || cat.includes('food') || cat.includes('bistro')) {
            dining += a.estimated_cost_usd;
          } else {
            activitiesCost += a.estimated_cost_usd;
          }
        }
      }
    }

    // Accommodation costs from journey
    let accommodation = 0;
    if (journey) {
      for (const city of journey.cities) {
        if (city.accommodation?.estimated_nightly_usd) {
          accommodation += city.accommodation.estimated_nightly_usd * city.days;
        }
      }
    }

    // Transport costs from journey
    let transport = 0;
    if (journey) {
      for (const leg of journey.travel_legs) {
        if (leg.fare_usd) {
          transport += leg.fare_usd;
        }
      }
    }

    const total = dining + activitiesCost + accommodation + transport;
    const breakdown: CostBreakdown | null = total > 0 ? {
      accommodation_usd: Math.round(accommodation * 100) / 100,
      transport_usd: Math.round(transport * 100) / 100,
      activities_usd: Math.round(activitiesCost * 100) / 100,
      dining_usd: Math.round(dining * 100) / 100,
      total_usd: Math.round(total * 100) / 100,
    } : null;
    set({ dayPlans: plans, costBreakdown: breakdown });
  },
  updateJourney: (journey) => set({ journey }),
  updateDayPlans: (plans) => set({ dayPlans: plans }),
  reset: () => {
    set({ journey: null, dayPlans: null, tripId: null, tips: {}, costBreakdown: null });
    sessionStorage.removeItem('tc_tripId');
    sessionStorage.removeItem('tc_phase');
  },

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
