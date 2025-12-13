# ez_discord/client.py

import asyncio
from .http import HTTPClient
from .gateway import GatewayClient

class Client:
    """
    Represents the client connection to Discord.
    """
    def __init__(self, token, intents=513):
        self.http = HTTPClient(token)
        self.gateway = GatewayClient(self.http, token, intents)

    def run(self):
        asyncio.run(self.gateway.connect())

    async def fetch_user(self, user_id):
        """
        Fetches a user's profile from Discord.
        Args:
            user_id (int): The ID of the user to fetch.
        Returns:
            dict: The user object.
        """
        return await self.http.get(f"/users/{user_id}")

    async def close(self):
        """
        Closes the client's session.
        """
        await self.gateway.close()
        await self.http.close()
