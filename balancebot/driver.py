from datetime import datetime as dt

class Driver:
  DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
  
  def __eq__(self, other):
    if not type(self) is type(other):
      return False
    return self.id == other.id
  
  def __hash__(self):
    return hash(self.id)

  def __init__(self, id, name, irating, last_updated=dt.today()):
    self.id = int(id)
    self.name = name
    self.irating = int(irating)
    self.last_updated = last_updated
    
  def __repr__(self):
    return "<Driver id:{0} name:{1} irating:{2} last_updated{3}>".format(self.id, self.name, self.irating, self.last_updated)
  
  def find(drivers, driver_id):
    for driver in drivers:
      if driver.id == int(driver_id):
        return driver
    return None
  
  def find_by_name(drivers, driver_name):
    for driver in drivers:
      if driver.name == driver_name:
        return driver
    return None
    
  def print_format(self):
    return '{0} (iRacing ID {1}), road iRating {2} (last updated {3})'.format(self.name, self.id, self.irating, self.last_updated)