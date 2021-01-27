import logging
logging.basicConfig(filename='bot.log',
                    level=logging.INFO,
                    format='[%(asctime)s %(levelname)07s]:%(message)s')

import asyncio
import copy
import datetime
import discord
import dotenv
from enum import Enum
import glob
import json
import os
import pathlib
import pdb
from periodic import Periodic
from pyracing import client as pyracing
from pyracing import constants
import re
from textwrap import dedent

BACKGROUND_RECHECK_PERIOD_MINUTES = 15
QUARTER_CHECK_PERIOD_MINUTES = 60

dotenv.load_dotenv()
di_client = discord.Client()
ir_client = pyracing.Client(os.getenv('IR_USERNAME'), os.getenv('IR_PASSWORD'))
message_text_re = re.compile(r'<@!*\d+> (.*)')

class Driver:
  DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

  def __init__(self, id, name, irating, last_updated):
    self.id = id
    self.name = name
    self.irating = irating
    self.last_updated = last_updated
    
  def __repr__(self):
    return "<Driver id:{0} name:{1} irating:{2} last_updated{3}>".format(self.id, self.name, self.irating, self.last_updated)
  
  def decode(json_data):
    drivers = []
    for id in json_data.keys():
      name, irating, last_updated_str = json_data[id]
      last_updated = datetime.datetime.strptime(last_updated_str, Driver.DATETIME_FORMAT)
      drivers.append(Driver(id, name, irating, last_updated))
    return drivers
  
  def encode(drivers):
    json_data = {}
    for driver in drivers:
      last_updated_str = driver.last_updated.strftime(Driver.DATETIME_FORMAT)
      json_data[driver.id] = [driver.name, driver.irating, last_updated_str]
    return json_data

class FilePrefix(Enum):
  drivers = 'drivers'
  team_sizes = 'team_sizes'
  teams = 'teams'
  balance = 'balance'
  balance_threshold = 'balance_threshold'
  channel_id = 'channel_id'
  quarter_number = 'quarter_number'

def guild_ids():
  return [file.name for file in os.scandir('data') if file.is_dir()]

def data_dir_path():
  return 'data'

def guild_dir_path(guild_id):
  return '{0}/{1}'.format(data_dir_path(), guild_id)

def guild_has_data(guild_id):
  return os.path.isdir(guild_dir_path(guild_id))
  
def initialize_guild_data(guild_id):
  pathlib.Path(guild_dir_path(guild_id)).mkdir()

def global_file_path(file_type):
  path = '{0}/{1}.json'.format(data_dir_path(), file_type.value)
  return path

def guild_file_path(guild_id, file_type):
  path = '{0}/{1}.json'.format(guild_dir_path(guild_id), file_type.value)
  return path
  
def global_data_has_file(file_type):
  return os.path.isfile(global_file_path(file_type))

def guild_has_file(guild_id, file_type):
  return os.path.isfile(guild_file_path(guild_id, file_type))
  
def clear_guild_file(guild_id, file_type):
  logging.info('Clearing guild {0} file type {1}'.format(guild_id, file_type))
  if guild_has_file(guild_id, file_type):
    os.remove(guild_file_path(guild_id, file_type))
 
def clear_drivers(guild_id):
  if guild_has_data(guild_id):
    clear_guild_file(guild_id, FilePrefix.drivers)
    clear_guild_file(guild_id, FilePrefix.balance)
    clear_teams(guild_id)

def load_drivers(guild_id):
  logging.info('Loading drivers for guild {0}'.format(guild_id))
  if not guild_has_data(guild_id):
    return []
  if not guild_has_file(guild_id, FilePrefix.drivers):
    return []
  file_path = guild_file_path(guild_id, FilePrefix.drivers)
  with open(file_path, 'r') as driver_file:
    try:
      driver_json_data = json.load(driver_file)
    except json.JSONDecodeError:
      logging.warning('Encountered JSONDecodeError for file {0}'.format(file_path))
      driver_json_data = []
    return Driver.decode(driver_json_data)

def persist_drivers(guild_id, drivers):
  logging.info('Persisting drivers for guild {0}'.format(guild_id))
  if not guild_has_data(guild_id):
    initialize_guild_data(guild_id)
  with open(guild_file_path(guild_id, FilePrefix.drivers), 'w') as driver_file:
    json.dump(Driver.encode(drivers), driver_file)
    
def load_team_sizes(guild_id):
  logging.info('Loading team sizes for guild {0}'.format(guild_id))
  if not guild_has_data(guild_id):
    return []
  if not guild_has_file(guild_id, FilePrefix.team_sizes):
    return []
  file_path = guild_file_path(guild_id, FilePrefix.team_sizes)
  with open(file_path, 'r') as team_sizes_file:
    try:
      return json.load(team_sizes_file)
    except json.JSONDecodeError:
      logging.warning('Encountered JSONDecodeError for file {0}'.format(file_path))
      return []
  
def persist_team_sizes(guild_id, team_sizes):
  logging.info('Persisting team sizes for guild {0}'.format(guild_id))
  if not guild_has_data(guild_id):
    initialize_guild_data(guild_id)
  with open(guild_file_path(guild_id, FilePrefix.team_sizes), 'w') as team_sizes_file:
    json.dump(team_sizes, team_sizes_file)

