import unittest

from validation import validate_bytes


class ValidateBytesTestCase(unittest.TestCase):
    def test_valid(self):  # type: () -> None
        validate_bytes(b"deadbeaf")

    def test_unicode(self):
        with self.assertRaises(TypeError):
            validate_bytes(u"hello world")

    def test_min_length(self):  # type: () -> None
        validate_bytes(b"123456", min_length=6)

        with self.assertRaises(ValueError):
            validate_bytes(b"123456", min_length=7)

    def test_max_length(self):  # type: () -> None
        validate_bytes(b"123456", max_length=6)

        with self.assertRaises(ValueError):
            validate_bytes(b"123456", max_length=5)

    def test_not_required(self):  # type: () -> None
        validate_bytes(None, required=False)

    def test_required(self):
        with self.assertRaises(TypeError):
            validate_bytes(None)

    def test_closure(self):  # type: () -> None
        validator = validate_bytes(min_length=4)
        validator(b"12345")
        with self.assertRaises(ValueError):
            validator(b"123")

    def test_repr(self):  # type: () -> None
        validator = validate_bytes(min_length=4, max_length=10, required=False)
        self.assertEqual(
            repr(validator),
            'validate_bytes(min_length=4, max_length=10, required=False)',
        )

    def test_check_requested_bounds(self):
        with self.assertRaises(TypeError):
            validate_bytes(min_length='1')

        with self.assertRaises(ValueError):
            validate_bytes(min_length=-1)

        with self.assertRaises(TypeError):
            validate_bytes(max_length='1')

        with self.assertRaises(ValueError):
            validate_bytes(max_length=-1)

        with self.assertRaises(ValueError):
            validate_bytes(min_length=10, max_length=9)
