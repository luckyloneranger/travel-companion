import { create } from 'zustand';
import type { JourneyPlan, DayPlan, TripSummary, CostBreakdown, Travelers } from '@/types';
import { api, type TipsResponse } from '@/services/api';
import { showToast } from '@/components/ui/toast';

function isAuthError(e: unknown): boolean {
  return e instanceof Error && e.message === '__auth_required__';
}

interface TripState {
  // Data
  journey: JourneyPlan | null;
  dayPlans: DayPlan[] | null;
  tripId: string | null;
  travelers: Travelers;
  savedTrips: TripSummary[];
  tripsLoading: boolean;
  tips: Record<string, string>;
  tipsLoading: boolean;
  costBreakdown: CostBreakdown | null;
  recentChanges: {
    added: Set<string>;
    modified: Set<string>;
    removed: string[];
  } | null;

  // Actions
  setJourney: (journey: JourneyPlan, tripId?: string) => void;
  setDayPlans: (plans: DayPlan[]) => void;
  setTravelers: (travelers: Travelers) => void;
  updateJourney: (journey: JourneyPlan) => void;
  updateDayPlans: (plans: DayPlan[]) => void;
  setRecentChanges: (changes: { added: Set<string>; modified: Set<string>; removed: string[] } | null) => void;
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
  travelers: { adults: 1, children: 0, infants: 0 },
  savedTrips: [],
  tripsLoading: false,
  tips: {},
  tipsLoading: false,
  costBreakdown: null,
  recentChanges: null,

  setJourney: (journey, tripId) => {
    set({ journey, tripId: tripId ?? null });
    if (tripId) sessionStorage.setItem('tc_tripId', tripId);
  },
  setTravelers: (travelers) => set({ travelers }),
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
        } else if (leg.fare) {
          const match = leg.fare.match(/[\d.]+/);
          if (match) transport += parseFloat(match[0]);
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
  setRecentChanges: (changes) => set({ recentChanges: changes }),
  reset: () => {
    set({ journey: null, dayPlans: null, tripId: null, travelers: { adults: 1, children: 0, infants: 0 }, tips: {}, costBreakdown: null, recentChanges: null });
    sessionStorage.removeItem('tc_tripId');
    sessionStorage.removeItem('tc_phase');
    sessionStorage.removeItem('tc_wizard');
  },

  loadTrips: async () => {
    const { useAuthStore } = await import('./authStore');
    if (!useAuthStore.getState().user) {
      set({ savedTrips: [], tripsLoading: false });
      return;
    }
    set({ tripsLoading: true });
    try {
      const trips = await api.listTrips();
      set({ savedTrips: trips, tripsLoading: false });
    } catch (e) {
      set({ tripsLoading: false });
      if (isAuthError(e)) return;
      console.error('Failed to load trips:', e);
      showToast('Failed to load trips. Please try again.', 'error');
      const { useUIStore } = await import('./uiStore');
      useUIStore.getState().setError('Failed to load saved trips. Please try again.');
    }
  },

  loadTrip: async (id) => {
    try {
      const trip = await api.getTrip(id);
      set({
        journey: trip.journey,
        dayPlans: trip.day_plans,
        tripId: trip.id,
        travelers: trip.request.travelers ?? { adults: 1, children: 0, infants: 0 },
        costBreakdown: trip.cost_breakdown ?? null,
      });
    } catch (e) {
      if (isAuthError(e)) throw e;
      console.error('Failed to load trip:', e);
      const { useUIStore } = await import('./uiStore');
      useUIStore.getState().setError('Failed to load trip. Please try again.');
      throw e;
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
      if (isAuthError(e)) throw e;
      console.error('Failed to delete trip:', e);
      const { useUIStore } = await import('./uiStore');
      useUIStore.getState().setError('Failed to delete trip. Please try again.');
      throw e;
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
      if (isAuthError(e)) return;
      console.error('Failed to fetch tips:', e);
      const { useUIStore } = await import('./uiStore');
      useUIStore.getState().setError('Failed to load tips. Please try again.');
    } finally {
      set({ tipsLoading: false });
    }
  },
}));
