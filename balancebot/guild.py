from balancebot.driver_set        import DriverSet
from balancebot.driver_collection import DriverCollection

class Guild:
  def __init__(self, id, data_store):
    self._id         = id
    self.name       = None
    self._data_store = data_store
    
    self._drivers          = data_store.load_drivers()
    self.balance           = data_store.load_balance(self._drivers)
    self.balance_threshold = data_store.load_balance_threshold()
    self.combinations      = data_store.load_combinations(self._drivers)
    self.monitoring_data   = data_store.load_monitoring_data()
    self.team_sizes        = data_store.load_team_sizes()
    self.teams             = data_store.load_teams(self._drivers)
  
  def add_combinations(self, combinations):
    for combination in combinations.driver_sets:
      self.combinations.add_driver_set(combination)
    self._data_store.save_combinations(self.combinations)
  
  def add_driver(self, driver):
    # TODO clear balance
    # TODO what should happen to teams?
    self._drivers.add_driver(driver)
    self._data_store.save_drivers(self._drivers)
  
  def clear_balance(self):
    self.balance = DriverCollection()
    self._data_store.save_balance(self.balance)
    
  def clear_combinations(self):
    self.combinations = DriverCollection()
    self._data_store.save_combinations(self.combinations)
  
  def clear_drivers(self):
    self.clear_balance()
    self.clear_combinations()
    self.clear_teams()
    self._drivers = DriverSet()
    self._data_store.save_drivers(self._drivers)
  
  def clear_teams(self):
    self.teams = DriverCollection()
    self._data_store.save_teams(self.teams)
  
  def driver_count(self):
    return self._drivers.size()
  
  def get_drivers(self):
    return self._drivers.drivers
  
  def has_drivers(self):
    return self.driver_count() > 0
    
  def remove_combinations(self, combinations):
    for combination in combinations:
      self.combinations.remove_driver_set(combination)
    self._data_store.save_combinations(self.combinations)
  
  def remove_driver(self, driver):
    if self.teams:
      self.clear_teams()
    if self.balance:
      self.clear_balance()
    combinations_to_remove = []
    for combination in self.combinations.driver_sets:
      if combination.has_driver(driver):
        combinations_to_remove.append(combination)
    self.remove_combinations(combinations_to_remove)
    self._drivers.remove_driver(driver)
    self._data_store.save_drivers(self._drivers)
  
  # TODO maybe update_driver?
  def save_driver(self, driver):
    self._drivers = self._drivers.with_updated_driver(driver)
    self._data_store.save_drivers(self._drivers)
  
  def set_balance(self, balance):
    self.balance = balance
    self._data_store.save_balance(self.balance)
    
  def set_balance_threshold(self, balance_threshold):
    self.balance_threshold = balance_threshold
    self._data_store.save_balance_threshold(self.balance_threshold)
  
  def set_channel_id(self, channel_id):
    self.channel_id = channel_id
    self._data_store.save_channel_id(channel_id)
  
  def set_monitoring_data(self, data):
    self.monitoring_data = data
    self._data_store.save_monitoring_data(data)
  
  def set_name(self, name):
    self.name = name
  
  def set_team_sizes(self, team_sizes):
    self.team_sizes = team_sizes
    self._data_store.save_team_sizes(team_sizes)
  
  def set_teams(self, teams):
    self.teams = teams
    self._data_store.save_teams(self.teams)