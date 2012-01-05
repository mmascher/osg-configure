#!/usr/bin/env python

""" Module to handle attributes and configuration for RSV service """

import os, re, pwd, sys, shutil, ConfigParser, logging

from osg_configure.modules import exceptions
from osg_configure.modules import utilities
from osg_configure.modules import validation
from osg_configure.modules import configfile
from osg_configure.modules.configurationbase import BaseConfiguration

__all__ = ['RsvConfiguration']


class RsvConfiguration(BaseConfiguration):
  """Class to handle attributes and configuration related to osg-rsv services"""

  def __init__(self, *args, **kwargs):
    # pylint: disable-msg=W0142
    super(RsvConfiguration, self).__init__(*args, **kwargs)    
    self.log('RsvConfiguration.__init__ started')    
    self.options = {'enable_local_probes' : 
                      configfile.Option(name = 'enable_local_probes',
                                        required = configfile.Option.OPTIONAL,
                                        type = bool,
                                        default_value = True),
                    'gratia_probes' : 
                      configfile.Option(name = 'gratia_probes',
                                        default_value = '',
                                        required = configfile.Option.OPTIONAL),
                    'ce_hosts' : 
                      configfile.Option(name = 'ce_hosts',
                                        required = configfile.Option.OPTIONAL),
                    'gridftp_hosts' : 
                      configfile.Option(name = 'gridftp_hosts',
                                        required = configfile.Option.OPTIONAL),
                    'gridftp_dir' : 
                      configfile.Option(name = 'gridftp_dir',
                                        default_value = '/tmp'),
                    'gums_hosts' : 
                      configfile.Option(name = 'gums_hosts',
                                        required = configfile.Option.OPTIONAL),
                    'srm_hosts' : 
                      configfile.Option(name = 'srm_hosts',
                                        required = configfile.Option.OPTIONAL),
                    'srm_dir' : 
                      configfile.Option(name = 'srm_dir',
                                        required = configfile.Option.OPTIONAL),
                    'srm_webservice_path' : 
                      configfile.Option(name = 'srm_webservice_path',
                                        required = configfile.Option.OPTIONAL),
                    'service_cert' : 
                      configfile.Option(name = 'service_cert',
                                        required = configfile.Option.OPTIONAL,
                                        default_value = '/etc/grid-security/rsv/rsvcert.pem'),
                    'service_key' : 
                      configfile.Option(name = 'service_key',
                                        required = configfile.Option.OPTIONAL,
                                        default_value = '/etc/grid-security/rsv/rsvkey.pem'),
                    'service_proxy' : 
                      configfile.Option(name = 'service_proxy',
                                        required = configfile.Option.OPTIONAL,
                                        default_value = '/tmp/rsvproxy'),
                    'user_proxy' : 
                      configfile.Option(name = 'user_proxy',
                                        default_value = '',
                                        required = configfile.Option.OPTIONAL),
                    'enable_gratia' : 
                      configfile.Option(name = 'enable_gratia',
                                        type = bool),
                    'gratia_collector' : 
                      configfile.Option(name = 'gratia_collector',
                                        required = configfile.Option.OPTIONAL,
                                        default_value = 'rsv.grid.iu.edu:8880'),
                    'enable_nagios' : 
                      configfile.Option(name = 'enable_nagios',
                                        type = bool),
                    'nagios_send_nsca' : 
                      configfile.Option(name = 'nagios_send_nsca',
                                        required = configfile.Option.OPTIONAL,
                                        type = bool,
                                        default_value = False)}

    self.__rsv_user = "rsv"
    self.__ce_hosts = []
    self.__gridftp_hosts = []
    self.__gums_hosts = []
    self.__srm_hosts = []
    self.__gratia_probes_2d = []
    self.__gratia_metric_map = {}
    self.__enable_rsv_downloads = False
    self.__meta = ConfigParser.RawConfigParser()
    self.grid_group = 'OSG'
    self.site_name = 'Generic Site'
    self.config_section = "RSV"
    self.rsv_control = os.path.join('/', 'usr', 'bin', 'rsv-control')
    self.rsv_meta_dir = os.path.join('/', 'etc', 'rsv', 'meta', 'metrics')
    self.log('RsvConfiguration.__init__ completed')

  def parseConfiguration(self, configuration):
    """
    Try to get configuration information from ConfigParser or 
    SafeConfigParser object given by configuration and write recognized settings 
    to attributes dict
    """
    self.log('RsvConfiguration.parseConfiguration started')    

    self.checkConfig(configuration)

    if not configuration.has_section(self.config_section):
      self.enabled = False
      self.log("%s section not in config file" % self.config_section)    
      self.log('RsvConfiguration.parseConfiguration completed')    
      return True

    if not self.setStatus(configuration):
      self.log('RsvConfiguration.parseConfiguration completed')    
      return True

    for option in self.options.values():
      self.log("Getting value for %s" % option.name)
      configfile.get_option(configuration,
                            self.config_section, 
                            option)
      self.log("Got %s" % option.value)


    # If we're on a CE, get the grid group if possible
    if configuration.has_section('Site Information'): 
      if configuration.has_option('Site Information', 'group'):
        self.grid_group = configuration.get('Site Information', 'group')

      if configuration.has_option('Site Information', 'resource'):
        self.site_name = configuration.get('Site Information', 'resource')
      elif configuration.has_option('Site Information', 'site_name'):
        self.site_name = configuration.get('Site Information', 'site_name')


    # check and warn if unknown options found 
    temp = utilities.get_set_membership(configuration.options(self.config_section),
                                        self.options.keys(),
                                        configuration.defaults().keys())
    for option in temp:
      if option == 'enabled':
        continue
      self.log("Found unknown option",
               option = option, 
               section = self.config_section,
               level = logging.WARNING)


    # Parse lists
    self.__ce_hosts = split_list(self.options['ce_hosts'].value)
    self.__gums_hosts = split_list(self.options['gums_hosts'].value)
    self.__srm_hosts = split_list(self.options['srm_hosts'].value)

    # If the gridftp hosts are not defined then they default to the CE hosts
    if self.options['gridftp_hosts'].value is not None:
      self.__gridftp_hosts = split_list(self.options['gridftp_hosts'].value)
    else:
      self.__gridftp_hosts = self.__ce_hosts

    if self.options['gratia_probes'].value is not None:
      self.__gratia_probes_2d = self.split_2d_list(self.options['gratia_probes'].value)

    self.log('RsvConfiguration.parseConfiguration completed')    
  

