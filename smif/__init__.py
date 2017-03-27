#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

"""
from __future__ import division, print_function, absolute_import

import pkg_resources

__author__ = "Will Usher"
__copyright__ = "Will Usher"
__license__ = "mit"


try:
    __version__ = pkg_resources.get_distribution(__name__).version
except:
    __version__ = 'unknown'


class SpaceTimeValue(object):
    """A tuple of scenario data

    Parameters
    ----------
    region: str
        A valid (unique) region name which is registered in the region register
    interval: str
        A valid (unique) interval name which is registered in the interval
        register
    value: float
        The value
    units: str
        The units associated with the `value`
    """
    def __init__(self, region, interval, value, units):
        self.region = region
        self.interval = interval
        self.value = value
        self.units = units

    def __repr__(self):
        return "SpaceTimeValue({}, {}, {}, {})".format(
            repr(self.region),
            repr(self.interval),
            repr(self.value),
            repr(self.units)
        )

    def __add__(self, other):
        if other.region != self.region:
            raise ValueError("Cannot add SpaceTimeValue of differing region")
        if other.interval != self.interval:
            raise ValueError("Cannot add SpaceTimeValue of differing interval")
        if other.units != self.units:
            raise ValueError("Cannot add SpaceTimeValue of differing units")

        return SpaceTimeValue(
            self.region,
            self.interval,
            self.value + other.value,
            self.units)

    def __eq__(self, other):
        return self.region == other.region and \
               self.interval == other.interval and \
               self.value == other.value and \
               self.units == other.units
