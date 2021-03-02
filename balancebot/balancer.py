import copy

from balancebot.driver_set        import DriverSet
from balancebot.driver_collection import DriverCollection

class Balancer:
  def __init__(self, drivers, team_sizes, combinations):
    if isinstance(drivers, DriverSet):
      self.drivers = list(drivers.drivers)
    elif isinstance(drivers, set):
      self.drivers = list(drivers)
    else:
      self.drivers = drivers
    self.driver_count = len(self.drivers)
    self.team_sizes = team_sizes
    self.combinations = combinations
    
    self.best_collection = None
    self.best_collection_gap = None
  
  def optimal_balance(self):
    for size_pattern in Balancer.possible_size_patterns(self.driver_count, self.team_sizes):
      base_collection = DriverCollection()
      self.search_possible_collections(base_collection, self.drivers, size_pattern)
    return self.best_collection
    
  def search_possible_collections(self, current_collection, remaining_drivers, remaining_size_pattern):
    team_size = remaining_size_pattern[0]
    for driver_set in Balancer.unique_driver_sets(remaining_drivers, team_size):
      if Balancer.driver_set_respects_combinations(driver_set, self.combinations):
        new_collection = current_collection.copy()
        new_collection.add_driver_set(driver_set)
        new_size_pattern = remaining_size_pattern[1:]
        if len(new_size_pattern) == 0:
          if self.best_collection_gap == None or new_collection.irating_gap() < self.best_collection_gap:
            self.best_collection = new_collection
            self.best_collection_gap = new_collection.irating_gap()
          return
        new_remaining_drivers = [driver for driver in remaining_drivers if not driver_set.has_driver(driver)]
        self.search_possible_collections(new_collection, new_remaining_drivers, new_size_pattern)
  
  
  def possible_size_patterns(driver_count, team_sizes):
    patterns = []
    # Find the maximum number of driver_sets. Note // for floor division
    max_size = (driver_count // min(team_sizes)) + 1
    # Arrange the driver_set sizes into all possible combinations of length <= max size.
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
    patterns = list(filter(lambda l: sum(l) == driver_count, patterns))
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
    return unique_patterns
  
  def is_team_formation_possible(driver_count, team_sizes):
    return len(Balancer.possible_size_patterns(driver_count, team_sizes)) > 0
        
  def driver_set_respects_combinations(driver_set, combinations):
    for combination in combinations.driver_sets:
      included = [driver in driver_set.drivers for driver in combination.drivers]
      if any(included) and not all(included):
        return False
    return True
  
  def unique_driver_sets(drivers, size):
    if size == 1:
      driver_sets = []
      for driver in drivers:
        driver_set = DriverSet()
        driver_set.add_driver(driver)
        driver_sets.append(driver_set)
      return driver_sets
    driver_sets = []
    # Maintain uniqueness by keeping the elements in the grouping in order with the original elements.
    # Find the elements which could come first in the grouping.
    # In general, if there are n elements, and a grouping of size m is needed, only the first (n - m + 1) could come first.
    stop_index = len(drivers) - size + 1
    possible_firsts = drivers[0:stop_index]
    for driver in possible_firsts:
      # If this element is selected first, find the elements that could go next *while maintaining order*.
      remaining_drivers = drivers[drivers.index(driver) + 1:]
      for driver_set in Balancer.unique_driver_sets(remaining_drivers, size - 1):
        driver_set.add_driver(driver)
        driver_sets.append(driver_set)
    return driver_sets