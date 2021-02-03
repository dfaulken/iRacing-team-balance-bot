from datetime import datetime as dt
import discord
import re
from textwrap import dedent

MESSAGE_TEXT_RE = re.compile(r'<@!*\d+> (.*)')
TEAM_SEPARATOR = ';'
DRIVER_SEPARATOR = ','

class DiscordChannel:
  
  def __init__(self, client):
    self.bot = None
    self.channel = None
    self.client = client
    self.message = None
  
  async def indicate_progress(self):
    await self.channel.trigger_typing() 
  
  def is_monitoring_possible(self):
    channel_id = self.bot.get_monitoring_data().get('channel_id')
    return channel_id is not None
  
  async def list_commands(self):
    commands_list_part_1 = dedent('''
      List of commands:
      
      **status** - shows the current status of your server's data, and what actions I am able to perform with this data.
      
      **drivers** - show list of added drivers for this server
      **add driver** Driver Name *Driver ID* - add this driver to the driver list for this server.
          You can comma-separate multiple drivers.
          You can write just the driver name, and I will look up the driver ID for you.
          I will periodically check each driver's iRating and cache it if it's changed.
      **remove driver** Driver Name - remove this driver from the driver list for this server.
      **clear drivers** - clear the driver list for this server.
          I won't monitor anything or alert you at all if you have no drivers, so this is a good way to let me know between events that I don't need to do anything.
      
      **recheck rating** Driver Name - manually trigger a recheck of the named driver's road iRating.
      **recheck rating all** - manually trigger a recheck of all drivers' road iRatings.
    
      **team sizes** - shows the allowed team sizes for the current event. I will only allow for teams of these sizes when calculating balance.
          Once team sizes are set (and drivers are added), I will report on the optimal balance as it changes.
      **set team sizes** *m*, *n*, ... - set the allowed team sizes for the current event. I will only allow for teams of these sizes when calculating balance.
      
      **combine drivers** Driver Name, Driver Name, .... - force balance calculations to only consider sets of teams where the named drivers are on a team together.
        Note that using this feature may significantly hurt your server's ability to balance its drivers.
      **combinations** - show current combinations of drivers.
      **remove combination** Driver Name, Driver Name, ... - remove the combination of drivers listed.
      **clear combinations** - clear all combinations.
    ''').strip()
    await self.print(commands_list_part_1)
    commands_list_part_2 = dedent('''
      **balance** - show most recently calculated optimal balance of team members into teams.
      **recalculate balance** - manually trigger a recheck of the optimal balance based on most recently cached road iRatings.
      
      **teams** - show fixed teams for the upcoming event.
          I will monitor the balance of these teams to make sure it does not fall outside of the configured threshold. 
      **set teams** Driver Name, Driver Name, ...; ... - set fixed teams for the upcoming event. Team members are comma-separated and teams are semicolon-separated.
      **set teams according to balance** sets teams to the most recently calculated optimal balance.
      **clear teams** - clear the fixed teams for the upcoming event.
      
      **balance threshold** - show the balance threshold.
          If the gap between fixed teams' average iRating falls outside of this threshold, I will alert you.
          Before fixed teams are set, I will also note if the current optimal balance falls outside of this threshold - but I wouldn't worry about it too much yet.
      **set balance threshold** *n* - set the balance threshold.
      
      **set notification channel** - set this channel as the channel I should use to send notifications.
      **notification channel** - check which channel has been configured for notifications
      
      Remember to tag me at the beginning of a command message with {0.mention} !
    ''').strip().format(self.client.user)
    await self.print(commands_list_part_2)
  
  def parse_driver_identifier(self, text):
    identifier = text.strip()
    last_id_part = identifier.split(' ')[-1]
    if last_id_part.isnumeric():
      return int(last_id_part)
    return identifier
  
  def parse_driver_identifiers(self, command_text, command_prefix, collection=False):
    drivers_text = self.parse_target(command_text, command_prefix)
    if collection:
      return [[self.parse_driver_identifier(driver) for driver in team_text.split(DRIVER_SEPARATOR)] for team_text in drivers_text.split(TEAM_SEPARATOR)]
    else:
      return [self.parse_driver_identifier(driver) for driver in drivers_text.replace(TEAM_SEPARATOR, DRIVER_SEPARATOR).split(DRIVER_SEPARATOR)]
  
  def parse_integer_list(self, list_text):
    return [int(int_text.strip()) for int_text in list_text.split(DRIVER_SEPARATOR) if int_text.strip().isnumeric()]
  
  def parse_target(self, command_text, command_prefix):
    return command_text.split(command_prefix)[1].strip()
  
  async def perform_background_recheck(self, guild_id):
    self.bot.initialize_guild(guild_id)
    channel_id = self.bot.get_monitoring_data().get('channel_id')
    if not channel_id:
      return
    self.channel = self.client.get_channel(channel_id)
    if not self.channel:
      return
    self.bot.set_guild_name(self.channel.guild.name)
    await self.bot.background_recheck()
  
  async def print(self, message):
    if self.channel:
      await self.channel.send(message)
  
  async def process_request(self, message):
    self.message = message
    self.channel = message.channel
    self.bot.initialize_guild(message.channel.guild.id)
    self.bot.set_guild_name(message.channel.guild.name)
    cmd = self.strip_mention().strip()
    if cmd.startswith('list commands'):
      await self.list_commands()
    elif cmd.startswith('status'):
      await self.bot.show_status()
    elif cmd.startswith('drivers'):
      await self.bot.list_drivers()
    elif cmd.startswith('add driver'):
      await self.bot.add_drivers(self.parse_driver_identifiers(cmd, 'add driver'))
    elif cmd.startswith('remove driver'):
      await self.bot.remove_drivers(self.parse_driver_identifiers(cmd, 'remove driver'))
    elif cmd.startswith('clear drivers'):
      await self.bot.clear_drivers()
    elif cmd.startswith('recheck rating'):
      target = self.parse_target(cmd, 'recheck rating')
      if target == 'all':
        await self.bot.recheck_all_ratings()
      else:
        await self.bot.recheck_ratings(self.parse_driver_identifiers(cmd, 'recheck rating'))
    elif cmd.startswith('team sizes'):
      await self.bot.list_team_sizes()
    elif cmd.startswith('set team sizes'):
      team_sizes = self.parse_integer_list(self.parse_target(cmd, 'set team sizes'))
      await self.bot.set_team_sizes(team_sizes)
    elif cmd.startswith('combinations'):
      await self.bot.list_combinations()
    elif cmd.startswith('combine drivers'):
      await self.bot.add_combinations(self.parse_driver_identifiers(cmd, 'combine drivers', collection=True))
    elif cmd.startswith('remove combination'):
      await self.bot.remove_combinations(self.parse_driver_identifiers(cmd, 'remove combination', collection=True))
    elif cmd.startswith('clear combinations'):
      await self.bot.clear_combinations()
    elif cmd.startswith('balance threshold'):
      await self.bot.show_balance_threshold()
    elif cmd.startswith('set balance threshold'):
      await self.bot.set_balance_threshold(int(self.parse_target(cmd, 'set balance threshold')))
    elif cmd.startswith('balance'):
      await self.bot.list_balance()
    elif cmd.startswith('recalculate balance'):
      await self.bot.recalculate_balance()
    elif cmd.startswith('teams'):
      await self.bot.list_teams()
    elif cmd.startswith('set teams'):
      if self.parse_target(cmd, 'set teams') == 'according to balance':
        await self.bot.set_teams_according_to_balance()
      else:
        await self.bot.set_teams(self.parse_driver_identifiers(cmd, 'set teams', collection=True))
    elif cmd.startswith('clear teams'):
      await self.bot.clear_teams()
    elif cmd.startswith('notification channel'):
      channel_id = self.bot.get_monitoring_data().get('channel_id')
      if channel_id:  
        found_channel = discord.utils.find(lambda c: c.id == channel_id and c.type == discord.ChannelType.text, self.channel.guild.channels)
        if found_channel:
          await self.print('I am currently sending notifications to {0}.'.format(found_channel.mention))
        else:
          await self.print("Oops, the channel I am currently sending notifications to doesn't seem to exist anymore. If desired, please set a new channel.")
      else:
        await self.print('No channel is currently configured for notifications.')
    elif cmd.startswith('set notification channel'):
      monitoring_data = {'channel_id': self.channel.id}
      self.bot.set_monitoring_data(monitoring_data)
      await self.print('Set {0} as the notification channel.'.format(self.channel.mention))
    elif cmd.startswith('test background recheck'):
      await self.bot.background_recheck()
    else:
      await self.bot.alert_unrecognized_command()
  
  def set_bot(self, bot):
    self.bot = bot
  
  def strip_mention(self):
    re_match = MESSAGE_TEXT_RE.match(self.message.content)
    return re_match.group(1)