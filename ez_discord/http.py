# ez_discord/http.py

import requests
import json
import time
import logging  # For logging errors and debugging

from .errors import (  # Import all custom error classes
    HTTPError,
    NotFoundError,
    RateLimitError,
    InvalidTokenError,
    InternalServerError,
    BadRequestError,
    UnauthorizedError,
    ForbiddenError,
    DiscordAPIError,  # General Discord API Error
    GatewayError,  # Specific Gateway related HTTP errors if needed later
    ServerError,  # More general server error
    ClientError, # General client side error (4xx)
)

BASE_URL = "https://discord.com/api/v10"  # Current Discord API Version

# Configure logging (you might want to customize this further in your main application)
logger = logging.getLogger(__name__) # Logger for this module
logger.setLevel(logging.WARNING) # Or logging.DEBUG for more detailed logs

class HTTPClient:
    """
    Handles making HTTP requests to the Discord API with robust error handling
    and basic rate limit management.
    """

    def __init__(self, token, max_retries=3):
        """
        Initializes the HTTPClient.

        Args:
            token (str): Discord Bot token.
            max_retries (int): Maximum number of retries for rate limited or server errors.
                               Defaults to 3.
        """
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bot {self.token}",
            "User-Agent": "EzDiscord (Python Discord API Wrapper)"
        })
        self.max_retries = max_retries
        self._global_rate_limit_lock = None # Placeholder for future global rate limit handling

    def _request(self, method, endpoint, **kwargs):
        """
        Internal method to make an HTTP request to the Discord API with retry logic
        and comprehensive error handling.

        Args:
            method (str): HTTP method (GET, POST, PUT, PATCH, DELETE).
            endpoint (str): API endpoint path (e.g., "/channels/{channel_id}").
            **kwargs: Optional arguments to pass to the requests.request method
                      (e.g., params, json, data, headers, files).

        Returns:
            dict or str or None: JSON response as a dictionary, raw text response, or None for 204.

        Raises:
            HTTPError: For general HTTP errors.
            NotFoundError: For 404 Not Found errors.
            RateLimitError: For 429 Rate Limit errors (after retries).
            InvalidTokenError: For 401 Unauthorized errors due to invalid token.
            DiscordAPIError: For other Discord API specific errors.
        """
        url = BASE_URL + endpoint
        headers = kwargs.pop('headers', {})
        if 'json' in kwargs:
            kwargs['headers'] = {**headers, 'Content-Type': 'application/json'}

        for retry in range(self.max_retries + 1):  # Retry loop
            try:
                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()  # Raise HTTPError for bad status codes (4xx or 5xx)
                return self._process_response(response) # Process successful response

            except requests.exceptions.HTTPError as e:
                if e.response is not None:
                    status_code = e.response.status_code
                    if status_code == 429: # Rate Limit
                        retry_after = float(e.response.headers.get('Retry-After', 1)) # Default to 1 sec if header missing
                        is_global = e.response.json().get('global', False) # Check if it's a global rate limit (if JSON is parsable)

                        logger.warning(f"Rate Limited on {method} {endpoint}, retrying in {retry_after} seconds (Global: {is_global}, Retry attempt: {retry+1}/{self.max_retries+1})")

                        if retry >= self.max_retries:
                            raise RateLimitError(f"Rate limited after {self.max_retries+1} retries. Retry-After: {retry_after} seconds. Global: {is_global}")

                        time.sleep(retry_after) # Wait before retrying
                        continue # Retry the request

                    elif 400 <= status_code < 500: # Client Errors (4xx)
                        self._handle_client_error(e) # Handle specific 4xx errors
                    elif 500 <= status_code < 600: # Server Errors (5xx)
                        if retry >= self.max_retries:
                            self._handle_server_error(e) # Handle server errors, and raise after max retries
                        else:
                            logger.warning(f"Server Error ({status_code}) on {method} {endpoint}, retrying... (Attempt: {retry+1}/{self.max_retries+1})")
                            time.sleep(1 * (retry + 1)) # Exponential backoff (simple example)
                            continue # Retry
                    else: # Other HTTP Errors (unlikely, but handle)
                        raise HTTPError(f"Unhandled HTTP Error: {status_code} on {method} {endpoint} - {e}")

                else: # No response object in exception (very rare, but possible)
                    raise HTTPError(f"HTTP Error without response object: {e}")

            except requests.exceptions.RequestException as e: # Catch other request exceptions (connection errors, etc.)
                if retry >= self.max_retries:
                    raise HTTPError(f"Request Error after {self.max_retries+1} retries: {e}")
                else:
                    logger.warning(f"Request Exception on {method} {endpoint}, retrying... (Attempt: {retry+1}/{self.max_retries+1}) - {e}")
                    time.sleep(1 * (retry + 1)) # Exponential backoff for request errors too
                    continue # Retry

        # If the loop completes without returning or raising, it means max retries exceeded without success in a non-rate-limit case.
        # This point should ideally not be reached for rate limits due to the RateLimitError being raised inside the 429 block after max retries.
        raise HTTPError(f"Max retries ({self.max_retries+1}) exceeded for {method} {endpoint} without success.") # Fallback error

    def _process_response(self, response):
        """
        Processes a successful HTTP response.

        Args:
            response (requests.Response): The successful response object.

        Returns:
            dict or str or None: JSON response, raw text, or None.
        """
        if response.status_code == 204 or not response.text:
            return None

        try:
            return response.json()
        except json.JSONDecodeError:
            return response.text


    def _handle_client_error(self, error):
        """Handles 4xx Client Errors and raises specific EzDiscord error types."""
        status_code = error.response.status_code
        endpoint = error.request.path_url # Get the endpoint from the request in the exception

        if status_code == 400:
            raise BadRequestError(f"Bad Request: {endpoint} - {error.response.text}")
        elif status_code == 401:
            raise UnauthorizedError("Invalid Discord Bot Token")
        elif status_code == 403:
            raise ForbiddenError(f"Forbidden: Missing permissions for {endpoint}")
        elif status_code == 404:
            raise NotFoundError(f"Resource not found at endpoint: {endpoint}")
        # Add more specific 4xx error handling as needed (e.g., 405 Method Not Allowed, 413 Payload Too Large etc.)
        else:
            raise ClientError(f"Client Error ({status_code}) on {endpoint} - {error.response.text}") # General 4xx error

    def _handle_server_error(self, error):
        """Handles 5xx Server Errors and raises ServerError."""
        status_code = error.response.status_code
        endpoint = error.request.path_url # Get the endpoint

        if 500 <= status_code < 600:
            raise ServerError(f"Discord Server Error ({status_code}) on {endpoint} - {error.response.text}") # General 5xx Error
        else: # Should not reach here in normal cases, but for safety
            raise ServerError(f"Server Error (Unexpected Status {status_code}) on {endpoint} - {error.response.text}")


    # --- Public Request Methods ---

    def get(self, endpoint, **kwargs):
        """Makes a GET request."""
        return self._request('GET', endpoint, **kwargs)

    def post(self, endpoint, **kwargs):
        """Makes a POST request."""
        return self._request('POST', endpoint, **kwargs)

    def put(self, endpoint, **kwargs):
        """Makes a PUT request."""
        return self._request('PUT', endpoint, **kwargs)

    def patch(self, endpoint, **kwargs):
        """Makes a PATCH request."""
        return self._request('PATCH', endpoint, **kwargs)

    def delete(self, endpoint, **kwargs):
        """Makes a DELETE request."""
        return self._request('DELETE', endpoint, **kwargs)
