# TO DO
### USING GATEWAY API:
- The client object needs to establish a connection (see [this](https://discord.com/developers/docs/topics/gateway))
- The client then needs to start a heartbeat event and respond to ACKS
- It then sends the client's identity/intents to the discord gateway
- We need extra functions to add basic customization to the bot, and it needs to send opcodes accordingly.
- After the client objct is finished, we need to add extra objects to corrospond to members channels and such 