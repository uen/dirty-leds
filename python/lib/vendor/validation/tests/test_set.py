import unittest

from validation import validate_int, validate_set


class ValidateSetTestCase(unittest.TestCase):
    def test_empty_is_not_missing(self):  # type: () -> None
        validate_set(set())

    def test_non_empty_no_validator(self):  # type: () -> None
        validate_set({1, 'string'})

    def test_validator_valid(self):  # type: () -> None
        validate_set({1, 2, 3}, validator=validate_int())

    def test_validator_invalid(self):  # type: () -> None
        with self.assertRaises(ValueError):
            validate_set(
                {1, 2, 3, -1},
                validator=validate_int(min_value=0),
            )

    def test_validate_list(self):
        with self.assertRaises(TypeError):
            validate_set([1], validator=validate_int())

    def test_min_len_valid(self):  # type: () -> None
        validate_set({1, 2, 3}, min_length=3)

    def test_min_len_invalid(self):  # type: () -> None
        with self.assertRaises(ValueError):
            validate_set({1, 2, 3}, min_length=4)

    def test_max_len_valid(self):  # type: () -> None
        validate_set({1, 2, 3}, max_length=3)

        with self.assertRaises(ValueError):
            validate_set({1, 2, 3, 4}, max_length=3)

    def test_not_required(self):  # type: () -> None
        validate_set(None, required=False)

    def test_required(self):
        with self.assertRaises(TypeError):
            validate_set(None)

    def test_closure(self):  # type: () -> None
        validator = validate_set(max_length=3)
        validator({1})
        with self.assertRaises(ValueError):
            validator({1, 2, 3, 4})

    def test_repr_1(self):  # type: () -> None
        validator = validate_set(min_length=1, max_length=100)
        self.assertEqual(
            repr(validator),
            'validate_set(min_length=1, max_length=100)',
        )

    def test_repr_2(self):  # type: () -> None
        validator = validate_set(validator=validate_int(), required=False)
        self.assertEqual(
            repr(validator),
            'validate_set(validator=validate_int(), required=False)',
        )

    def test_check_requested_bounds(self):
        with self.assertRaises(TypeError):
            validate_set(min_length='1')

        with self.assertRaises(ValueError):
            validate_set(min_length=-1)

        with self.assertRaises(TypeError):
            validate_set(max_length='1')

        with self.assertRaises(ValueError):
            validate_set(max_length=-1)

        with self.assertRaises(ValueError):
            validate_set(min_length=10, max_length=9)
