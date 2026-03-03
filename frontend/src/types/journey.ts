/**
 * TypeScript interfaces for V6 Journey Planning API
 */

import { Pace } from './itinerary';

// ═══════════════════════════════════════════════════════════════
// REQUEST TYPES
// ═══════════════════════════════════════════════════════════════

export type TransportMode = 'flight' | 'train' | 'bus' | 'car' | 'ferry';

/**
 * Request to generate a journey plan.
 * Supports flexible input - destinations, region, or both.
 */
export interface JourneyRequest {
  /** Starting location (e.g., "New York, USA") */
  origin: string;
  
  /** Specific destinations to include (can be empty for LLM suggestions) */
  destinations: string[];
  
  /** Region to explore if destinations not fully specified */
  region?: string;
  
  /** Trip start date (ISO format) */
  start_date: string;
  
  /** Total trip duration (alternative: use end_date) */
  total_days?: number;
  
  /** Trip end date (alternative: use total_days) */
  end_date?: string;
  
  /** User interests for activity selection */
  interests: string[];
  
  /** Daily activity pace */
  pace: Pace;
  
  /** Whether to return to starting city */
  return_to_origin: boolean;
  
  /** Destinations that must be included */
  must_include?: string[];
  
  /** Places or types to avoid */
  avoid?: string[];
  
  /** Preferred modes of transport between cities (optional - AI suggests best for region) */
  transport_preferences?: TransportMode[];
}

// ═══════════════════════════════════════════════════════════════
// V6 JOURNEY TYPES (SCOUT → ENRICH → REVIEW → PLANNER LOOP)
// ═══════════════════════════════════════════════════════════════

/** V6 City Highlight - attraction within a city */
export interface V6CityHighlight {
  name: string;
  description: string;
  category: string;  // food, culture, nature, history, etc.
  suggested_duration_hours?: number;
}

/** V6 Accommodation - hotel for a city stop */
export interface V6Accommodation {
  name: string;
  address?: string;
  latitude?: number;
  longitude?: number;
  place_id?: string;
  rating?: number;
  photo_url?: string;
  price_level?: number;
}

/** V6 City Stop - a destination in the journey */
export interface V6CityStop {
  name: string;
  country: string;
  days: number;
  why_visit: string;
  best_time_to_visit?: string;
  highlights: V6CityHighlight[];
  latitude?: number;
  longitude?: number;
  accommodation?: V6Accommodation;
}

/** V6 Travel Leg - transport between cities */
export interface V6TravelLeg {
  from_city: string;
  to_city: string;
  mode: TransportMode;
  duration_hours: number;
  distance_km?: number;
  notes?: string;
  estimated_cost?: string;
  booking_tip?: string;
  fare?: string;
  num_transfers?: number;
  departure_time?: string;
  arrival_time?: string;
}

/** V6 Journey Plan - complete plan from Scout/Planner */
export interface V6JourneyPlan {
  theme: string;
  summary: string;
  route: string;  // "City1 → City2 → City3"
  origin: string;
  region: string;
  total_days: number;
  cities: V6CityStop[];
  travel_legs: V6TravelLeg[];
  review_score?: number;
  total_travel_hours?: number;
  total_distance_km?: number;
}

/** V6 streaming progress event types */
export type V6EventPhase = 
  | 'scout'
  | 'enrich'
  | 'review'
  | 'planner'
  | 'complete'
  | 'error';

/** V6 streaming progress event */
export interface V6ProgressEvent {
  phase: V6EventPhase;
  step: string;  // 'start', 'complete', 'failed'
  message: string;
  progress: number;  // 0-100
  iteration: number;
  data?: {
    // Scout complete
    route?: string;
    city_names?: string[];  // Scout returns city names as strings
    theme?: string;
    
    // Enrich complete
    total_travel_hours?: number;
    total_distance_km?: number;
    
    // Review complete
    score?: number;
    is_acceptable?: boolean;
    summary?: string;
    critical_issues?: number;
    warnings?: number;
    
    // Planner complete
    revised_route?: string;
    
    // Complete - full journey data
    origin?: string;
    region?: string;
    total_days?: number;
    cities?: V6CityStop[];  // Final plan has full city objects
    travel_legs?: V6TravelLeg[];
    review_score?: number;
    
    // Error
    error?: string;
    
    [key: string]: unknown;
  };
}

// ═══════════════════════════════════════════════════════════════
// V6 DAY PLANS - Detailed itineraries for each city
// ═══════════════════════════════════════════════════════════════

/** Request to generate day plans for a V6 journey */
export interface V6DayPlansRequest {
  journey: V6JourneyPlan;
  start_date: string;  // ISO date string
  interests: string[];
  pace: 'relaxed' | 'moderate' | 'packed';
  travel_mode: 'WALK' | 'DRIVE' | 'TRANSIT';
}

/** Route information between two activities */
export interface V6Route {
  distance_meters: number;
  duration_seconds: number;
  duration_text: string;
  travel_mode: 'WALK' | 'DRIVE' | 'TRANSIT';
  polyline?: string;
}

/** Activity in a day plan */
export interface V6Activity {
  time_start: string;
  time_end: string;
  place: {
    name: string;
    category: string;
    address: string;
    location: { lat: number; lng: number };
    rating?: number;
    website?: string;
    photo_url?: string;
  };
  duration_minutes: number;
  notes?: string;
  route_to_next?: V6Route;
}

