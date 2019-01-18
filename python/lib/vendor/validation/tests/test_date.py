import unittest
from datetime import date, datetime

from validation import validate_date


class ValidateDateTestCase(unittest.TestCase):
    def test_valid(self):  # type: () -> None
        validate_date(date.today())

    def test_datetime(self):
        with self.assertRaises(TypeError):
            validate_date(datetime.now())

    def test_invalid_type(self):
        with self.assertRaises(TypeError):
            validate_date("1970-01-01")

    def test_not_required(self):  # type: () -> None
        validate_date(None, required=False)

    def test_required(self):
        with self.assertRaises(TypeError):
            validate_date(None)

    def test_closure_valid(self):  # type() -> None
        validator = validate_date()
        validator(date.today())

    def test_closure_datetime(self):
        validator = validate_date()
        with self.assertRaises(TypeError):
            validator(datetime.now())

    def test_repr(self):  # type: () -> None
        validator = validate_date(required=False)
        self.assertEqual(
            repr(validator),
            'validate_date(required=False)',
        )
