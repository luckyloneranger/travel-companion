/**
 * API client for the Travel Companion backend
 * 
 * This module provides V6 streaming journey planning API functions.
 */

import type { 
  JourneyRequest,
  V6ProgressEvent,
  V6JourneyPlan,
  V6DayPlansRequest,
  V6DayPlanProgress,
  V6DayPlan,
} from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Timeout for SSE events (3 minutes - generation can take a while)
const SSE_TIMEOUT_MS = 180000;
// Timeout for individual read operations (60 seconds between events)
const READ_TIMEOUT_MS = 60000;

/**
 * Create a promise that rejects after a timeout
 */
function createTimeout(ms: number, message: string): Promise<never> {
  return new Promise((_, reject) => {
    setTimeout(() => reject(new Error(message)), ms);
  });
}

/**
 * Read with timeout - ensures we don't hang indefinitely
 */
async function readWithTimeout(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  timeoutMs: number
): Promise<ReadableStreamReadResult<Uint8Array>> {
  return Promise.race([
    reader.read(),
    createTimeout(timeoutMs, `No data received for ${timeoutMs / 1000} seconds`),
  ]);
}

/**
 * Extract V6JourneyPlan from complete event data
 */
export function extractV6JourneyFromEvent(event: V6ProgressEvent): V6JourneyPlan {
  const data = event.data || {};
  return {
    theme: data.theme as string || 'Journey of Discovery',
    summary: data.summary as string || '',
    route: data.route as string || '',
    origin: data.origin as string || '',
    region: data.region as string || '',
    total_days: data.total_days as number || 0,
    cities: (data.cities as unknown as V6JourneyPlan['cities']) || [],
    travel_legs: (data.travel_legs as unknown as V6JourneyPlan['travel_legs']) || [],
    review_score: data.review_score as number,
    total_travel_hours: data.total_travel_hours as number,
    total_distance_km: data.total_distance_km as number,
  };
}

// ═══════════════════════════════════════════════════════════════
// V6 JOURNEY PLANNING (Scout → Enrich → Review → Planner Loop)
// ═══════════════════════════════════════════════════════════════

/**
 * Plan journey using V6 LLM-first workflow with streaming progress
 * Flow: Scout → Enrich → Review → [Loop] → Planner → Enrich → Review → ...
 * 
 * Features:
 * - LLM decides number of cities based on days/pace/region
 * - Regional transport intelligence (buses in Vietnam, trains in India, etc.)
 * - Iterative refinement until quality threshold met
 * 
 * @param request - Journey planning request
 * @param signal - Optional AbortSignal for cancellation
 * @yields V6ProgressEvent - Progress updates during generation
 * @returns V6JourneyPlan - The final journey plan
 */
export async function* planJourneyV6Stream(
  request: JourneyRequest,
  signal?: AbortSignal
): AsyncGenerator<V6ProgressEvent, V6JourneyPlan> {
  const controller = new AbortController();
  const overallTimeout = setTimeout(() => controller.abort(), SSE_TIMEOUT_MS);

  // Combine external signal with our timeout controller
  if (signal) {
    signal.addEventListener('abort', () => controller.abort());
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/journey/v6/plan/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
      signal: controller.signal,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        (errorData as { detail?: string }).detail || `HTTP error! status: ${response.status}`
      );
    }

    if (!response.body) {
      throw new Error('Response body is null');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const result = await readWithTimeout(reader, READ_TIMEOUT_MS);

        if (result.done) {
          // Process any remaining buffer content
          if (buffer.trim()) {
            const remainingLines = buffer.split('\n');
            for (const line of remainingLines) {
              if (line.startsWith('data: ')) {
                const jsonStr = line.slice(6).trim();
                if (jsonStr) {
                  try {
                    const event = JSON.parse(jsonStr) as V6ProgressEvent;
                    yield event;
                    
                    if (event.phase === 'complete' && event.data) {
                      return extractV6JourneyFromEvent(event);
                    }
                  } catch (parseError) {
                    console.warn('Failed to parse final V6 SSE event:', jsonStr, parseError);
                  }
                }
              }
            }
          }
          break;
        }

        buffer += decoder.decode(result.value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const jsonStr = line.slice(6).trim();
            if (jsonStr) {
              try {
                const event = JSON.parse(jsonStr) as V6ProgressEvent;
                yield event;

                // Return final response on 'complete'
                if (event.phase === 'complete' && event.data) {
                  return extractV6JourneyFromEvent(event);
                }

                // Handle error event
                if (event.phase === 'error') {
                  throw new Error(event.data?.error as string || 'V6 generation failed');
                }
              } catch (parseError) {
                if (parseError instanceof Error && parseError.message.includes('generation failed')) {
                  throw parseError;
                }
                console.warn('Failed to parse V6 SSE event:', jsonStr, parseError);
              }
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }

    throw new Error('V6 stream ended unexpectedly');
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('Request timed out. Please try again.');
    }
    throw error;
  } finally {
    clearTimeout(overallTimeout);
  }
}

