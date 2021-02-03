class DriverCollection:
  def __eq__(self, other):
    if not type(self) is type(other):
      return False
    return self.driver_sets == other.driver_sets
  
  def __hash__(self):
    return hash(tuple(self.ordered_driver_sets()))
    
  def __init__(self):
    self.driver_sets = set()
  
  def add_driver_set(self, driver_set):
    for driver in driver_set.drivers:
      if self.has_driver(driver):
        raise KeyError("Team set already includes driver {0}".format(driver.name))
    self.driver_sets.add(driver_set)
    
  def copy(collection):
    new = DriverCollection()
    for driver_set in collection.driver_sets:
      new.add_driver_set(driver_set)
    return new
  
  def drivers(self):
    return sum([list(driver_set.drivers) for driver_set in self.driver_sets], []) # flatten
  
  def has_driver(self, driver):
    return driver in self.drivers()
  
  def irating_gap(self):
    if not self.driver_sets:
      return 0
    averages = [driver_set.average_irating() for driver_set in self.driver_sets]
    return max(averages) - min(averages)
  
  def ordered_driver_sets(self):
    ordered = list(self.driver_sets)
    ordered.sort(key=lambda driver_set: driver_set.highest_irating())
    return ordered
    
  def remove_driver_set(self, driver_set):
    self.driver_sets.remove(driver_set)
  
  def size(self):
    return len(self.driver_sets)