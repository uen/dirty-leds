from .common import make_optional_argument_default


_undefined = make_optional_argument_default()


def _validate_bool(value, required=True):
    if value is None:
        if required:
            raise TypeError("required value is None")
        return

    if not isinstance(value, bool):
        raise TypeError((
            "expected 'bool', but value is of type {cls!r}"
        ).format(cls=value.__class__.__name__))


class _bool_validator(object):
    def __init__(self, required):
        _validate_bool(required)
        self.__required = required

    def __call__(self, value):
        _validate_bool(value, required=self.__required)

    def __repr__(self):
        args = []
        if not self.__required:
            args.append('required={required!r}'.format(
                required=self.__required,
            ))

        return 'validate_bool({args})'.format(args=', '.join(args))


def validate_bool(value=_undefined, required=True):
    """
    Checks that the target value is a valid boolean.

    :param value:
        The value to be validated.
    :param bool required:
        Whether the value can be `None`.  Defaults to `True`.

    :raises TypeError:
        If the value is not a boolean, or if it was marked as `required` but
        `None` was passed in.
    """
    validate = _bool_validator(required=required)

    if value is not _undefined:
        validate(value)
    else:
        return validate