def load_teams(guild_id):
  logging.info('Loading teams for guild {0}'.format(guild_id))
  if not guild_has_data(guild_id):
    return []
  if not guild_has_file(guild_id, FilePrefix.teams):
    return []
  file_path = guild_file_path(guild_id, FilePrefix.teams)
  with open(file_path, 'r') as teams_file:
    try:
      teams_json_data = json.load(teams_file)
      teams = []
      for team_json_data in teams_json_data:
        teams.append(Driver.decode(team_json_data))
      return teams
    except json.JSONDecodeError:
      logging.warning('Encountered JSONDecodeError for file {0}'.format(file_path))
      return []

def persist_teams(guild_id, teams):
  logging.info('Persisting teams for guild {0}'.format(guild_id))
  if not guild_has_data(guild_id):
    initialize_guild_data(guild_id)
  with open(guild_file_path(guild_id, FilePrefix.teams), 'w') as teams_file:
    teams_json_data = []
    for team in teams:
      teams_json_data.append(Driver.encode(team))
    json.dump(teams_json_data, teams_file)
    
def clear_teams(guild_id):
  if guild_has_file(guild_id, FilePrefix.teams):
    clear_guild_file(guild_id, FilePrefix.teams)

def load_balance(guild_id):
  logging.info('Loading balance for guild {0}'.format(guild_id))
  if not guild_has_data(guild_id):
    return []
  if not guild_has_file(guild_id, FilePrefix.balance):
    return []
  file_path = guild_file_path(guild_id, FilePrefix.balance)
  with open(file_path, 'r') as teams_file:
    try:
      teams_json_data = json.load(teams_file)
      teams = []
      for team_json_data in teams_json_data:
        teams.append(Driver.decode(team_json_data))
      return teams
    except json.JSONDecodeError:
      logging.warning('Encountered JSONDecodeError for file {0}'.format(file_path))
      return []

def persist_balance(guild_id, teams):
  logging.info('Persisting balance for guild {0}'.format(guild_id))
  if not guild_has_data(guild_id):
    initialize_guild_data(guild_id)
  with open(guild_file_path(guild_id, FilePrefix.balance), 'w') as teams_file:
    teams_json_data = []
    for team in teams:
      teams_json_data.append(Driver.encode(team))
    json.dump(teams_json_data, teams_file)
    
def clear_balance(guild_id):
  if guild_has_file(guild_id, FilePrefix.balance):
    clear_guild_file(guild_id, FilePrefix.balance)
    
def load_balance_threshold(guild_id):
  logging.info('Loading balance threshold for guild {0}'.format(guild_id))
  if not guild_has_data(guild_id):
    return []
  if not guild_has_file(guild_id, FilePrefix.balance_threshold):
    return []
  file_path = guild_file_path(guild_id, FilePrefix.balance_threshold)
  with open(file_path, 'r') as balance_threshold_file:
    try:
      str_threshold = json.load(balance_threshold_file)['balance_threshold']
      return float(str_threshold)
    except json.JSONDecodeError:
      logging.warning('Encountered JSONDecodeError for file {0}'.format(file_path))
      return []
  
def persist_balance_threshold(guild_id, balance_threshold):
  logging.info('Persisting balance threshold for guild {0}'.format(guild_id))
  if not guild_has_data(guild_id):
    initialize_guild_data(guild_id)
  with open(guild_file_path(guild_id, FilePrefix.balance_threshold), 'w') as balance_threshold_file:
    json.dump({'balance_threshold': balance_threshold}, balance_threshold_file)
    
def load_channel_id(guild_id):
  logging.info('Loading channel ID for guild {0}'.format(guild_id))
  if not guild_has_data(guild_id):
    return None
  if not guild_has_file(guild_id, FilePrefix.channel_id):
    return None
  file_path = guild_file_path(guild_id, FilePrefix.channel_id)
  with open(file_path, 'r') as channel_id_file:
    try:
      return json.load(channel_id_file)['channel_id']
    except json.JSONDecodeError:
      logging.warning('Encountered JSONDecodeError for file {0}'.format(file_path))
      return None
  
def persist_channel_id(guild_id, channel_id):
  logging.info('Persisting channel ID for guild {0}'.format(guild_id))
  if not guild_has_data(guild_id):
    initialize_guild_data(guild_id)
  with open(guild_file_path(guild_id, FilePrefix.channel_id), 'w') as channel_id_file:
    json.dump({'channel_id': channel_id}, channel_id_file)

def load_quarter_number():
  if not global_data_has_file(FilePrefix.quarter_number):
    logging.warning("Could not find current quarter number.")
    return None
  file_path = global_file_path(FilePrefix.quarter_number)
  with open(file_path, 'r') as quarter_number_file:
    try:
      return json.load(quarter_number_file)['quarter_number']
    except json.JSONDecodeError:
      logging.warning('Encountered JSONDecodeError for file {0}'.format(file_path))
      return None
    
