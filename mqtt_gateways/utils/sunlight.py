'''
Function to calculate sunrise and sunset times out of date and latitude.

Based on the paper:
Predicting Sunrise and Sunset Times
Donald A. Teets (donald.teets@sdsmt.edu),
South Dakota School of Mines and Technology,
Rapid City, SD 57701
'''

import math
import datetime
import pytz

# Constants--------------------

# Inclination in radians
epsilon = 0.409
sinE = math.sin(epsilon)
# Earth radius in km
R = 6378.0
# Earth to Sun distance in km
r = 149598000.0
# Relative radius
Rrel = R/r
# Adjustment for size of sun in sky, in minutes
Adjust = 5.0
# Numbers used often
Factor1 = 2.0*math.pi/365.25
Factor2 = 1440.0/(2.0*math.pi)

class Sunlight(object):
    ''' Class to calculate sunrise and sunset times.

    As a quite a few calculations rely on parameters that will not change much
    like latitude, it is better to define a class with a location data (latitude
    and time-zone) and then call a method to compute the sunset and sunrise
    for that location on a given date.

    Args:
        latitude (float): latitude of the observer in degrees.
        zone (string): time zone identifier as defined in https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
    '''
    def __init__(self, latitude, zone=None):
        self.ready = False
        lat_r = math.radians(latitude)
        self.sinL = math.sin(lat_r)
        self.cosL = math.cos(lat_r)
        if zone is None: zone = 'Etc/UTC'
        self.tzone = pytz.timezone(zone)
        anyday = datetime.datetime(2010, 6, 1)
        self.tzone_offset = self.tzone.utcoffset(anyday)-self.tzone.dst(anyday)

    def _calc(self, d):
        ''' Performs the *raw* calculation, no date library involved

        Args:
            d (int): day number within year (e.g. 2Jan is 2, 1Feb is 32)

        Returns:
            pair of int: the sunrise and sunset time in minutes after midnight
        '''
        theta = (d - 80.0) * Factor1
        coef = math.sin(theta) * sinE
        n = 720.0 - (10.0 * math.sin((d-80.0) * 2.0 * Factor1)) + (8.0 * math.sin(d * Factor1))
        t0 = Factor2 * math.acos((Rrel-(coef*self.sinL))/(math.sqrt(1.0 - (coef * coef)) * self.cosL))
        sunrise_min = int(round(n - (t0 + Adjust))) # sunrise in minutes after midnight
        sunset_min = int(round(n + (t0 + Adjust))) # sunset in minutes after midnight
        return sunrise_min, sunset_min

    def day(self, date=None):
        ''' Calculate the sunrise and sunset times in a given day

        Args:
            date (datetime.date): calculate the sunset and sunrise for this date

        Returns:
            datetime.datetime: sunrise and sunset date and time, adjusted for time zone
        '''
        if date is None: date = datetime.date.today()
        # test if date is a date object?
        sunrise, sunset = self._calc(date.timetuple().tm_yday) # sunrise and sunset are minutes (int)
        sunrise_delta = datetime.timedelta(minutes=sunrise) - self.tzone_offset
        sunset_delta = datetime.timedelta(minutes=sunset) - self.tzone_offset
        sunrise_date = pytz.utc.localize(datetime.datetime.combine(date, datetime.time(0, 0, 0)) + sunrise_delta)
        sunset_date = pytz.utc.localize(datetime.datetime.combine(date, datetime.time(0, 0, 0)) + sunset_delta)
        return sunrise_date.astimezone(self.tzone), sunset_date.astimezone(self.tzone)

# latitudes in degrees
LondonLAT = 51.5
NewYorkCityLAT = 40.44

# timezones
LondonTZ = 'Europe/London'
EasternTZ = 'US/Eastern'
UTCTZ = 'Etc/UTC'

if __name__ == '__main__':
    obj = Sunlight(LondonLAT, LondonTZ)
    srise, sset = obj.day()
    print 'sunrise and sunset today: ', srise.ctime(), sset.ctime()
    srise, sset = obj.day(datetime.date(2018, 6, 1))
    print 'another date: ', srise.ctime(), sset.ctime()
