from balancebot.driver import Driver

class DriverSet:
  def __eq__(self, other):
    if not type(self) is type(other):
      return False
    if not self.size() == other.size():
      return False
    matches = [other.has_driver(driver) for driver in self.drivers]
    return all(matches)
  
  def __hash__(self):
    return hash(tuple(self.ordered_drivers()))

  def __init__(self):
    self.drivers = set()
    
  def add_driver(self, driver):
    self.drivers.add(driver)
  
  def average_irating(self):
    if self.size() == 0:
      return None
    return sum([driver.irating for driver in self.drivers], 0) / self.size()
  
  def has_driver(self, driver):
    return driver.id in [team_driver.id for team_driver in self.drivers]
  
  def highest_irating(self):
    return max([driver.irating for driver in self.drivers])
    
  def ordered_drivers(self):
    ordered = list(self.drivers)
    ordered.sort(key=lambda driver: driver.irating, reverse=True)
    return ordered
  
  def remove_driver(self, driver):
    self.drivers.discard(driver)
  
  def size(self):
    return len(self.drivers)
  
  # Returns a copy of self with `driver` in place of its matching outdated record in self.
  def with_updated_driver(self, new_driver):
    updated = DriverSet()
    for driver in self.drivers:
      if driver == new_driver:
        updated.add_driver(new_driver)
      else:
        updated.add_driver(driver)
    return updated