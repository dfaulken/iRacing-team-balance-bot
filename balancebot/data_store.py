from datetime import datetime as dt
from enum import Enum
import json
import logging
import os
import pathlib

from balancebot.driver            import Driver
from balancebot.driver_set        import DriverSet
from balancebot.driver_collection import DriverCollection

DATA_DIRECTORY = 'data'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
FILE_EXT = '.json'

class FileName(Enum):
  balance           = 'balance'
  balance_threshold = 'balance_threshold'
  combinations      = 'combinations'
  drivers           = 'drivers'
  monitoring_data   = 'monitoring_data'
  quarter_number    = 'quarter_number'
  team_sizes        = 'team_sizes'
  teams             = 'teams'

class DataStore:
  def __init__(self, guild_id):
    self.guild_id = guild_id
    
    self.balance_file           = self.guild_file_path(FileName.balance.value)
    self.balance_threshold_file = self.guild_file_path(FileName.balance_threshold.value)
    self.combinations_file      = self.guild_file_path(FileName.combinations.value)
    self.drivers_file           = self.guild_file_path(FileName.drivers.value)
    self.monitoring_data_file   = self.guild_file_path(FileName.monitoring_data.value)
    self.team_sizes_file        = self.guild_file_path(FileName.team_sizes.value)
    self.teams_file             = self.guild_file_path(FileName.teams.value)
    
    if not self.is_data_initialized():
      self.initialize_data()
  
  def data_subdirectory_numbers():
    return [int(file.name) for file in os.scandir(DATA_DIRECTORY) if file.is_dir()]
  
  def guild_dir_path(self):
    return os.path.join(DATA_DIRECTORY, str(self.guild_id))
  
  def guild_file_path(self, file_name):
    return os.path.join(self.guild_dir_path(), file_name + FILE_EXT)
  
  def is_data_initialized(self):
    return os.path.isdir(self.guild_dir_path())
  
  def initialize_data(self):
    pathlib.Path(self.guild_dir_path()).mkdir()
    self.save_balance(DriverCollection())
    self.save_balance_threshold(None)
    self.save_monitoring_data({})
    self.save_combinations(DriverCollection())
    self.save_drivers(DriverSet())
    self.save_team_sizes([])
    self.save_driver_sets(DriverCollection())
    
  # Data access methods below sorted by data type rather than name of method.
  
  def load_balance(self, driver_set):
    return DataStore.load_driver_collection(self.balance_file, driver_set)
  
  def save_balance(self, balance):
    DataStore.save_driver_collection(self.balance_file, balance)
    
  def load_balance_threshold(self):
    return DataStore.json_load_simple_key(self.balance_threshold_file, FileName.balance_threshold.value)
  
  def save_balance_threshold(self, balance_threshold):
    DataStore.json_write_simple_key(self.balance_threshold_file, FileName.balance_threshold.value, balance_threshold)
    
  def load_combinations(self, driver_set):
    return DataStore.load_driver_collection(self.combinations_file, driver_set)
  
  def save_combinations(self, combinations):
    DataStore.save_driver_collection(self.combinations_file, combinations)
  
  def load_drivers(self):
    data = DataStore.json_load_file(self.drivers_file, {})
    drivers = DriverSet()
    for id, attrs in data.items():
      name, irating, last_updated_str = attrs
      last_updated = dt.strptime(last_updated_str, DATETIME_FORMAT)
      drivers.add_driver(Driver(id, name, irating, last_updated=last_updated))
    return drivers
  
  def save_drivers(self, driver_set):
    data = {}
    for driver in driver_set.drivers:
      last_updated_str = dt.strftime(driver.last_updated, DATETIME_FORMAT)
      data[driver.id] = [driver.name, driver.irating, last_updated_str]
    DataStore.json_write_file(self.drivers_file, data) 
    
  def load_monitoring_data(self):
    return DataStore.json_load_file(self.monitoring_data_file, {})
  
  def save_monitoring_data(self, data):
    DataStore.json_write_file(self.monitoring_data_file, data)
  
  def load_team_sizes(self):
    return DataStore.json_load_simple_key(self.team_sizes_file, FileName.team_sizes.value)
    
  def save_team_sizes(self, team_sizes):
    return DataStore.json_write_simple_key(self.team_sizes_file, FileName.team_sizes.value, team_sizes)
  
  def load_teams(self, driver_set):
    return DataStore.load_driver_collection(self.teams_file, driver_set)
  
  def save_teams(self, driver_sets):
    DataStore.save_driver_collection(self.teams_file, driver_sets)
  
  def global_file_path(file_name):
    return os.path.join(DATA_DIRECTORY, file_name + FILE_EXT)
  
  def json_load_file(filename, fallback):
    if not os.path.isfile(filename):
      return fallback
    try:
      with open(filename, 'r') as file:
        return json.load(file)
    except json.JSONDecodeError:
      logging.warning('Error parsing JSON file.')
      return fallback
      
  def json_load_simple_key(filename, key):
    data = DataStore.json_load_file(filename, {})
    value = data.get(key)
    return value
  
  def json_write_file(filename, data):
    with open(filename, 'w') as file:
      json.dump(data, file)
  
  def json_write_simple_key(filename, key, value):
    DataStore.json_write_file(filename, {key: value})
  
  def load_driver_collection(filename, driver_set):
    driver_collection = DriverCollection()
    data = DataStore.json_load_file(filename, [])
    for driver_set_driver_ids in data:
      set = DriverSet()
      for driver_id in driver_set_driver_ids:
        driver = Driver.find(driver_set.drivers, driver_id)
        if driver:
          set.add_driver(driver)
      driver_collection.add_driver_set(set)
    return driver_collection
  
  def save_driver_collection(filename, driver_collection):
    data = [[driver.id for driver in driver_set.drivers] for driver_set in driver_collection.driver_sets]
    DataStore.json_write_file(filename, data)
  
  def load_quarter_number():
    file_path = DataStore.global_file_path(FileName.quarter_number.value)
    return DataStore.json_load_simple_key(file_path, FileName.quarter_number.value)
    
  def save_quarter_number(quarter_number):
    file_path = DataStore.global_file_path(FileName.quarter_number.value)
    return DataStore.json_write_simple_key(file_path, FileName.quarter_number.value, quarter_number)