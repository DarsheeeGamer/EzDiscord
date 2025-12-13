# ez_discord/errors.py

"""
Custom exception classes for EzDiscord to handle specific API errors.
"""

class DiscordAPIError(Exception):
    """Base exception class for all errors raised by this library."""
    pass

class HTTPError(DiscordAPIError):
    """An exception that occurs for HTTP-related errors."""
    pass

class ClientError(HTTPError):
    """An exception for 4xx client errors."""
    pass

class BadRequestError(ClientError):
    """Exception for 400 Bad Request errors."""
    pass

class UnauthorizedError(ClientError):
    """Exception for 401 Unauthorized errors."""
    pass

class InvalidTokenError(UnauthorizedError):
    """An exception that occurs when an invalid token is provided."""
    pass

class ForbiddenError(ClientError):
    """Exception for 403 Forbidden errors."""
    pass

class NotFoundError(ClientError):
    """An exception that occurs when a resource is not found (404)."""
    pass

class RateLimitError(ClientError):
    """An exception for when the rate limit is exceeded (429)."""
    pass

class ServerError(HTTPError):
    """An exception for 5xx server errors."""
    pass

class InternalServerError(ServerError):
    """An exception for 500 Internal Server Error."""
    pass

class GatewayError(DiscordAPIError):
    """An exception related to the Discord Gateway."""
    pass