def persist_quarter_number(number):
  logging.info('Persisting quarter number.')
  with open(global_file_path(FilePrefix.quarter_number), 'w') as quarter_number_file:
    json.dump({'quarter_number': number}, quarter_number_file)
    
def possible_size_patterns(driver_count, team_sizes):
  logging.info('Calculating possible size patterns for driver count {0} and team sizes {1}'.format(driver_count, team_sizes))
  patterns = []
  # Find the maximum number of teams. Note // for floor division
  max_size = (driver_count // min(team_sizes)) + 1
  logging.debug('Max size is {0}'.format(max_size))
  # Arrange the team sizes into all possible combinations of length <= max size.
  for size in team_sizes:
    patterns.append([size])
  last_level_patterns = copy.copy(patterns)
  for _ in range(max_size):
    level_patterns = []
    for pattern in last_level_patterns:
      for size in team_sizes:
        level_patterns.append(pattern + [size])
    patterns += level_patterns
    last_level_patterns = level_patterns
  # Find those that add up to the driver count.
  logging.debug('{0} patterns found before filtering for count being correct.'.format(len(patterns)))
  patterns = list(filter(lambda l: sum(l) == driver_count, patterns))
  logging.debug('{0} patterns found after count filtering but before uniquifying.'.format(len(patterns)))
  # Sort and uniquify.
  unique_patterns = []
  for pattern in patterns:
    pattern.sort()
    unique = True
    for checked_pattern in unique_patterns:
      matches = []
      for index, element in enumerate(checked_pattern):
        matches.append(element == pattern[index])
      if all(matches):
        unique = False
        break
    if unique:
      unique_patterns.append(pattern)
  for pattern in unique_patterns:
    logging.info('Found pattern {0}'.format(pattern))
  return unique_patterns
  
def unique_groupings(elements, size):
  logging.debug('Calculating unique groupings of {0} elements into size {1}'.format(len(elements), size))
  if size == 1:
    return [[element] for element in elements]
  groupings = []
  # Maintain uniqueness by keeping the elements in the grouping in order with the original elements.
  # Find the elements which could come first in the grouping.
  # For instance, if there are 5 elements, and a grouping of 3 is needed, only the first 3 could come first.
  # In general, if there are n elements, and a grouping of size m is needed, only the first (n - m + 1) could come first.
  stop_index = len(elements) - size + 1
  possible_firsts = elements[0:stop_index]
  for element in possible_firsts:
    # If this element is selected first, find the elements that could go next *while maintaining order*.
    remaining_elements = elements[elements.index(element) + 1:]
    for grouping in unique_groupings(remaining_elements, size - 1):
      groupings.append([element] + grouping)
  logging.debug('Found {0} groupings.'.format(len(groupings)))
  return groupings

def find_possible_combinations(drivers, team_sizes):
  combinations = []
  # Find the possible (unique) ways to break down the number of drivers into teams of the allowed size.
  # Throughout, sort the drivers in each team by iRating (highest first), and the teams in each combination by iRating of first driver in each team.
  for size_pattern in possible_size_patterns(len(drivers), team_sizes):
    logging.debug('Size pattern is {0}.'.format(size_pattern))
    # Find the possible ways to assign drivers to the first team in the pattern.
    pattern_combinations = [[team] for team in unique_groupings(drivers, size_pattern[0])]
    for combination in pattern_combinations:
      for team in combination:
        team.sort(key=lambda driver: driver.irating, reverse=True)
    # For the next team, expand each existing possibility for the first n teams into a suite of combinations for how to assign some of the remaining drivers into the first n + 1 teams.
    for team_size in size_pattern[1:]:
      next_level_pattern_combinations = []
      for combination in pattern_combinations:
        already_assigned_driver_names = [driver.name for driver in sum(combination, [])]
        remaining_drivers = [driver for driver in drivers if driver.name not in already_assigned_driver_names]
        groupings = unique_groupings(remaining_drivers, team_size)
        for grouping in groupings:
          grouping.sort(key=lambda driver: driver.irating, reverse=True)
          new_combination = combination + [grouping]
          new_combination.sort(key=lambda team: team[0].irating, reverse=True)
          next_level_pattern_combinations.append(new_combination)
      pattern_combinations = next_level_pattern_combinations
    combinations += pattern_combinations
  logging.info('Found {0} possible combinations of {1} drivers into teams of size {2}'.format(len(combinations), len(drivers), team_sizes))
  return combinations
  
def average_irating(team):
  return sum([driver.irating for driver in team], 0) / len(team);

def irating_gap(combination):
  averages = [average_irating(team) for team in combination]
  return max(averages) - min(averages)

def find_balanced_teams(drivers, team_sizes):
  # Find all possible combinations of drivers into teams of allowed sizes.
  # Sort these combinations according to the gap between the teams' average iRating.
  combinations = find_possible_combinations(drivers, team_sizes)
  combinations.sort(key=irating_gap)
  # Return the combination with the smallest gap.
  return combinations[0]
  
def combinations_equivalent(comb1, comb2):
  logging.debug('Checking equivalency of combinations {0} and {1}'.format(comb1, comb2))
  if len(comb1) != len(comb2):
    return False
  for team1 in comb1:
    equivalent_team_found = False
    for team2 in comb2:
      matches = [driver2.name in [driver1.name for driver1 in team1] for driver2 in team2]
      if all(matches):
        equivalent_team_found = True
        break
    if not equivalent_team_found:
      return False
  return True

def display_format_teams(teams, header):
  message = "{0}:\n\n".format(header)
  for team_number, team in enumerate(teams, start=1):
    message += "Team {0} (average iRating: {1})\n".format(team_number, round(average_irating(team), 2))
    for driver in team:
      message += "  {0} ({1})\n".format(driver.name, driver.irating)
    message += "\n"
  message += "iRating gap between teams: {0}".format(round(irating_gap(teams), 2))
  return message
  
# This method assumes that every driver present in `teams` is present in `drivers`.
def apply_new_drivers_to_teams(drivers, teams):
  for team in teams:
    for index, old_driver in enumerate(team):
      for new_driver in drivers:
        if old_driver.name == new_driver.name:
          team[index] = new_driver
          break
  return teams
 
async def lookup_current_quarter_number():
  seasons = await ir_client.current_seasons(only_active=True)
  quarters = [season.season_quarter for season in seasons]
  persist_quarter_number(quarters[0]) # They should all be fine.
  
async def get_irating_from_chart(driver_id):
  chart_data = await ir_client.irating(cust_id=driver_id, category=constants.Category.road.value)
  return chart_data.current().value
 
async def get_irating(driver_id):
  irating = None
  event_results = await ir_client.event_results(driver_id, 
                                                load_quarter_number(), 
                                                show_races=1, 
                                                show_official=1, 
                                                result_num_high=1, 
                                                category=constants.Category.road.value)
  subsession_ids = [event_result.subsession_id for event_result in event_results]
  subsession_id = subsession_ids[0]
  subsession_data = await ir_client.subsession_data(subsession_id)
  new_iratings = [driver.irating_new for driver in subsession_data.driver if str(driver.cust_id) == driver_id]
  if new_iratings:
    irating = new_iratings[0] # They're all the same.
  else:
    logging.info("Couldn't find iRating for driver ID {0} from subsessions. Finding from chart.".format(driver_id))
    irating = await get_irating_from_chart(driver_id)
  return irating
  
async def recheck_all_driver_iratings(channel, drivers, on_demand=False):
  logging.info('Rechecking all driver ratings.')
  changed = False
  for driver in drivers:
    if on_demand or changed:
      await channel.trigger_typing()
    logging.info('Initiating iRating request.')
    new_irating = await get_irating(driver.id)
    if new_irating != driver.irating:
      changed = True
      driver.irating = new_irating
      await channel.send('Driver {0} has changed iRating: {1}.'.format(driver.name, driver.irating))
  if on_demand:
    if changed:
      await channel.send('Check complete.')
    else:
      await channel.send('No drivers have changed iRating since their most recently cached update.')
  logging.info('Changed = {0}'.format(changed))
  return changed

async def background_recheck():
  logging.info('Starting background recheck.')
  for guild_id in guild_ids():
    logging.info('Looking for data for guild {0}'.format(guild_id))
    if not guild_has_file(guild_id, FilePrefix.channel_id):
      return
    logging.info('Data found.')
    channel_id = load_channel_id(guild_id)
    logging.info('Found channel ID {0}'.format(channel_id))
    channel = di_client.get_channel(channel_id)
    drivers = load_drivers(guild_id)
    if not drivers:
      return
    changed = await recheck_all_driver_iratings(channel, drivers, on_demand=False)
    if not changed:
      return
    persist_drivers(guild_id, drivers)
    team_sizes = load_team_sizes(guild_id)
    if not team_sizes:
      return
    balance = load_balance(guild_id)
    new_balance = find_balanced_teams(drivers, team_sizes)
    persist_balance(guild_id, new_balance)
    threshold = load_balance_threshold(guild_id)
    fixed_teams = load_teams(guild_id)
    if fixed_teams:
      logging.info('Guild has fixed teams. Applying newly updated drivers to existing teams in order to calculate new iRating gap.')
      old_gap = irating_gap(fixed_teams)
      new_fixed_teams = apply_new_drivers_to_teams(drivers, fixed_teams)
      persist_teams(guild_id, new_fixed_teams)
      new_gap = irating_gap(new_fixed_teams)
      if threshold and new_gap > threshold:
        logging.info('Balance threshold is configured and the new gap exceeds the threshold.')
        verb = 'remains' if old_gap > threshold else 'has moved'
        message = "**WARNING**: The iRating gap of the fixed teams {0} outside of the balance threshold ({1})".format(verb, round(threshold, 2))
        teams_to_show = new_fixed_teams
      else:
        logging.info('Balance threshold is not configured, or the new gap does not exceed the threshold.')
        message = "The iRating gap of the fixed teams has changed from {0} to {1}.".format(round(old_gap, 2), round(new_gap, 2))
        teams_to_show = None
    else:
      logging.info('Guild does not have fixed teams. Calculating the difference in iRating gap between the new and old balances.')
      old_gap = irating_gap(balance)
      new_gap = irating_gap(new_balance)
      if combinations_equivalent(balance, new_balance):
        logging.info('New and old balances are equivalent.')
        if threshold:
          logging.info('Balance threshold is configured.')
          if new_gap > threshold:
            logging.info('New gap exceeds balance threshold.')
            if old_gap > threshold:
              conjunction, verb = 'and', 'remains'
            else:
              conjunction, verb = 'but', 'has moved'
            message = "The optimal balance of team members has not changed, {0} the iRating gap {1} outside of the balance threshold ({2})".format(conjunction, verb, round(threshold, 2))
            teams_to_show = new_balance
          else:
            logging.info('New gap does not exceed balance threshold.')
            message = "The optimal balance of team members has not changed.\nThe iRating gap has changed from {0} to {1}, which is inside the balance threshold ({2}).".format(round(old_gap, 2), round(new_gap, 2), round(threshold, 2))
            teams_to_show = None
        else:
          logging.info('Balance threshold is not configured. Nothing to report.')
      else:
        logging.info('New combination is not equivalent to old combination.')
        teams_to_show = new_balance
        if threshold:
          logging.info('Balance threshold is configured.')
          if new_gap > threshold:
            logging.info('New gap exceeds threshold.')
            if old_gap > threshold:
              conjunction, verb = 'but', 'remains'
            else:
              conjunction, verb = 'and', 'has moved'
            message = "The optimal balance of team members has changed, {0} the iRating gap {1} outside of the balance threshold ({2})".format(conjunction, verb, round(threshold, 2))
          else:
            logging.info('New gap is within threshold.')
            if old_gap > threshold:
              conjunction, verb = 'and', 'has moved'
            else:
              conjunction, verb = 'but', 'remains'
            message = "The optimal balance of team members has changed, {0} the iRating gap {1} inside the balance threshold ({2})".format(conjunction, verb, round(threshold, 2))
        else:
          logging.info('Balance threshold is not configured.')
          message = "The optimal balance of team members has changed"
    if teams_to_show:
      logging.info('Teams will be shown.')
      await channel.send(display_format_teams(teams_to_show, message))
    else:
      logging.info('Teams will not be shown.')
      await channel.send(message)

async def periodic_task():
  logging.info('Establishing periodic tasks.')
  p1 = Periodic(BACKGROUND_RECHECK_PERIOD_MINUTES * 60, background_recheck)
  await p1.start()
  p2 = Periodic(QUARTER_CHECK_PERIOD_MINUTES * 60, lookup_current_quarter_number)
  await p2.start()
  
@di_client.event
async def on_ready():
  logging.info('Logged in as {0.user}'.format(di_client))
  asyncio.get_event_loop().create_task(periodic_task())
  await lookup_current_quarter_number()

@di_client.event
async def on_message(message):
  author = message.author
  channel = message.channel
  try:
    if author == di_client.user:
      return
    
    if len(message.mentions) == 0:
      return
    
    if not di_client.user in message.mentions:
      return
    
    logging.debug('Message content is ' + message.content)
    re_match = message_text_re.match(message.content)
    if not re_match:
      pdb.set_trace()
      logging.warning('RE failed to match message content despite bot being mentioned.')
      return
      
    guild_id = str(channel.guild.id)
    guild_name = channel.guild.name
    
    msg = re_match.group(1)
    logging.info('Processing msg = {0}'.format(msg))

    if msg.startswith('hello') or msg.startswith('hi'):
      logging.info('Processing hello request.')
      await channel.send('Hello, {0.mention}!'.format(author))
      if author.name == 'DavidMcCourt' and author.discriminator == '9806':
        logging.info('Recognized creator.')
        await channel.send('Thanks for bringing me into this world.')
      logging.info('Response sent.')
      
    elif msg.startswith('sorry'):
      logging.info('Processing sorry request.')
      await channel.send("It's okay, {0.mention}. Unlike me, you're only human.".format(author))
      logging.info('Response sent.')
      
    elif msg.startswith('test background recheck'):
      logging.info('Processing test background recheck request.')
      await channel.send("Testing background recheck.")
      await background_recheck()
      logging.info('Background recheck test complete.')
      
    elif msg.startswith('list commands'):
      logging.info('Processing list commands request.')
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
        
      ''').strip()
      await channel.send(commands_list_part_1)
      commands_list_part_2 = dedent('''
        **balance** - show most recently calculated optimal balance of team members into teams.
        **recheck balance** - manually trigger a recheck of the optimal balance based on most recently cached road iRatings.
        
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
      ''').strip().format(di_client.user)
      await channel.send(commands_list_part_2)
      logging.info('Response sent.')

    elif msg.startswith('status'):
      logging.info('Processing status request.')
      message = 'Current status of data for {0}:\n'.format(guild_name)
      if guild_has_file(guild_id, FilePrefix.drivers):
        message += '{0} drivers have been added.\n'.format(len(load_drivers(guild_id)))
      else:
        message += 'No drivers have been added.\n'
      if guild_has_file(guild_id, FilePrefix.team_sizes):
        message += '{0} team sizes have been configured for balance calculation purposes.\n'.format(len(load_team_sizes(guild_id)))
      else:
        message += 'Team sizes have not yet been configured for balance calculation purposes.\n'
      if guild_has_file(guild_id, FilePrefix.balance):
        message += 'I have calculated the optimal iRating balance of team members into teams based on the added drivers and configured team sizes.\n'
      else:
        message += 'I have not yet calculated balance, but calculation is possible at any time.\n'
      if guild_has_file(guild_id, FilePrefix.teams):
        message += 'Drivers have been set into {0} fixed teams. If monitoring is established, I will monitor the balance of these specific teams, whether or not they are the optimal balance.\n'.format(len(load_teams(guild_id)))
      else:
        message += 'Teams have not yet been fixed. If monitoring is established, I will monitor and report on the optimal balance of drivers into teams.\n'
      if guild_has_file(guild_id, FilePrefix.channel_id):
        message += 'Notification channel has been configured for alerts based on automated monitoring. Automated monitoring is established.\n'
      else:
        message += 'Notification channel has not yet been set. I am not able to perform automated monitoring and notification.\n'
      if guild_has_file(guild_id, FilePrefix.balance_threshold):
        message += 'Balance threshold has been set. As I monitor, I will note how the balance of teams compares to the threshold, if monitoring is established.'
      else:
        message += 'Balance threshold has not been set. I will monitor the balance (if monitoring is established), but not against any particular warning threshold.'
      await channel.send(message)
      logging.info('Response sent.')
    
    elif msg.startswith('drivers'):
      logging.info('Processing list drivers request.')
      drivers = load_drivers(guild_id)
      if not drivers:
        await channel.send('No {0} drivers have been added.'.format(guild_name))
        logging.info('Response not sent. No drivers added.')
      else:
        driver_data = []
        for driver in drivers:
          driver_data.append('  {0} (iRacing ID {1}), road iRating {2} (last updated {3})'.format(driver.name, driver.id, driver.irating, driver.last_updated))
        await channel.send("Current list of {0} drivers:\n".format(guild_name) + "\n".join(driver_data))
        logging.info('Response sent.')
    
    elif msg.startswith('add driver '):
      logging.info('Processing add driver request.')
      drivers = load_drivers(guild_id)
      if not drivers:
        drivers = []
      drivers_data = msg.split('add driver ')[1]
      for driver_data in drivers_data.split(', '):
        if(len(drivers) >= 20):
          logging.info('Limit of 20 drivers has been reached.')
          await channel.send("Sorry, due to rate limitations on the iRacing API, I'm not able to balance more than 20 drivers per server.")
          logging.info('Response sent.')
          return
        logging.info(' Parsing driver data {0}'.format(driver_data))
        driver_identifiers = driver_data.split(' ')
        driver_id = driver_identifiers[-1]
        driver_name = driver_data.split(' ' + driver_id)[0]
        if not driver_id.isnumeric():
          logging.info('Driver ID is not not numeric.')
          driver_name = driver_data
          await channel.trigger_typing()
          response = await ir_client._build_request(constants.URL_DRIVER_STATUS, {'searchTerms': driver_name})
          drivers_response_data = response.json()['searchRacers']
          if not drivers_response_data:
            logging.info('No ID found.')
            await channel.send('No driver was found with the name {0}. Please check if that is their exact name on iRacing - or add them with their iRacing ID.'.format(driver_name))
            return
          exact_matches = [data['custid'] for data in drivers_response_data if data['name'].replace('+', ' ') == driver_name]
          if exact_matches:
            logging.info('One ID found.')
            driver_id = exact_matches[0]
          else:
            logging.info('Multiple IDs found.')
            await channel.send("Multiple drivers were found with the name {0}. Please check if the driver you're trying to add has a more specific name (maybe a digit at the end).".format(driver_name))
            return
        found_driver = None
        for driver in drivers:
          if driver.name == driver_name:
            found_driver = driver
            break
        if found_driver:
          logging.info('Driver has already been added.')
          await channel.send('Driver {0} has already been added.'.format(driver_name))
          logging.info('Response sent.')
          continue
        await channel.trigger_typing()
        logging.info('Initiating iRating request.')
        driver_irating = await get_irating(driver_id)
        driver = Driver(driver_id, driver_name, driver_irating, datetime.datetime.today())
        drivers.append(driver)
        persist_drivers(guild_id, drivers)
        await channel.send('Added driver {0} (iRacing ID {1}), road iRating {2} (last updated {3})'.format(driver.name, driver.id, driver.irating, driver.last_updated))
          
    
    elif msg.startswith('remove driver '):
      logging.info('Processing remove driver request.')
      drivers = load_drivers(guild_id)
      if not drivers:
        logging.info('No drivers set.')
        await channel.send('No {0} drivers have been added.'.format(guild_name))
        logging.info('Response sent.')
        return
      driver_name = msg.split('remove driver ')[1]
      found_driver = None
      for driver in drivers:
        if driver.name == driver_name:
          found_driver = driver
          break
      if found_driver:
        drivers.remove(found_driver)
        persist_drivers(guild_id, drivers)
        logging.info('Driver removed.')
        await channel.send('Removed {0} driver {1} (iRacing ID {2}).'.format(guild_name, found_driver.name, found_driver.id))
        if guild_has_file(guild_id, FilePrefix.teams):
          clear_teams(guild_id)
          await channel.send('Fixed teams are no longer valid and have been cleared.')
        if guild_has_file(guild_id, FilePrefix.balance):
          clear_balance(guild_id)
          await channel.send('Calculated optimal balance is no longer valid and has been cleared.')
      else:
        logging.info('Driver not found.')
        await channel.send("Sorry, I couldn't find a {0} driver named {1}. Use the 'drivers' command to see the list of currently added drivers.".format(guild_name, driver_name))
        
    elif msg.startswith('clear drivers'):
      logging.info('Processing clear drivers request.')
      clear_drivers(guild_id)
      if guild_has_file(guild_id, FilePrefix.teams):
        clear_teams(guild_id)
      if guild_has_file(guild_id, FilePrefix.balance):
        clear_balance(guild_id)
      await channel.send('Cleared all {0} drivers, including fixed teams and calculated balance.'.format(guild_name))
    
    elif msg.startswith('recheck rating '):
      logging.info('Processing recheck rating request.')
      drivers = load_drivers(guild_id)
      if not drivers:
        logging.info('Drivers not set.')
        await channel.send("No {0} drivers have been added yet. Once drivers are added, then I can recheck their iRating for you.".format(guild_name))
      else:
        driver_name = msg.split('recheck rating ')[1]
        changed = False
        if driver_name == 'all':
          logging.info('Processing recheck ALL rating request.')
          changed = await recheck_all_driver_iratings(channel, drivers, on_demand=True)
          if changed:
            persist_drivers(guild_id, drivers)
        else:
          found_driver = None
          for driver in drivers:
            if driver.name == driver_name:
              found_driver = driver
              await channel.trigger_typing()
              logging.info('Initiating iRating request.')
              new_irating = await get_irating(driver.id)
              if new_irating != driver.irating:
                logging.info('iRating has changed.')
                changed = True
                driver.irating = new_irating
                driver.last_updated = datetime.datetime.today()
                await channel.send('Driver {0} has changed iRating: {1}.'.format(driver.name, driver.irating))
              else:
                logging.info('iRating has not changed.')
                await channel.send('The iRating of driver {0} has not changed since the most recently cached update ({1}).'.format(driver.name, driver.last_updated))
              break
          if not found_driver:
            logging.info('Driver not found.')
            await channel.send("Sorry, I couldn't find a {0} driver named {1}. Use 'drivers' command to see the list of currently added drivers.".format(guild_name, driver_name))
        if changed:
          persist_drivers(guild_id, drivers)
    
    elif msg.startswith('team sizes'):
      logging.info('Processing team size get request')
      sizes = load_team_sizes(guild_id)
      if sizes:
        str_sizes = list(map(str, sizes))
        size_list = ', '.join(str_sizes)
        await channel.send('Team sizes for {0}: {1}.'.format(guild_name, size_list))
        logging.info('Response sent.')
      else:
        logging.info('Team sizes not set.')
        await channel.send("Team sizes for {0} have not been set. Use 'set team sizes' command to set the allowed team sizes.".format(guild_name))
    
    elif msg.startswith('set team sizes '):
      logging.info('Processing team size set request')
      size_list = msg.split('set team sizes ')[1]
      sizes = list(map(int, size_list.split(', ')))
      persist_team_sizes(guild_id, sizes)
      await channel.send('Team sizes for {0} set to {1}.'.format(guild_name, size_list))
      logging.info('Response sent.')
      if guild_has_file(guild_id, FilePrefix.balance):
        clear_balance(guild_id)
        await channel.send('Calculated balance has been cleared.')
    
    elif msg.startswith('balance') and not msg.startswith('balance threshold'):
      logging.info('Processing balance get request')
      balance = load_balance(guild_id)
      if not balance:
        logging.info('Balance not found.')
        await channel.send("Balance has not yet been calculated for {0}. Use command 'recheck balance' to manually trigger balance calculation.".format(guild_name))
      else:
        await channel.send(display_format_teams(balance, "Optimal balance of {0} drivers".format(guild_name)))
        logging.info('Response sent.')
    
    elif msg.startswith('recheck balance'):
      logging.info('Processing balance check request')
      drivers = load_drivers(guild_id)
      if not drivers:
        logging.info('Drivers not found.')
        await channel.send("No {0} drivers have been added. Use 'add drivers' command to add drivers first.".format(guild_name))
        return
      team_sizes = load_team_sizes(guild_id)
      if not team_sizes:
        logging.info('Team sizes not found.')
        await channel.send("Allowed team sizes have not been defined. Use 'set team sizes' command to set allowed team sizes first.".format(guild_name))
        return
      balance = load_balance(guild_id)
      await channel.trigger_typing()
      balanced_teams = find_balanced_teams(drivers, team_sizes)
      logging.info('Balance calculated.')
      header = "Optimal balance of {0} drivers".format(guild_name)
      if not combinations_equivalent(balance, balanced_teams):
        logging.info('Balance is new.')
        persist_balance(guild_id, balanced_teams)
        header = "**New** optimal balance of {0} drivers".format(guild_name)
      await channel.send(display_format_teams(balanced_teams, header))
      logging.info('Response sent.')
    
    elif msg.startswith('teams'):
      logging.info('Processing teams get request')
      teams = load_teams(guild_id)
      if teams:
        await channel.send(display_format_teams(teams, "Current {0} teams".format(guild_name)))
        logging.info('Response sent.')
      else:
        await channel.send("{0} teams have not been set. Use 'set teams' command to set fixed teams.".format(guild_name))
        logging.info('Teams not found.')
    
    elif msg.startswith('set teams '):
      logging.info('Processing teams set request.')
      drivers = load_drivers(guild_id)
      remaining_drivers = copy.copy(drivers)
      teams_list_str = msg.split('set teams ')[1]
      teams = []
      if(teams_list_str == 'according to balance'):
        logging.info('Processing teams set according to balance request.')
        teams = load_balance(guild_id)
        if not teams:
          logging.info('Balance not found.')
          await channel.send("Balance has not yet been calculated for {0}. Use command 'recheck balance' to manually trigger balance calculation.".format(guild_name))
          return
      else:  
        for drivers_list_str in teams_list_str.split('; '):
          team_drivers = []
          for driver_name in drivers_list_str.split(', '):
            found_driver = None
            for driver in drivers:
              if driver.name == driver_name:
                found_driver = driver
                break
            if found_driver:
              if found_driver in remaining_drivers:
                team_drivers.append(found_driver)
                remaining_drivers.remove(found_driver)
              else:
                logging.info('Driver not found in remaining drivers, so is a repeat.')
                await channel.send('Driver {0} was listed more than once. Please ensure drivers are only listed once.'.format(found_driver.name))
                return
            else:
              logging.info('Driver not found in known drivers.')
              await channel.send("Sorry, I couldn't find a {0} driver named {1}. Use 'drivers' command to see the list of currently added drivers.".format(guild_name, driver_name))
              return
          teams.append(team_drivers)
      persist_teams(guild_id, teams)
      await channel.send(display_format_teams(teams, "New {0} teams".format(guild_name)))
      logging.info('Response sent.')
      
    elif msg.startswith('clear teams'):
      logging.info('Processing clear teams request.')
      clear_teams(guild_id)
      await channel.send('Cleared {0} fixed teams.'.format(guild_name))
      logging.info('Response sent.')
    
    elif msg.startswith('balance threshold'):
      logging.info('Processing balance threshold get request')
      threshold = load_balance_threshold(guild_id)
      if threshold:
        await channel.send('Balance threshold for {0}: {1}.'.format(guild_name, threshold))
        logging.info('Response sent.')
      else:
        logging.info('Threshold not found.')
        await channel.send("Balance threshold for {0} has not been set. Use 'set balance threshold' command to set it.".format(guild_name))
    
    elif msg.startswith('set balance threshold '):
      logging.info('Processing balance threshold set request')
      threshold = msg.split('set balance threshold ')[1]
      if threshold.replace('.', '', 1).isdigit():
        persist_balance_threshold(guild_id, threshold)
        await channel.send('Balance threshold for {0} set to {1}.'.format(guild_name, threshold))
        logging.info('Response sent.')
      else:
        logging.info('Received threshold is not a number.')
        await channel.send('Balance threshold must be a number.')
    
    elif msg.startswith('notification channel'):
      logging.info('Processing notification channel get request')
      channel_id = load_channel_id(guild_id)
      if channel_id:
        found_channel = discord.utils.find(lambda c: c.id == channel_id and c.type == discord.ChannelType.text, channel.guild.channels)
        if found_channel:
          await channel.send("I am currently sending notifications to {0.mention}.".format(found_channel))
          logging.info('Response sent.')
        else:
          logging.info('Channel ID loaded, but channel not identified as text channel by Discord client.')
          await channel.send("Oops, the channel I am currently sending notifications to doesn't seem to exist anymore. Please use 'set notification channel' command to set a new one.")
      else:
        logging.info('Channel ID not found.')
        await channel.send("No channel is currently configured for notifications. If you wish, use 'set notification channel' command to let me know where to send notifications.")
    
    elif msg.startswith('set notification channel'):
      logging.info('Processing set notification channel request')
      persist_channel_id(guild_id, message.channel.id)
      await channel.send('Set {0.mention} as the notification channel for {1}.'.format(message.channel, guild_name))
      logging.info('Response sent.')
    
    else:
      logging.info('Unrecognized command.')
      await channel.send("Sorry, I didn't understand that command. For a list of available commands, use the 'list commands' command.")
      logging.info('Response sent.')
  
  except:
    logging.error('Error encountered.')
    await channel.send('Sorry, that command was recognized, but I encountered an error processing it.')
    logging.info('Response sent.')
    raise

logging.info('Running Discord client event loop.')
di_client.run(os.getenv('TOKEN'))