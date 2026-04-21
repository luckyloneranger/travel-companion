const BASE = import.meta.env.VITE_API_BASE_URL || "";

function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem("auth_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handle401(res: Response) {
  if (res.status === 401) {
    localStorage.removeItem("auth_token");
    window.dispatchEvent(new Event("auth-logout"));
  }
}

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...getAuthHeaders(), ...options?.headers },
    credentials: "include",
  });
  await handle401(res);
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json();
}

// Cities
export async function listCities(params?: { region?: string; sort?: string; limit?: number; offset?: number }) {
  const qs = new URLSearchParams();
  if (params?.region) qs.set("region", params.region);
  if (params?.sort) qs.set("sort", params.sort);
  if (params?.limit) qs.set("limit", String(params.limit));
  if (params?.offset) qs.set("offset", String(params.offset));
  return fetchJSON<{ cities: CityResponse[]; total: number }>(`/api/cities?${qs}`);
}

export async function getCity(cityId: string) {
  return fetchJSON<CityDetailResponse>(`/api/cities/${cityId}`);
}

export async function getCityVariants(cityId: string, params?: { pace?: string; budget?: string }) {
  const qs = new URLSearchParams();
  if (params?.pace) qs.set("pace", params.pace);
  if (params?.budget) qs.set("budget", params.budget);
  return fetchJSON<{ variants: VariantSummary[] }>(`/api/cities/${cityId}/variants?${qs}`);
}

export async function getVariantDetail(cityId: string, variantId: string) {
  return fetchJSON<VariantDetailResponse>(`/api/cities/${cityId}/variants/${variantId}`);
}

// Journeys
export async function createJourney(request: JourneyCreateRequest) {
  return fetchJSON<{ id: string; status: string; job_id?: string }>("/api/journeys", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function listJourneys(limit = 50, offset = 0) {
  return fetchJSON<{ journeys: JourneySummary[]; total: number }>(`/api/journeys?limit=${limit}&offset=${offset}`);
}

export async function getJourney(id: string) {
  return fetchJSON<JourneyResponse>(`/api/journeys/${id}`);
}

export async function deleteJourney(id: string) {
  return fetchJSON<{ deleted: boolean }>(`/api/journeys/${id}`, { method: "DELETE" });
}

// Jobs
export async function pollJob(jobId: string) {
  return fetchJSON<{ id: string; status: string; progress_pct: number; result?: Record<string, unknown>; error?: string }>(`/api/jobs/${jobId}`);
}

// Sharing
export async function shareJourney(journeyId: string) {
  return fetchJSON<{ token: string; url: string }>(`/api/journeys/${journeyId}/share`, { method: "POST" });
}

export async function revokeShare(journeyId: string) {
  return fetchJSON<{ revoked: boolean }>(`/api/journeys/${journeyId}/share`, { method: "DELETE" });
}

export async function getSharedJourney(token: string) {
  return fetchJSON<JourneyResponse>(`/api/shared/${token}`);
}

// Auth (keep existing)
export async function getMe() {
  return fetchJSON<{ user: User | null }>("/api/auth/me");
}

export async function logout() {
  return fetchJSON<void>("/api/auth/logout", { method: "POST" });
}

// Utils
export function photoUrl(ref: string, width = 400): string {
  return `${BASE}/api/places/photo/${ref}?w=${width}`;
}

// Types
export interface CityResponse {
  id: string;
  name: string;
  country: string;
  country_code: string;
  location: { lat: number; lng: number };
  timezone: string;
  currency: string;
  population_tier: string;
  region: string | null;
  created_at: string;
}

export interface CityDetailResponse extends CityResponse {
  landmarks: PlaceInfo[];
  available_variants: { id: string; pace: string; budget: string; day_count: number; quality_score: number | null; status: string }[];
}

export interface PlaceInfo {
  id: string;
  name: string;
  google_place_id: string;
  address: string | null;
  location: { lat: number; lng: number };
  types: string[];
  rating: number | null;
  user_rating_count: number | null;
  photo_references: string[];
  editorial_summary: string | null;
}

export interface VariantSummary {
  id: string;
  pace: string;
  budget: string;
  day_count: number;
  quality_score: number | null;
  cost_total: number | null;
  status: string;
}

export interface ActivityResponse {
  id: string;
  place_id: string;
  place_name: string;
  place_address: string | null;
  place_location: { lat: number; lng: number };
  place_rating: number | null;
  place_photo_url: string | null;
  place_types: string[];
  place_opening_hours: Record<string, unknown>[] | null;
  sequence: number;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  category: string;
  description: string | null;
  is_meal: boolean;
  meal_type: string | null;
  estimated_cost_usd: number | null;
}

export interface RouteResponse {
  from_activity_sequence: number;
  to_activity_sequence: number;
  travel_mode: string;
  distance_meters: number;
  duration_seconds: number;
  polyline: string | null;
}

export interface DayPlanResponse {
  day_number: number;
  theme: string;
  theme_description: string | null;
  activities: ActivityResponse[];
  routes: RouteResponse[];
}

export interface VariantDetailResponse {
  id: string;
  city_id: string;
  city_name?: string;
  pace: string;
  budget: string;
  day_count: number;
  quality_score: number | null;
  status: string;
  accommodation: Record<string, unknown> | null;
  accommodation_alternatives: Record<string, unknown>[];
  booking_hint: string | null;
  cost_breakdown: Record<string, unknown> | null;
  day_plans: DayPlanResponse[];
}

export interface JourneyCreateRequest {
  destination: string;
  origin?: string;
  start_date: string;
  total_days: number;
  pace: string;
  budget: string;
  travelers?: { adults: number; children?: number; infants?: number };
}

export interface JourneySummary {
  id: string;
  destination: string;
  start_date: string;
  total_days: number;
  city_count: number;
  status: string;
  created_at: string;
}

export interface JourneyResponse {
  id: string;
  destination: string;
  origin: string | null;
  start_date: string;
  total_days: number;
  pace: string;
  budget: string;
  travelers: Record<string, unknown>;
  status: string;
  city_sequence: Record<string, unknown>[];
  transport_legs: Record<string, unknown>[] | null;
  weather_forecasts: Record<string, unknown>[] | null;
  cost_breakdown: Record<string, unknown> | null;
  created_at: string;
}

export interface User {
  id: string;
  name: string;
  email: string;
  avatar_url: string | null;
}
