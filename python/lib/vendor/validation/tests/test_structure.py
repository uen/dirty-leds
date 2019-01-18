import unittest

from validation import validate_int, validate_text, validate_structure


class ValidateStructureTestCase(unittest.TestCase):
    def test_basic_valid(self):  # type: () -> None
        validate_structure({'hello': "world"})

    def test_not_required(self):  # type: () -> None
        validate_structure(None, required=False)

    def test_required(self):
        with self.assertRaises(TypeError):
            validate_structure(None)

    def test_invalid_container_type(self):
        with self.assertRaises(TypeError):
            validate_structure([])

    def test_schema_valid(self):  # type: () -> None
        validator = validate_structure(schema={
            'hello': validate_text(),
            'count': validate_int(),
        })

        validator({'hello': u"world", 'count': 2})

    def test_schema_invalid_value_type(self):
        validator = validate_structure(schema={
            'hello': validate_text(),
            'count': validate_int(),
        })

        with self.assertRaises(TypeError):
            validator({
                'hello': u"world",
                'count': "one hundred",
            })

    def test_schema_invalid_value(self):  # type: () -> None
        validator = validate_structure(schema={
            'hello': validate_text(),
            'count': validate_int(min_value=0),
        })

        with self.assertRaises(ValueError):
            validator({
                'hello': u"world",
                'count': -1,
            })

    def test_schema_positional_argument(self):  # type: () -> None
        def validator(*args):
            assert len(args) == 1

        validate_structure({"key": "value"}, schema={"key": validator})

    def test_schema_unexpected_key(self):  # type: () -> None
        validator = validate_structure(schema={
            'expected': validate_int(),
        })

        with self.assertRaises(ValueError):
            validator({
                'expected': 1,
                'unexpected': 2,
            })

    def test_schema_missing_key(self):  # type: () -> None
        validator = validate_structure(schema={
            'expected': validate_int(),
        })

        with self.assertRaises(KeyError):
            validator({})

    def test_schema_allow_extra(self):  # type: () -> None
        validator = validate_structure(schema={
            'expected': validate_int(),
        }, allow_extra=True)

        validator({
            'expected': 1,
            'unexpected': 2,
        })

    def test_repr_1(self):  # type: () -> None
        validator = validate_structure(schema={'key': validate_int()})
        self.assertEqual(
            repr(validator),
            'validate_structure(schema={\'key\': validate_int()})',
        )

    def test_repr_2(self):  # type: () -> None
        validator = validate_structure(allow_extra=True, required=False)
        self.assertEqual(
            repr(validator),
            'validate_structure(allow_extra=True, required=False)',
        )

    def test_reraise_builtin(self):
        thrown = TypeError("message")

        def inner(value):
            raise thrown

        with self.assertRaises(TypeError) as cm:
            validate_structure({'two': 2}, schema={'two': inner})
        caught = cm.exception

        self.assertIsNot(caught, thrown)
        self.assertEqual(str(caught), "invalid value for key 'two': message")

    def test_reraise_builtin_nomessage(self):
        thrown = TypeError()

        def inner(value):
            raise thrown

        with self.assertRaises(TypeError) as cm:
            validate_structure({'one': 1}, schema={'one': inner})
        caught = cm.exception

        self.assertIs(caught, thrown)

    def test_dont_reraise_builtin_nonstring(self):
        thrown = ValueError(1)

        def inner(value):
            raise thrown

        with self.assertRaises(ValueError) as cm:
            validate_structure({'three': 3}, schema={'three': inner})
        caught = cm.exception

        self.assertIs(caught, thrown)

    def test_dont_reraise_builtin_subclass(self):
        class DerivedException(ValueError):
            pass
        thrown = DerivedException("message")

        def inner(value):
            raise thrown

        with self.assertRaises(ValueError) as cm:
            validate_structure({"key": "value"}, schema={"key": inner})
        caught = cm.exception

        self.assertIs(caught, thrown)
