import logging
logging.basicConfig(filename='bot.log',
                    level=logging.INFO,
                    format='[%(asctime)s %(levelname)07s]:%(message)s')

import asyncio
import discord
import dotenv
import os
from periodic import Periodic
from pyracing import client as pyracing

from balancebot.balance_bot                import BalanceBot
from balancebot.data_store                 import DataStore
from balancebot.interfaces.discord_channel import DiscordChannel

BACKGROUND_RECHECK_PERIOD_MINUTES = 15
QUARTER_CHECK_PERIOD_MINUTES = 60

dotenv.load_dotenv()
di_client = discord.Client()
ir_client = pyracing.Client(os.getenv('IR_USERNAME'), os.getenv('IR_PASSWORD'))

async def check_quarter_number():
  bot = BalanceBot(ir_client, DataStore)
  await bot.update_quarter_number()

async def perform_background_rechecks():
  for guild_id in DataStore.data_subdirectory_numbers():
    bot = BalanceBot(ir_client, DataStore)
    interface = DiscordChannel(di_client)
    bot.set_interface(interface)
    interface.set_bot(bot)
    await interface.perform_background_recheck(guild_id)

@di_client.event
async def on_ready():
  await Periodic(BACKGROUND_RECHECK_PERIOD_MINUTES * 60, perform_background_rechecks).start()
  await Periodic(QUARTER_CHECK_PERIOD_MINUTES * 60, check_quarter_number).start()

@di_client.event
async def on_message(message):
  if not di_client.user in message.mentions:
    return
  if di_client.user == message.author:
    return
  try:
    bot = BalanceBot(ir_client, DataStore)
    interface = DiscordChannel(di_client)
    bot.set_interface(interface)
    interface.set_bot(bot)
    await interface.process_request(message)
  except:
    await bot.alert_error_received()
    raise

di_client.run(os.getenv('TOKEN'))