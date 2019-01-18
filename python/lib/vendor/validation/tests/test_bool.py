import unittest

from validation import validate_bool


class ValidateBoolTestCase(unittest.TestCase):
    def test_valid(self):  # type: () -> None
        validate_bool(True)
        validate_bool(False)

    def test_invalid(self):
        with self.assertRaises(TypeError):
            validate_bool(1)

        with self.assertRaises(TypeError):
            validate_bool(0)

        with self.assertRaises(TypeError):
            validate_bool("true")

    def test_not_required(self):  # type: () -> None
        validate_bool(None, required=False)

    def test_required(self):
        with self.assertRaises(TypeError):
            validate_bool(None)

    def test_closure_valid(self):  # type: () -> None
        validator = validate_bool()
        validator(False)

    def test_closure_invalid(self):
        validator = validate_bool()
        with self.assertRaises(TypeError):
            validator(None)

    def test_repr(self):  # type: () -> None
        validator = validate_bool(required=False)
        self.assertEqual(
            repr(validator),
            'validate_bool(required=False)',
        )
