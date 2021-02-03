import unittest

from balancebot.driver            import Driver
from balancebot.driver_set        import DriverSet
from balancebot.driver_collection import DriverCollection

class TestEquality(unittest.TestCase):
  def test_equality_for_same_drivers_arranged_into_same_sets(self):
    driver1 = Driver(9875796, 'Gerhard Schneider', 1545)
    driver2 = Driver(6001789, 'Hans Richter', 2152)
    driver3 = Driver(2247084, 'Andreas Hartmann', 610)
    driver4 = Driver(2565069, 'Martin Köhler', 930)
    set1 = DriverSet()
    set1.add_driver(driver1)
    set1.add_driver(driver2)
    set2 = DriverSet()
    set2.add_driver(driver3)
    set2.add_driver(driver4)
    set3 = DriverSet()
    set3.add_driver(driver1)
    set3.add_driver(driver2)
    set4 = DriverSet()
    set4.add_driver(driver3)
    set4.add_driver(driver4)
    coll1 = DriverCollection()
    coll1.add_driver_set(set1)
    coll1.add_driver_set(set2)
    coll2 = DriverCollection()
    coll2.add_driver_set(set3)
    coll2.add_driver_set(set4)
    
    self.assertEqual(coll1, coll2,
    "DriverCollections with the same drivers arranged into the same sets should be equal")
    
  def test_equality_for_same_drivers_arranged_into_different_sets(self):
    driver1 = Driver(3818591, 'Friedrich Weber', 652) 
    driver2 = Driver(3980541, 'Karl Wagner', 1223)
    driver3 = Driver(8367833, 'Jürgen Schmitt', 1452)
    driver4 = Driver(9705677, 'Sebastian Kðnig', 2240)
    set1 = DriverSet()
    set1.add_driver(driver1)
    set1.add_driver(driver2)
    set2 = DriverSet()
    set2.add_driver(driver3)
    set2.add_driver(driver4)
    coll1 = DriverCollection()
    coll1.add_driver_set(set1)
    coll1.add_driver_set(set2)
    set3 = DriverSet()
    set3.add_driver(driver1)
    set3.add_driver(driver3)
    set4 = DriverSet()
    set4.add_driver(driver2)
    set4.add_driver(driver4)
    coll2 = DriverCollection()
    coll2.add_driver_set(set3)
    coll2.add_driver_set(set4)

class TestAddition(unittest.TestCase):
  def addition_fails_for_drivers_present_in_another_set(self):
    driver1 = Driver(3818591, 'Heinz Bauer', 323)
    driver2 = Driver(3980541, 'Klaus Lange', 997)
    driver3 = Driver(8367833, 'Stefan Huber', 2467)
    set1 = DriverSet()
    set1.add_driver(driver1)
    set1.add_driver(driver2)
    set2 = DriverSet()
    set2.add_driver(driver3)
    set2.add_driver(driver1) # repeated
    coll = DriverCollection()
    coll.add_driver_set(set1)
    
    self.assertRaises(coll.add_driver_set(set2), KeyError,
    "Adding a set containing a driver already contained in the collection's set(s) should raise a KeyError")

class TestRemoval(unittest.TestCase):
  def removal_works_as_expected(self):
    driver1 = Driver(9694609, 'Kurt Schulze', 2726)
    driver2 = Driver(5234104, 'Jonas Schäfer', 2709)
    set1 = DriverSet()
    set1.add_driver(driver1)
    set1.add_driver(driver2)
    coll = DriverCollection()
    coll.add_driver_set(set1)
    self.assertEqual(coll.size(), 1)
    
    set2 = DriverSet()
    set2.add_driver(driver1)
    set2.add_driver(driver2)
    coll.remove_driver_set(set2)
    self.assertEqual(coll.size(), 0,
    "remove_driver_set() should work on equality, not object equality")
  
  def remove_on_a_set_not_contained_does_nothing(self):
    driver1 = Driver(8869106, 'Hermann Schmitz', 1598)
    driver2 = Driver(6708923, 'Frank Lehmann', 1616)
    driver3 = Driver(4449968, 'Jannik Fuchs', 1034)
    set1 = DriverSet()
    set1.add_driver(driver1)
    set1.add_driver(driver2)
    set2 = DriverSet()
    set2.add_driver(driver1)
    set2.add_driver(driver3) # different
    coll = DriverCollection()
    coll.add_driver_set(set1)
    self.assertEqual(coll.size(), 1)
    
    coll.remove_driver_set(set2)
    self.assertEqual(coll.size(), 1,
    "Removing a DriverSet not contained in the DriverCollection does nothing")

class TestCopying(unittest.TestCase):
  pass # TODO

class TestSorting(unittest.TestCase):
  pass # TODO

class TestArithmetic(unittest.TestCase):
  pass # TODO