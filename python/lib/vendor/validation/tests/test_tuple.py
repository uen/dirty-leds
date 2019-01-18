import unittest

from validation import validate_int, validate_text, validate_tuple


class ValidateTupleTestCase(unittest.TestCase):
    def test_basic_valid(self):  # type: () -> None
        validate_tuple((1, 'string'))

    def test_not_required(self):  # type: () -> None
        validate_tuple(None, required=False)

    def test_required(self):
        with self.assertRaises(TypeError):
            validate_tuple(None)

    def test_invalid_container_type(self):
        with self.assertRaises(TypeError):
            validate_tuple([])

    def test_schema_length_mutually_exclusive(self):
        with self.assertRaises(TypeError):
            validate_tuple(schema=(validate_int(),), length=1)

    def test_schema_valid(self):  # type: () -> None
        validator = validate_tuple(schema=(
            validate_text(), validate_int(),
        ))

        validator((u"hello world", 9001))

    def test_schema_invalid_value_type(self):
        validator = validate_tuple(schema=(
            validate_text(), validate_int(),
        ))

        with self.assertRaises(TypeError):
            validator((u"string", '1000'))

    def test_schema_invalid_value(self):  # type: () -> None
        validator = validate_tuple(schema=(
            validate_text(), validate_int(min_value=0),
        ))

        with self.assertRaises(ValueError):
            validator((u"string", -1))

    def test_schema_positional_argument(self):  # type: () -> None
        def validator(*args):
            assert len(args) == 1

        validate_tuple((u"value",), schema=(validator,))

    def test_schema_too_long(self):
        validator = validate_tuple(schema=(validate_int(), validate_int()))

        with self.assertRaises(TypeError):
            validator((1, 2, 3))

    def test_schema_too_short(self):
        validator = validate_tuple(schema=(validate_int(), validate_int()))

        with self.assertRaises(TypeError):
            validator((1,))

    def test_length_too_long(self):
        validator = validate_tuple(length=2)

        with self.assertRaises(TypeError):
            validator((1, 2, 3))

    def test_length_too_short(self):
        validator = validate_tuple(length=2)

        with self.assertRaises(TypeError):
            validator((1,))

    def test_length_just_right(self):  # type: () -> None
        validator = validate_tuple(length=2)
        validator((1, 2))

    def test_repr_1(self):  # type: () -> None
        validator = validate_tuple(schema=(validate_int(),))
        self.assertEqual(
            repr(validator),
            'validate_tuple(schema=(validate_int(),))',
        )

    def test_repr_2(self):  # type: () -> None
        validator = validate_tuple(length=2, required=False)
        self.assertEqual(
            repr(validator),
            'validate_tuple(length=2, required=False)',
        )

    def test_reraise_builtin(self):
        thrown = TypeError("message")

        def inner(value):
            raise thrown

        with self.assertRaises(TypeError) as cm:
            validate_tuple(("value",), schema=(inner,))
        caught = cm.exception

        self.assertIsNot(caught, thrown)
        self.assertEqual(str(caught), "invalid value at index 0: message")

    def test_reraise_builtin_nomessage(self):
        thrown = TypeError()

        def inner(value):
            raise thrown

        with self.assertRaises(TypeError) as cm:
            validate_tuple(("value",), schema=(inner,))
        caught = cm.exception

        self.assertIs(caught, thrown)

    def test_dont_reraise_builtin_nonstring(self):
        thrown = ValueError(1)

        def inner(value):
            raise thrown

        with self.assertRaises(ValueError) as cm:
            validate_tuple(("value",), schema=(inner,))
        caught = cm.exception

        self.assertIs(caught, thrown)

    def test_dont_reraise_builtin_subclass(self):
        class DerivedException(ValueError):
            pass
        thrown = DerivedException("message")

        def inner(value):
            raise thrown

        with self.assertRaises(ValueError) as cm:
            validate_tuple(("value",), schema=(inner,))
        caught = cm.exception

        self.assertIs(caught, thrown)