/** Single day's itinerary */
export interface V6DayPlan {
  date: string;
  day_number: number;
  theme: string;
  activities: V6Activity[];
  total_walking_minutes?: number;
}

/** Day plans for a single city */
export interface V6CityDayPlans {
  city: string;
  days: number;
  day_plans_count: number;
  error?: string;
}

/** Day plan generation progress event types */
export type V6DayPlanEventPhase = 
  | 'city_start'
  | 'city_complete'
  | 'city_error'
  | 'complete'
  | 'error';

/** Day plan generation progress event */
export interface V6DayPlanProgress {
  phase: V6DayPlanEventPhase;
  city_name: string | null;
  city_index: number;
  total_cities: number;
  city_days: number;  // Number of days for current city
  message: string;
  progress: number;  // 0-100 overall
  city_progress: number;  // 0-100 for current city
  data?: {
    // city_start
    country?: string;
    start_date?: string;
    
    // city_complete
    days_generated?: number;
    day_plans?: Array<{
      date: string;
      day_number: number;
      theme: string;
      activity_count: number;
    }>;
    
    // complete - full results
    journey_theme?: string;
    total_days?: number;
    total_cities?: number;
    city_summaries?: V6CityDayPlans[];
    all_day_plans?: V6DayPlan[];
    
    // error
    error?: string;
    
    [key: string]: unknown;
  };
}

// ═══════════════════════════════════════════════════════════════
// UI CONSTANTS
// ═══════════════════════════════════════════════════════════════

export const TRANSPORT_OPTIONS = [
  { value: 'flight' as TransportMode, label: 'Flights', icon: '✈️', description: 'Travel by air' },
  { value: 'train' as TransportMode, label: 'Trains', icon: '🚄', description: 'Rail travel' },
  { value: 'bus' as TransportMode, label: 'Bus', icon: '🚌', description: 'Coach/bus travel' },
  { value: 'car' as TransportMode, label: 'Drive', icon: '🚗', description: 'Rent a car' },
  { value: 'ferry' as TransportMode, label: 'Ferry', icon: '⛴️', description: 'Boat/ferry travel' },
] as const;

/** Example regions for inspiration (users can type any region) */
export const SUGGESTED_REGIONS = [
  { label: 'Northern Italy', value: 'Northern Italy', example: 'Milan → Venice → Florence' },
  { label: 'Japanese Alps', value: 'Japanese Alps', example: 'Tokyo → Takayama → Kanazawa' },
  { label: 'Swiss Alps', value: 'Swiss Alps', example: 'Zurich → Lucerne → Interlaken' },
  { label: 'Andalusia', value: 'Andalusia, Spain', example: 'Madrid → Seville → Granada' },
  { label: 'Scottish Highlands', value: 'Scottish Highlands', example: 'Edinburgh → Inverness → Isle of Skye' },
  { label: 'Greek Islands', value: 'Greek Islands', example: 'Athens → Santorini → Mykonos' },
  { label: 'Vietnam Coast', value: 'Central Vietnam Coast', example: 'Hanoi → Hue → Hoi An' },
  { label: 'New Zealand South', value: 'South Island New Zealand', example: 'Christchurch → Queenstown → Milford Sound' },
  { label: 'Portugal Coast', value: 'Portuguese Atlantic Coast', example: 'Lisbon → Sintra → Porto' },
  { label: 'Balkans', value: 'Western Balkans', example: 'Dubrovnik → Mostar → Sarajevo' },
] as const;

export const DAYS_OPTIONS = [
  { value: 5, label: '5 days', description: 'Long weekend trip' },
  { value: 7, label: '1 week', description: 'Standard vacation' },
  { value: 10, label: '10 days', description: 'Extended trip' },
  { value: 14, label: '2 weeks', description: 'In-depth exploration' },
  { value: 21, label: '3 weeks', description: 'Epic adventure' },
] as const;

// ═══════════════════════════════════════════════════════════════
// CHAT EDIT TYPES
// ═══════════════════════════════════════════════════════════════

/** Request to edit a journey via chat */
export interface ChatEditRequest {
  /** User's edit request message */
  message: string;
  /** Current journey plan to edit */
  journey: V6JourneyPlan;
  /** Original trip context */
  context?: {
    origin?: string;
    region?: string;
    interests?: string[];
    pace?: string;
  };
}

/** Response from journey chat edit */
export interface ChatEditResponse {
  /** Whether the edit was successfully applied */
  success: boolean;
  /** Assistant's response message */
  message: string;
  /** What the AI understood from the request */
  understood_request: string;
  /** List of changes applied */
  changes_made: string[];
  /** Updated journey plan (if successful) */
  updated_journey: V6JourneyPlan | null;
  /** Error message (if failed) */
  error: string | null;
}

/** Chat message for UI display */
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  changes?: string[];
  isLoading?: boolean;
}

/** Request to edit day plans via chat */
export interface DayPlanChatEditRequest {
  /** User's edit request message */
  message: string;
  /** Current day plans to edit */
  day_plans: V6DayPlan[];
  /** Trip context */
  context?: {
    interests?: string[];
    pace?: string;
  };
}

/** Response from day plan chat edit */
export interface DayPlanChatEditResponse {
  /** Whether the edit was successfully applied */
  success: boolean;
  /** Assistant's response message */
  message: string;
  /** What the AI understood from the request */
  understood_request: string;
  /** List of changes applied */
  changes_made: string[];
  /** Updated day plans (if successful) */
  updated_day_plans: V6DayPlan[] | null;
  /** Error message (if failed) */
  error: string | null;
}
