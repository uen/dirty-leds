import math

import six

from .core import _validate_bool
from .common import make_optional_argument_default


_undefined = make_optional_argument_default()


def _validate_int(value, min_value=None, max_value=None, required=True):
    if value is None:
        if required:
            raise TypeError("required value is None")
        return

    if not isinstance(value, six.integer_types):
        raise TypeError((
            "expected 'int', but value is of type {cls!r}"
        ).format(cls=value.__class__.__name__))

    if min_value is not None and value < min_value:
        raise ValueError((
            "expected value less than {min}, but got {value}"
        ).format(value=value, min=min_value))

    if max_value is not None and value > max_value:
        raise ValueError((
            "expected value greater than {max}, but got {value}"
        ).format(value=value, max=max_value))


class _int_validator(object):
    def __init__(self, min_value, max_value, required):
        _validate_int(min_value, required=False)
        _validate_int(max_value, required=False)
        if (
            min_value is not None and max_value is not None and
            min_value > max_value
        ):
            raise ValueError((
                'minimum value {min!r} is greater than maximum value {max!r}'
            ).format(min=min_value, max=max_value))

        self.__min_value = min_value
        self.__max_value = max_value

        _validate_bool(required)
        self.__required = required

    def __call__(self, value):
        _validate_int(
            value,
            min_value=self.__min_value, max_value=self.__max_value,
            required=self.__required,
        )

    def __repr__(self):
        args = []
        if self.__min_value is not None:
            args.append('min_value={min_value!r}'.format(
                min_value=self.__min_value,
            ))

        if self.__max_value is not None:
            args.append('max_value={max_value!r}'.format(
                max_value=self.__max_value,
            ))

        if not self.__required:
            args.append('required={required!r}'.format(
                required=self.__required,
            ))

        return 'validate_int({args})'.format(args=', '.join(args))


def validate_int(
    value=_undefined,
    min_value=None, max_value=None,
    required=True,
):
    """
    Checks that the target value is a valid integer, and that it fits in the
    requested bounds.

    Does not accept integer values encoded as ``floats``.
    Adding a value to a ``float`` will result in a loss of precision if the
    total is greater than ``2**53``.
    The division operator also behaves differently in python 2.

    :param int value:
        The number to be validated.
    :param int min_value:
        The minimum acceptable value for the number.
    :param int max_value:
        The maximum acceptable value for the number.
    :param bool required:
        Whether the value can be `None`.  Defaults to `True`.

    :raises TypeError:
        If the value is not an integer, or if it was marked as `required` but
        `None` was passed in.
    :raises ValueError:
        If the value is not within bounds.
    """
    validate = _int_validator(
        min_value=min_value, max_value=max_value,
        required=required,
    )

    if value is not _undefined:
        validate(value)
    else:
        return validate


def _validate_float(
    value,
    min_value=None, max_value=None,
    allow_infinite=False, allow_nan=False,
    required=True,
):
    if value is None:
        if required:
            raise TypeError("required value is None")
        return

    if not isinstance(value, int) and not isinstance(value, float):
        raise TypeError((
            "expected 'float', but value is of type {cls!r}"
        ).format(cls=value.__class__.__name__))

    if not allow_infinite and math.isinf(value):
        raise ValueError((
            "expected finite value, but got {value}"
        ).format(value=value))

    if not allow_nan and math.isnan(value):
        raise ValueError((
             "expected valid float, but got {value}"
        ).format(value=value))

    if min_value is not None and value < min_value:
        raise ValueError((
            "expected value less than {min}, but got {value}"
        ).format(value=value, min=min_value))

    if max_value is not None and value > max_value:
        raise ValueError((
            "expected value greater than {max}, but got {value}"
        ).format(value=value, max=max_value))


class _float_validator(object):
    def __init__(
        self,
        min_value, max_value,
        allow_infinite, allow_nan,
        required,
    ):
        _validate_float(
            min_value, allow_infinite=True, required=False,
        )
        _validate_float(
            max_value, allow_infinite=True, required=False,
        )

        if (
            min_value is not None and max_value is not None and
            min_value > max_value
        ):
            raise ValueError((
                'minimum value {min!r} is greater than maximum value {max!r}'
            ).format(min=min_value, max=max_value))

        self.__min_value = min_value
        self.__max_value = max_value

        _validate_bool(allow_infinite)
        self.__allow_infinite = allow_infinite

        _validate_bool(allow_nan)
        self.__allow_nan = allow_nan

        _validate_bool(required)
        self.__required = required

    def __call__(self, value):
        _validate_float(
            value,
            min_value=self.__min_value, max_value=self.__max_value,
            allow_infinite=self.__allow_infinite, allow_nan=self.__allow_nan,
            required=self.__required,
        )

    def __repr__(self):
        args = []
        if self.__min_value is not None:
            args.append('min_value={min_value!r}'.format(
                min_value=self.__min_value,
            ))

        if self.__max_value is not None:
            args.append('max_value={max_value!r}'.format(
                max_value=self.__max_value,
            ))

        if self.__allow_infinite:
            args.append('allow_infinite={allow_infinite!r}'.format(
                allow_infinite=self.__allow_infinite,
            ))

        if self.__allow_nan:
            args.append('allow_nan={allow_nan!r}'.format(
                allow_nan=self.__allow_nan,
            ))

        if not self.__required:
            args.append('required={required!r}'.format(
                required=self.__required,
            ))

        return 'validate_float({args})'.format(args=', '.join(args))


def validate_float(
    value=_undefined,
    min_value=None, max_value=None,
    allow_infinite=False, allow_nan=False,
    required=True,
):
    """
    Checks that the target value is a valid floating point number and that it
    fits in the requested bounds.

    :param int value:
        The number to be validated.
    :param int min_value:
        The minimum acceptable value for the number.
    :param int max_value:
        The maximum acceptable value for the number.
    :param bool allow_infinite:
        Whether or not to accept positive or negative infinities.  Defaults to
        ``False``.
    :param bool allow_nan:
        Whether or not to accept NaNs.  Defaults to ``False``.
    :param bool required:
        Whether the value can be ``None``.  Defaults to ``True``.

    :raises TypeError:
        If the value is not an integer, or if it was marked as ``required`` but
        ``None`` was passed in.
    :raises ValueError:
        If the value is not within bounds.
    """
    validate = _float_validator(
        min_value=min_value, max_value=max_value,
        allow_infinite=allow_infinite, allow_nan=allow_nan,
        required=required,
    )

    if value is not _undefined:
        validate(value)
    else:
        return validate
