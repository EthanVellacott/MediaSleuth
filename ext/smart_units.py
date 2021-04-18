"""
EKV 2019
- made portable
Single python file
Only builtin libraries

Smartly manage unit conversions, that are configurable, and comprehensible to the human brain

There are other libraries to do similar things but they either:
- require numpy
- come with a lot more features than I want
- are intended for scientific purposes (and read like it)

No need to be perfect, just to be easy, and light

The function I am most interested in is "fit"
Which is finding the ideal unit descriptor given a certain magnitude or quanity of a unit
Particularly, for data, and time - though I've added some other units, because

CBB
- it would be nice if you could define a smartunit using the category as unit (in the event you don't know the unit yet)
- rather than using strings for categories, use enumerators eg Unit.cm Unit.mm
     https://docs.python.org/3/library/enum.html
"""


class UnitType:
    VALID_CATEGORIES = ['TIME', 'WEIGHT', 'DISTANCE', 'DATA']

    def __init__(self, longname, unit_category, factor_to_base, shortnames=()):

        self.category = unit_category
        if self.category not in self.VALID_CATEGORIES:
            raise TypeError("{} is not a valid UnitType".format(self.category))

        # the name of the unit
        self.longname = longname

        # shortened ways that it gets referred to
        self.shortnames = shortnames

        # multiply it by this to convert it to the base unit
        # 1 indicates that it is the base unit
        self.factor_to_base = factor_to_base


class UnitDetect:
    """
    A static class containing methods for detecting information about units
    """
    # TIME
    MILLISECONDS = UnitType('milliseconds',  'TIME', 1,                ['ms', ])
    SECONDS      = UnitType('seconds',       'TIME', 1000,             ['s', 'secs'])
    MINUTES      = UnitType('minutes',       'TIME', 60000,            ['m', 'mins'])
    HOURS        = UnitType('hours',         'TIME', 36000000,         ['h', 'hrs'])
    DAYS         = UnitType('days',          'TIME', 864000000)
    WEEKS        = UnitType('weeks',         'TIME', 6048000000,       ['wk', 'wks'])
    MONTHS       = UnitType('months',        'TIME', 24192000000,      ['mth', 'mnth'])
    YEARS        = UnitType('years',         'TIME', 290304000000,     ['yr', 'yrs'])

    # WEIGHT
    MILLIGRAMS   = UnitType('milligrams',    'WEIGHT',  1,             ['mg', 'mgs'])
    GRAMS        = UnitType('milligrams',    'WEIGHT',  100,           ['g', 'gs'])
    KILOGRAMS    = UnitType('milligrams',    'WEIGHT',  10000,         ['kg', 'kgs'])

    # DISTANCE
    MILLIMETRES  = UnitType('millimetres',   'DISTANCE', 1,            ['mm', ])
    CENTIMETRES  = UnitType('centimetres',   'DISTANCE', 10,           ['cm', ])
    METRES       = UnitType('metres',        'DISTANCE', 100)
    KILOMETRES   = UnitType('kilometres',    'DISTANCE', 1000,         ['km', ])

    # DATA
    BYTES        = UnitType('bytes',         'DATA', 1,                ['b', 'bs'])
    KILOBYTES    = UnitType('kilobytes',     'DATA', 1000,             ['kb', 'kbs'])
    MEGABYTES    = UnitType('megabytes',     'DATA', 1000000,          ['mb', 'mbs'])
    GIGABYTES    = UnitType('gigabytes',     'DATA', 1000000000,       ['gb', 'gbs'])
    TERABYTES    = UnitType('terabytes',     'DATA', 1000000000000,    ['tb', 'tbs'])
    PETABYTES    = UnitType('petabytes',     'DATA', 1000000000000000, ['pb', 'pbs'])

    ALL_UNITS = [
        # TIME
        MILLISECONDS, SECONDS, MINUTES, HOURS,
        DAYS, WEEKS, MONTHS, YEARS,
        # WEIGHT
        MILLIGRAMS, GRAMS, KILOGRAMS,
        # DISTANCE
        MILLIMETRES, CENTIMETRES, METRES, KILOMETRES,
        # DATA
        BYTES, KILOBYTES, MEGABYTES, GIGABYTES, TERABYTES, PETABYTES
    ]

    @classmethod
    def get_type_by_string(cls, type_string):
        # check the longname and shortnames
        for u in cls.ALL_UNITS:
            if type_string == u.longname:
                return u
            elif type_string in u.shortnames:
                return u
        return None

    @classmethod
    def get_category_base(cls, category):
        all_category_units = [x for x in cls.ALL_UNITS if x.category == category]

        if not all_category_units:
            return ''

        base_unit = ''

        for u in all_category_units:
            if not base_unit:
                base_unit = u

            if u.factor_to_base < base_unit.factor_to_base:
                base_unit = u

        return base_unit

    @classmethod
    def get_category_max(cls, category):
        all_category_units = [x for x in cls.ALL_UNITS if x.category == category]

        if not all_category_units:
            return ''

        largest_unit = ''

        for u in all_category_units:
            if not largest_unit:
                largest_unit = u

            if u.factor_to_base > largest_unit.factor_to_base:
                largest_unit = u

        return largest_unit

    @classmethod
    def get_category_fit(cls, category, number):
        """
        return the unit that "fits" the number
        the largest unit where the number is still >= 1
        """
        all_category_units = [x for x in cls.ALL_UNITS if x.category == category]

        if not all_category_units:
            return ''

        fit_unit = ''

        for u in all_category_units:
            if not fit_unit:
                fit_unit = u

            if (number / u.factor_to_base) < 1:
                continue

            if u.factor_to_base > fit_unit.factor_to_base:
                fit_unit = u

        return fit_unit


