import unittest

from balancebot.driver     import Driver
from balancebot.driver_set import DriverSet

class TestEquality(unittest.TestCase):
  def test_equality_for_driver_sets_containing_same_drivers(self):
    driver1 = Driver(9135924, 'Samuel Korhonen', 1889)
    driver2 = Driver(7540813, 'Aleksi Karjalainen', 1309)
    driver3 = Driver(9009975, 'Otto Lahtinen', 488)
    
    set1 = DriverSet()
    set1.add_driver(driver1)
    set1.add_driver(driver2)
    set1.add_driver(driver3)
    set2 = DriverSet()
    set2.add_driver(driver1)
    set2.add_driver(driver2)
    set2.add_driver(driver3)
    
    self.assertEqual(set1, set2,
    "Driver sets with same drivers added in same order should pass equality test")
  
  def test_equality_for_driver_sets_containing_same_drivers_added_in_different_order(self):
    driver1 = Driver(7132829, 'Juuso Lehtonen', 417)
    driver2 = Driver(3091787, 'Antti Koskinen', 2836)
    driver3 = Driver(2344484, 'Jaakko Niemi', 2196)
    
    set1 = DriverSet()
    set1.add_driver(driver1)
    set1.add_driver(driver2)
    set1.add_driver(driver3)
    set2 = DriverSet()
    set2.add_driver(driver3)
    set2.add_driver(driver2)
    set2.add_driver(driver1)
    
    self.assertEqual(set1, set2,
    "Driver sets with same drivers added in different order should pass equality test")
  
  def test_equality_for_driver_sets_containing_different_drivers(self):
    driver1 = Driver(3591356, 'Teemu Love', 1002)
    driver2 = Driver(1648538, 'Jami Heinonen', 1687)
    driver3 = Driver(2848445, 'Miika Saarinen', 1015)

    set1 = DriverSet()
    set1.add_driver(driver1)
    set1.add_driver(driver2)
    set2 = DriverSet()
    set2.add_driver(driver2)
    set2.add_driver(driver3)
    
    self.assertNotEqual(set1, set2,
    "Driver sets with different drivers should not pass equality test even if they share drivers")
    
  def test_equality_for_driver_sets_subsets(self):
    driver1 = Driver(8274655, 'Joni Tuominen', 1723)
    driver2 = Driver(7614363, 'Mikael Turunen', 1806)
    driver3 = Driver(6560730, 'Matias Savolainen', 1116)
    
    set1 = DriverSet()
    set1.add_driver(driver1)
    set1.add_driver(driver2)
    set1.add_driver(driver3)
    set2 = DriverSet()
    set2.add_driver(driver1)
    set2.add_driver(driver3)
    
    self.assertNotEqual(set1, set2)
    self.assertNotEqual(set2, set1,
    "Driver sets should not pass equality test when one is a strict subset of the other")

class TestSize(unittest.TestCase):
  def test_size(self):
    set = DriverSet()
    self.assertEqual(set.size(), 0, 
    "Empty set should have size 0")
    
    set.add_driver(Driver(4110533, 'Lauri Ahonen', 347))
    self.assertEqual(set.size(), 1,
    "Set with one driver added should have size 1")
    
    set.add_driver(Driver(3394063, 'Nikke Karjalainen', 699))
    self.assertEqual(set.size(), 2,
    "Set with a second driver added should have size 2")

class TestAddition(unittest.TestCase):
  def test_adding_the_same_driver_twice_does_not_increase_size(self):
    set = DriverSet()
    driver = Driver(5901753, 'Sergei Virtanen', 1003)
    set.add_driver(driver)
    self.assertEqual(set.size(), 1)
    
    set.add_driver(driver)
    self.assertEqual(set.size(), 1,
    "Adding the same driver multiple times should only increase size once")

