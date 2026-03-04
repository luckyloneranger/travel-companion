import { useCallback, useRef } from 'react';
import { api } from '@/services/api';
import { useTripStore } from '@/stores/tripStore';
import { useUIStore } from '@/stores/uiStore';
import type { DayPlan } from '@/types';

const STALL_TIMEOUT_MS = 90_000;

export function useStreamingDayPlans() {
  const abortRef = useRef<AbortController | null>(null);
  const { tripId, setDayPlans } = useTripStore();
  const { setPhase, setProgress, setLoading, setError } = useUIStore();

  const startGenerating = useCallback(async () => {
    if (!tripId) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setPhase('planning'); // reuse planning phase for day plans too
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

      for await (const event of api.generateDayPlansStream(tripId, controller.signal)) {
        if (controller.signal.aborted) break;

        resetStallTimer();
        setProgress(event);

        if (event.phase === 'complete' && event.data) {
          const dayPlans = (event.data as Record<string, unknown>).day_plans as DayPlan[];
          setDayPlans(dayPlans);
          setPhase('day-plans');
        }

        if (event.phase === 'error') {
          setError(event.message);
          setPhase('preview');
        }
      }
    } catch (err) {
      if (!controller.signal.aborted) {
        const message = err instanceof Error ? err.message : 'Day plan generation failed';
        const userMessage = message.includes('fetch') || message.includes('network') || message.includes('Failed to fetch') || message.startsWith('HTTP')
          ? 'Connection lost. Please try again.'
          : message;
        setError(userMessage);
        setPhase('preview');
      }
    } finally {
      clearStallTimer();
      setLoading(false);
      abortRef.current = null;
    }
  }, [tripId, setDayPlans, setPhase, setProgress, setLoading, setError]);

  const cancelGenerating = useCallback(() => {
    abortRef.current?.abort();
    setPhase('preview');
    setLoading(false);
    setProgress(null);
  }, [setPhase, setLoading, setProgress]);

  return { startGenerating, cancelGenerating };
}
