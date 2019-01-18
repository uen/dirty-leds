import unittest

from . import (
    test_bool,
    test_int,
    test_float,
    test_text,
    test_bytes,
    test_date,
    test_datetime,
    test_list,
    test_set,
    test_mapping,
    test_structure,
    test_tuple,
    test_optional_argument,
)  # noqa:


loader = unittest.TestLoader()
suite = unittest.TestSuite((
    loader.loadTestsFromModule(test_bool),  # type: ignore
    loader.loadTestsFromModule(test_int),  # type: ignore
    loader.loadTestsFromModule(test_float),  # type: ignore
    loader.loadTestsFromModule(test_text),  # type: ignore
    loader.loadTestsFromModule(test_bytes),  # type: ignore
    loader.loadTestsFromModule(test_date),  # type: ignore
    loader.loadTestsFromModule(test_datetime),  # type: ignore
    loader.loadTestsFromModule(test_list),  # type: ignore
    loader.loadTestsFromModule(test_set),  # type: ignore
    loader.loadTestsFromModule(test_mapping),  # type: ignore
    loader.loadTestsFromModule(test_structure),  # type: ignore
    loader.loadTestsFromModule(test_tuple),  # type: ignore
    loader.loadTestsFromModule(test_optional_argument),  # type: ignore
))
