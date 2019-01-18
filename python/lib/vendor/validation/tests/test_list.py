import unittest

from validation import validate_int, validate_list


class ValidateListTestCase(unittest.TestCase):
    def test_empty_is_not_missing(self):  # type: () -> None
        validate_list([])

    def test_non_empty_no_validator(self):  # type: () -> None
        validate_list([1, 'string'])

    def test_validator_valid(self):  # type: () -> None
        validate_list([1, 2, 3], validator=validate_int())

    def test_validator_invalid(self):  # type: () -> None
        with self.assertRaises(ValueError):
            validate_list([1, 2, 3, -1], validator=validate_int(min_value=0))

    def test_validate_set(self):
        with self.assertRaises(TypeError):
            validate_list({1}, validator=validate_int())

    def test_validate_iterator(self):
        with self.assertRaises(TypeError):
            validate_list(iter([1]), validator=validate_int())

    def test_min_len(self):  # type: () -> None
        validate_list([1, 2, 3], min_length=3)

        with self.assertRaises(ValueError):
            validate_list([1, 2, 3], min_length=4)

    def test_max_len(self):  # type: () -> None
        validate_list([1, 2, 3], max_length=3)

        with self.assertRaises(ValueError):
            validate_list([1, 2, 3, 4], max_length=3)

    def test_not_required(self):  # type: () -> None
        validate_list(None, required=False)

    def test_required(self):
        with self.assertRaises(TypeError):
            validate_list(None)

    def test_closure(self):  # type: () -> None
        validator = validate_list(max_length=3)
        validator([1])
        with self.assertRaises(ValueError):
            validator([1, 2, 3, 4])

    def test_repr_1(self):  # type: () -> None
        validator = validate_list(min_length=1, max_length=100)
        self.assertEqual(
            repr(validator),
            'validate_list(min_length=1, max_length=100)',
        )

    def test_repr_2(self):  # type: () -> None
        validator = validate_list(validator=validate_int(), required=False)
        self.assertEqual(
            repr(validator),
            'validate_list(validator=validate_int(), required=False)',
        )

    def test_reraise_builtin(self):
        thrown = TypeError("message")

        def inner(value):
            raise thrown

        with self.assertRaises(TypeError) as cm:
            validate_list([1], validator=inner)
        caught = cm.exception

        self.assertIsNot(caught, thrown)
        self.assertEqual(str(caught), "invalid item at position 0: message")

    def test_reraise_builtin_nomessage(self):
        thrown = TypeError()

        def inner(value):
            raise thrown

        with self.assertRaises(TypeError) as cm:
            validate_list([2], validator=inner)
        caught = cm.exception

        self.assertIs(caught, thrown)

    def test_dont_reraise_builtin_nonstring(self):
        thrown = ValueError(1)

        def inner(value):
            raise thrown

        with self.assertRaises(ValueError) as cm:
            validate_list([3], validator=inner)
        caught = cm.exception

        self.assertIs(caught, thrown)

    def test_dont_reraise_builtin_subclass(self):
        class DerivedException(ValueError):
            pass
        thrown = DerivedException("message")

        def inner(value):
            raise thrown

        with self.assertRaises(ValueError) as cm:
            validate_list(["value"], validator=inner)
        caught = cm.exception

        self.assertIs(caught, thrown)

    def test_check_requested_bounds(self):
        with self.assertRaises(TypeError):
            validate_list(min_length='1')

        with self.assertRaises(ValueError):
            validate_list(min_length=-1)

        with self.assertRaises(TypeError):
            validate_list(max_length='1')

        with self.assertRaises(ValueError):
            validate_list(max_length=-1)

        with self.assertRaises(ValueError):
            validate_list(min_length=10, max_length=9)
