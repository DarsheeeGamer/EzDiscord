# ez_discord/http.py

import aiohttp
import asyncio
import json
import logging

from .errors import (
    HTTPError,
    NotFoundError,
    RateLimitError,
    InvalidTokenError,
    InternalServerError,
    BadRequestError,
    UnauthorizedError,
    ForbiddenError,
    DiscordAPIError,
    GatewayError,
    ServerError,
    ClientError,
)

BASE_URL = "https://discord.com/api/v10"

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class HTTPClient:
    """
    Handles making asynchronous HTTP requests to the Discord API with robust error handling
    and basic rate limit management.
    """

    def __init__(self, token, max_retries=3):
        self.token = token
        headers = {
            "Authorization": f"Bot {self.token}",
            "User-Agent": "EzDiscord (Python Discord API Wrapper)"
        }
        self.session = aiohttp.ClientSession(headers=headers)
        self.max_retries = max_retries
        self._global_rate_limit_lock = asyncio.Event()
        self._global_rate_limit_lock.set()

    async def _request(self, method, endpoint, **kwargs):
        url = BASE_URL + endpoint
        if 'json' in kwargs:
            kwargs.setdefault('headers', {}).update({'Content-Type': 'application/json'})

        await self._global_rate_limit_lock.wait()

        for retry in range(self.max_retries + 1):
            try:
                async with self.session.request(method, url, **kwargs) as response:
                    if response.status == 429:
                        retry_after = float(response.headers.get('Retry-After', 1))
                        try:
                            data = await response.json()
                            is_global = data.get('global', False)
                        except (json.JSONDecodeError, aiohttp.ContentTypeError):
                            is_global = False

                        logger.warning(f"Rate Limited on {method} {endpoint}, retrying in {retry_after}s (Global: {is_global})")

                        if is_global:
                            self._global_rate_limit_lock.clear()
                            await asyncio.sleep(retry_after)
                            self._global_rate_limit_lock.set()
                        else:
                            await asyncio.sleep(retry_after)

                        if retry >= self.max_retries:
                            raise RateLimitError("Rate limited after max retries.")
                        continue

                    response.raise_for_status()
                    return await self._process_response(response)

            except aiohttp.ClientResponseError as e:
                if 400 <= e.status < 500:
                    self._handle_client_error(e, endpoint)
                elif 500 <= e.status < 600:
                    if retry >= self.max_retries:
                        self._handle_server_error(e)
                    else:
                        await asyncio.sleep(1 * (retry + 1))
                        continue
                else:
                    raise HTTPError(f"Unhandled HTTP Error: {e.status}")

            except aiohttp.ClientError as e:
                if retry >= self.max_retries:
                    raise HTTPError(f"Request Error after max retries: {e}")
                else:
                    await asyncio.sleep(1 * (retry + 1))
                    continue

        raise HTTPError(f"Max retries exceeded for {method} {endpoint}.")

    async def _process_response(self, response):
        if response.status == 204 or response.content_length == 0:
            return None
        try:
            return await response.json()
        except json.JSONDecodeError:
            return await response.text()

    def _handle_client_error(self, error, endpoint):
        if error.status == 400:
            raise BadRequestError(f"Bad Request: {error.message}")
        elif error.status == 401:
            raise UnauthorizedError("Invalid Discord Bot Token")
        elif error.status == 403:
            raise ForbiddenError(f"Forbidden: {error.message}")
        elif error.status == 404:
            raise NotFoundError(f"Resource not found at endpoint: {endpoint}")
        else:
            raise ClientError(f"Client Error ({error.status}): {error.message}")

    def _handle_server_error(self, error):
        raise ServerError(f"Discord Server Error ({error.status}): {error.message}")

    async def get(self, endpoint, **kwargs):
        return await self._request('GET', endpoint, **kwargs)

    async def post(self, endpoint, **kwargs):
        return await self._request('POST', endpoint, **kwargs)

    async def put(self, endpoint, **kwargs):
        return await self._request('PUT', endpoint, **kwargs)

    async def patch(self, endpoint, **kwargs):
        return await self._request('PATCH', endpoint, **kwargs)

    async def delete(self, endpoint, **kwargs):
        return await self._request('DELETE', endpoint, **kwargs)

    async def close(self):
        await self.session.close()
