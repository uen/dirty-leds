import unittest
from copy import copy, deepcopy
import pickle

from validation.common import make_optional_argument_default


class ValidateDateTestCase(unittest.TestCase):
    def test_equal(self):  # type: () -> None
        undefined = make_optional_argument_default()

        self.assertTrue(undefined == undefined)

    def test_not_equal(self):  # type: () -> None
        undefined_a = make_optional_argument_default()
        undefined_b = make_optional_argument_default()

        self.assertFalse(undefined_a == undefined_b)

    def test_is(self):  # type: () -> None
        undefined = make_optional_argument_default()

        self.assertTrue(undefined == undefined)

    def test_is_not(self):  # type: () -> None
        undefined_a = make_optional_argument_default()
        undefined_b = make_optional_argument_default()

        self.assertFalse(undefined_a == undefined_b)

    def test_copy(self):  # type: () -> None
        undefined = make_optional_argument_default()

        self.assertIs(undefined, copy(undefined))

    def test_deepcopy(self):  # type: () -> None
        undefined = make_optional_argument_default()

        self.assertIs(undefined, deepcopy(undefined))

    def test_pickle(self):  # type: () -> None
        undefined = make_optional_argument_default()

        with self.assertRaises(TypeError):
            pickle.dumps(undefined)

    def test_repr(self):  # type: () -> None
        undefined = make_optional_argument_default()

        self.assertEqual(repr(undefined), "<optional>")
