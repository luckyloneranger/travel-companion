// Types mirroring backend Pydantic models
// Source: backend/app/models/

// ── common.py ──────────────────────────────────────────────

export interface Location {
  lat: number;
  lng: number;
}

export type Pace = 'relaxed' | 'moderate' | 'packed';

export type TravelMode = 'WALK' | 'DRIVE' | 'TRANSIT';

export type TransportMode = 'flight' | 'train' | 'bus' | 'drive' | 'ferry';

export type Budget = 'budget' | 'moderate' | 'luxury';

// ── journey.py ─────────────────────────────────────────────

export interface Accommodation {
  name: string;
  address: string;
  location: Location | null;
  place_id: string | null;
  rating: number | null;
  photo_url: string | null;
  price_level: number | null;
}

export interface CityHighlight {
  name: string;
  description: string;
  category: string;
  suggested_duration_hours: number | null;
}

export interface CityStop {
  name: string;
  country: string;
  days: number;
  highlights: CityHighlight[];
  why_visit: string;
  best_time_to_visit: string;
  location: Location | null;
  place_id: string | null;
  accommodation: Accommodation | null;
}

export interface TravelLeg {
  from_city: string;
  to_city: string;
  mode: TransportMode;
  duration_hours: number;
  distance_km: number | null;
  notes: string;
  fare: string | null;
  operator: string | null;
  booking_tip: string | null;
  polyline: string | null;
  num_transfers: number;
  departure_time: string | null;
  arrival_time: string | null;
}

export interface ReviewIssue {
  severity: string;
  category: string;
  description: string;
  affected_leg: number | null;
  affected_city: number | null;
  suggested_fix: string;
}

export interface ReviewResult {
  is_acceptable: boolean;
  score: number;
  issues: ReviewIssue[];
  summary: string;
  iteration: number;
}

export interface JourneyPlan {
  theme: string;
  summary: string;
  origin: string;
  cities: CityStop[];
  travel_legs: TravelLeg[];
  total_days: number;
  total_distance_km: number | null;
  total_travel_hours: number | null;
  review_score: number | null;
  route: string | null;
}

// ── day_plan.py ────────────────────────────────────────────

export interface Place {
  place_id: string;
  name: string;
  address: string;
  location: Location;
  category: string;
  rating: number | null;
  photo_url: string | null;
  photo_urls: string[];
  opening_hours: string[];
  website: string | null;
}

export interface Route {
  distance_meters: number;
  duration_seconds: number;
  duration_text: string;
  travel_mode: TravelMode;
  polyline: string | null;
}

export interface Activity {
  id: string;
  time_start: string;
  time_end: string;
  duration_minutes: number;
  place: Place;
  notes: string;
  route_to_next: Route | null;
  weather_warning: string | null;
}

export interface Weather {
  temperature_high_c: number;
  temperature_low_c: number;
  condition: string;
  precipitation_chance_percent: number;
  wind_speed_kmh: number;
  humidity_percent: number;
  uv_index: number | null;
}

export interface DayPlan {
  date: string;
  day_number: number;
  theme: string;
  activities: Activity[];
  city_name: string;
  weather: Weather | null;
}

// ── trip.py ────────────────────────────────────────────────

export interface TripRequest {
  destination: string;
  origin: string;
  total_days: number;
  start_date: string; // ISO date string (YYYY-MM-DD)
  interests: string[];
  pace: Pace;
  travel_mode?: TravelMode;
  must_include: string[];
  avoid: string[];
}

export interface TripSummary {
  id: string;
  theme: string;
  destination: string;
  total_days: number;
  cities_count: number;
  created_at: string; // ISO datetime string
  has_day_plans: boolean;
}

export interface TripResponse {
  id: string;
  request: TripRequest;
  journey: JourneyPlan;
  day_plans: DayPlan[] | null;
  quality_score: number | null;
  created_at: string; // ISO datetime string
  updated_at: string; // ISO datetime string
}

// ── chat.py ────────────────────────────────────────────────

export interface ChatEditRequest {
  message: string;
  context: string;
}

export interface ChatEditResponse {
  reply: string;
  updated_journey: JourneyPlan | null;
  updated_day_plans: DayPlan[] | null;
  changes_made: string[];
}

// ── progress.py ────────────────────────────────────────────

export interface ProgressEvent {
  phase: string;
  message: string;
  progress: number;
  data?: Record<string, unknown>;
}

// ── quality.py ─────────────────────────────────────────────

export interface MetricResult {
  name: string;
  score: number;
  grade: string;
  issues: string[];
  details: string;
}

export interface QualityReport {
  overall_score: number;
  overall_grade: string;
  metrics: MetricResult[];
  critical_issues: string[];
  recommendations: string[];
}
