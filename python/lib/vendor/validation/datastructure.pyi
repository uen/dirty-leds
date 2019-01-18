from typing import (
    Callable, List, Set, Tuple, Dict, Type, TypeVar, Optional, overload,
)
from datetime import date, datetime


T = TypeVar('T')


@overload
def validate_list(
    value: List[T],
    *, min_length: int=None, max_length: int=None,
    validator: Callable[[T], None]=None,
) -> None:
    ...


@overload
def validate_list(
    value: Optional[List[T]],
    *, min_length: int=None, max_length: int=None,
    validator: Callable[[T], None]=None,
    required: bool,
) -> None:
    ...


@overload
def validate_list(
    *, min_length: int=None, max_length: int=None,
) -> Callable[[List], None]:
    ...


@overload
def validate_list(
    *, min_length: int=None, max_length: int=None,
    required: bool,
) -> Callable[[Optional[List]], None]:
    ...


@overload
def validate_list(
    *, min_length: int=None, max_length: int=None,
    validator: Callable[[T], None],
) -> Callable[[List[T]], None]:
    ...


@overload
def validate_list(
    *, min_length: int=None, max_length: int=None,
    validator: Callable[[T], None],
    required: bool,
) -> Callable[[Optional[List[T]]], None]:
    ...


@overload
def validate_set(
    value: Set[T],
    *, min_length: int=None, max_length: int=None,
    validator: Callable[[T], None]=None,
) -> None:
    ...


@overload
def validate_set(
    value: Optional[Set[T]],
    *, min_length: int=None, max_length: int=None,
    validator: Callable[[T], None]=None,
    required: bool,
) -> None:
    ...


@overload
def validate_set(
    *, min_length: int=None, max_length: int=None,
) -> Callable[[Set], None]:
    ...


@overload
def validate_set(
    *, min_length: int=None, max_length: int=None,
    required: bool,
) -> Callable[[Optional[Set]], None]:
    ...


@overload
def validate_set(
    *, min_length: int=None, max_length: int=None,
    validator: Callable[[T], None],
) -> Callable[[Set[T]], None]:
    ...


@overload
def validate_set(
    *, min_length: int=None, max_length: int=None,
    validator: Callable[[T], None],
    required: bool,
) -> Callable[[Optional[Set[T]]], None]:
    ...


K = TypeVar('K')
V = TypeVar('V')


@overload
def validate_mapping(
    value: Dict[K, V],
    *, key_validator: Callable[[K], None]=None,
    value_validator: Callable[[V], None]=None,
) -> None:
    ...


@overload
def validate_mapping(
    value: Optional[Dict[K, V]],
    *, required: bool,
    key_validator: Callable[[K], None]=None,
    value_validator: Callable[[V], None]=None,
) -> None:
    ...


@overload
def validate_mapping() -> Callable[[Dict[object, object]], None]:
    ...


@overload
def validate_mapping(
    *, key_validator: Callable[[K], None],
) -> Callable[[Dict[K, object]], None]:
    ...


@overload
def validate_mapping(
    *, value_validator: Callable[[V], None],
) -> Callable[[Dict[object, V]], None]:
    ...


@overload
def validate_mapping(
    *, key_validator: Callable[[K], None],
    value_validator: Callable[[V], None],
) -> Callable[[Dict[K, V]], None]:
    ...


@overload
def validate_mapping(
    *, required: bool,
) -> Callable[[Optional[Dict[object, object]]], None]:
    ...


@overload
def validate_mapping(
    *, required: bool,
    key_validator: Callable[[K], None],
) -> Callable[[Optional[Dict[K, object]]], None]:
    ...


@overload
def validate_mapping(
    *, required: bool,
    value_validator: Callable[[V], None],
) -> Callable[[Optional[Dict[object, V]]], None]:
    ...


@overload
def validate_mapping(
    *, required: bool,
    key_validator: Callable[[K], None],
    value_validator: Callable[[V], None],
) -> Callable[[Optional[Dict[K, V]]], None]:
    ...


@overload
def validate_structure(
    value: Dict,
    *, allow_extra: bool=False,
    schema: Dict=None,
) -> None:
    ...


@overload
def validate_structure(
    value: Optional[Dict],
    *, allow_extra: bool=False,
    schema: Dict=None,
    required: bool,
) -> None:
    ...


@overload
def validate_structure(
    *, allow_extra: bool=False,
    schema: Dict=None,
) -> Callable[[Dict], None]:
    ...


@overload
def validate_structure(
    *, allow_extra: bool=False,
    schema: Dict=None,
    required: bool,
) -> Callable[[Optional[Dict]], None]:
    ...


@overload
def validate_tuple(
    value: Tuple,
    *, schema: Tuple=None,
    length: int=None,
) -> None:
    ...


@overload
def validate_tuple(
    value: Optional[Tuple],
    *, required: bool,
    schema: Tuple=None,
    length: int=None,
) -> None:
    ...


@overload
def validate_tuple(
    *, schema: Tuple=None,
    length: int=None,
) -> Callable[[Tuple], None]:
    ...

@overload
def validate_tuple(
    *, required: bool,
    schema: Tuple=None,
    length: int=None,
) -> Callable[[Optional[Tuple]], None]:
    ...
