import ext.smart_units as smart_units


class Property:
    """
    The base class for data about our media.
    We want to store the original value for posterity, and display a formatted value consistently
    Classes that inherit from this override the _display method for their own ends

    self._value is the raw value from our query
    For the purposes of display, we never want to access this

    self._null is an indicator that this value is not applicable
    Because our data is coming from a number of different places, and different properties are valid in different ways
    ie There are a number of values self._value may take that are not None, but still "not applicable"
    This provides flexibility for inherited classes to specify their own terms for what is not applicable

    self._set is an indicator that the value has been set
    Because _value can be _null, and set to None, we need a separate value to consider if it has been set

    There are two use cases for this in the wild:
    1) We know exactly what we want the value to be up front, and it likely doesn't change
        - eg filepath, filename
        In this case, we want to initialize the value right in there from the start
    2) We want to initialize the property, but don't have it's value yet
        In this case, we want an undefined new class, which we will call set on later

    TODO can set properties be set again? or should calling set be final
    """
    def __init__(self, value=None):
        self._value = None
        self._null = False
        self._set = False

        if value is not None:
            self.set(value)

    def __bool__(self):
        if not self._null:
            return False
        if self._value:
            return True

    def set(self, value=None):
        if value is None:
            self._null = True
        else:
            self._null = False
        self._value = value
        self._set = True

    def value(self):
        """
        Returns the held value, as-is
        """
        return self._value

    def _display(self):
        """
        This is intended to be overwritten in child classes, with each doing something specific to it's value
        for example, coercing it to a string, or formatting it with extra text for readability
        """
        return self._value

    def display(self):
        """
        Returns the held value displayed in it's given format
        """
        if not self._set:
            return 'loading...'
        elif self._null:
            return 'N/A'
        elif not self._value or self._value is None:
            return 'None'

        return self._display()


class BasicProperty(Property):
    """
    For property values that can handle a straight shot to being a string
    eg.
    float  - coerced to string
    int    - coerced to string
    string - as is
    bool   - becomes "Yes" or "No"
    """

    def _display(self):
        if isinstance(self._value, bool):
            if self._value:
                return 'Yes'
            else:
                return 'No'
        else:
            return str(self._value)


class TimecodeProperty(Property):
    """
    For property values that use the timecode module to display timecode

    TODO - since this is just coerced to string, is there any reason this is not a basic property?
    """
    def _display(self):
        return str(self._value)


class TimeProperty(Property):
    """
    For property values that use the smart_units module to display time
    """
    def _display(self):
        return smart_units.fit_string(self._value, 'seconds')


class ConditionsProperty(Property):
    """
    For property values which house a table of conditions

    TODO - for now this just coerces to string, but expanding this more is on the roadmap
    """
    def _display(self):
        return str(self._value)


class ListProperty(Property):
    """
    For property values that are lists, but we want coerced to str

    TODO - for now this just coerces to string, but expanding this more is on the roadmap
    """
    def _display(self):
        return ', '.join([str(x) for x in self._value])


class NotImplementedProperty(Property):
    """
    For list property values which are not implemented yet
    """
    def _display(self):
        return 'Not Implemented'
