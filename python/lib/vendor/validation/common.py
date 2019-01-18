class _Default(object):
    def __repr__(self):
        return "<optional>"

    def __copy__(self):
        return self

    def __deepcopy__(self, _memo):
        return self

    def __reduce__(self):
        raise TypeError("default values cannot be pickled")


def make_optional_argument_default():
    """
    Returns a value that can be used as the default for an optional function
    argument that should be interpreted differently if explicitly set to
    ``None``.

        _undefined = make_optional_argument_default()

        def function(arg=_undefined):
            if arg is None:
                # Do something.
                ...
            elif arg is _undefined:
                # Do something else.
                ...
            else:
                # Whatever.
                ...

    Never pass objects created by this function as an explicit argument.
    Never assume that another function uses the same instance for a default
    argument, i.e. don't pass a value that is defaulted using this function
    through to another function without interpreting it first.
    It is fine to share one default value between all functions in a module,
    but it should always be assumed that some functions will eventually be
    moved out and will get their own default value.
    """
    return _Default()
