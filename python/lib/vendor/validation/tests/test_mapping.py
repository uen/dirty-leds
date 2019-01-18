import unittest

from validation import validate_int, validate_text, validate_mapping


class ValidateMappingTestCase(unittest.TestCase):
    def test_basic_valid(self):  # type: () -> None
        validate_mapping({
            "key1": 1,
            "key2": 2,
        })

    def test_valid_keys(self):  # type: () -> None
        validate_mapping({
            u"key1": 1,
            u"key2": 2,
        }, key_validator=validate_text())

    def test_invalid_key_type(self):
        with self.assertRaises(TypeError):
            validate_mapping({
                u"key1": 1,
                u"key2": 2,
            }, key_validator=validate_int())

    def test_invalid_key(self):  # type: () -> None
        with self.assertRaises(ValueError):
            validate_mapping({
                u"key1": 1,
                u"key2": 2,
            }, key_validator=validate_text(min_length=20))

    def test_key_validator_positional_argument(self):  # type: () -> None
        def validator(*args):
            assert len(args) == 1

        validate_mapping({"key": "value"}, key_validator=validator)

    def test_invalid_value_type(self):
        with self.assertRaises(TypeError):
            validate_mapping({
                u"key1": "1",
                u"key2": "2",
            }, value_validator=validate_int())

    def test_invalid_value(self):  # type: () -> None
        with self.assertRaises(ValueError):
            validate_mapping({
                u"key1": 1,
                u"key2": 2,
            }, value_validator=validate_int(max_value=1))

    def test_value_validator_positional_argument(self):  # type: () -> None
        def validator(*args):
            assert len(args) == 1

        validate_mapping({"key": "value"}, value_validator=validator)

    def test_invalid_type(self):
        with self.assertRaises(TypeError):
            validate_mapping([
                (u"key1", 1),
                (u"key2", 2),
            ])

    def test_not_required(self):  # type: () -> None
        validate_mapping(None, required=False)

    def test_required(self):
        with self.assertRaises(TypeError):
            validate_mapping(None)

    def test_closure_valid(self):  # type: () -> None
        validator = validate_mapping(key_validator=validate_int())
        validator({1: 2})

    def test_closure_invalid(self):
        validator = validate_mapping(key_validator=validate_int())
        with self.assertRaises(TypeError):
            validator({"1": 1})

    def test_repr_1(self):  # type: () -> None
        validator = validate_mapping(
            key_validator=validate_text(), value_validator=validate_int(),
        )
        self.assertEqual(
            repr(validator),
            'validate_mapping('
            'key_validator=validate_text(), value_validator=validate_int()'
            ')',
        )

    def test_repr_2(self):  # type: () -> None
        validator = validate_mapping(required=False)
        self.assertEqual(
            repr(validator),
            'validate_mapping(required=False)',
        )

    def test_key_reraise_builtin(self):
        thrown = TypeError("message")

        def inner(value):
            raise thrown

        with self.assertRaises(TypeError) as cm:
            validate_mapping({'one': 1}, key_validator=inner)
        caught = cm.exception

        self.assertIsNot(caught, thrown)
        self.assertEqual(str(caught), "invalid key 'one': message")

    def test_key_reraise_builtin_nomessage(self):
        thrown = TypeError()

        def inner(value):
            raise thrown

        with self.assertRaises(TypeError) as cm:
            validate_mapping({'two': 2}, key_validator=inner)
        caught = cm.exception

        self.assertIs(caught, thrown)

    def test_key_dont_reraise_builtin_nonstring(self):
        thrown = ValueError(1)

        def inner(value):
            raise thrown

        with self.assertRaises(ValueError) as cm:
            validate_mapping({'three': 3}, key_validator=inner)
        caught = cm.exception

        self.assertIs(caught, thrown)

    def test_key_dont_reraise_builtin_subclass(self):
        class DerivedException(ValueError):
            pass
        thrown = DerivedException("message")

        def inner(value):
            raise thrown

        with self.assertRaises(ValueError) as cm:
            validate_mapping({'key': "value"}, key_validator=inner)
        caught = cm.exception

        self.assertIs(caught, thrown)

    def test_value_reraise_builtin(self):
        thrown = TypeError("message")

        def inner(value):
            raise thrown

        with self.assertRaises(TypeError) as cm:
            validate_mapping({'one': 1}, value_validator=inner)
        caught = cm.exception

        self.assertIsNot(caught, thrown)
        self.assertEqual(str(caught), "invalid value for key 'one': message")

    def test_value_reraise_builtin_nomessage(self):
        thrown = TypeError()

        def inner(value):
            raise thrown

        with self.assertRaises(TypeError) as cm:
            validate_mapping({'two': 2}, value_validator=inner)
        caught = cm.exception

        self.assertIs(caught, thrown)

    def test_value_dont_reraise_builtin_nonstring(self):
        thrown = ValueError(1)

        def inner(value):
            raise thrown

        with self.assertRaises(ValueError) as cm:
            validate_mapping({'three': 3}, value_validator=inner)
        caught = cm.exception

        self.assertIs(caught, thrown)

    def test_value_dont_reraise_builtin_subclass(self):
        class DerivedException(ValueError):
            pass
        thrown = DerivedException("message")

        def inner(value):
            raise thrown

        with self.assertRaises(ValueError) as cm:
            validate_mapping({'key': "value"}, value_validator=inner)
        caught = cm.exception

        self.assertIs(caught, thrown)
