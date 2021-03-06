""" Exceptions used in configuration script """


class Error(Exception):
    """Base exception class for all exceptions defined"""
    pass


class SettingError(Error):
    """Class for exceptions due to missing setting or due to an invalid value for a setting"""
    pass


class ConfigureError(Error):
    """Class for exceptions due to problems while running vdt configure scripts"""
    pass
