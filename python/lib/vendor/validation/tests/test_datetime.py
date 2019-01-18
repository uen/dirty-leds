import unittest
from datetime import date, datetime

import pytz

from validation import validate_datetime


class ValidateDateTimeTestCase(unittest.TestCase):
    def test_valid(self):  # type: () -> None
        validate_datetime(datetime.now(pytz.utc))

    def test_no_timezone(self):  # type: () -> None
        with self.assertRaises(ValueError):
            validate_datetime(datetime.now())

    def test_date(self):
        with self.assertRaises(TypeError):
            validate_datetime(date.today())

    def test_invalid_type(self):
        with self.assertRaises(TypeError):
            validate_datetime("1970-01-01T12:00:00+00:00")

    def test_not_required(self):  # type: () -> None
        validate_datetime(None, required=False)

    def test_required(self):
        with self.assertRaises(TypeError):
            validate_datetime(None)

    def test_closure_valid(self):  # type: () -> None
        validator = validate_datetime()
        validator(datetime.now(pytz.utc))

    def test_closure_date(self):
        validator = validate_datetime()
        with self.assertRaises(TypeError):
            validator(date.today())

    def test_repr(self):  # type: () -> None
        validator = validate_datetime()
        self.assertEqual(
            repr(validator),
            'validate_datetime()',
        )

        validator = validate_datetime(required=False)
        self.assertEqual(
            repr(validator),
            'validate_datetime(required=False)',
        )
