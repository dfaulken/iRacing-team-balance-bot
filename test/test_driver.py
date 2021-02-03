import unittest

from balancebot.driver import Driver

class TestEquality(unittest.TestCase):
  def test_equality_for_exact_matching_data(self):
    driver1 = Driver(4831980, 'Jessica Smith', 858)
    driver2 = Driver(4831980, 'Jessica Smith', 858)
    self.assertEqual(driver1, driver2,
    "Drivers with exactly matching data should pass equality test")
    
  def test_equality_without_irating_matching(self):
    driver1 = Driver(4833703, 'Lauren Johnson', 2572)
    driver2 = Driver(4833703, 'Lauren Johnson', 1739)
    self.assertEqual(driver1, driver2,
    "Drivers with different iRatings should pass equality test")
  
  def test_equality_without_name_matching(self):
    driver1 = Driver(6390762, 'Emily Moore', 1972)
    driver2 = Driver(6390762, 'Ashley Davis', 1972)
    self.assertEqual(driver1, driver2,
    "Drivers with different names should pass equality test")
  
  def test_equality_without_id_matching(self):
    driver1 = Driver(5946747, 'Samantha Brown', 1078)
    driver2 = Driver(7292705, 'Samantha Brown', 1078)
    self.assertNotEqual(driver1, driver2,
    "Drivers with different IDs should not pass equality test")
    
class TestFindMethods(unittest.TestCase):
  def test_find_driver_from_collection_by_id(self):
    drivers = []
    drivers.append(Driver(3659239, 'Megan Williams', 958))
    target = Driver(1383412, 'Sadie Jones', 781)
    drivers.append(target)
    drivers.append(Driver(1272222, 'Rachel Wilson', 1011))
    self.assertEqual(Driver.find(drivers, 1383412), target,
    "Driver.find should find driver by ID")
  
  def test_find_driver_from_collection_by_id_with_other_data_matching(self):
    drivers = []
    drivers.append(Driver(9599241, 'Nicole Martin', 1178))
    drivers.append(Driver(5181551, 'Nicole Martin', 1178))
    target = Driver(3567345, 'Nicole Martin', 1178)
    drivers.append(target)
    self.assertEqual(Driver.find(drivers, 3567345), target,
    "Driver.find should find driver by ID even when other driver data is shared between multiple drivers")
  
  def test_find_driver_from_collection_by_name(self):
    drivers = []
    target = Driver(2854863, 'Elizabeth Martinez', 414)
    drivers.append(target)
    drivers.append(Driver(1524853, 'Kayla White', 2767))
    drivers.append(Driver(2532633, 'Laura Jackson', 961))
    self.assertEqual(Driver.find_by_name(drivers, 'Elizabeth Martinez'), target,
    "Driver.find_by_name should find driver by name")
  
  def test_find_driver_from_collection_by_name_with_other_data_matching(self):
    drivers = []
    target = Driver(7653542, 'Danielle Smith', 1650)
    drivers.append(target)
    drivers.append(Driver(7653542, 'Alexandra Davis', 1650))
    drivers.append(Driver(7653542, 'Stephanie Johnson', 1650))
    self.assertEqual(Driver.find_by_name(drivers, 'Danielle Smith').name, target.name,
    "Driver.find_by_name should find driver by name even when other driver data is shared between multiple drivers")
    # Note using name here to match since equality on ID means they will all be equal - this would be a false positive