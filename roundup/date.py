#
# Copyright (c) 2001 Bizar Software Pty Ltd (http://www.bizarsoftware.com.au/)
# This module is free software, and you may redistribute it and/or modify
# under the same terms as Python, so long as this copyright message and
# disclaimer are retained in their original form.
#
# IN NO EVENT SHALL BIZAR SOFTWARE PTY LTD BE LIABLE TO ANY PARTY FOR
# DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES ARISING
# OUT OF THE USE OF THIS CODE, EVEN IF THE AUTHOR HAS BEEN ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# BIZAR SOFTWARE PTY LTD SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING,
# BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE.  THE CODE PROVIDED HEREUNDER IS ON AN "AS IS"
# BASIS, AND THERE IS NO OBLIGATION WHATSOEVER TO PROVIDE MAINTENANCE,
# SUPPORT, UPDATES, ENHANCEMENTS, OR MODIFICATIONS.
# 
# $Id: date.py,v 1.17 2002-01-16 07:02:57 richard Exp $

__doc__ = """
Date, time and time interval handling.
"""

import time, re, calendar
from i18n import _

class Date:
    '''
    As strings, date-and-time stamps are specified with the date in
    international standard format (yyyy-mm-dd) joined to the time
    (hh:mm:ss) by a period ("."). Dates in this form can be easily compared
    and are fairly readable when printed. An example of a valid stamp is
    "2000-06-24.13:03:59". We'll call this the "full date format". When
    Timestamp objects are printed as strings, they appear in the full date
    format with the time always given in GMT. The full date format is
    always exactly 19 characters long. 

    For user input, some partial forms are also permitted: the whole time
    or just the seconds may be omitted; and the whole date may be omitted
    or just the year may be omitted. If the time is given, the time is
    interpreted in the user's local time zone. The Date constructor takes
    care of these conversions. In the following examples, suppose that yyyy
    is the current year, mm is the current month, and dd is the current day
    of the month; and suppose that the user is on Eastern Standard Time.

      "2000-04-17" means <Date 2000-04-17.00:00:00>
      "01-25" means <Date yyyy-01-25.00:00:00>
      "2000-04-17.03:45" means <Date 2000-04-17.08:45:00>
      "08-13.22:13" means <Date yyyy-08-14.03:13:00>
      "11-07.09:32:43" means <Date yyyy-11-07.14:32:43>
      "14:25" means <Date yyyy-mm-dd.19:25:00>
      "8:47:11" means <Date yyyy-mm-dd.13:47:11>
      "." means "right now"

    The Date class should understand simple date expressions of the form
    stamp + interval and stamp - interval. When adding or subtracting
    intervals involving months or years, the components are handled
    separately. For example, when evaluating "2000-06-25 + 1m 10d", we
    first add one month to get 2000-07-25, then add 10 days to get
    2000-08-04 (rather than trying to decide whether 1m 10d means 38 or 40
    or 41 days).

    Example usage:
        >>> Date(".")
        <Date 2000-06-26.00:34:02>
        >>> _.local(-5)
        "2000-06-25.19:34:02"
        >>> Date(". + 2d")
        <Date 2000-06-28.00:34:02>
        >>> Date("1997-04-17", -5)
        <Date 1997-04-17.00:00:00>
        >>> Date("01-25", -5)
        <Date 2000-01-25.00:00:00>
        >>> Date("08-13.22:13", -5)
        <Date 2000-08-14.03:13:00>
        >>> Date("14:25", -5)
        <Date 2000-06-25.19:25:00>
    '''
    def __init__(self, spec='.', offset=0):
        """Construct a date given a specification and a time zone offset.

          'spec' is a full date or a partial form, with an optional
                 added or subtracted interval. Or a date 9-tuple.
        'offset' is the local time zone offset from GMT in hours.
        """
        if type(spec) == type(''):
            self.set(spec, offset=offset)
        else:
            y,m,d,H,M,S,x,x,x = spec
            ts = calendar.timegm((y,m,d,H+offset,M,S,0,0,0))
            self.year, self.month, self.day, self.hour, self.minute, \
                self.second, x, x, x = time.gmtime(ts)

    def applyInterval(self, interval):
        ''' Apply the interval to this date
        '''
        t = (self.year + interval.year,
             self.month + interval.month,
             self.day + interval.day,
             self.hour + interval.hour,
             self.minute + interval.minute,
             self.second + interval.second, 0, 0, 0)
        self.year, self.month, self.day, self.hour, self.minute, \
            self.second, x, x, x = time.gmtime(calendar.timegm(t))

    def __add__(self, other):
        """Add an interval to this date to produce another date."""
        t = (self.year + other.sign * other.year,
            self.month + other.sign * other.month,
            self.day + other.sign * other.day,
            self.hour + other.sign * other.hour,
            self.minute + other.sign * other.minute,
            self.second + other.sign * other.second, 0, 0, 0)
        return Date(time.gmtime(calendar.timegm(t)))

    # XXX deviates from spec to allow subtraction of dates as well
    def __sub__(self, other):
        """ Subtract:
             1. an interval from this date to produce another date.
             2. a date from this date to produce an interval.
        """
        if isinstance(other, Date):
            # TODO this code will fall over laughing if the dates cross
            # leap years, phases of the moon, ....
            a = calendar.timegm((self.year, self.month, self.day, self.hour,
                self.minute, self.second, 0, 0, 0))
            b = calendar.timegm((other.year, other.month, other.day, other.hour,
                other.minute, other.second, 0, 0, 0))
            diff = a - b
            if diff < 0:
                sign = -1
                diff = -diff
            else:
                sign = 1
            S = diff%60
            M = (diff/60)%60
            H = (diff/(60*60))%60
            if H>1: S = 0
            d = (diff/(24*60*60))%30
            if d>1: H = S = M = 0
            m = (diff/(30*24*60*60))%12
            if m>1: H = S = M = 0
            y = (diff/(365*24*60*60))
            if y>1: d = H = S = M = 0
            return Interval((y, m, d, H, M, S), sign=sign)
        t = (self.year - other.sign * other.year,
             self.month - other.sign * other.month,
             self.day - other.sign * other.day,
             self.hour - other.sign * other.hour,
             self.minute - other.sign * other.minute,
             self.second - other.sign * other.second, 0, 0, 0)
        return Date(time.gmtime(calendar.timegm(t)))

    def __cmp__(self, other):
        """Compare this date to another date."""
        if other is None:
            return 1
        for attr in ('year', 'month', 'day', 'hour', 'minute', 'second'):
            r = cmp(getattr(self, attr), getattr(other, attr))
            if r: return r
        return 0

    def __str__(self):
        """Return this date as a string in the yyyy-mm-dd.hh:mm:ss format."""
        return '%4d-%02d-%02d.%02d:%02d:%02d'%(self.year, self.month, self.day,
            self.hour, self.minute, self.second)

    def pretty(self):
        ''' print up the date date using a pretty format...
        '''
        return time.strftime('%e %B %Y', (self.year, self.month,
            self.day, self.hour, self.minute, self.second, 0, 0, 0))

    def set(self, spec, offset=0, date_re=re.compile(r'''
              (((?P<y>\d\d\d\d)-)?((?P<m>\d\d?)-(?P<d>\d\d?))?)? # yyyy-mm-dd
              (?P<n>\.)?                                       # .
              (((?P<H>\d?\d):(?P<M>\d\d))?(:(?P<S>\d\d))?)?    # hh:mm:ss
              (?P<o>.+)?                                       # offset
              ''', re.VERBOSE)):
        ''' set the date to the value in spec
        '''
        m = date_re.match(spec)
        if not m:
            raise ValueError, _('Not a date spec: [[yyyy-]mm-dd].[[h]h:mm[:ss]]'
                '[offset]')
        info = m.groupdict()

        # get the current date/time using the offset
        y,m,d,H,M,S,x,x,x = time.gmtime(time.time())

        # override year, month, day parts
        if info['m'] is not None and info['d'] is not None:
            m = int(info['m'])
            d = int(info['d'])
            if info['y'] is not None: y = int(info['y'])
            H = M = S = 0

        # override hour, minute, second parts
        if info['H'] is not None and info['M'] is not None:
            H = int(info['H']) - offset
            M = int(info['M'])
            S = 0
            if info['S'] is not None: S = int(info['S'])

        # now handle the adjustment of hour
        ts = calendar.timegm((y,m,d,H,M,S,0,0,0))
        self.year, self.month, self.day, self.hour, self.minute, \
            self.second, x, x, x = time.gmtime(ts)

        if info['o']:
            self.applyInterval(Interval(info['o']))

    def __repr__(self):
        return '<Date %s>'%self.__str__()

    def local(self, offset):
        """Return this date as yyyy-mm-dd.hh:mm:ss in a local time zone."""
        t = (self.year, self.month, self.day, self.hour + offset, self.minute,
             self.second, 0, 0, 0)
        self.year, self.month, self.day, self.hour, self.minute, \
            self.second, x, x, x = time.gmtime(calendar.timegm(t))

    def get_tuple(self):
        return (self.year, self.month, self.day, self.hour, self.minute,
            self.second, 0, 0, 0)

