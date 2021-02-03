import asyncio
import unittest
from unittest.mock import AsyncMock
from unittest.mock import Mock

from balancebot.interfaces.discord_channel import DiscordChannel

class TestStatusRequest(unittest.TestCase):
  def test_status_request_delegates_to_bot_show_status(self):
    interface = DiscordChannel(None) # Discord client shouldn't matter for this request
    bot = Mock()
    bot.show_status = AsyncMock()
    interface.set_bot(bot)
    message = Mock()
    message.content = '<@12345> status'
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(interface.process_request(message))
    loop.close()
    
    bot.show_status.assert_awaited_once()