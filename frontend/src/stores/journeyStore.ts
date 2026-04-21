import { create } from "zustand";
import { createJourney, getJourney, listJourneys, deleteJourney, pollJob, type JourneyResponse, type JourneySummary, type JourneyCreateRequest } from "@/lib/api";

interface JourneyStore {
  journeys: JourneySummary[];
  currentJourney: JourneyResponse | null;
  creating: boolean;
  jobId: string | null;
  jobProgress: number;
  loading: boolean;
  error: string | null;

  create: (request: JourneyCreateRequest) => Promise<{ id: string; status: string; job_id?: string }>;
  pollUntilComplete: (jobId: string, onComplete: (result: Record<string, unknown>) => void) => Promise<void>;
  fetchJourney: (id: string) => Promise<void>;
  fetchJourneys: () => Promise<void>;
  removeJourney: (id: string) => Promise<void>;
  clearCurrent: () => void;
}

export const useJourneyStore = create<JourneyStore>((set) => ({
  journeys: [],
  currentJourney: null,
  creating: false,
  jobId: null,
  jobProgress: 0,
  loading: false,
  error: null,

  create: async (request) => {
    set({ creating: true, error: null, jobProgress: 0 });
    try {
      const result = await createJourney(request);
      set({ jobId: result.job_id || null, creating: false });
      return result;
    } catch (e) {
      set({ error: (e as Error).message, creating: false });
      throw e;
    }
  },

  pollUntilComplete: async (jobId, onComplete) => {
    const poll = async () => {
      try {
        const status = await pollJob(jobId);
        set({ jobProgress: status.progress_pct });
        if (status.status === "completed") {
          set({ jobId: null });
          onComplete(status.result || {});
          return;
        }
        if (status.status === "failed") {
          set({ error: status.error || "Generation failed", jobId: null });
          return;
        }
        setTimeout(poll, 3000);
      } catch (e) {
        set({ error: (e as Error).message, jobId: null });
      }
    };
    poll();
  },

  fetchJourney: async (id) => {
    set({ loading: true, error: null });
    try {
      const journey = await getJourney(id);
      set({ currentJourney: journey, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  fetchJourneys: async () => {
    set({ loading: true, error: null });
    try {
      const data = await listJourneys();
      set({ journeys: data.journeys, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  removeJourney: async (id) => {
    await deleteJourney(id);
    set((state) => ({ journeys: state.journeys.filter((j) => j.id !== id) }));
  },

  clearCurrent: () => set({ currentJourney: null }),
}));