class Interval:
    '''
    Date intervals are specified using the suffixes "y", "m", and "d". The
    suffix "w" (for "week") means 7 days. Time intervals are specified in
    hh:mm:ss format (the seconds may be omitted, but the hours and minutes
    may not).

      "3y" means three years
      "2y 1m" means two years and one month
      "1m 25d" means one month and 25 days
      "2w 3d" means two weeks and three days
      "1d 2:50" means one day, two hours, and 50 minutes
      "14:00" means 14 hours
      "0:04:33" means four minutes and 33 seconds

    Example usage:
        >>> Interval("  3w  1  d  2:00")
        <Interval 22d 2:00>
        >>> Date(". + 2d") - Interval("3w")
        <Date 2000-06-07.00:34:02>
    '''
    def __init__(self, spec, sign=1):
        """Construct an interval given a specification."""
        if type(spec) == type(''):
            self.set(spec)
        else:
            self.sign = sign
            self.year, self.month, self.day, self.hour, self.minute, \
                self.second = spec

    def __cmp__(self, other):
        """Compare this interval to another interval."""
        if other is None:
            return 1
        for attr in ('year', 'month', 'day', 'hour', 'minute', 'second'):
            r = cmp(getattr(self, attr), getattr(other, attr))
            if r: return r
        return 0
        
    def __str__(self):
        """Return this interval as a string."""
        sign = {1:'+', -1:'-'}[self.sign]
        l = [sign]
        if self.year: l.append('%sy'%self.year)
        if self.month: l.append('%sm'%self.month)
        if self.day: l.append('%sd'%self.day)
        if self.second:
            l.append('%d:%02d:%02d'%(self.hour, self.minute, self.second))
        elif self.hour or self.minute:
            l.append('%d:%02d'%(self.hour, self.minute))
        return ' '.join(l)

    def set(self, spec, interval_re = re.compile('''
            \s*
            (?P<s>[-+])?         # + or -
            \s*
            ((?P<y>\d+\s*)y)?    # year
            \s*
            ((?P<m>\d+\s*)m)?    # month
            \s*
            ((?P<w>\d+\s*)w)?    # week
            \s*
            ((?P<d>\d+\s*)d)?    # day
            \s*
            (((?P<H>\d?\d):(?P<M>\d\d))?(:(?P<S>\d\d))?)?   # time
            \s*
            ''', re.VERBOSE)):
        ''' set the date to the value in spec
        '''
        self.year = self.month = self.week = self.day = self.hour = \
            self.minute = self.second = 0
        self.sign = 1
        m = interval_re.match(spec)
        if not m:
            raise ValueError, _('Not an interval spec: [+-] [#y] [#m] [#w] '
                '[#d] [[[H]H:MM]:SS]')

        info = m.groupdict()
        for group, attr in {'y':'year', 'm':'month', 'w':'week', 'd':'day',
                'H':'hour', 'M':'minute', 'S':'second'}.items():
            if info[group] is not None:
                setattr(self, attr, int(info[group]))

        if self.week:
            self.day = self.day + self.week*7

        if info['s'] is not None:
            self.sign = {'+':1, '-':-1}[info['s']]

    def __repr__(self):
        return '<Interval %s>'%self.__str__()

    def pretty(self):
        ''' print up the date date using one of these nice formats..
        '''
        if self.year or self.month > 2:
            return None
        if self.month or self.day > 13:
            days = (self.month * 30) + self.day
            if days > 28:
                if int(days/30) > 1:
                    return _('%(number)s months')%{'number': int(days/30)}
                else:
                    return _('1 month')
            else:
                return _('%(number)s weeks')%{'number': int(days/7)}
        if self.day > 7:
            return _('1 week')
        if self.day > 1:
            return _('%(number)s days')%{'number': self.day}
        if self.day == 1 or self.hour > 12:
            return _('yesterday')
        if self.hour > 1:
            return _('%(number)s hours')%{'number': self.hour}
        if self.hour == 1:
            if self.minute < 15:
                return _('an hour')
            quart = self.minute/15
            if quart == 2:
                return _('1 1/2 hours')
            return _('1 %(number)s/4 hours')%{'number': quart}
        if self.minute < 1:
            return _('just now')
        if self.minute == 1:
            return _('1 minute')
        if self.minute < 15:
            return _('%(number)s minutes')%{'number': self.minute}
        quart = int(self.minute/15)
        if quart == 2:
            return _('1/2 an hour')
        return _('%(number)s/4 hour')%{'number': quart}

    def get_tuple(self):
        return (self.year, self.month, self.day, self.hour, self.minute,
            self.second)


