"""
This module contains functions for validating plain data-structures.

These functions typically expect to be passed another validator function for
one or more of their arguments, that will be used to check every entry, key or
value that that the data-structure contains.
All validator functions in this library, when called with no value argument,
will return a closure that is intended to be used in this context.

As an example, to check that a list contains only positive integers, you can
call :func:`~validation.number.validate_int` with ``min_value`` equal to zero
to create a closure that will check for positive integers, and pass it as the
``validator`` argument to :func:`validate_list`.

    >>> from validation import validate_int
    >>> values = [3, 2, 1, -1]
    >>> validate_list(values, validator=validate_int(min_value=0))
    Traceback (most recent call last):
    ...
    ValueError: invalid item at position 3:  expected value less than 0, but \
got -1

Note that the exception raised here is not the exception that was raised by
:func:`~validation.number.validate_int`.
For the subset of built-in exceptions that can be raised, in normal usage, by
validators in this library - namely :exc:`TypeError`, :exc:`ValueError`,
:exc:`KeyError`, :exc:`IndexError` and :exc:`AssertionError` - we will attempt
to create and raise a copy of the original with additional context information
added to the message.
The other built-in exceptions don't make sense as validation errors and so we
don't try to catch them.
There doesn't appear to be a safe way to extend custom exceptions so these are
also left alone.

There is no single ``validate_dict`` function.
Dictionaries can be validated either as a mapping, that maps between keys of
one type and values of another, using :func:`validate_mapping`, or as struct
like objects, that map predefined keys to values with key specific types, using
:func:`validate_structure`.

The relationship between :func:`validate_list` and :func:`validate_tuple` is
similar.  :func:`validate_list` expects the list to be homogeneous, while
:func:`validate_tuple` will check each entry with its own validation function.


Sequences
---------

.. autofunction:: validate_list
.. autofunction:: validate_set
.. autofunction:: validate_tuple


Dictionaries
------------

.. autofunction:: validate_mapping
.. autofunction:: validate_structure
"""
import sys
import itertools

import six

from .core import _validate_bool
from .number import _validate_int
from .common import make_optional_argument_default


_undefined = make_optional_argument_default()


def _try_contextualize_exception(context):
    """
    Will attempt to re-raise a caught :exc:`TypeError`, :exc:`ValueError`,
    :exc:`KeyError, :exc:`IndexError` or :exc:`AssertionError` with a
    description of the context.

    If the original error does not match the expected form, or is not one of
    the supported types, will simply return without raising anything.
    """
    exc_type, exc_value, exc_traceback = sys.exc_info()

    # The list of built-in exceptions that it seems likely will be raised by a
    # validation function in normal operation.  Stuff like :exc:`SyntaxError`
    # probably indicates something more fundamental, for which the original
    # exception is more useful.
    supported_exceptions = (
        TypeError, ValueError,
        KeyError, IndexError,
        AssertionError
    )

    if exc_type not in supported_exceptions:
        # No safe way to extend the message for subclasses.
        return

    # Check that the exception has been properly constructed.  The
    # documentation requires that :exception:`TypeError`s and
    # :exception:`ValueError`s are constructed with a single,
    # string argument, but this is not enforced anywhere.
    if len(exc_value.args) != 1:
        return

    if not isinstance(exc_value.args[0], str):
        return

    message = "{context}: {message}".format(
        context=context, message=exc_value.args[0],
    )

    six.raise_from(exc_type(message), exc_value)


def _validate_list(
    value, validator=None,
    min_length=None, max_length=None,
    required=True,
):
    if value is None:
        if not required:
            return
        raise TypeError("required value is None")

    if not isinstance(value, list):
        raise TypeError((
            "expected 'list', value is of type {cls!r}"
        ).format(cls=type(value).__name__))

    if min_length is not None and len(value) < min_length:
        raise ValueError((
            "expected at least {expected} elements, "
            "but list contains only {actual}"
        ).format(expected=min_length, actual=len(value)))

    if max_length is not None and len(value) > max_length:
        raise ValueError((
            "expected at most {expected} elements, "
            "but list contains {actual}"
        ).format(expected=max_length, actual=len(value)))

    if validator is not None:
        for index, item in enumerate(value):
            try:
                validator(item)
            except (TypeError, ValueError, KeyError):
                _try_contextualize_exception(
                    "invalid item at position {index}".format(index=index),
                )
                raise


