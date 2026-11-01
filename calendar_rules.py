"""Price-free conditional calendar; 2010 dates only in this public snapshot."""
from datetime import date,datetime
from zoneinfo import ZoneInfo
HOLIDAYS={2010:"01-01 01-18 02-15 04-02 05-31 07-05 09-06 11-25 12-24"}
NY=ZoneInfo("America/New_York")
def planned_open(day):
    if not isinstance(day, date) or isinstance(day, datetime) or day.year not in HOLIDAYS:
        raise ValueError('Only date objects within frozen 2010-2015 development are allowed')
    return day.weekday() < 5 and day.strftime('%m-%d') not in HOLIDAYS[day.year].split()