class SmartUnit:
    """
    A class that helps do unit conversions

    Accepts a raw number and unit

    Does a conversion back to the base unit, which allows us to then go to a unit of choice
    """
    def __init__(self, number, from_unit):
        self.raw_number = number
        self.raw_unit = from_unit

        self.unit_type = UnitDetect.get_type_by_string(str(from_unit))
        self.category = self.unit_type.category
        self.base_number = self.raw_number * self.unit_type.factor_to_base

    def original(self):
        """returns tuple with (number as originally fed in, unit as originally fed in)"""
        return self.raw_number, self.raw_unit

    def as_base(self):
        """returns tuple with (number according base factor, the base unit longname)"""
        return self.base_number, UnitDetect.get_category_base(self.category)

    def as_unit(self, unit_type):
        """returns tuple with (number according to the given unit, the given unit longname)"""
        target_unit = UnitDetect.get_type_by_string(unit_type)
        target_number = self.base_number / target_unit.factor_to_base
        return target_number, target_unit.longname

    def as_fit_unit(self):
        """returns values for the highest available unit, where the number fits above decimal
        returns tuple with (number according to fit unit, fit unit longname)"""
        fit_unit = UnitDetect.get_category_fit(self.category, self.base_number)
        fit_number = self.base_number / fit_unit.factor_to_base
        return fit_number, fit_unit.longname


# methods
def convert(number, from_unit, to_unit):
    """
    Convert number from_unit to_unit
    Returns converted number, as SmartUnit
    """
    su = SmartUnit(number, from_unit)

    target_number, target_unit = su.as_unit(to_unit)
    target_su = SmartUnit(target_number, target_unit)

    return target_su


def convert_float(number, from_unit, to_unit, round_to=2):
    """
    Convert number from_unit to_unit
    Returns converted number, as float
    """
    su = SmartUnit(number, from_unit)

    target_number, target_unit = su.as_unit(to_unit)

    return round(target_number, round_to)


def convert_string(number, from_unit, to_unit, round_to=2):
    """
    Convert number from_unit to_unit
    Returns converted number, as string formatted with to_unit
    """
    su = SmartUnit(number, from_unit)

    target_number, target_unit = su.as_unit(to_unit)

    return "{} {}".format(round(target_number, round_to), target_unit)


def fit(number, from_unit):
    """
    Find the best unit fit for number
    Returns converted number, as SmartUnit
    """
    su = SmartUnit(number, from_unit)

    target_number, target_unit = su.as_fit_unit()
    target_su = SmartUnit(target_number, target_unit)

    return target_su


def fit_float(number, from_unit, round_to=2):
    """
    Find the best unit fit for number
    Returns converted number, as float
    """
    su = SmartUnit(number, from_unit)

    target_number, target_unit = su.as_fit_unit()

    return round(target_number, round_to)


def fit_string(number, from_unit, round_to=2):
    """
    Find the best unit fit for number
    Returns converted number, as string formatted with the fit target_unit
    """
    su = SmartUnit(number, from_unit)

    target_number, target_unit = su.as_fit_unit()

    return "{} {}".format(round(target_number, round_to), target_unit)