class _list_validator(object):
    def __init__(self, validator, min_length, max_length, required):
        self.__validator = validator

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
        _validate_list(
            value, validator=self.__validator,
            min_length=self.__min_length, max_length=self.__max_length,
            required=self.__required,
        )

    def __repr__(self):
        args = []
        if self.__validator is not None:
            args.append('validator={validator!r}'.format(
                validator=self.__validator,
            ))

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

        return 'validate_list({args})'.format(args=', '.join(args))


def validate_list(
    value=_undefined,
    validator=None,
    min_length=None, max_length=None,
    required=True,
):
    """
    Checks that the supplied value is a valid list.

    :param list value:
        The array to be validated.
    :param func validator:
        A function to be called on each value in the list to check that it is
        valid.
    :param int min_length:
        The minimum acceptable length for the list.  If `None`, the minimum
        length is not checked.
    :param int max_length:
        The maximum acceptable length for the list.  If `None`, the maximum
        length is not checked.
    :param bool required:
        Whether the value can be `None`.  Defaults to `True`.
    """
    validate = _list_validator(
        min_length=min_length, max_length=max_length,
        validator=validator, required=required,
    )

    if value is not _undefined:
        validate(value)
    else:
        return validate


def _validate_set(
    value, validator=None,
    min_length=None, max_length=None,
    required=True,
):
    if value is None:
        if not required:
            return
        raise TypeError("required value is None")

    if not isinstance(value, set):
        raise TypeError((
            "expected 'set', but value is of type {cls!r}"
        ).format(cls=type(value).__name__))

    if min_length is not None and len(value) < min_length:
        raise ValueError((
            "expected at least {expected} entries, "
            "but set contains only {actual}"
        ).format(expected=min_length, actual=len(value)))

    if max_length is not None and len(value) > max_length:
        raise ValueError((
            "expected at most {expected} entries, "
            "but set contains {actual}"
        ).format(expected=max_length, actual=len(value)))

    if validator is not None:
        for item in value:
            validator(item)


class _set_validator(object):
    def __init__(self, validator, min_length, max_length, required):
        self.__validator = validator

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
        _validate_set(
            value, validator=self.__validator,
            min_length=self.__min_length, max_length=self.__max_length,
            required=self.__required,
        )

    def __repr__(self):
        args = []
        if self.__validator is not None:
            args.append('validator={validator!r}'.format(
                validator=self.__validator,
            ))

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

        return 'validate_set({args})'.format(args=', '.join(args))


def validate_set(
    value=_undefined,
    validator=None,
    min_length=None, max_length=None,
    required=True,
):
    """
    Validator to check a set and all entries in it.

    :param set value:
        The set to be validated.
    :param func validator:
        A function to be called on each entry in the set to check that it is
        valid.
    :param int min_length:
        The minimum acceptable number of entries in the set.  If `None`, the
        minimum size is not checked.
    :param int max_length:
        The maximum acceptable number of entries in the set.  If `None`, the
        maximum size is not checked.
    :param bool required:
        Whether the value can be `None`.  Defaults to `True`.
    """
    validate = _set_validator(
        min_length=min_length, max_length=max_length,
        validator=validator, required=required,
    )

    if value is not _undefined:
        validate(value)
    else:
        return validate


def _validate_mapping(
    value,
    key_validator=None, value_validator=None,
    required=True,
):
    if value is None:
        if not required:
            return
        raise TypeError("required value is None")

    if not isinstance(value, dict):
        raise TypeError((
            "expected 'dict', but value is of type {cls!r}"
        ).format(cls=value.__class__.__name__))

    for item_key, item_value in value.items():
        if key_validator is not None:
            try:
                key_validator(item_key)
            except (TypeError, ValueError, KeyError):
                _try_contextualize_exception(
                    "invalid key {key!r}".format(key=item_key),
                )
                raise

        if value_validator is not None:
            try:
                value_validator(item_value)
            except (TypeError, ValueError, KeyError):
                _try_contextualize_exception(
                    "invalid value for key {key!r}".format(key=item_key),
                )
                raise