def test():
    intervals = ("  3w  1  d  2:00", " + 2d", "3w")
    for interval in intervals:
        print '>>> Interval("%s")'%interval
        print `Interval(interval)`

    dates = (".", "2000-06-25.19:34:02", ". + 2d", "1997-04-17", "01-25",
        "08-13.22:13", "14:25")
    for date in dates:
        print '>>> Date("%s")'%date
        print `Date(date)`

    sums = ((". + 2d", "3w"), (".", "  3w  1  d  2:00"))
    for date, interval in sums:
        print '>>> Date("%s") + Interval("%s")'%(date, interval)
        print `Date(date) + Interval(interval)`

if __name__ == '__main__':
    test()

#
# $Log: not supported by cvs2svn $
# Revision 1.16  2002/01/08 11:56:24  richard
# missed an import _
#
# Revision 1.15  2002/01/05 02:27:00  richard
# I18N'ification
#
# Revision 1.14  2001/11/22 15:46:42  jhermann
# Added module docstrings to all modules.
#
# Revision 1.13  2001/09/18 22:58:37  richard
#
# Added some more help to roundu-admin
#
# Revision 1.12  2001/08/17 03:08:11  richard
# fixed prettification of intervals of 1 week
#
# Revision 1.11  2001/08/15 23:43:18  richard
# Fixed some isFooTypes that I missed.
# Refactored some code in the CGI code.
#
# Revision 1.10  2001/08/07 00:24:42  richard
# stupid typo
#
# Revision 1.9  2001/08/07 00:15:51  richard
# Added the copyright/license notice to (nearly) all files at request of
# Bizar Software.
#
# Revision 1.8  2001/08/05 07:46:12  richard
# Changed date.Date to use regular string formatting instead of strftime -
# win32 seems to have problems with %T and no hour... or something...
#
# Revision 1.7  2001/08/02 00:27:04  richard
# Extended the range of intervals that are pretty-printed before actual dates
# are displayed.
#
# Revision 1.6  2001/07/31 09:54:18  richard
# Fixed the 2.1-specific gmtime() (no arg) call in roundup.date. (Paul Wright)
#
# Revision 1.5  2001/07/29 07:01:39  richard
# Added vim command to all source so that we don't get no steenkin' tabs :)
#
# Revision 1.4  2001/07/25 04:09:34  richard
# Fixed offset handling (shoulda read the spec a little better)
#
# Revision 1.3  2001/07/23 07:56:05  richard
# Storing only marshallable data in the db - no nasty pickled class references.
#
# Revision 1.2  2001/07/22 12:09:32  richard
# Final commit of Grande Splite
#
# Revision 1.1  2001/07/22 11:58:35  richard
# More Grande Splite
#
#
# vim: set filetype=python ts=4 sw=4 et si
