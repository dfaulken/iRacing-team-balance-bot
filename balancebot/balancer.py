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
  
    self._driver_collections = []
  
  def filter_driver_collections_by_combinations(self):
    matching_sets = copy.copy(self._driver_collections)
    for combination in self.combinations.driver_sets:
      sets_matching_combination = []
      for driver_collection in matching_sets:
          if Balancer.driver_collection_respects_combination(driver_collection, combination):
            sets_matching_combination.append(driver_collection)
      matching_sets = sets_matching_combination
    self._driver_collections = matching_sets
  
  def lowest_irating_gap_driver_collection(self):
    self._driver_collections.sort(key=lambda driver_collection: driver_collection.irating_gap())
    return self._driver_collections[0]
  
  def optimal_balance(self):
    self.populate_possible_driver_collections()
    if self.combinations:
      self.filter_driver_collections_by_combinations()
    return self.lowest_irating_gap_driver_collection()
    
  def populate_possible_driver_collections(self):
    # Find the possible (unique) ways to break down the number of drivers into driver_sets of the allowed size.
    for size_pattern in Balancer.possible_size_patterns(self.driver_count, self.team_sizes):
      # Find the possible ways to assign drivers to the first driver_set in the pattern.
      pattern_sets = []
      for driver_set in Balancer.unique_driver_sets(self.drivers, size_pattern[0]):
        driver_collection = DriverCollection()
        driver_collection.add_driver_set(driver_set)
        pattern_sets.append(driver_collection)
      # For the next driver_set, expand each existing possibility for the first n driver_sets into a suite of sets for how to assign some of the remaining drivers into the first n + 1 driver_sets.
      for team_size in size_pattern[1:]:
        next_level_pattern_sets = []
        for driver_collection in pattern_sets:
          remaining_drivers = [driver for driver in self.drivers if not driver_collection.has_driver(driver)]
          driver_sets = Balancer.unique_driver_sets(remaining_drivers, team_size)
          for driver_set in Balancer.unique_driver_sets(remaining_drivers, team_size):
            new_collection = DriverCollection.copy(driver_collection)
            new_collection.add_driver_set(driver_set)
            next_level_pattern_sets.append(new_collection)
        pattern_sets = next_level_pattern_sets
      self._driver_collections += pattern_sets
  
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
  
  # TODO this might belong in driver_collection since it's entirely about driver_collections
  def driver_collection_respects_combination(driver_collection, combination):
    for driver_set in driver_collection.driver_sets:
      included = [driver in driver_set.drivers for driver in combination.drivers]
      if all(included):
        return True
    return False
  
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