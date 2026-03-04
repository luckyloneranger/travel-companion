import { useCallback, useRef } from 'react';
import { api } from '@/services/api';
import { useTripStore } from '@/stores/tripStore';
import { useUIStore } from '@/stores/uiStore';
import type { TripRequest, JourneyPlan } from '@/types';

const STALL_TIMEOUT_MS = 180_000;

export function useStreamingPlan() {
  const abortRef = useRef<AbortController | null>(null);
  const { setJourney } = useTripStore();
  const { setPhase, setProgress, setLoading, setError } = useUIStore();

  const startPlanning = useCallback(async (request: TripRequest) => {
    // Cancel any existing stream
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setPhase('planning');
    setLoading(true);
    setError(null);

    let stallTimer: ReturnType<typeof setTimeout> | null = null;

    const clearStallTimer = () => {
      if (stallTimer !== null) {
        clearTimeout(stallTimer);
        stallTimer = null;
      }
    };

    const resetStallTimer = () => {
      clearStallTimer();
      stallTimer = setTimeout(() => {
        if (!controller.signal.aborted) {
          setError('Planning is taking longer than expected. You can wait or cancel and try again.');
        }
      }, STALL_TIMEOUT_MS);
    };

    try {
      resetStallTimer();

      for await (const event of api.planTripStream(request, controller.signal)) {
        if (controller.signal.aborted) break;

        resetStallTimer();
        setProgress(event);

        if (event.phase === 'complete' && event.data) {
          const { trip_id, ...journeyData } = event.data as Record<string, unknown>;
          setJourney(journeyData as unknown as JourneyPlan, trip_id as string);
          setPhase('preview');
        }

        if (event.phase === 'error') {
          setError(event.message);
          setPhase('input');
        }
      }
    } catch (err) {
      if (!controller.signal.aborted) {
        const message = err instanceof Error ? err.message : 'Planning failed';
        const userMessage = message.includes('fetch') || message.includes('network') || message.includes('Failed to fetch') || message.startsWith('HTTP')
          ? 'Connection lost. Please try again.'
          : message;
        setError(userMessage);
        setPhase('input');
      }
    } finally {
      clearStallTimer();
      setLoading(false);
      abortRef.current = null;
    }
  }, [setJourney, setPhase, setProgress, setLoading, setError]);

  const cancelPlanning = useCallback(() => {
    abortRef.current?.abort();
    setPhase('input');
    setLoading(false);
    setProgress(null);
  }, [setPhase, setLoading, setProgress]);

  return { startPlanning, cancelPlanning };
}
