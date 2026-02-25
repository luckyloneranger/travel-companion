/**
 * TypeScript interfaces for the Travel Companion API
 * Core types shared across the application.
 */

export type Pace = 'relaxed' | 'moderate' | 'packed';
export type TravelMode = 'WALK' | 'DRIVE' | 'TRANSIT';
export type GenerationMode = 'fast' | 'pristine';

// ═══════════════════════════════════════════════════════════════
// UI CONSTANTS
// ═══════════════════════════════════════════════════════════════

// Available interest options
export const INTERESTS = [
  { id: 'art', label: 'Art & Museums', icon: '🎨' },
  { id: 'history', label: 'History', icon: '🏛️' },
  { id: 'food', label: 'Food & Dining', icon: '🍽️' },
  { id: 'nature', label: 'Nature', icon: '🌿' },
  { id: 'shopping', label: 'Shopping', icon: '🛍️' },
  { id: 'nightlife', label: 'Nightlife', icon: '🌙' },
  { id: 'architecture', label: 'Architecture', icon: '🏰' },
  { id: 'culture', label: 'Culture', icon: '🎭' },
  { id: 'adventure', label: 'Adventure', icon: '🎢' },
  { id: 'relaxation', label: 'Relaxation', icon: '🧘' },
] as const;

// ═══════════════════════════════════════════════════════════════
// SINGLE-CITY ITINERARY TYPES
// ═══════════════════════════════════════════════════════════════

/** Geographic coordinates */
export interface Location {
  lat: number;
  lng: number;
}

/** Trip destination information */
export interface Destination {
  name: string;
  place_id: string;
  location: Location;
  country: string;
  timezone: string;
}

/** Trip date range */
export interface TripDates {
  start: string;
  end: string;
  duration_days: number;
}

/** Place in the itinerary */
export interface Place {
  place_id: string;
  name: string;
  address: string;
  location: Location;
  category: string;
  rating?: number;
  photo_url?: string;
  opening_hours?: string[];
  website?: string;
  phone?: string;
}

/** Route between two places */
export interface Route {
  distance_meters: number;
  duration_seconds: number;
  duration_text: string;
  travel_mode: TravelMode;
  polyline: string;
}

/** Scheduled activity in the itinerary */
export interface Activity {
  id: string;
  time_start: string;
  time_end: string;
  duration_minutes: number;
  place: Place;
  notes: string;
  route_to_next?: Route;
}

/** Single day's itinerary */
export interface DayPlan {
  date: string;
  day_number: number;
  theme: string;
  activities: Activity[];
}

/** Itinerary summary statistics */
export interface ItinerarySummary {
  total_activities: number;
  total_distance_km: number;
  interests_covered: string[];
  estimated_cost_range?: string;
}

/** Quality score metrics */
export interface QualityScore {
  meal_timing: number;
  geographic_clustering: number;
  travel_efficiency: number;
  variety: number;
  opening_hours: number;
  theme_alignment: number;
  duration_appropriateness: number;
  overall: number;
  grade?: string;
}

/** Single-city itinerary request */
export interface ItineraryRequest {
  destination: string;
  start_date: string;
  end_date: string;
  interests: string[];
  pace?: Pace;
  travel_mode?: TravelMode;
  mode?: GenerationMode;
}

/** Single-city itinerary response */
export interface ItineraryResponse {
  id: string;
  destination: Destination;
  trip_dates: TripDates;
  days: DayPlan[];
  summary: ItinerarySummary;
  generated_at: string;
  generation_mode: GenerationMode;
  quality_score?: QualityScore;
  iterations_used?: number;
}

/** SSE progress event for itinerary generation */
export interface ItineraryProgressEvent {
  type: 'progress' | 'complete' | 'error';
  phase?: string;
  message?: string;
  progress?: number;
  result?: ItineraryResponse;
  error?: string;
}