class _mapping_validator(object):
    def __init__(self, key_validator, value_validator, required):
        self.__key_validator = key_validator
        self.__value_validator = value_validator

        _validate_bool(required)
        self.__required = required

    def __call__(self, value):
        _validate_mapping(
            value,
            key_validator=self.__key_validator,
            value_validator=self.__value_validator,
            required=self.__required,
        )

    def __repr__(self):
        args = []
        if self.__key_validator is not None:
            args.append('key_validator={key_validator!r}'.format(
                key_validator=self.__key_validator,
            ))

        if self.__value_validator is not None:
            args.append('value_validator={value_validator!r}'.format(
                value_validator=self.__value_validator,
            ))

        if not self.__required:
            args.append('required={required!r}'.format(
                required=self.__required,
            ))

        return 'validate_mapping({args})'.format(args=', '.join(args))


def validate_mapping(
    value=_undefined,
    key_validator=None, value_validator=None,
    required=True,
):
    """
    Validates a dictionary representing a simple mapping from keys of one type
    to values of another.

    For validating dictionaries representing structured data, where the keys
    are known ahead of time and values can have different constraints depending
    on the key, use :func:`validate_struct`.

    :param dict value:
        The value to be validated.
    :param func key_validator:
        Optional function to be call to check each of the keys in the
        dictionary.
    :param func value_validator:
        Optional function to be call to check each of the values in the
        dictionary.
    :param bool required:
        Whether the value can't be `None`. Defaults to `True`.
    """
    validate = _mapping_validator(
        key_validator=key_validator,
        value_validator=value_validator,
        required=required,
    )

    if value is not _undefined:
        validate(value)
    else:
        return validate


def _validate_structure(
    value,
    schema=None, allow_extra=False,
    required=True,
):
    if value is None:
        if not required:
            return
        raise TypeError("required value is None")

    if not isinstance(value, dict):
        raise TypeError((
            "expected 'dict' but value is of type {cls!r}"
        ).format(cls=value.__class__.__name__))

    if schema is not None:
        for key, validator in schema.items():
            if key not in value:
                raise KeyError((
                    "dictionary missing expected key: {key!r}"
                ).format(key=key, dictionary=value))

            try:
                validator(value[key])
            except (TypeError, ValueError, KeyError):
                _try_contextualize_exception(
                    "invalid value for key {key!r}".format(key=key),
                )
                raise

        if not allow_extra and set(schema) != set(value):
            raise ValueError((
                "dictionary contains unexpected keys: {unexpected}"
            ).format(
                unexpected=', '.join(
                    repr(unexpected)
                    for unexpected in set(value) - set(schema)
                )
            ))


class _structure_validator(object):
    def __init__(self, schema, allow_extra, required):
        _validate_structure(schema, schema=None, required=False)
        if schema is not None:
            # Make a copy of the schema to make sure it won't be mutated while
            # we are using it.
            schema = dict(schema)
        self.__schema = schema

        _validate_bool(allow_extra)
        self.__allow_extra = allow_extra

        _validate_bool(required)
        self.__required = required

    def __call__(self, value):
        _validate_structure(
            value,
            schema=self.__schema,
            allow_extra=self.__allow_extra,
            required=self.__required,
        )

    def __repr__(self):
        args = []
        if self.__schema is not None:
            args.append('schema={schema!r}'.format(
                schema=self.__schema,
            ))

        if self.__allow_extra:
            args.append('allow_extra={allow_extra!r}'.format(
                allow_extra=self.__allow_extra,
            ))

        if not self.__required:
            args.append('required={required!r}'.format(
                required=self.__required,
            ))

        return 'validate_structure({args})'.format(args=', '.join(args))


