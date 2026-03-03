// Minimal type stubs — will be replaced by full type definitions.

/** High-level journey plan returned by the backend. */
export interface JourneyPlan {
  cities: CityOverview[];
  transport_segments: TransportSegment[];
  total_days: number;
  title?: string;
  [key: string]: unknown;
}

export interface CityOverview {
  city: string;
  country: string;
  days: number;
  highlights: string[];
  [key: string]: unknown;
}

export interface TransportSegment {
  from_city: string;
  to_city: string;
  mode: string;
  duration_minutes: number;
  [key: string]: unknown;
}

/** Detailed day plan for a single day. */
export interface DayPlan {
  day_number: number;
  city: string;
  date?: string;
  activities: Activity[];
  [key: string]: unknown;
}

export interface Activity {
  name: string;
  type: string;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  location?: {
    lat: number;
    lng: number;
    address?: string;
  };
  [key: string]: unknown;
}

/** Summary of a saved trip (used in trip listing). */
export interface TripSummary {
  id: string;
  title: string;
  cities: string[];
  total_days: number;
  created_at: string;
  [key: string]: unknown;
}

/** Full trip response from the backend. */
export interface TripResponse {
  id: string;
  journey: JourneyPlan;
  day_plans: DayPlan[];
  [key: string]: unknown;
}

/** SSE progress event emitted during planning. */
export interface ProgressEvent {
  type: 'progress' | 'complete' | 'error';
  phase?: string;
  message?: string;
  progress?: number;
  data?: unknown;
}
