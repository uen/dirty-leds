import unittest
import sys

import six

from validation import validate_int


class ValidateIntTestCase(unittest.TestCase):
    def test_valid(self):  # type: () -> None
        validate_int(0)
        validate_int(1)

    def test_long(self):  # pragma: no cover
        if six.PY3:
            raise unittest.SkipTest("not relevant in python3")

        validate_int(2 * sys.maxint)  # pylint: disable=no-member
        validate_int(-2 * sys.maxint)  # pylint: disable=no-member

    def test_float(self):
        with self.assertRaises(TypeError):
            validate_int(1.0)

    def test_min(self):  # type: () -> None
        validate_int(5, min_value=5)

        with self.assertRaises(ValueError):
            validate_int(5, min_value=6)

    def test_max(self):  # type: () -> None
        validate_int(5, max_value=5)

        with self.assertRaises(ValueError):
            validate_int(5, max_value=4)

    def test_not_required(self):  # type: () -> None
        validate_int(None, required=False)

    def test_required(self):
        with self.assertRaises(TypeError):
            validate_int(None)

    def test_closure(self):  # type: () -> None
        validator = validate_int(min_value=0)
        with self.assertRaises(ValueError):
            validator(-1)

    def test_repr(self):  # type: () -> None
        validator = validate_int(min_value=1, max_value=1, required=False)
        self.assertEqual(
            repr(validator),
            'validate_int(min_value=1, max_value=1, required=False)',
        )

    def test_check_requested_bounds(self):
        with self.assertRaises(TypeError):
            validate_int(min_value='1')

        with self.assertRaises(TypeError):
            validate_int(max_value='1')

        with self.assertRaises(ValueError):
            validate_int(min_value=10, max_value=9)
