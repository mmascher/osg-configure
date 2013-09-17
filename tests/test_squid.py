"""Unit tests to test squid configuration"""

#pylint: disable=W0703
#pylint: disable=R0904

import os
import sys
import unittest
import ConfigParser
import logging

# setup system library path
pathname = os.path.realpath('../')
sys.path.insert(0, pathname)

from osg_configure.modules import exceptions
from osg_configure.configure_modules import squid
from osg_configure.modules.utilities import get_test_config
from osg_configure.modules.utilities import ce_installed

global_logger = logging.getLogger(__name__)
if sys.version_info[0] >= 2 and sys.version_info[1] > 6:
  global_logger.addHandler(logging.NullHandler())
else:
  # NullHandler is only in python 2.7 and above
  class NullHandler(logging.Handler):
    def emit(self, record):
      pass
            
  global_logger.addHandler(NullHandler())

class TestSquid(unittest.TestCase):
  """
  Unit test class to test SquidConfiguration class
  """

  def testParsing1(self):
    """
    Test squid parsing
    """
    
    config_file = get_test_config("squid/squid1.ini")
    configuration = ConfigParser.SafeConfigParser()
    configuration.read(config_file)

    settings = squid.SquidConfiguration(logger=global_logger)
    try:
      settings.parseConfiguration(configuration)
    except Exception, e:
      self.fail("Received exception while parsing configuration: %s" % e)
 

    attributes = settings.getAttributes()
    variables = {'OSG_SQUID_LOCATION' : "test.com:3128",
                 'OSG_SQUID_POLICY' : 'LRU',
                 'OSG_SQUID_CACHE_SIZE' : '2048',
                 'OSG_SQUID_MEM_CACHE' : '256'}
    for var in variables:      
      self.assertTrue(attributes.has_key(var), 
                      "Attribute %s missing" % var)
      self.assertEqual(attributes[var], 
                       variables[var], 
                       "Wrong value obtained for %s, got %s but " \
                       "expected %s" % (var, attributes[var], variables[var]))
        
  def testParsing2(self):
    """
    Test squid parsing
    """
    
    config_file = get_test_config("squid/squid2.ini")
    configuration = ConfigParser.SafeConfigParser()
    configuration.read(config_file)

    settings = squid.SquidConfiguration(logger=global_logger)
    try:
      settings.parseConfiguration(configuration)
    except Exception, e:
      self.fail("Received exception while parsing configuration: %s" % e)
 

    attributes = settings.getAttributes()
    variables = {'OSG_SQUID_LOCATION' : 'example.com:3128',
                 'OSG_SQUID_POLICY' : 'LRU',
                 'OSG_SQUID_CACHE_SIZE' : '2048',
                 'OSG_SQUID_MEM_CACHE' : '256'}
    for var in variables:      
      self.assertTrue(attributes.has_key(var), 
                      "Attribute %s missing" % var)
      self.assertEqual(attributes[var], 
                       variables[var], 
                       "Wrong value obtained for %s, got %s but " \
                       "expected %s" % (var, attributes[var], variables[var]))
    
  def testParsingDisabled(self):
    """
    Test parsing when disabled
    """
    
    config_file = get_test_config("squid/squid_disabled.ini")
    configuration = ConfigParser.SafeConfigParser()
    configuration.read(config_file)

    settings = squid.SquidConfiguration(logger=global_logger)
    try:
      settings.parseConfiguration(configuration)
    except Exception, e:
      self.fail("Received exception while parsing configuration: %s" % e)
 

    attributes = settings.getAttributes()
    self.assertEqual(len(attributes), 0, 
                     "Disabled configuration should have 0 attributes")
    
    self.assertEqual(attributes, 
                     {}, 
                     "Error attributes from squid configuration " +
                     "not empty when disabled")
                                                            
  def testParsingIgnored(self):
    """
    Test parsing when ignored
    """
    
    config_file = get_test_config("squid/ignored.ini")
    configuration = ConfigParser.SafeConfigParser()
    configuration.read(config_file)

    settings = squid.SquidConfiguration(logger=global_logger)
    try:
      settings.parseConfiguration(configuration)
    except Exception, e:
      self.fail("Received exception while parsing configuration: %s" % e)
 

    attributes = settings.getAttributes()
    self.assertEqual(len(attributes), 4, 
                     "Ignored configuration should have 4 attributes")
    
    variables = {'OSG_SQUID_LOCATION' : 'test.com:3128',
                 'OSG_SQUID_POLICY' : 'LRU',
                 'OSG_SQUID_CACHE_SIZE' : '2048',
                 'OSG_SQUID_MEM_CACHE' : '256'}
    for var in variables:      
      self.assertTrue(attributes.has_key(var), 
                      "Attribute %s missing" % var)
      self.assertEqual(attributes[var], 
                       variables[var], 
                       "Wrong value obtained for %s, got %s but " \
                       "expected %s" % (var, attributes[var], variables[var]))


  def testMissingAttribute(self):
    """
    Test the parsing when attributes are missing, should get exceptions
    """
        

    mandatory = ['location']
    for option in mandatory:
      config_file = get_test_config("squid/squid1.ini")
      configuration = ConfigParser.SafeConfigParser()
      configuration.read(config_file)
      configuration.remove_option('Squid', option)

      settings = squid.SquidConfiguration(logger=global_logger)
      self.assertRaises(exceptions.SettingError, 
                        settings.parseConfiguration, 
                        configuration)


  def testBadMemory(self):
    """
    Test the checkAttributes function when memory size is not an integer
    """
    
    if not ce_installed():
      return True
    config_file = get_test_config("squid/squid_bad_mem.ini")
    configuration = ConfigParser.SafeConfigParser()
    configuration.read(config_file)

    settings = squid.SquidConfiguration(logger=global_logger)
    self.assertRaises(exceptions.SettingError,
                      settings.parseConfiguration,
                      configuration)
    
  def testBadCache(self):
    """
    Test the checkAttributes function when cache size is not an integer
    """
        
    if not ce_installed():
      return True
    config_file = get_test_config("squid/squid_bad_cache.ini")
    configuration = ConfigParser.SafeConfigParser()
    configuration.read(config_file)

    settings = squid.SquidConfiguration(logger=global_logger)
    self.assertRaises(exceptions.SettingError,
                      settings.parseConfiguration,
                      configuration)


  def testBadHost(self):
    """
    Test the checkAttributes function when the squid proxy hostname is
    not valie
    """
        
    if not ce_installed():
      return True
    config_file = get_test_config("squid/squid_bad_host.ini")
    configuration = ConfigParser.SafeConfigParser()
    configuration.read(config_file)

    settings = squid.SquidConfiguration(logger=global_logger)
    try:
      settings.parseConfiguration(configuration)
    except Exception, e:
      self.fail("Received exception while parsing configuration: %s" % e)

    attributes = settings.getAttributes()
    self.assertFalse(settings.checkAttributes(attributes), 
                     "Did not notice invalid host")

    config_file = get_test_config("squid/squid_bad_host2.ini")
    configuration = ConfigParser.SafeConfigParser()
    configuration.read(config_file)

    settings = squid.SquidConfiguration(logger=global_logger)
    try:
      settings.parseConfiguration(configuration)
    except Exception, e:
      self.fail("Received exception while parsing configuration")

    attributes = settings.getAttributes()
    self.assertFalse(settings.checkAttributes(attributes), 
                     "Did not notice invalid host")

  def testBadPort(self):
    """
    Test the checkAttributes function when port for the squid proxy is 
    not an integer
    """
        
    if not ce_installed():
      return True
    config_file = get_test_config("squid/squid_bad_port.ini")
    configuration = ConfigParser.SafeConfigParser()
    configuration.read(config_file)

    settings = squid.SquidConfiguration(logger=global_logger)
    try:
      settings.parseConfiguration(configuration)
    except Exception, e:
      self.fail("Received exception while parsing configuration: %s" % e)

    attributes = settings.getAttributes()
    self.assertFalse(settings.checkAttributes(attributes), 
                     "Did not notice invalid port number")

  def testValidSettings(self):
    """
    Test the checkAttributes function to see if it oks good attributes
    """

    if not ce_installed():
      return True
    config_file = get_test_config("squid/valid_settings.ini")
    configuration = ConfigParser.SafeConfigParser()
    configuration.read(config_file)

    settings = squid.SquidConfiguration(logger=global_logger)
    try:
      settings.parseConfiguration(configuration)
    except Exception, e:
      self.fail("Received exception while parsing configuration: %s" % e)
 
    attributes = settings.getAttributes()
    self.assertTrue(settings.checkAttributes(attributes), 
                    "Correct locations incorrectly flagged as missing")

  def testDisabled(self):
    """
    Test the checkAttributes function to see if it indicates that a disabled 
    section has an error
    """
        
    config_file = get_test_config("squid/squid_disabled.ini")
    configuration = ConfigParser.SafeConfigParser()
    configuration.read(config_file)

    settings = squid.SquidConfiguration(logger=global_logger)
    try:
      settings.parseConfiguration(configuration)
    except Exception, e:
      self.fail("Received exception while parsing configuration: %s" % e)
 
    attributes = settings.getAttributes()
    self.assertTrue(settings.checkAttributes(attributes), 
                     "Disabled squid flagged as good")

  def testBlankLocation(self):
    """
    Test the checkAttributes function to see if it raises an error when
    location is left blank
    """

    if not ce_installed():
      return True
    config_file = get_test_config("squid/squid_blank_location.ini")
    configuration = ConfigParser.SafeConfigParser()
    configuration.read(config_file)

    settings = squid.SquidConfiguration(logger=global_logger)
    try:
      settings.parseConfiguration(configuration)
    except Exception, e:
      self.fail("Received exception while parsing configuration: %s" % e)
 
    attributes = settings.getAttributes()
    self.assertTrue(settings.checkAttributes(attributes), 
                     "Blank location flagged as bad")

  def testLocationUnavailable(self):
    """
    Test the checkAttributes function to see if it oks a section
    where location is set to UNAVAILABLE
    """
        
    config_file = get_test_config("squid/squid_unavailable.ini")
    configuration = ConfigParser.SafeConfigParser()
    configuration.read(config_file)

    settings = squid.SquidConfiguration(logger=global_logger)
    try:
      settings.parseConfiguration(configuration)
    except Exception, e:
      self.fail("Received exception while parsing configuration: %s" % e)
 
    attributes = settings.getAttributes()
    self.assertTrue(settings.checkAttributes(attributes), 
                    "location set to UNAVAIALBLE flagged as bad")
    
if __name__ == '__main__':
  console = logging.StreamHandler()
  console.setLevel(logging.ERROR)
  global_logger.addHandler(console)
  unittest.main()
