# -----------------------------------------------------------------------------
# Getting Things GNOME! - a personal organizer for the GNOME desktop
# Copyright (c) 2008-2013 - Lionel Dricot & Bertrand Rousseau
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------

""" General class for representing dates in GTG.

Dates Could be normal like 2012-04-01 or fuzzy like now, soon,
someday, later or no date.

Date.parse() parses all possible representations of a datetime.date. """

import calendar
import locale
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from gettext import gettext as _
from gettext import ngettext

__all__ = ['Date', 'Accuracy']

# trick to obtain the timezone of the machine GTG is executed on
LOCAL_TIMEZONE = datetime.now(timezone.utc).astimezone().tzinfo
NOW, SOON, SOMEDAY, NODATE = list(range(4))

# Localized strings for fuzzy values
STRINGS = {
    # Translators: Used for display
    NOW: _('now'),
    # Translators: Used for display
    SOON: _('soon'),
    # Translators: Used for display
    SOMEDAY: _('someday'),
    NODATE: '',
}

# Allows looking up any value which is not a date but points towards one and
# find one of the four constant for fuzzy dates: SOON, SOMEDAY, and NODATE
LOOKUP = {
    NOW: NOW,
    'now': NOW,
    # Translators: Used in parsing, made lowercased in code
    _('now'): NOW,
    SOON: SOON,
    'soon': SOON,
    # Translators: Used in parsing, made lowercased in code
    _('soon').lower(): SOON,
    SOMEDAY: SOMEDAY,
    'later': SOMEDAY,
    # Translators: Used in parsing, made lowercased in code
    _('later').lower(): SOMEDAY,
    'someday': SOMEDAY,
    # Translators: Used in parsing, made lowercased in code
    _('someday').lower(): SOMEDAY,
    NODATE: NODATE,
    '': NODATE,
    None: NODATE,
    'none': NODATE,
}


class Accuracy(Enum):
    """ GTG.core.dates.Date supported accuracies

    From less accurate to the most:
     * fuzzy is when a date is just a string not representing a real date
       (like `someday`)
     * date is a datetime.date accurate to the day (see datetime.date)
     * datetime is a datetime.datetime accurate to the microseconds
       (see datetime.datetime)
     * timezone ia a datetime.datetime accurate to the microseconds with tzinfo
    """
    fuzzy = 'fuzzy'
    date = 'date'
    datetime = 'datetime'
    timezone = 'timezone'


# ISO 8601 date format
# get date format from locale
DATE_FORMATS = [(locale.nl_langinfo(locale.D_T_FMT), Accuracy.datetime),
                ('%Y-%m-%dT%H:%M%S.%f%z', Accuracy.timezone),
                ('%Y-%m-%d %H:%M%S.%f%z', Accuracy.timezone),
                ('%Y-%m-%dT%H:%M%S.%f', Accuracy.datetime),
                ('%Y-%m-%d %H:%M%S.%f', Accuracy.datetime),
                ('%Y-%m-%dT%H:%M%S', Accuracy.datetime),
                ('%Y-%m-%d %H:%M%S', Accuracy.datetime),
                (locale.nl_langinfo(locale.D_FMT), Accuracy.date),
                ('%Y-%m-%d', Accuracy.date)]


