""" Module to handle attributes related to the site location and details """

import re
import logging

from osg_configure.modules import utilities
from osg_configure.modules import configfile
from osg_configure.modules import validation
from osg_configure.modules.baseconfiguration import BaseConfiguration

__all__ = ['SiteInformation']

# convenience
MANDATORY = configfile.Option.MANDATORY
MANDATORY_ON_CE = configfile.Option.MANDATORY_ON_CE
OPTIONAL = configfile.Option.OPTIONAL

class SiteInformation(BaseConfiguration):
    """Class to handle attributes related to site information such as location and
    contact information
    """
    # The wlcg_* options are read by GIP directly
    IGNORE_OPTIONS = ['wlcg_tier', 'wlcg_parent', 'wlcg_name', 'wlcg_grid']

    def __init__(self, *args, **kwargs):
        # pylint: disable-msg=W0142
        super(SiteInformation, self).__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)
        self.log('SiteInformation.__init__ started')
        self.options = {'group':
                            configfile.Option(name='group',
                                              required=MANDATORY,
                                              default_value='OSG',
                                              mapping='OSG_GROUP'),
                        'host_name':
                            configfile.Option(name='host_name',
                                              required=MANDATORY_ON_CE,
                                              default_value='',
                                              mapping='OSG_HOSTNAME'),
                        'site_name':
                            configfile.Option(name='site_name',
                                              required=OPTIONAL,
                                              default_value='',
                                              mapping='OSG_SITE_NAME'),
                        'sponsor':
                            configfile.Option(name='sponsor',
                                              required=MANDATORY_ON_CE,
                                              mapping='OSG_SPONSOR'),
                        'site_policy':
                            configfile.Option(name='site_policy',
                                              required=OPTIONAL,
                                              default_value='',
                                              mapping='OSG_SITE_INFO'),
                        'contact':
                            configfile.Option(name='contact',
                                              required=MANDATORY_ON_CE,
                                              mapping='OSG_CONTACT_NAME'),
                        'email':
                            configfile.Option(name='email',
                                              required=MANDATORY_ON_CE,
                                              mapping='OSG_CONTACT_EMAIL'),
                        'city':
                            configfile.Option(name='city',
                                              required=MANDATORY_ON_CE,
                                              mapping='OSG_SITE_CITY'),
                        'country':
                            configfile.Option(name='country',
                                              required=MANDATORY_ON_CE,
                                              mapping='OSG_SITE_COUNTRY'),
                        'longitude':
                            configfile.Option(name='longitude',
                                              opt_type=float,
                                              required=MANDATORY_ON_CE,
                                              mapping='OSG_SITE_LONGITUDE'),
                        'latitude':
                            configfile.Option(name='latitude',
                                              opt_type=float,
                                              required=MANDATORY_ON_CE,
                                              mapping='OSG_SITE_LATITUDE'),
                        'resource':
                            configfile.Option(name='resource',
                                              required=OPTIONAL,
                                              default_value='',
                                              mapping='OSG_SITE_NAME'),
                        'resource_group':
                            configfile.Option(name='resource_group',
                                              default_value='',
                                              required=OPTIONAL)}

        self.config_section = "Site Information"
        self.enabled = True
        self.log('SiteInformation.__init__ completed')

    def parse_configuration(self, configuration):
        """Try to get configuration information from ConfigParser or SafeConfigParser object given
        by configuration and write recognized settings to attributes dict
        """
        self.log('SiteInformation.parse_configuration started')

        self.check_config(configuration)

        if not configuration.has_section(self.config_section):
            self.enabled = False
            self.log("%s section not in config file" % self.config_section)
            self.log('SiteInformation.parse_configuration completed')
            return

        self.get_options(configuration, ignore_options=self.IGNORE_OPTIONS)
        self.log('SiteInformation.parse_configuration completed')

    # pylint: disable-msg=W0613
    def check_attributes(self, attributes):
        """Check attributes currently stored and make sure that they are consistent"""
        self.log('SiteInformation.check_attributes started')
        attributes_ok = True

        if not self.enabled:
            self.log('Not enabled, returning True')
            self.log('SiteInformation.check_attributes completed')
            return attributes_ok

        # OSG_GROUP must be either OSG or OSG-ITB
        group = self.opt_val("group")
        if group not in ('OSG', 'OSG-ITB'):
            self.log("The group setting must be either OSG or OSG-ITB, got: %s" %
                     group,
                     option='group',
                     section=self.config_section,
                     level=logging.ERROR)
            attributes_ok = False

        host_name = self.opt_val("host_name")
        # host_name must be a valid dns name, check this by getting it's ip adddress
        if not utilities.blank(host_name) and not validation.valid_domain(host_name, True):
            self.log("hostname %s can't be resolved" % host_name,
                     option='host_name',
                     section=self.config_section,
                     level=logging.ERROR)
            attributes_ok = False

        if not utilities.blank(self.opt_val("site_name")):
            self.log("The site_name setting has been deprecated in favor of the"
                     " resource and resource_group settings and will be removed",
                     section=self.config_section,
                     option="site_name",
                     level=logging.WARNING)

        latitude = self.opt_val("latitude")
        if not utilities.blank(latitude) and not -90 < latitude < 90:
            self.log("Latitude must be between -90 and 90, got %s" %
                     latitude,
                     section=self.config_section,
                     option='latitude',
                     level=logging.ERROR)
            attributes_ok = False

        longitude = self.opt_val("longitude")
        if not utilities.blank(longitude) and not -180 < longitude < 180:
            self.log("Longitude must be between -180 and 180, got %s" %
                     longitude,
                     section=self.config_section,
                     option='longitude',
                     level=logging.ERROR)
            attributes_ok = False

        email = self.opt_val("email")
        # make sure the email address has the correct format
        if not utilities.blank(email) and not validation.valid_email(email):
            self.log("Invalid email address in site information: %s" %
                     email,
                     section=self.config_section,
                     option='email',
                     level=logging.ERROR)
            attributes_ok = False

        sponsor = self.opt_val("sponsor")
        if not utilities.blank(sponsor):
            attributes_ok &= self.check_sponsor(sponsor)

        self.log('SiteInformation.check_attributes completed')
        return attributes_ok

    def check_sponsor(self, sponsor):
        attributes_ok = True
        percentage = 0
        vo_names = utilities.get_vos(None)
        if vo_names == []:
            map_file_present = False
        else:
            map_file_present = True
        vo_names.append('usatlas')  # usatlas is a valid vo name
        vo_names.append('uscms')  # uscms is a valid vo name
        vo_names.append('local')  # local is a valid vo name

        cap_vo_names = [vo.upper() for vo in vo_names]
        for vo in re.split(r'\s*,?\s*', sponsor):
            vo_name = vo.split(':')[0]
            if vo_name not in vo_names:
                if vo_name.upper() in cap_vo_names:
                    self.log("VO name %s has the wrong capitialization" % vo_name,
                             section=self.config_section,
                             option='sponsor',
                             level=logging.WARNING)
                    vo_mesg = "Valid VO names are as follows:\n"
                    for name in vo_names:
                        vo_mesg += name + "\n"
                    self.log(vo_mesg, level=logging.WARNING)
                else:
                    if map_file_present:
                        self.log("In %s section, problem with sponsor setting" % \
                                 self.config_section)
                        self.log("VO name %s not found" % vo_name,
                                 section=self.config_section,
                                 option='sponsor',
                                 level=logging.ERROR)
                        vo_mesg = "Valid VO names are as follows:\n"
                        for name in vo_names:
                            vo_mesg += name + "\n"
                        self.log(vo_mesg, level=logging.ERROR)
                        attributes_ok = False
                    else:
                        self.log("Can't currently check VOs in sponsor setting because " +
                                 "the /var/lib/osg/user-vo-map is empty. If you are " +
                                 "configuring osg components, this may be resolved when " +
                                 "osg-configure runs the appropriate script to generate " +
                                 "this file later in the configuration process",
                                 section=self.config_section,
                                 option='sponsor',
                                 level=logging.WARNING)

            if len(vo.split(':')) == 1:
                percentage += 100
            elif len(vo.split(':')) == 2:
                vo_percentage = vo.split(':')[1]
                try:
                    percentage += int(vo_percentage)
                except ValueError:
                    self.log("VO percentage (%s) in sponsor field (%s) not an integer" \
                             % (vo_percentage, vo),
                             section=self.config_section,
                             option='sponsor',
                             level=logging.ERROR,
                             exception=True)
                    attributes_ok = False
            else:
                self.log("VO sponsor field is not formated correctly: %s" % vo,
                         section=self.config_section,
                         option='sponsor',
                         level=logging.ERROR)
                self.log("Sponsors should be given as sponsor:percentage "
                         "separated by a space or comma")

        if percentage != 100:
            self.log("VO percentages in sponsor field do not add up to 100, got %s" \
                     % percentage,
                     section=self.config_section,
                     option='sponsor',
                     level=logging.ERROR)
            attributes_ok = False

        return attributes_ok

    def module_name(self):
        """Return a string with the name of the module"""
        return "SiteInformation"

    def separately_configurable(self):
        """Return a boolean that indicates whether this module can be configured separately"""
        return True

    def get_attributes(self, converter=str):
        """
        Get attributes for the osg attributes file using the dict in self.options

        Returns a dictionary of ATTRIBUTE => value mappings

        Need to override parent class method since two options may map to OSG_SITE_NAME
        """

        self.log("%s.get_attributes started" % self.__class__)

        attributes = BaseConfiguration.get_attributes(self, converter)
        if attributes == {}:
            self.log("%s.get_attributes completed" % self.__class__)
            return attributes

        if ('OSG_SITE_NAME' in attributes and
                    self.options['resource'].value is not None and
                not utilities.blank(self.options['resource'].value)):
            attributes['OSG_SITE_NAME'] = self.options['resource'].value

        self.log("%s.get_attributes completed" % self.__class__)
        return attributes
