import discord
import websockets
import json
import typing
from typing import Any,Coroutine
import asyncio


class Client:
  '''
  Client:
  -----------------------------------------------------------------
  An object that represents a connection to the discord Gateway API.
  Requires the bot token, found in the developer portal.'''

            
  def __init__(self) -> None:
    self.session = websockets.connect("wss://gateway.discord.gg/?v=10&encoding=json")
    self.get = self.session.recv()
        
            
  async def connect(self):    
    got = await self.get()
    print(f"Recieved: {got}! Reading and initiating shard heartbeat...")
    self.heartbeat_interval = int(json.loads(got)['heartbeat_interval'])
    self.got = self.session.recv()

'''
WORK IN PROGRESS'''