def validate_structure(
    value=_undefined,
    schema=None, allow_extra=False,
    required=True,
):
    """
    Validates a structured dictionary, with value types depending on the key,
    checking it against an optional schema.

    The schema should be a dictionary, with keys corresponding to the expected
    keys in `value`, but with the values replaced by functions which will be
    called to with the corresponding value in the input.

    For validating dictionaries that represent a mapping from one set of values
    to another, use :func:`validate_mapping`.

    A simple example:

    .. code:: python

        validator = validate_structure(schema={
            'id': validate_key(kind='Model'),
            'count': validate_int(min=0),
        })
        validator({'id': self.key, 'count': self.count})

    :param dict value:
        The value to be validated.
    :param dict schema:
        The schema against which the value should be checked.
    :param bool allow_extra:
        Set to `True` to ignore extra keys.
    :param bool required:
        Whether the value can't be `None`. Defaults to True.
    """
    validate = _structure_validator(
        schema=schema, allow_extra=allow_extra, required=required,
    )

    if value is not _undefined:
        validate(value)
    else:
        return validate


def _validate_tuple(
    value,
    schema=None,
    length=None,
    required=True,
):
    if value is None:
        if not required:
            return
        raise TypeError("required value is None")

    if not isinstance(value, tuple):
        raise TypeError((
            "expected 'tuple' but value is of type {cls!r}"
        ).format(cls=value.__class__.__name__))

    # If a schema is provided, its length takes priority over then value in
    # the length argument.  `_tuple_validator` is responsible for ensuring
    # that the two are mutually exclusive.
    if schema is not None:
        length = len(schema)

    if length is not None and len(value) != length:
        raise TypeError((
            "expected tuple of length {expected} "
            "but value is of length {actual}"
        ).format(expected=length, actual=len(value)))

    if schema is not None:
        for index, entry, validator in zip(itertools.count(), value, schema):
            try:
                validator(entry)
            except (TypeError, ValueError, KeyError):
                _try_contextualize_exception(
                    "invalid value at index {index}".format(index=index),
                )
                raise


class _tuple_validator(object):
    def __init__(self, length, schema, required):
        if length is not None and schema is not None:
            raise TypeError(
                "length and schema arguments are mutually exclusive",
            )

        _validate_int(length, required=False)
        self.__length = length

        _validate_tuple(schema, schema=None, required=False)
        self.__schema = schema

        _validate_bool(required)
        self.__required = required

    def __call__(self, value):
        _validate_tuple(
            value,
            length=self.__length,
            schema=self.__schema,
            required=self.__required,
        )

    def __repr__(self):
        args = []
        if self.__schema is not None:
            args.append('schema={schema!r}'.format(
                schema=self.__schema,
            ))

        if self.__length is not None:
            args.append('length={length!r}'.format(
                length=self.__length,
            ))

        if not self.__required:
            args.append('required={required!r}'.format(
                required=self.__required,
            ))

        return 'validate_tuple({args})'.format(args=', '.join(args))


def validate_tuple(
    value=_undefined,
    schema=None, length=None,
    required=True,
):
    """
    Validates a tuple, checking it against an optional schema.

    The schema should be a tuple of validator functions, with each validator
    corresponding to an entry in the value to be checked.

    As an alternative, `validate_tuple` can accept a `length` argument.  Unlike
    the validators for other sequence types, `validate_tuple` will always
    enforce an exact length.  This is because the length of a tuple is part of
    its type.

    A simple example:

    .. code:: python

        validator = validate_tuple(schema=(
            validate_int(), validate_int(), validate_int(),
        ))
        validator((1, 2, 3))

    :param tuple value:
        The value to be validated.
    :param tuple schema:
        An optional schema against which the value should be checked.
    :param int length:
        The maximum length of the tuple.  `schema` and `length` arguments
        are mutually exclusive and must not be passed at the same time.
    :param bool required:
        Whether the value can't be `None`. Defaults to True.
    """
    validate = _tuple_validator(
        length=length, schema=schema, required=required,
    )

    if value is not _undefined:
        validate(value)
    else:
        return validate