class TestRemoval(unittest.TestCase):
  def test_removal(self):
    set = DriverSet()
    driver = Driver(4848446, 'Liinus Koskinen', 461)
    set.add_driver(driver)
    self.assertEqual(set.size(), 1)
    self.assertTrue(set.has_driver(driver))

    set.remove_driver(driver)
    self.assertEqual(set.size(), 0)
    self.assertFalse(set.has_driver(driver),
    "set.remove_driver should remove driver")
    
  def test_removal_of_not_existing(self):
    set = DriverSet()
    driver1 = Driver(7281438, 'Arvi Salminen', 2934)
    driver2 = Driver(8309914, 'Akseli Jokinen', 1565)
    set.add_driver(driver1)
    self.assertEqual(set.size(), 1)

    set.remove_driver(driver2)
    self.assertEqual(set.size(), 1,
    "Attempting to remove a driver from a set not contained in that set does not alter the set size")

class TestUpdatingOutdatedElements(unittest.TestCase):
  def test_with_updated_driver(self):
    set = DriverSet()
    driver1 = Driver(9995638, 'Christian Rantanen', 2803) 
    driver2 = Driver(3152024, 'Topias Laine', 532)
    driver3 = Driver(7186265, 'Petteri Mattila', 1632)
    set.add_driver(driver1)
    set.add_driver(driver2)
    set.add_driver(driver3)
    
    driver3_updated = Driver(7186265, 'Petteri Mattila', 1933)
    new_set = set.with_updated_driver(driver3_updated)
    
    self.assertFalse(set is new_set,
    "The result of with_updated_driver should be a different object")
    self.assertEqual(set, new_set,
    "The result of with_updated_driver should be an equal set")
    self.assertEqual(Driver.find(set.drivers, driver3.id).irating, driver3.irating,
    "Old set should not be affected by with_updated_driver procedure")
    self.assertEqual(Driver.find(new_set.drivers, driver3.id).irating, driver3_updated.irating,
    "New set should have updated copy of driver")

class TestSorting(unittest.TestCase):
  def test_ordered_drivers(self):
    set = DriverSet()
    driver1 = Driver(5306133, 'Anni Haapala', 2829)
    driver2 = Driver(1861639, 'Veera Eskola', 1190)
    driver3 = Driver(1583942, 'Roosa Lahti', 1209)
    set.add_driver(driver1)
    set.add_driver(driver2)
    set.add_driver(driver3)
    
    ordered = set.ordered_drivers()
    self.assertTrue(isinstance(ordered, list),
    "Set.ordered_drivers() should return a list")
    self.assertEqual(len(ordered), set.size(),
    "ordered_drivers() should return a list of the same length as the set cardinality")
    self.assertEqual(ordered[0], driver1,
    "First element of ordered_drivers() should be highest iRating driver")
    self.assertEqual(ordered[2], driver2,
    "Last element of ordered_drivers() should be the lowest iRating driver")
    self.assertEqual(ordered[1], driver3,
    "ordered_drivers() should contain all drivers from the original set")
  
  def test_highest_irating(self):
    set = DriverSet()
    driver1 = Driver(1755478, 'Elina Laakso', 375)
    driver2 = Driver(5879949, 'Jenna Seppanen', 2395)
    driver3 = Driver(7231171, 'Pinja Toivonen', 2335)
    set.add_driver(driver1)
    set.add_driver(driver2)
    set.add_driver(driver3)
    
    self.assertEqual(set.highest_irating(), driver2.irating,
    "highest_irating() should return the iRating of the driver with the highest iRating")

class TestAveraging(unittest.TestCase):
  def test_average_irating(self):
    set = DriverSet()
    set.add_driver(Driver(8468530, 'Sonja Karjala', 1500))
    set.add_driver(Driver(6407800, 'Juuli Kumpula', 2000))
    set.add_driver(Driver(7124841, 'Ansku Nieminen', 2500))
    
    self.assertEqual(set.average_irating(), 2000,
    "average_irating() should average the iRatings of the drivers in the set")
    self.assertTrue(isinstance(set.average_irating(), float),
    "average_irating() should return a float even if the answer is a whole number")