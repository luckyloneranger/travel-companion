/** Shared constants used across the frontend. */

/** localStorage key for the JWT auth token. */
export const AUTH_TOKEN_KEY = 'tc_auth_token';

/** SSE stall timeout in milliseconds (3 minutes). */
export const SSE_STALL_TIMEOUT_MS = 180_000;

/** Auth token refresh interval in milliseconds (30 minutes). */
export const AUTH_REFRESH_INTERVAL_MS = 30 * 60 * 1000;