// ═══════════════════════════════════════════════════════════════
// V6 DAY PLANS API
// ═══════════════════════════════════════════════════════════════

/**
 * Generate detailed day plans for a V6 journey with streaming progress.
 * 
 * Takes an approved journey plan and generates detailed itineraries
 * for each city. Yields progress events as each city is processed.
 * 
 * @param request - Day plans request with journey and preferences
 * @param signal - Optional AbortSignal for cancellation
 * @yields V6DayPlanProgress - Progress updates during generation
 * @returns V6DayPlan[] - Array of day plans for all cities
 */
export async function* generateV6DayPlansStream(
  request: V6DayPlansRequest,
  signal?: AbortSignal
): AsyncGenerator<V6DayPlanProgress, V6DayPlan[]> {
  const controller = new AbortController();
  // Day plans take longer - allow 5 minutes per city
  const timeoutMs = Math.max(SSE_TIMEOUT_MS, (request.journey.cities?.length || 5) * 300000);
  const overallTimeout = setTimeout(() => controller.abort(), timeoutMs);

  if (signal) {
    signal.addEventListener('abort', () => controller.abort());
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/journey/v6/days/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
      signal: controller.signal,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        (errorData as { detail?: string }).detail || `HTTP error! status: ${response.status}`
      );
    }

    if (!response.body) {
      throw new Error('Response body is null');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const result = await readWithTimeout(reader, READ_TIMEOUT_MS);

        if (result.done) {
          // Process remaining buffer
          if (buffer.trim()) {
            const lines = buffer.split('\n');
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const jsonStr = line.slice(6).trim();
                if (jsonStr) {
                  try {
                    const event = JSON.parse(jsonStr) as V6DayPlanProgress;
                    yield event;
                    if (event.phase === 'complete' && event.data?.all_day_plans) {
                      return event.data.all_day_plans as V6DayPlan[];
                    }
                  } catch (e) {
                    console.warn('Failed to parse final day plan event:', jsonStr, e);
                  }
                }
              }
            }
          }
          break;
        }

        buffer += decoder.decode(result.value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const jsonStr = line.slice(6).trim();
            if (jsonStr) {
              try {
                const event = JSON.parse(jsonStr) as V6DayPlanProgress;
                yield event;

                if (event.phase === 'complete' && event.data?.all_day_plans) {
                  return event.data.all_day_plans as V6DayPlan[];
                }

                if (event.phase === 'error') {
                  throw new Error(event.data?.error as string || 'Day plan generation failed');
                }
              } catch (parseError) {
                if (parseError instanceof Error && parseError.message.includes('generation failed')) {
                  throw parseError;
                }
                console.warn('Failed to parse day plan SSE event:', jsonStr, parseError);
              }
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }

    throw new Error('Day plan stream ended unexpectedly');
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('Request timed out. Please try again.');
    }
    throw error;
  } finally {
    clearTimeout(overallTimeout);
  }
}
