""" Module to handle attributes related to the site location and details """

import logging

from osg_configure.modules import configfile
from osg_configure.modules import validation
from osg_configure.modules.baseconfiguration import BaseConfiguration

__all__ = ['InstallLocations']


class InstallLocations(BaseConfiguration):
    """Class to handle attributes related to installation locations"""

    def __init__(self, *args, **kwargs):
        # pylint: disable-msg=W0142
        super(InstallLocations, self).__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)
        self.log('InstallLocations.configure started')
        self.options = {'globus':
                            configfile.Option(name='globus',
                                              default_value='/usr',
                                              required=configfile.Option.OPTIONAL,
                                              mapping='GLOBUS_LOCATION'),
                        'user_vo_map':
                            configfile.Option(name='user_vo_map',
                                              default_value='/var/lib/osg/user-vo-map',
                                              required=configfile.Option.OPTIONAL),
                        'gridftp_log':
                            configfile.Option(name='gridftp_log',
                                              default_value='/var/log/gridftp.log',
                                              required=configfile.Option.OPTIONAL)}
        self.config_section = 'Install Locations'
        self._self_configured = False
        self.log('InstallLocations.configure completed')

    def parse_configuration(self, configuration):
        """Try to get configuration information from ConfigParser or SafeConfigParser object given
        by configuration and write recognized settings to attributes dict
        """
        self.log('InstallLocations.parse_configuration started')

        self.check_config(configuration)

        if not configuration.has_section(self.config_section):
            self.log('Install Locations section not found in config file')
            self.log('Automatically configuring')
            self._auto_configure()
            self.log('InstallLocations.parse_configuration completed')
            self._self_configured = True
            self.enabled = True
            return
        else:
            self.log("Install Locations section found and will be used to " +
                     "configure your resource, however, this section is not " +
                     "needed for typical resources and can be deleted from " +
                     "your config file",
                     level=logging.WARNING)

        self.enabled = True
        self.get_options(configuration)
        self.log('InstallLocations.parse_configuration completed')

    # pylint: disable-msg=W0613
    def check_attributes(self, attributes):
        """Check attributes currently stored and make sure that they are consistent"""
        self.log('InstallLocations.check_attributes started')
        attributes_ok = True

        if self._self_configured:
            return True

        # make sure locations exist
        for option in self.options.values():
            if option.name == 'user_vo_map':
                # skip the user vo map check since we'll create it later if it doesn't
                # exist
                continue
            if not validation.valid_location(option.value):
                attributes_ok = False
                self.log("Invalid location: %s" % option.value,
                         option=option.name,
                         section=self.config_section,
                         level=logging.ERROR)

        self.log('InstallLocations.check_attributes completed')
        return attributes_ok

    def configure(self, attributes):
        """
        Setup basic osg/vdt services
        """

        self.log("InstallLocations.configure started")
        status = True

        self.log("InstallLocations.configure completed")
        return status

    def module_name(self):
        """Return a string with the name of the module"""
        return "InstallLocations"

    def separately_configurable(self):
        """Return a boolean that indicates whether this module can be configured separately"""
        return True

    def _auto_configure(self):
        """
        Configure settings for Install Locations based on defaults
        """
        self.log("InstallLocations._auto_configure started")
        for option in self.options.values():
            self.log("Setting value for %s" % option.name)
            option.value = option.default_value
        self.log("InstallLocations._auto_configure completed")
