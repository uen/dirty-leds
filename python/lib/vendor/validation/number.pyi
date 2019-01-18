from typing import overload, Callable, Optional


@overload
def validate_int(
    value: int,
    *, min_value: int=None, max_value: int=None,
) -> None:
    ...


@overload
def validate_int(
    value: Optional[int],
    *, min_value: int=None, max_value: int=None,
    required: bool,
) -> None:
    ...


@overload
def validate_int(
    *, min_value: int=None, max_value: int=None,
) -> Callable[[int], None]:
    ...


@overload
def validate_int(
    *, min_value: int=None, max_value: int=None,
    required: bool,
) -> Callable[[Optional[int]], None]:
    ...


@overload
def validate_float(
    value: float,
    *, min_value: float=None, max_value: float=None,
    allow_infinite: bool=False, allow_nan: bool=False,
) -> None:
    ...


@overload
def validate_float(
    value: Optional[float],
    *, min_value: float=None, max_value: float=None,
    allow_infinite: bool=False, allow_nan: bool=False,
    required: bool,
) -> None:
    ...


@overload
def validate_float(
    *, min_value: float=None, max_value: float=None,
    allow_infinite: bool=False, allow_nan: bool=False,
) -> Callable[[float], None]:
    ...


@overload
def validate_float(
    *, min_value: float=None, max_value: float=None,
    allow_infinite: bool=False, allow_nan: bool=False,
    required: bool,
) -> Callable[[Optional[float]], None]:
    ...
