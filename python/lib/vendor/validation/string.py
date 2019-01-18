import re

# The typing module provides an abstract base class that we can check compiled
# regular expressions against.  Unfortunately this wasn't available until
# python 3.5.  For older versions of python, we fall back to using the private
# ``_pattern_type`` class in ``re``.
try:
    from typing.re import Pattern as _pattern_type
except ImportError:  # pragma: no cover
    _pattern_type = re._pattern_type  # pylint: disable=no-member

import six

from .core import _validate_bool
from .number import _validate_int
from .common import make_optional_argument_default


_undefined = make_optional_argument_default()


def _validate_text(
    value,
    min_length=None, max_length=None,
    pattern=None,
    required=True,
):
    if value is None:
        if required:
            raise TypeError("required value is None")
        return

    if not isinstance(value, six.text_type):
        raise TypeError((
            "expected unicode string, but value is of type {cls!r}"
        ).format(cls=value.__class__.__name__))

    if min_length is not None and len(value) < min_length:
        raise ValueError((
            "expected at least {min} characters, but string is only "
            "{length} characters long"
        ).format(length=len(value), min=min_length))

    if max_length is not None and len(value) > max_length:
        raise ValueError((
            "expected at most {max} characters, but string is {length} "
            "characters long"
        ).format(length=len(value), max=max_length))

    if pattern is not None:
        # Unfortunately `fullmatch` is not available in python2.
        match = pattern.match(value)

        if not (
            match is not None and
            match.start() == 0 and
            match.end() == len(value)
        ):
            raise ValueError(
                "string did not match pattern"
            )


class _text_validator(object):
    def __init__(self, min_length, max_length, pattern, required):
        _validate_int(min_length, min_value=0, required=False)
        _validate_int(max_length, min_value=0, required=False)
        if (
            min_length is not None and max_length is not None and
            min_length > max_length
        ):
            raise ValueError((
                'minimum length {min!r} is greater than maximum length {max!r}'
            ).format(min=min_length, max=max_length))

        self.__min_length = min_length
        self.__max_length = max_length

        _validate_bool(required)
        self.__required = required

        if pattern is None:
            compiled_pattern = pattern
        elif isinstance(pattern, six.string_types):
            # Note that we are a little more permissive about non-unicode
            # patterns in python2 than we are about non-unicode arguments.
            # Users will probably written the pattern argument inline.
            compiled_pattern = re.compile(pattern)
        elif isinstance(pattern, _pattern_type):
            compiled_pattern = pattern
        else:
            raise TypeError((
                "expected compiled regex or string, "
                "but pattern is of type {cls!r}"
            ).format(cls=pattern.__class__.__name__))

        self.__pattern = pattern
        self.__compiled_pattern = compiled_pattern

    def __call__(self, value):
        _validate_text(
            value,
            min_length=self.__min_length, max_length=self.__max_length,
            pattern=self.__compiled_pattern, required=self.__required,
        )

    def __repr__(self):
        args = []
        if self.__min_length is not None:
            args.append('min_length={min_length!r}'.format(
                min_length=self.__min_length,
            ))

        if self.__max_length is not None:
            args.append('max_length={max_length!r}'.format(
                max_length=self.__max_length,
            ))

        if self.__pattern is not None:
            args.append('pattern={pattern!r}'.format(
                pattern=self.__pattern,
            ))

        if not self.__required:
            args.append('required={required!r}'.format(
                required=self.__required,
            ))

        return 'validate_text({args})'.format(args=', '.join(args))


def validate_text(
    value=_undefined,
    min_length=None, max_length=None,
    pattern=None,
    required=True,
):
    """
    Checks that the target value is a valid human readable string value.

    In python 2 this will strictly enforce the use of ``unicode``.
    ``str``s are not accepted as there is no way to tell if they are the
    result of decoding a byte-string containing only ``latin-1`` characters
    or if they are still encoded.  In python 3 things are much simpler.

    Patterns are python regular expressions and must match the entire string.

    A simple example that uses the pattern parameter to validate a string
    describing a date:

    .. code:: python

        def parse_date(string):
            validate_text(string, pattern='[0-9]{4}-[0-9]{2}-[0-9]{2}')

            # Do something
            ...

    :param unicode value:
        The string to be validated.
    :param int min_length:
        The minimum length of the string.
    :param int max_length:
        The maximum acceptable length for the string.  By default, the length
        is not checked.
    :param str|re.Pattern pattern:
        Regular expression to check the value against.
    :param bool required:
        Whether the value can be `None`.  Defaults to `True`.

    :raises TypeError:
        If the value is not a unicode string , or if it was marked as
        `required` but `None` was passed in.
    :raises ValueError:
        If the value was longer or shorter than expected, or did not match
        the pattern.
    """
    validate = _text_validator(
        min_length=min_length, max_length=max_length,
        pattern=pattern, required=required,
    )

    if value is not _undefined:
        validate(value)
    else:
        return validate


def _validate_bytes(value, min_length, max_length, required):
    if value is None:
        if required:
            raise TypeError("required value is None")
        return

    if not isinstance(value, six.binary_type):
        raise TypeError((
            "expected byte string, but value is of type {cls!r}"
        ).format(cls=value.__class__.__name__))

    if min_length is not None and len(value) < min_length:
        raise ValueError((
            "expected at least {min} bytes, but bytestring contains only "
            "{length}"
        ).format(length=len(value), min=min_length))

    if max_length is not None and len(value) > max_length:
        raise ValueError((
            "expected at most {max} bytes, but bytestring contains {length}"
        ).format(length=len(value), max=max_length))


class _bytes_validator(object):
    def __init__(self, min_length, max_length, required):
        _validate_int(min_length, min_value=0, required=False)
        _validate_int(max_length, min_value=0, required=False)
        if (
            min_length is not None and max_length is not None and
            min_length > max_length
        ):
            raise ValueError((
                'minimum length {min!r} is greater than maximum length {max!r}'
            ).format(min=min_length, max=max_length))

        self.__min_length = min_length
        self.__max_length = max_length

        _validate_bool(required)
        self.__required = required

    def __call__(self, value):
        _validate_bytes(
            value,
            min_length=self.__min_length,
            max_length=self.__max_length,
            required=self.__required,
        )

    def __repr__(self):
        args = []
        if self.__min_length is not None:
            args.append('min_length={min_length!r}'.format(
                min_length=self.__min_length,
            ))

        if self.__max_length is not None:
            args.append('max_length={max_length!r}'.format(
                max_length=self.__max_length,
            ))

        if not self.__required:
            args.append('required={required!r}'.format(
                required=self.__required,
            ))

        return 'validate_bytes({args})'.format(args=', '.join(args))


def validate_bytes(
    value=_undefined,
    min_length=None, max_length=None,
    required=True,
):
    """
    Checks that the supplied value is a valid byte-string.

    In python 3 will accepts `bytes`, in python 2 `str`.

    Should not be used for validating human readable strings,  Please use
    :func:`validate_text` instead.

    :param bytes value:
        The string to be validated.
    :param int min_length:
        The minimum length of the string.
    :param int max_length:
        The maximum acceptable length for the string.  By default, the length
        is not checked.
    :param bool required:
        Whether the value can be `None`.  Defaults to `True`.

    :raises TypeError:
        If the value is not a byte-string, or if it was marked as `required`
        but `None` was passed in.
    :raises ValueError:
        If the value was longer or shorter than expected.
    """

    validate = _bytes_validator(
        min_length=min_length, max_length=max_length,
        required=required,
    )

    if value is not _undefined:
        validate(value)
    else:
        return validate