# pylint: disable-msg=W0613
  def checkAttributes(self, attributes):
    """
    Check attributes currently stored and make sure that they are consistent
    """

    self.log('RsvConfiguration.checkAttributes started')
    attributes_ok = True

    if not self.enabled:
      self.log('Not enabled, returning True')
      self.log('RsvConfiguration.checkAttributes completed')    
      return attributes_ok

    if self.ignored:
      self.log('Ignored, returning True')
      self.log('RsvConfiguration.checkAttributes completed')    
      return attributes_ok

    # Slurp in all the meta files which will tell us what type of metrics
    # we have and if they are enabled by default.
    self.load_rsv_meta_files()

    attributes_ok &= self.__check_auth_settings()
    
    # check hosts
    attributes_ok &= self.__validate_host_list(self.__ce_hosts, "ce_hosts")
    attributes_ok &= self.__validate_host_list(self.__gums_hosts, "gums_hosts")
    attributes_ok &= self.__validate_host_list(self.__srm_hosts, "srm_hosts")
    attributes_ok &= self.__check_gridftp_settings()

    # check Gratia list
    attributes_ok &= self.__check_gratia_settings()

    self.log('RsvConfiguration.checkAttributes completed')    
    return attributes_ok 


  def configure(self, attributes):
    """Configure installation using attributes"""
    self.log('RsvConfiguration.configure started')    

    if self.ignored:
      self.logger.warning("%s configuration ignored" % self.config_section)
      self.log('RsvConfiguration.configure completed') 
      return True

    if not self.enabled:
      self.log('Not enabled, returning True')
      self.log('RsvConfiguration.configure completed') 
      return True

    # Reset always?
    if not self.__reset_configuration():
      return False

    # Put proxy information into rsv.ini
    if not self.__configure_cert_info():
      return False
    
    # Enable consumers
    if not self.__configure_consumers():
      return False

    # Enable metrics
    if not self.__configure_ce_metrics():
      return False

    if not self.__configure_gums_metrics():
      return False

    if not self.__configure_gridftp_metrics():
      return False

    if not self.__configure_gratia_metrics():
      return False

    if not self.__configure_local_metrics():
      return False

    if not self.__configure_srm_metrics():
      return False

    # Setup Apache?  I think this is done in the RPM

    # Fix the Gratia ProbeConfig file to point at the appropriate collector
    self.__set_gratia_collector(self.options['gratia_collector'].value)

    self.log('RsvConfiguration.configure completed')
    return True

  def moduleName(self):
    """Return a string with the name of the module"""
    return "RSV"

  def separatelyConfigurable(self):
    """Return a boolean that indicates whether this module can be configured separately"""
    return True  

  def parseSections(self):
    """Returns the sections from the configuration file that this module handles"""
    return [self.config_section]


  def __check_gridftp_settings(self):
    """ Check gridftp settings and make sure they are valid """
    status_check = self.__validate_host_list(self.__gridftp_hosts, "gridftp_hosts")

    if utilities.blank(self.options['gridftp_dir'].value):
      self.logger.error("In %s section" % self.config_section)
      self.logger.error("Invalid gridftp_dir given: %s" %
                        self.options['gridftp_dir'].value)
      status_check = False

    return status_check 

  def __check_auth_settings(self):
    """ Check authorization/certificate settings and make sure that they are valid """

    check_value = True

    # Do not allow both the service cert settings and proxy settings
    # first create some helper variables
    blank_service_vals = (utilities.blank(self.options['service_cert'].value) and
                          utilities.blank(self.options['service_key'].value) and
                          utilities.blank(self.options['service_proxy'].value))
    default_service_vals = (self.options['service_cert'].value == 
                            self.options['service_cert'].default_value)
    default_service_vals &= (self.options['service_key'].value == 
                             self.options['service_key'].default_value)
    default_service_vals &= (self.options['service_proxy'].value == 
                             self.options['service_proxy'].default_value)
    blank_user_proxy = utilities.blank(self.options['user_proxy'].value)
    if (not  blank_user_proxy and default_service_vals):
      self.logger.warning("In %s section" % self.config_section)
      self.logger.warning('User proxy specified and service_cert, service_key, service_proxy at default values, assuming user_proxy takes precedence')
    elif not (blank_user_proxy or (blank_service_vals or blank_service_vals)):
      self.logger.error("In %s section" % self.config_section)
      self.logger.error("You cannot specify user_proxy with any of (service_cert, service_key, service_proxy).  They are mutually exclusive options.")
      check_value = False
            

    # Make sure that either a service cert or user cert is selected
    if not ((self.options['service_cert'].value and
             self.options['service_key'].value and
             self.options['service_proxy'].value)
            or
            self.options['user_proxy'].value):
      self.logger.error("In %s section" % self.config_section)
      self.logger.error("You must specify either service_cert/service_key/service_proxy *or* user_proxy in order to provide credentials for RSV to run jobs")
      check_value = False

    if not blank_user_proxy:
      # if not using a service certificate, make sure that the proxy file exists
      value = self.options['user_proxy'].value
      if utilities.blank(value) or not validation.valid_file(value):
        self.logger.error("In %s section" % self.config_section)
        self.logger.error("user_proxy does not point to an existing file: %s" % value)
        check_value = False      
    else:
      value = self.options['service_cert'].value
      if utilities.blank(value) or not validation.valid_file(value):
        self.logger.error("In %s section" % self.config_section)
        self.logger.error("service_cert must point to an existing file: %s" % value)
        check_value = False

      value = self.options['service_key'].value
      if utilities.blank(value) or not validation.valid_file(value):
        self.logger.error("In %s section" % self.config_section)
        self.logger.error("service_key must point to an existing file: %s" % value)
        check_value = False

      value = self.options['service_proxy'].value
      if utilities.blank(value):
        self.logger.error("In %s section" % self.config_section)
        self.logger.error("service_proxy must have a valid location: %s" % value)
        check_value = False

      value = os.path.dirname(self.options['service_proxy'].value)
      if not validation.valid_location(value):
        self.logger.error("In %s section" % self.config_section)
        self.logger.error("service_proxy must be located in a valid directory: %s" % value)
        check_value = False

    return check_value


  def __reset_configuration(self):
    """ Reset all metrics and consumers to disabled """

    self.log("Resetting all metrics and consumers to disabled")

    parent_dir = os.path.join('/', 'etc', 'rsv')
    for file in os.listdir(parent_dir):
      if not re.search('\.conf$', file):
        continue

      if file == "rsv.conf" or file == "rsv-nagios.conf":
        continue

      path = os.path.join(parent_dir, file)
      self.log("Removing %s as part of reset" % path)
      os.unlink(path)

    # Remove any host specific metric configuration
    parent_dir = os.path.join('/', 'etc', 'rsv', 'metrics')
    for dir in os.listdir(parent_dir):
      path = os.path.join(parent_dir, dir)
      if not os.path.isdir(path):
        continue

      shutil.rmtree(path)
      
    return True    


  def __get_metrics_by_type(self, type, enabled=True):
    """ Examine meta info and return the metrics that are enabled by default for the defined type """

    metrics = []
    
    for metric in self.__meta.sections():
      if re.search(" env$", metric):
        continue

      if self.__meta.has_option(metric, "service-type"):
        if self.__meta.get(metric, "service-type") == type:
          if not enabled:
            metrics.append(metric)
          else:
            if self.__meta.has_option(metric, "enable-by-default"):
              if self.__meta.get(metric, "enable-by-default") == "true":
                metrics.append(metric)

    return metrics


  def __enable_metrics(self, host, metrics, args=[]):
    """ Given a host and array of metrics, enable them via rsv-control """

    if not metrics:
      return True

    if not utilities.run_script([self.rsv_control, "-v0", "--enable", "--host", host] + args + metrics):
      self.logger.error("ERROR: Attempt to enable metrics via rsv-control failed")
      self.logger.error("Host: %s" % host)
      self.logger.error("Metrics: %s" % " ".join(metrics))
      return False

    return True

  def __configure_ce_metrics(self):
    """
    Enable appropriate CE metrics
    """

    if not self.__ce_hosts:
      self.log("No ce_hosts defined.  Not configuring CE metrics")
      return True

    ce_metrics = self.__get_metrics_by_type("OSG-CE")

    for ce in self.__ce_hosts:
      self.log("Enabling CE metrics for host '%s'" % ce)
      if not self.__enable_metrics(ce, ce_metrics):
        return False

    return True


  def __configure_gridftp_metrics(self):
    """ Enable GridFTP metrics for each GridFTP host declared    """

    if not self.__gridftp_hosts:
      self.log("No gridftp_hosts defined.  Not configuring GridFTP metrics")
      return True

    gridftp_dirs = split_list(self.options['gridftp_dir'].value)
    if len(self.__gridftp_hosts) != len(gridftp_dirs) and len(gridftp_dirs) != 1:
      self.logger.error("RSV.gridftp_dir is set incorrectly.  When enabling GridFTP metrics you must specify either exactly 1 entry, or the same number of entries in the gridftp_dir variable as you have in the gridftp_hosts section.  There are %i host entries and %i gridftp_dir entries." % (len(self.__gridftp_hosts), len(gridftp_dirs)))
      raise exceptions.ConfigureError("Failed to configure RSV")

    gridftp_metrics = self.__get_metrics_by_type("OSG-GridFTP")

    count = 0
    for gridftp_host in self.__gridftp_hosts:
      self.log("Enabling GridFTP metrics for host '%s'" % gridftp_host)

      if len(gridftp_dirs) == 1:
        dir = gridftp_dirs[0]
      else:
        dir = gridftp_dirs[count]

      args = ["--arg", "destination-dir=%s" % dir]

      if not self.__enable_metrics(gridftp_host, gridftp_metrics, args):
        return False

      count += 1
             
    return True



  def __configure_gums_metrics(self):
    """ Enable GUMS metrics for each GUMS host declared """

    if not self.__gums_hosts:
      self.log("No gums_hosts defined.  Not configuring GUMS metrics")
      return True

    gums_metrics = self.__get_metrics_by_type("OSG-GUMS")

    if not gums_metrics:
      self.log("No current GUMS metrics.  No configuration to do at this time.")
      return True

    for gums_host in self.__gums_hosts:
      self.log("Enabling GUMS metrics for host '%s'" % gums_host)
      if not self.__enable_metrics(gums_host, gums_metrics):
        return False

    return True


  def __configure_local_metrics(self):
    """ Enable appropriate local metrics """

    if not self.options['enable_local_probes'].value:
      self.log("Local probes disabled.")
      return True

    local_metrics = self.__get_metrics_by_type("OSG-Local-Monitor")

    self.log("Enabling local metrics for host '%s'" % utilities.get_hostname())
    if not self.__enable_metrics(utilities.get_hostname(), local_metrics):
      return False
    
    return True


  def __configure_srm_metrics(self):
    """ Enable SRM metric """

    if not self.__srm_hosts:
      self.log("No srm_hosts defined.  Not configuring SRM metrics")
      return True

    # Do some checking on the values.  perhaps this should be in the validate section?
    srm_dirs = split_list(self.options['srm_dir'].value)
    if len(self.__srm_hosts) != len(srm_dirs):
      self.logger.error("When enabling SRM metrics you must specify the same number of entries in the srm_dir variable as you have in the srm_hosts section.  There are %i host entries and %i srm_dir entries." % (len(self.__srm_hosts), len(srm_dirs)))
      raise exceptions.ConfigureError("Failed to configure RSV")

    srm_ws_paths = []
    if not utilities.blank(self.options['srm_webservice_path'].value):
      srm_ws_paths = split_list(self.options['srm_webservice_path'].value)

      if len(self.__srm_hosts) != len(srm_ws_paths):
        self.logger.error("If you set srm_webservice_path when enabling SRM metrics you must specify the same number of entries in the srm_webservice_path variable as you have in the srm_hosts section.  There are %i host entries and %i srm_webservice_path entries." % (len(self.__srm_hosts), len(srm_ws_paths)))
        raise exceptions.ConfigureError("Failed to configure RSV")

    # Now time to do the actual configuration
    srm_metrics = self.__get_metrics_by_type("OSG-SRM")
    count = 0
    for srm_host in self.__srm_hosts:
      self.log("Enabling SRM metrics for host '%s'" % srm_host)

      args = ["--arg", "srm-destination-dir=%s" % srm_dirs[count]]
      if srm_ws_paths:
        args += ["--arg", "srm-webservice-path=%s" % srm_ws_paths[count]]

      if not self.__enable_metrics(srm_host, srm_metrics, args):
        return False

      count += 1
      
    return True


  def __map_gratia_metric(self, gratia_type):

    # The first time through we will populate the map.  It will be cached as a
    # data member in this class so that we don't have to do this each time
    if not self.__gratia_metric_map:
      ce_metrics = self.__get_metrics_by_type("OSG-CE", enabled=False)
      for metric in ce_metrics:
        match = re.search("\.gratia\.(\S+)$", metric)
        if match:
          self.__gratia_metric_map[match.group(1)] = metric
          self.log("Gratia map -> %s = %s" % (match.group(1), metric))

    # Now that we have the mapping, simply return the appropriate type.
    # This is the only code that should execute every time after the data structure is loaded.
    if gratia_type in self.__gratia_metric_map:
      return self.__gratia_metric_map[gratia_type]
    else:
      return None


  def __check_gratia_settings(self):
    """ Check to see if gratia settings are valid """

    tmp_2d = []

    # While checking the Gratia settings we will translate them to a list of
    # the actual probes to enable.
    status_check = True
    for list in self.__gratia_probes_2d:
      tmp = []
      for type in list:
        metric = self.__map_gratia_metric(type)
        if metric:
          tmp.append(metric)
        else:
          status_check = False
          err_mesg =  "In %s section, gratia_probes setting:" % self.config_section
          err_mesg += "Probe %s is not a valid probe, " % type
          self.logger.error(err_mesg)

      tmp_2d.append(tmp)

    self.__gratia_probes_2d = tmp_2d

    return status_check


  def __configure_gratia_metrics(self):
    """
    Enable Gratia metrics
    """

    if not self.__gratia_probes_2d:
      self.log("Skipping Gratia metric configuration because gratia_probes_2d is empty")
      return True

    if not self.__ce_hosts:
      self.log("Skipping Gratia metric configuration because ce_hosts is empty")
      return True

    num_ces = len(self.__ce_hosts)
    num_gratia = len(self.__gratia_probes_2d)
    if num_ces != num_gratia and num_gratia != 1:
      self.logger.error("The number of CE hosts does not match the number of Gratia host definitions")
      self.logger.error("Number of CE hosts: %s" % num_ces)
      self.logger.error("Number of Gratia host definitions: %2" % num_gratia)
      self.logger.error("They must match, or you must have only one Gratia host definition (which will be used for all hosts")
      return False

    i = 0
    for ce in self.__ce_hosts:
      gratia = None

      # There will either be a Gratia definition for each host, or else a single Gratia
      # definition which we will use across all hosts.
      if num_gratia == 1:
        gratia = self.__gratia_probes_2d[0]
      else:
        gratia = self.__gratia_probes_2d[i]
        i += 1

      if not self.__enable_metrics(ce, gratia):
        return False

    return True
  
      
  def __validate_host_list(self, hosts, setting):
    """ Validate a list of hosts """
    ret = True
    for host in hosts:
      # Strip off the port
      if ':' in host:
        (hostname, port) = host.split(':')
      else:
        hostname = host
        port = False
      if not validation.valid_domain(hostname):
        self.logger.error("Invalid domain in [%s].%s: %s" % (self.config_section, setting, host))
        ret = False

      if port and re.search('\D', port):
        self.logger.error("Invalid port in [%s].%s: %s" % (self.config_section, setting, host))

    return ret


  def __configure_cert_info(self):
    """ Configure certificate information """

    # Load in the existing configuration file
    config_file = os.path.join('/', 'etc', 'rsv', 'rsv.conf')
    config = ConfigParser.RawConfigParser()
    config.optionxform = str

    if os.path.exists(config_file):
      config.read(config_file)

    if not config.has_section('rsv'):
      config.add_section('rsv')

    # Set the appropriate options in the rsv.conf file
    if self.options['service_cert'].value:
      config.set('rsv', 'service-cert', self.options['service_cert'].value)
      config.set('rsv', 'service-key', self.options['service_key'].value)
      config.set('rsv', 'service-proxy', self.options['service_proxy'].value)
    elif self.options['user_proxy'].value:
      config.set('rsv', 'proxy-file', self.options['user_proxy'].value)

      # Remove these keys or they will override the proxy-file setting in rsv-control
      config.remove_option('rsv', 'service-cert')
      config.remove_option('rsv', 'service-key')
      config.remove_option('rsv', 'service-proxy')

    # Write back to disk
    config_fp = open(config_file, 'w')
    config.write(config_fp)
    config_fp.close()

    return True


  def __configure_consumers(self):
    """ Enable the appropriate consumers """

    # The current logic is:
    #  - we ALWAYS want the html-consumer if we are told to install consumers
    #  - we want the gratia-consumer if enable_gratia is True
    #  - we want the nagios-consumer if enable_nagios is True

    consumers = ["html-consumer"]

    if self.options['enable_gratia'].value:
      consumers.append("gratia-consumer")
      # TODO - set up Gratia directories?  Look at setup_gratia() in configure_rsv

    if self.options['enable_nagios'].value:
      consumers.append("nagios-consumer")
      self.__configure_nagios_files()

    consumer_list = " ".join(consumers)
    self.log("Enabling consumers: %s " % consumer_list)

    if utilities.run_script([self.rsv_control, "-v0", "--enable"] + consumers):
      return True
    else:
      return False


  def __configure_nagios_files(self):
    """ Store the nagios configuration """

    # The Nagios conf file contains a password so set it to mode 0400 owned by rsv
    pw_file = os.path.join('/', 'etc', 'rsv', 'rsv-nagios.conf')
    (uid,gid) = pwd.getpwnam(self.__rsv_user)[2:4]
    os.chown(pw_file, uid, gid)
    os.chmod(pw_file, 0400)
    
    # Add the configuration file 
    nagios_conf_file = os.path.join('/', 'etc', 'rsv', 'consumers', 'nagios-consumer.conf')
    config = ConfigParser.RawConfigParser()
    config.optionxform = str
    
    if os.path.exists(nagios_conf_file):
      config.read(nagios_conf_file)
      
    if not config.has_section('nagios-consumer'):
      config.add_section('nagios-consumer')

    args = "--conf-file %s" % pw_file
    if self.options['nagios_send_nsca'].value:
      args += " --send-nsca"

    config.set("nagios-consumer", "args", args)
    
    config_fp = open(nagios_conf_file, 'w')
    config.write(config_fp)
    config_fp.close()

    return


  def load_rsv_meta_files(self):
    """ All the RSV meta files are in INI format.  Pull them in so that we know what
    metrics to enable """

    if not os.path.exists(self.rsv_meta_dir):
      self.logger.warning("In RSV configuration, meta dir (%s) does not exist." % self.rsv_meta_dir)
      return
      
    files = os.listdir(self.rsv_meta_dir)

    for file in files:
      if re.search('\.meta$', file):
        self.__meta.read(os.path.join(self.rsv_meta_dir, file))

    return

  def split_2d_list(self, list):
    """ 
    Split a comma/whitespace separated list of list of items.
    Each list needs to be enclosed in parentheses and separated by whitespace and/or a comma.
    Parentheses are optional if only one list is supplied.
    
    Valid examples include:
    (1,2,3),(4,5)
    1,2,3,4,5
    (1,2), (4) , (5,6)  (8),    # comma at end is ok, comma between lists is optional

    Invalid examples:
    (1,2,3), 4    # 4 needs to be in parentheses
    1,2,3, (4,5)  # 1,2,3 needs to be parenthesized
    (1,2, (3, 4)  # missing a right parenthesis
    """

    if not list:
      return [[]]
          
    original_list = list

    # If there are no parentheses then just treat this like a normal comma-separated list
    # and return it as a 2-D array (with only one element in one direction)
    if not re.search("\(", list) and not re.search("\)", list):
      return [split_list(list)]

    # We want to grab parenthesized chunks
    pattern = re.compile("\s*\(([^()]+)\)\s*,?")
    array = []
    while 1:
      match = re.match(pattern, list)
      if not match:
        # If we don't have a match then we are either finished processing, or there is
        # a syntax error.  So if we have anything left in the string we will bail
        if re.search("\S", list):
          self.logger.error("ERROR: syntax error in parenthesized list")
          self.logger.error("ERROR: Supplied list:\n\t%s" % original_list)
          self.logger.error("ERROR: Leftover after parsing:\n\t%s" % list)
          return False
        else:
          return array

      array.append(split_list(match.group(1)))
    
      # Remove what we just matched so that we get the next chunk on the next iteration
      match_length = len(match.group(0))
      list = list[match_length:]

    # We shouldn't reach here, but just in case...
    return array


  def __set_gratia_collector(self, collector):
    """ Put the appropriate collector URL into the ProbeConfig file """

    if not self.options['enable_gratia'].value:
      self.log("Not configuring Gratia collector because enable_gratia is not true")
      return True

    probe_conf = os.path.join('/', 'etc', 'gratia', 'metric', 'ProbeConfig')

    self.log("Putting collector '%s' into Gratia conf file '%s'" % (collector, probe_conf))

    conf = open(probe_conf).read()

    conf = re.sub("CollectorHost=\".+\"", "CollectorHost=\"%s\"" % collector, conf)
    conf = re.sub("SSLHost=\".+\"", "SSLHost=\"%s\"" % collector, conf)
    conf = re.sub("SSLRegistrationHost=\".+\"", "SSLRegistrationHost=\"%s\"" % collector, conf)
    conf = re.sub(r'(\s*)EnableProbe\s*=.*', r'\1EnableProbe="1"', conf, 1)
    conf = re.sub(r'(\s*)Grid\s*=.*', r'\1Grid="' + self.grid_group + '"', conf, 1)
    conf = re.sub(r'(\s*)SiteName\s*=.*', r'\1SiteName="' + self.site_name + '"', conf, 1)

    if not utilities.atomic_write(probe_conf, conf):
      self.logger.error("Error while configuring metric probe: can't write to %s" % probe_file)
      raise exceptions.ConfigureError("Error configuring gratia")

    return True


def split_list(list):
  """ Split a comma separated list of items """

  # Special case - when the list just contains UNAVAILABLE we want to ignore it
  if utilities.blank(list):
    return []
  
  items = []
  for entry in list.split(','):
    items.append(entry.strip())
    
  return items

