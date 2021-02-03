from pyracing import constants

from balancebot.balancer          import Balancer
from balancebot.driver            import Driver
from balancebot.driver_set        import DriverSet
from balancebot.driver_collection import DriverCollection
from balancebot.guild             import Guild

class BalanceBot:
  def __init__(self, client, data_store_class):
    self.interface = None
    self.client = client
    self.data_store_class = data_store_class
    self.guild = None
    self.quarter_number = self.data_store_class.load_quarter_number()
  
  async def add_combinations(self, collection):
    if not self.guild.has_drivers():
      await self.interface.print('No {0} drivers have been added.'.format(self.guild.name))
      return
    combinations = self.guild.combinations
    new_combinations = DriverCollection()
    for driver_names in collection:
      combination = DriverSet()
      for driver_name in driver_names:
        driver = self.identify_driver(driver_name)
        if not driver:
          await self.alert_driver_does_not_exist(driver_name)
          return
        if combinations.has_driver(driver):
          await self.interface.print("{0} is already part of a combination. I don't currently support automatically combining new combinations with existing combinations. If desired, please remove the existing combination and add a new combination as necessary.".format(driver.name))
          return
        if combination.has_driver(driver) or new_combinations.has_driver(driver):
          await self.alert_driver_already_specified(driver.name)
          return
        combination.add_driver(driver)
      new_combinations.add_driver_set(combination)
    self.guild.add_combinations(new_combinations)
    await self.interface.print('Added new combination(s) of {0} drivers.'.format(self.guild.name))
    if self.guild.teams.size() > 0:
      await self.interface.print('Note that since {0} teams have been set, balance monitoring and notification will continue to check against the set teams. Driver combinations will not be taken into account.'.format(self.guild.name))

    
  async def add_drivers(self, driver_identifiers):
    for driver_identifier in driver_identifiers:
      await self.interface.indicate_progress()
      if isinstance(driver_identifier, str):
        driver_name = driver_identifier
        if Driver.find_by_name(self.guild.get_drivers(), driver_name):
          await self.alert_driver_already_exists(driver_name)
          return
        driver_id = await self.find_driver_id(driver_identifier)
        if not driver_id:
          return
      else:
        driver_id = driver_identifier
        driver_name = await self.find_driver_name(driver_id)
        if Driver.find_by_name(self.guild.get_drivers(), driver_name):
          await self.alert_driver_already_exists(driver_name)
          return
        if not driver_name:
          return
      driver_irating = await self.find_driver_irating(driver_id)
      driver = Driver(driver_id, driver_name, driver_irating)
      self.guild.add_driver(driver)
      await self.interface.print('Added driver {0}'.format(driver.print_format()))
      
  async def alert_driver_already_exists(self, driver_name):
    await self.interface.print('Driver {0} has already been added.'.format(driver_name))
  
  async def alert_driver_already_specified(self, driver_name):
    await self.interface.print('{0} was specified more than once. Please ensure drivers are specified at most once.'.format(driver_name))
  
  async def alert_driver_does_not_exist(self, driver_name):
    await self.interface.print("Sorry, I couldn't find a driver named {0}.".format(driver_name))
  
  async def alert_error_received(self):
    await self.interface.print('Sorry, that command was recognized, but I encountered an error processing it.')
    
  async def alert_unrecognized_command(self):
    await self.interface.print("Sorry, I didn't recognize that command. For a list of available commands, use the 'list commands' command.")
  
  async def background_recheck(self):
    if not self.guild.has_drivers():
      return
    if self.guild.teams.size() > 0:
      old_gap = self.guild.teams.irating_gap()
    else:
      old_gap = self.guild.balance.irating_gap()
    threshold = self.guild.balance_threshold
    any_changed = await self.recheck_driver_ratings(self.guild.get_drivers(), print_unchanged=False)
    if not any_changed:
      return
    if self.guild.teams.size() > 0:
      new_gap = self.guild.teams.irating_gap()
      if threshold and new_gap > threshold:
        verb = 'remains' if old_gap > threshold else 'has moved'
        message = "**WARNING**: The iRating gap of the fixed teams {0} outside of the balance threshold ({1})".format(verb, round(threshold, 2))
        teams_to_show = self.guild.teams
      else:
        message = "The iRating gap of the fixed teams has changed from {0} to {1}.".format(round(old_gap, 2), round(new_gap, 2))
        teams_to_show = None
    else:
      possible = await self.check_balance_possible(print_reason_not_possible=False)
      if not possible:
        return
      old_balance = self.guild.balance
      balancer = Balancer(self.guild.get_drivers(), self.guild.team_sizes, self.guild.combinations)
      await self.interface.indicate_progress()
      new_balance = balancer.optimal_balance()
      self.guild.set_balance(new_balance)
      new_gap = new_balance.irating_gap()
      if new_balance == old_balance:
        if threshold:
          if new_gap > threshold:
            if old_gap > threshold:
              conjunction, verb = 'and', 'remains'
            else:
              conjunction, verb = 'but', 'has moved'
            message = "The optimal balance of team members has not changed, {0} the iRating gap {1} outside of the balance threshold ({2})".format(conjunction, verb, round(threshold, 2))
            teams_to_show = new_balance
          else:
            message = "The optimal balance of team members has not changed.\nThe iRating gap has changed from {0} to {1}, which is inside the balance threshold ({2}).".format(round(old_gap, 2), round(new_gap, 2), round(threshold, 2))
            teams_to_show = None
      else:
        teams_to_show = new_balance
        if threshold:
          if new_gap > threshold:
            if old_gap > threshold:
              conjunction, verb = 'but', 'remains'
            else:
              conjunction, verb = 'and', 'has moved'
            message = "The optimal balance of team members has changed, {0} the iRating gap {1} outside of the balance threshold ({2})".format(conjunction, verb, round(threshold, 2))
          else:
            if old_gap > threshold:
              conjunction, verb = 'and', 'has moved'
            else:
              conjunction, verb = 'but', 'remains'
            message = "The optimal balance of team members has changed, {0} the iRating gap {1} inside the balance threshold ({2})".format(conjunction, verb, round(threshold, 2))
        else:
          message = "The optimal balance of team members has changed"
    if teams_to_show:
      await self.print_collection(teams_to_show, message)
    else:
      await self.interface.print(message)
      
  async def check_balance_possible(self, print_reason_not_possible=True):
    if not self.guild.has_drivers():
      if print_reason_not_possible:
        await self.interface.print('No {0} drivers have been added.'.format(self.guild.name))
      return False
    if not self.guild.team_sizes:
      if print_reason_not_possible:
        await self.interface.print('Team sizes have not been set.')
      return False
    if not self.guild.driver_count() >= min(self.guild.team_sizes) * 2:
      if print_reason_not_possible:
        await self.interface.print('There are not enough drivers to form teams of the specified size(s).')
      return False
    if not Balancer.is_team_formation_possible(self.guild.driver_count(), self.guild.team_sizes):
      if print_reason_not_possible:
        await self.interface.print('It is not possible to form teams of the specified size(s) with {0} drivers.'.format(self.guild.driver_count()))
      return False
    return True
  
  async def clear_combinations(self):
    self.guild.clear_combinations()
    await self.interface.print('Cleared combinations of {0} drivers.'.format(self.guild.name))
  
  async def clear_drivers(self):
    if not self.guild.has_drivers():
      await self.interface.print('No {0} drivers have been added.'.format(self.guild.name))
      return
    self.guild.clear_drivers()
    await self.interface.print('Cleared {0} drivers, including calculated balance, driver combinations, and fixed teams.'.format(self.guild.name))
  
  async def clear_teams(self):
    if self.guild.teams.size() == 0:
      await self.interface.print('No {0} teams have been set.'.format(self.guild.name))
      return
    self.guild.clear_teams()
    await self.interface.print('Cleared {0} teams.'.format(self.guild.name))
  
  async def find_driver_id(self, driver_name):
    response = await self.client._build_request(constants.URL_DRIVER_STATUS, {'searchTerms': driver_name})
    drivers_response_data = response.json()['searchRacers']
    if not drivers_response_data:
      await self.interface.print('No driver was found with the name {0}. Please check if that is their exact name on iRacing - or add them with their iRacing ID.'.format(driver_name))
      return
    exact_matches = [int(data['custid']) for data in drivers_response_data if data['name'].replace('+', ' ') == driver_name]
    if not exact_matches:
      await self.interface.print("Multiple drivers were found with the name {0}. Please check if the driver you're trying to add has a more specific name (maybe a digit at the end).".format(driver_name))
      return
    return exact_matches[0]
   
  async def find_driver_irating(self, driver_id):
    if not self.quarter_number:
      await self.update_quarter_number()
    try:
      event_results = await self.client.event_results(driver_id,
                                                      self.quarter_number,
                                                      show_races=1,
                                                      show_official=1,
                                                      result_num_high=1,
                                                      category=constants.Category.road.value)
      subsession_ids = [event_result.subsession_id for event_result in event_results]
      subsession_id = subsession_ids[0]
      subsession_data = await self.client.subsession_data(subsession_id)
      new_iratings = [driver.irating_new for driver in subsession_data.driver if str(driver.cust_id) == driver_id]
    except TypeError: # iRacing client doesn't gracefully handle empty response.
      new_iratings = []
    if new_iratings:
      return new_iratings[0]
    else:
      irating = await self.find_driver_irating_from_chart(driver_id)
      return irating
  
  async def find_driver_irating_from_chart(self, driver_id):
    chart_data = await self.client.irating(cust_id=driver_id, category=constants.Category.road.value)
    return chart_data.current().value
  
  async def find_driver_name(self, driver_id):
    status = await self.client.driver_status(driver_id)
    return status.name.replace('+', ' ') # Why does the client not do this, I ask you
  
  def get_monitoring_data(self):
    return self.guild.monitoring_data
  
  async def get_quarter_number(self):
    seasons = await self.client.current_seasons(only_active=True)
    quarters = [season.season_quarter for season in seasons]
    return quarters[0] # They should all be the same. Unless VLN enduro gets in the way or something.
  
  def identify_driver(self, driver_identifier):
    if isinstance(driver_identifier, str):
      return Driver.find_by_name(self.guild.get_drivers(), driver_identifier)
    else:
      return Driver.find(self.guild.get_drivers(), driver_identifier)
        
  def initialize_guild(self, guild_id):
    data_store = self.data_store_class(guild_id)
    self.guild = Guild(guild_id, data_store)
  
  async def list_balance(self):
    if self.guild.balance.size() == 0:
      await self.interface.print('Balance has not yet been calculated for {0} drivers.'.format(self.guild.name))
      return
    await self.print_collection(self.guild.balance, 'Most recently calculated balance of {0} drivers'.format(self.guild.name))
  
  async def list_combinations(self):
    if self.guild.combinations.size() == 0:
      await self.interface.print('No combinations of {0} drivers have been set.'.format(self.guild.name))
      return
    message = 'Current combinations of {0} drivers:\n'.format(self.guild.name)
    for driver_set in self.guild.combinations.driver_sets:
      message += ', '.join([driver.name for driver in driver_set.drivers]) + '\n'
    await self.interface.print(message)
    
  async def list_drivers(self):
    if not self.guild.has_drivers():
      await self.interface.print('No {0} drivers have been added.'.format(self.guild.name))
      return
    message = 'Current list of {0} drivers:\n'.format(self.guild.name)
    for driver in self.guild.get_drivers():
      message += '  {0}\n'.format(driver.print_format())
    await self.interface.print(message)
    
  async def list_team_sizes(self):
    if not self.guild.team_sizes:
      await self.interface.print('Team sizes have not been set for {0}.'.format(self.guild.name))
      return
    team_sizes_str = ', '.join([str(team_size) for team_size in self.guild.team_sizes])
    await self.interface.print('Team sizes for {0}: {1}.'.format(self.guild.name, team_sizes_str))
    
  async def list_teams(self):
    if self.guild.teams.size() == 0:
      await self.interface.print('No fixed teams have been set for {0}.'.format(self.guild.name))
      return
    await self.print_collection(self.guild.teams, 'Current list of {0} teams'.format(self.guild.name))

  async def print_collection(self, collection, header):
    message = '{0}:\n\n'.format(header)
    for index, driver_set in enumerate(collection.ordered_driver_sets(), 1):
      message += '  Team {0} (average iRating: {1}):\n'.format(index, round(driver_set.average_irating(), 2))
      for driver in driver_set.ordered_drivers():
        message += '    {0} ({1})\n'.format(driver.name, driver.irating)
      message += '\n'
    message += 'iRating gap between teams: {0}'.format(round(collection.irating_gap(), 2))
    await self.interface.print(message)
    
  async def recalculate_balance(self):
    if self.guild.teams.size() > 0:
      await self.print_collection(self.guild.teams, 'Current balance of {0} teams'.format(self.guild.name))
      return
    possible = await self.check_balance_possible(print_reason_not_possible=True)
    if not possible:
      return
    old_balance = self.guild.balance
    balancer = Balancer(self.guild.get_drivers(), self.guild.team_sizes, self.guild.combinations)
    await self.interface.indicate_progress()
    new_balance = balancer.optimal_balance()
    self.guild.set_balance(new_balance)
    if self.guild.balance == old_balance:
      header = 'Optimal balance of {0} drivers'.format(self.guild.name)
    else:
      header = 'New optimal balance of {0} drivers'.format(self.guild.name)
    await self.print_collection(self.guild.balance, header)
  
  async def recheck_all_ratings(self, indicate_progress_before_first_change=True):
    any_changed = False
    for driver in self.guild.get_drivers():
      if indicate_progress_before_first_change or any_changed:
        await self.interface.indicate_progress()
      changed = await self.update_driver_irating(driver, print_unchanged=False)
      if changed:
        any_changed = True
    if not any_changed:
      await self.interface.print('No {0} drivers have changed iRating since their latest update.'.format(self.guild.name))
  
  async def recheck_driver_ratings(self, drivers, print_unchanged=True):
    any_changed = False
    for driver in drivers:
      await self.interface.indicate_progress()
      changed = await self.update_driver_irating(driver, print_unchanged=print_unchanged)
      if changed:
        any_changed = True
    return any_changed
  
  async def recheck_ratings(self, driver_identifiers):
    if not self.guild.has_drivers():
      await self.interface.print('No {0} drivers have been added.'.format(self.guild.name))
      return
    drivers = []
    for driver_identifier in driver_identifiers:
      driver = self.identify_driver(driver_identifier)
      if not driver:
        await self.alert_driver_does_not_exist(driver_identifier)
        return
      drivers.append(driver)
    await self.recheck_driver_ratings(drivers, print_unchanged=True)
  
  async def remove_combinations(self, collection):
    combinations = self.guild.combinations
    combinations_to_remove = []
    for driver_names in collection:
      combination_to_remove = DriverSet()
      for driver_name in driver_names:
        driver = self.identify_driver(driver_name)
        if not driver:
          await self.alert_driver_does_not_exist(driver_name)
          return
        combination_to_remove.add_driver(driver)
      matching_combinations = [combination for combination in combinations.driver_sets if combination == combination_to_remove]
      if not matching_combinations:
        await self.interface.print('No combination of {0} was found matching {1}.'.format(self.guild.name, ', '.join(driver_names)))
        return
      combinations_to_remove += matching_combinations # There'll just be one, but I don't know of a 'find' in Python, so list comprehensions with a conditional are the best I can do.
    self.guild.remove_combinations(combinations_to_remove)
    await self.interface.print('Removed combination(s) of {0} drivers.'.format(self.guild.name))
 
  async def remove_drivers(self, driver_identifiers):
    if not self.guild.has_drivers():
      await self.interface.print('No {0} drivers have been added.'.format(self.guild.name))
      return
    for driver_identifier in driver_identifiers:
      driver = self.identify_driver(driver_identifier)
      if not driver:
        await self.alert_driver_does_not_exist(driver_identifier)
        return
      self.guild.remove_driver(driver)
      await self.interface.print('Removed driver {0}. Fixed teams, calculated balance, and any combinations including this driver have been cleared.'.format(driver.name))
    
  async def set_balance_threshold(self, threshold_value):
    if not isinstance(threshold_value, int):
      await self.interface.print('Balance threshold must be an integer.')
      return
    if not threshold_value >= 1:
      await self.interface.print('Balance threshold must be at least 1.')
      return
    self.guild.set_balance_threshold(threshold_value)
    await self.interface.print('Set balance threshold for {0} to {1}.'.format(self.guild.name, threshold_value))
  
  def set_guild_name(self, name):
    self.guild.set_name(name)
  
  def set_interface(self, interface):
    self.interface = interface
  
  def set_monitoring_data(self, data):
    self.guild.set_monitoring_data(data)
  
  async def set_team_sizes(self, team_sizes):
    if not team_sizes:
      await self.interface.print('No valid team sizes specified. Team sizes must be integers between 2 and 10.')
      return
    for team_size in team_sizes:
      if not team_size >= 2 and team_size <= 10:
        await self.interface.print('Team size {0} is not valid. Team sizes must be integers between 2 and 10.'.format(str(team_size)))
        return
    team_sizes.sort()
    self.guild.set_team_sizes(team_sizes)
    team_sizes_str = ', '.join([str(team_size) for team_size in team_sizes])
    await self.interface.print('Set {0} team sizes to {1}.'.format(self.guild.name, team_sizes_str))
  
  async def set_teams(self, collection):
    teams = DriverCollection()
    for driver_names in collection:
      team = DriverSet()
      for driver_name in driver_names:
        driver = self.identify_driver(driver_name)
        if not driver:
          await self.alert_driver_does_not_exist(driver_name)
          return
        if team.has_driver(driver) or teams.has_driver(driver):
          await self.alert_driver_already_specified(driver.name)
          return
        team.add_driver(driver)
      teams.add_driver_set(team)
    drivers_not_included = [driver for driver in self.guild.get_drivers() if not teams.has_driver(driver)]
    if drivers_not_included:
      await self.interface.print('The specified teams did not include {0}. All drivers must be included in the fixed teams.'.format(', '.join([driver.name for driver in drivers_not_included])))
      return
    self.guild.set_teams(teams)
    await self.interface.print('Set teams for {0}.'.format(self.guild.name))
  
  async def set_teams_according_to_balance(self):
    if self.guild.balance.size() == 0:
      await self.interface.print('Balance has not been calculated.')
      return
    self.guild.set_teams(self.guild.balance)
    await self.interface.print('Set teams according to balance.')
  
  async def show_balance_threshold(self):
    threshold = self.guild.balance_threshold
    if not threshold:
      await self.interface.print('Balance threshold has not been set for {0}.'.format(self.guild.name))
      return
    await self.interface.print('Balance threshold for {0} has been set to {1}.'.format(self.guild.name, threshold))
  
  async def show_status(self):
    message_parts = []
    message_parts.append('Current status of data for {0}:'.format(self.guild.name))
    if self.guild.has_drivers():
      message_parts.append('{0} drivers have been added.'.format(self.guild.driver_count()))
    else:
      message_parts.append('No drivers have been added.')
    if self.guild.team_sizes:
      message_parts.append('Team sizes have been confgured for balance calculations purposes.')
    else:
      message_parts.append('Team sizes have not yet been configured for balance calculation purposes.')
    if self.guild.balance.size() > 0:
      message_parts.append('I have calculated the optimal iRating balance of team members into teams, based on the added drivers and configured team sizes.')
    else:
      message_parts.append('I have not yet calculated balance.')
    if self.guild.combinations.size() > 0:
      message_parts.append('{0} combination(s) of drivers has/have been set. Balance calculations will only include sets of teams where each combination of drivers is on the same team.'.format(self.guild.combinations.size()))
    else:
      message_parts.append('No combinations of drivers have been set. Balance calculations will include all possible sets of teams.')
    if self.guild.teams.size() > 0:
      message_parts.append('Drivers have been set into fixed teams. I will calculate balance for these specific teams, whether or not they are the optimal balance.')
    else:
      message_parts.append('Teams have not yet been fixed. I will monitor and report on the optimal balance of drivers into teams.')
    if self.interface.is_monitoring_possible():
      message_parts.append('Automated monitoring is possible and will be performed.')
    else:
      message_parts.append('Automated monitoring is not possible, so will not be performed.')
    if self.guild.balance_threshold:
      message_parts.append('Balance threshold has been set. As I monitor, I will note how the balance of teams compares to the threshold (if monitoring is possible).')
    else:
      message_parts.append('Balance threshold has not been set. I will monitor the balance (if monitoring is possible), but not against any particular warning threshold.')
    message = '\n'.join(message_parts)
    await self.interface.print(message)
    
  async def update_driver_irating(self, driver, print_unchanged=False):
    new_irating = await self.find_driver_irating(driver.id)
    if new_irating != driver.irating:
      await self.interface.print("The iRating of driver {0} has changed from {1} to {2}.".format(driver.name, driver.irating, new_irating))
      driver.irating = new_irating
      self.guild.save_driver(driver)
      return True
    elif print_unchanged:
      await self.interface.print("The iRating of driver {0} has not changed since the most recently cached update ({1}).".format(driver.name, driver.last_updated))
    return False
  
  async def update_quarter_number(self):
    self.quarter_number = await self.get_quarter_number()
    self.data_store_class.save_quarter_number(self.quarter_number)
    
  