class Date:
    """A date class that supports fuzzy dates.

    A Date can be constructed with:
      - the fuzzy strings 'now', 'soon', '' (no date, default), or 'someday'
      - a string containing an ISO format date: YYYY-MM-DD
      - a datetime.date instance
      - a datetime.datetime instance
      - a GTG.core.dates.Date instance
      - a string containing a locale format date.
    """

    __slots__ = ['dt_value']

    def __init__(self, value=None):
        self.dt_value = None
        if isinstance(value, (date, datetime)):
            self.dt_value = value
        elif isinstance(value, Date):
            # Copy internal values from other Date object
            self.dt_value = value.dt_value
        elif value in {'None', None, ''}:
            self.dt_value = NODATE
        elif isinstance(value, str):
            self.dt_value = self.__parse_dt_str(value)
        elif value == 0:  # support for dropped falsly fuzzy NOW
            self.dt_value = datetime.now()
        elif value in LOOKUP:
            self.dt_value = LOOKUP[value]
        if self.dt_value is None:
            raise ValueError(f"Unknown value for date: '{value}'")

    @staticmethod
    def __parse_dt_str(string):
        """Will try casting given string into a datetime or a date."""
        for cls in date, datetime:
            try:
                return cls.fromisoformat(string)
            except (ValueError,  # ignoring no iso format value
                    AttributeError):  # ignoring python < 3.7
                pass
        for date_format, accuracy in DATE_FORMATS:
            try:
                dt_value = datetime.strptime(string, date_format)
                if accuracy is Accuracy.date:
                    dt_value = dt_value.date()
                return dt_value
            except ValueError:
                pass
        if string in {'now', _('now').lower()}:
            return datetime.now()
        return LOOKUP.get(str(string).lower(), None)

    @property
    def accuracy(self):
        if isinstance(self.dt_value, datetime):
            if self.dt_value.tzinfo:
                return Accuracy.timezone
            return Accuracy.datetime
        if isinstance(self.dt_value, date):
            return Accuracy.date
        return Accuracy.fuzzy

    def date(self):
        """ Map date into real date, i.e. convert fuzzy dates """
        return self.dt_by_accuracy(Accuracy.date)

    @staticmethod
    def _dt_by_accuracy(dt_value, accuracy: Accuracy,
                        wanted_accuracy: Accuracy):
        if wanted_accuracy is Accuracy.timezone:
            if accuracy is Accuracy.date:
                return datetime(dt_value.year, dt_value.month, dt_value.day,
                                tzinfo=LOCAL_TIMEZONE)
            assert accuracy is Accuracy.datetime, f"{accuracy} wasn't expected"
            # datetime is naive and assuming local timezone
            return dt_value.replace(tzinfo=LOCAL_TIMEZONE)
        if wanted_accuracy is Accuracy.datetime:
            if accuracy is Accuracy.date:
                return datetime(dt_value.year, dt_value.month, dt_value.day)
            assert accuracy is Accuracy.timezone, f"{accuracy} wasn't expected"
            # returning UTC naive
            return dt_value.astimezone(LOCAL_TIMEZONE).replace(tzinfo=None)
        if wanted_accuracy is Accuracy.date:
            return dt_value.date()
        raise AssertionError(f"Couldn't process {dt_value!r} with actual "
                             f"accuracy is {accuracy.value} "
                             f"and we wanted {wanted_accuracy.value}")

    def dt_by_accuracy(self, wanted_accuracy: Accuracy):
        """Cast Date to the desired accuracy and returns either string
        for fuzzy, date, datetime or datetime with tzinfo.
        """
        if wanted_accuracy == self.accuracy:
            return self.dt_value
        if self.accuracy is Accuracy.fuzzy:
            now = datetime.now()
            delta_days = {SOON: 15, SOMEDAY: 365, NODATE: 9999}
            gtg_date = Date(now + timedelta(delta_days[self.dt_value]))
            if gtg_date.accuracy is wanted_accuracy:
                return gtg_date.dt_value
            return self._dt_by_accuracy(gtg_date.dt_value, gtg_date.accuracy,
                                        wanted_accuracy)
        return self._dt_by_accuracy(self.dt_value, self.accuracy,
                                    wanted_accuracy)

    def _cast_for_operation(self, other, is_comparison: bool = True):
        """Returns two values compatibles for operation or comparison.
        Will settle for the less accuracy: comparing a date and a datetime
        will cast the datetime to a date to allow comparison.
        """
        if isinstance(other, timedelta):
            if is_comparison:
                raise ValueError("can't compare with %r" % other)
            return self.dt_value, other
        if not isinstance(other, self.__class__):
            other = self.__class__(other)
        if self.accuracy is other.accuracy:
            return self.dt_value, other.dt_value
        for accuracy in Accuracy.date, Accuracy.datetime, Accuracy.timezone:
            if accuracy in {self.accuracy, other.accuracy}:
                return (self.dt_by_accuracy(accuracy),
                        other.dt_by_accuracy(accuracy))
        return (self.dt_by_accuracy(Accuracy.fuzzy),
                other.dt_by_accuracy(Accuracy.fuzzy))

    def __add__(self, other):
        a, b = self._cast_for_operation(other, is_comparison=False)
        return a + b

    def __sub__(self, other):
        a, b = self._cast_for_operation(other, is_comparison=False)
        return a - b

    __radd__ = __add__
    __rsub__ = __sub__

    def __lt__(self, other):
        a, b = self._cast_for_operation(other)
        return a < b

    def __le__(self, other):
        a, b = self._cast_for_operation(other)
        return a <= b

    def __eq__(self, other):
        a, b = self._cast_for_operation(other)
        return a == b

    def __ne__(self, other):
        return not self.__eq__(other)

    def __gt__(self, other):
        a, b = self._cast_for_operation(other)
        return a > b

    def __ge__(self, other):
        a, b = self._cast_for_operation(other)
        return a >= b

    def __str__(self):
        """ String representation - fuzzy dates are in English """
        if self.accuracy is Accuracy.fuzzy:
            strs = {SOON: 'soon', SOMEDAY: 'someday', NODATE: ''}
            return strs[self.dt_value]
        return self.dt_value.isoformat()

    @property
    def localized_str(self):
        """Will return displayable and localized string representation
        of the GTG.core.dates.Date.
        """
        if self.accuracy is Accuracy.fuzzy:
            return STRINGS[self.dt_value]
        if self.accuracy is Accuracy.datetime:
            span = timedelta(hours=1)
            now = datetime.now()
            if now - span <= self.dt_value < now + span:
                return _('now')
        return self.date().strftime(locale.nl_langinfo(locale.D_FMT))

    def __repr__(self):
        return f"<Date({self})>"

    def __bool__(self):
        return self.dt_value != NODATE

    def is_fuzzy(self):
        """
        True if the Date is one of the fuzzy values:
        now, soon, someday or no_date
        """
        return self.accuracy is Accuracy.fuzzy

    def days_left(self):
        """ Return the difference between the date and today in dates """
        if self.dt_value == NODATE:
            return None
        return (self.dt_by_accuracy(Accuracy.date) - date.today()).days

    @classmethod
    def today(cls):
        """ Return date for today """
        return cls(date.today())

    @classmethod
    def tomorrow(cls):
        """ Return date for tomorrow """
        return cls(date.today() + timedelta(days=1))

    @classmethod
    def now(cls):
        """ Return date representing fuzzy date now """
        return cls.today()

    @staticmethod
    def no_date():
        """ Return date representing no (set) date """
        return _GLOBAL_DATE_NODATE

    @staticmethod
    def soon():
        """ Return date representing fuzzy date soon """
        return _GLOBAL_DATE_SOON

    @staticmethod
    def someday():
        """ Return date representing fuzzy date someday """
        return _GLOBAL_DATE_SOMEDAY

    @staticmethod
    def _parse_only_month_day(string):
        """ Parse next Xth day in month """
        try:
            mday = int(string)
            if not 1 <= mday <= 31 or string.startswith('0'):
                return None
        except ValueError:
            return None

        today = date.today()
        try:
            result = today.replace(day=mday)
        except ValueError:
            result = None

        if result is None or result <= today:
            if today.month == 12:
                next_month = 1
                next_year = today.year + 1
            else:
                next_month = today.month + 1
                next_year = today.year

            try:
                result = date(next_year, next_month, mday)
            except ValueError:
                pass

        return result

    @staticmethod
    def _parse_numerical_format(string):
        """ Parse numerical formats like %Y/%m/%d, %Y%m%d or %m%d """
        result = None
        today = date.today()
        for fmt in ['%Y/%m/%d', '%Y%m%d', '%m%d']:
            try:
                result = datetime.strptime(string, fmt).date()
                if '%Y' not in fmt:
                    # If the day has passed, assume the next year
                    if result.month > today.month or \
                            (result.month == today.month and result.day >= today.day):
                        year = today.year
                    else:
                        year = today.year + 1
                    result = result.replace(year=year)
            except ValueError:
                continue
        return result

    @staticmethod
    def _parse_text_representation(string):
        """ Match common text representation for date """
        today = date.today()

        # accepted date formats
        formats = {
            'today': 0,
            # Translators: Used in parsing, made lowercased in code
            _('today').lower(): 0,
            'tomorrow': 1,
            # Translators: Used in parsing, made lowercased in code
            _('tomorrow').lower(): 1,
            'next week': 7,
            # Translators: Used in parsing, made lowercased in code
            _('next week').lower(): 7,
            'next month': calendar.mdays[today.month],
            # Translators: Used in parsing, made lowercased in code
            _('next month').lower(): calendar.mdays[today.month],
            'next year': 365 + int(calendar.isleap(today.year)),
            # Translators: Used in parsing, made lowercased in code
            _('next year').lower(): 365 + int(calendar.isleap(today.year)),
        }

        # add week day names in the current locale
        for i, (english, local) in enumerate([
            ("Monday", _("Monday")),
            ("Tuesday", _("Tuesday")),
            ("Wednesday", _("Wednesday")),
            ("Thursday", _("Thursday")),
            ("Friday", _("Friday")),
            ("Saturday", _("Saturday")),
            ("Sunday", _("Sunday")),
        ]):
            offset = i - today.weekday() + 7 * int(i <= today.weekday())
            formats[english.lower()] = offset
            formats[local.lower()] = offset

        offset = formats.get(string, None)
        if offset is None:
            return None
        return today + timedelta(offset)

    @classmethod
    def parse(cls, string):
        """Return a Date corresponding to string, or None.

        string may be in one of the following formats:
            - YYYY/MM/DD, YYYYMMDD, MMDD, D
            - fuzzy dates
            - 'today', 'tomorrow', 'next week', 'next month' or 'next year' in
                English or the system locale.
        """
        # sanitize input
        if string is None:
            string = ''
        else:
            string = string.lower()

        # try the default formats
        try:
            return cls(string)
        except ValueError:
            pass

        # do several parsing
        result = cls._parse_only_month_day(string)
        if result is None:
            result = cls._parse_numerical_format(string)
        if result is None:
            result = cls._parse_text_representation(string)

        # Announce the result
        if result is not None:
            return cls(result)
        else:
            raise ValueError(f"Can't parse date '{string}'")

    def _parse_only_month_day_for_recurrency(self, string, newtask=True):
        """ Parse next Xth day in month from a certain date"""
        self_date = self.dt_by_accuracy(Accuracy.date)
        if not newtask:
            self_date += timedelta(1)
        try:
            mday = int(string)
            if not 1 <= mday <= 31 or string.startswith('0'):
                return None
        except ValueError:
            return None

        try:
            result = self_date.replace(day=mday)
        except ValueError:
            result = None

        if result is None or result <= self_date:
            if self_date.month == 12:
                next_month = 1
                next_year = self_date.year + 1
            else:
                next_month = self_date.month + 1
                next_year = self_date.year

            try:
                result = date(next_year, next_month, mday)
            except ValueError:
                pass

        return result

    def _parse_numerical_format_for_recurrency(self, string, newtask=True):
        """ Parse numerical formats like %Y/%m/%d,
        %Y%m%d or %m%d and calculated from a certain date"""
        self_date = self.dt_by_accuracy(Accuracy.date)
        result = None
        if not newtask:
            self_date += timedelta(1)
        for fmt in ['%Y/%m/%d', '%Y%m%d', '%m%d']:
            try:
                result = datetime.strptime(string, fmt).date()
                if '%Y' not in fmt:
                    # If the day has passed, assume the next year
                    if (result.month > self_date.month or
                        (result.month == self_date.month and
                         result.day >= self_date.day)):
                        year = self_date.year
                    else:
                        year = self_date.year + 1
                    result = result.replace(year=year)
            except ValueError:
                continue
        return result

    def _parse_text_representation_for_recurrency(self, string, newtask=False):
        """Match common text representation from a certain date(self)

        Args:
            string (str): text representation.
            newtask (bool, optional): depending on the task if it is new, the offset changes
        """
        # accepted date formats
        self_date = self.dt_by_accuracy(Accuracy.date)
        formats = {
            # change the offset depending on the task.
            'day': 0 if newtask else 1,
            # Translators: Used in recurring parsing, made lowercased in code
            _('day').lower(): 0 if newtask else 1,
            'other-day': 0 if newtask else 2,
            # Translators: Used in recurring parsing, made lowercased in code
            _('other-day').lower(): 0 if newtask else 2,
            'week': 0 if newtask else 7,
            # Translators: Used in recurring parsing, made lowercased in code
            _('week').lower(): 0 if newtask else 7,
            'month': 0 if newtask else calendar.mdays[self_date.month],
            # Translators: Used in recurring parsing, made lowercased in code
            _('month').lower(): 0 if newtask else calendar.mdays[self_date.month],
            'year': 0 if newtask else 365 + int(calendar.isleap(self_date.year)),
            # Translators: Used in recurring parsing, made lowercased in code
            _('year').lower(): 0 if newtask else 365 + int(calendar.isleap(self_date.year)),
        }

        # add week day names in the current locale
        for i, (english, local) in enumerate([
            ("Monday", _("Monday")),
            ("Tuesday", _("Tuesday")),
            ("Wednesday", _("Wednesday")),
            ("Thursday", _("Thursday")),
            ("Friday", _("Friday")),
            ("Saturday", _("Saturday")),
            ("Sunday", _("Sunday")),
        ]):
            offset = i - self_date.weekday() + 7 * int(i <= self_date.weekday())
            formats[english.lower()] = offset
            formats[local.lower()] = offset

        offset = formats.get(string, None)
        if offset is None:
            return None
        else:
            return self_date + timedelta(offset)

    def parse_from_date(self, string, newtask=False):
        """parse_from_date returns the date from a string
        but counts since a given date"""
        if string is None:
            string = ''
        else:
            string = string.lower()

        try:
            return Date(string)
        except ValueError:
            pass

        result = self._parse_only_month_day_for_recurrency(string, newtask)
        if result is None:
            result = self._parse_numerical_format_for_recurrency(string, newtask)
        if result is None:
            result = self._parse_text_representation_for_recurrency(string, newtask)

        if result is not None:
            return Date(result)
        else:
            raise ValueError(f"Can't parse date '{string}'")

    def to_readable_string(self):
        """ Return nice representation of date.

        Fuzzy dates => localized version
        Close dates => Today, Tomorrow, In X days
        Other => with locale dateformat, stripping year for this year
        """
        if self.accuracy is Accuracy.fuzzy:
            return STRINGS[self.dt_value]

        days_left = self.days_left()
        if days_left == 0:
            return _('Today')
        elif days_left < 0:
            abs_days = abs(days_left)
            return ngettext('Yesterday', '%(days)d days ago', abs_days) % \
                {'days': abs_days}
        elif days_left > 0 and days_left <= 15:
            return ngettext('Tomorrow', 'In %(days)d days', days_left) % \
                {'days': days_left}
        else:
            locale_format = locale.nl_langinfo(locale.D_FMT)
            if calendar.isleap(date.today().year):
                year_len = 366
            else:
                year_len = 365
            if float(days_left) / year_len < 1.0:
                # if it's in less than a year, don't show the year field
                locale_format = locale_format.replace('/%Y', '')
                locale_format = locale_format.replace('.%Y', '.')
            return self.dt_by_accuracy(Accuracy.date).strftime(locale_format)


_GLOBAL_DATE_SOON = Date(SOON)
_GLOBAL_DATE_NODATE = Date(NODATE)
_GLOBAL_DATE_SOMEDAY = Date(SOMEDAY)
