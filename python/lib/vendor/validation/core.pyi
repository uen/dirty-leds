from typing import overload, Callable, Optional


@overload
def validate_bool(value: bool) -> None:
    ...


@overload
def validate_bool(value: Optional[bool], *, required: bool) -> None:
    ...


@overload
def validate_bool() -> Callable[[bool], None]:
    ...


@overload
def validate_bool(*, required: bool) -> Callable[[Optional[bool]], None]:
    ...
