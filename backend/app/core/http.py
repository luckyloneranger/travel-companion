import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None
DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 3
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}


async def get_http_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        transport = httpx.AsyncHTTPTransport(retries=2)
        _client = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, transport=transport)
    return _client


async def close_http_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


async def request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs,
) -> httpx.Response:
    """Make an HTTP request with exponential backoff on rate limits and server errors."""
    for attempt in range(MAX_RETRIES):
        response = await client.request(method, url, **kwargs)
        if response.status_code not in RETRY_STATUS_CODES:
            return response

        if attempt < MAX_RETRIES - 1:
            # Use Retry-After header if present, otherwise exponential backoff
            retry_after = response.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                wait = min(int(retry_after), 30)
            else:
                wait = 2 ** attempt  # 1s, 2s, 4s
            logger.warning(
                "[HTTP] %s %s returned %d, retrying in %ds (attempt %d/%d)",
                method, url, response.status_code, wait, attempt + 1, MAX_RETRIES,
            )
            await asyncio.sleep(wait)

    return response  # Return last response even if it was an error
