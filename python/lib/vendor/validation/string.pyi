from typing import Union, overload, Callable, Pattern, Optional
import six


@overload
def validate_text(
    value: six.text_type,
    *, min_length: int=None, max_length: int=None,
    pattern: Union[str, Pattern]=None,
) -> None:
    ...


@overload
def validate_text(
    value: Optional[six.text_type],
    *, min_length: int=None, max_length: int=None,
    pattern: Union[str, Pattern]=None,
    required: bool,
) -> None:
    ...


@overload
def validate_text(
    *, min_length: int=None, max_length: int=None,
    pattern: Union[str, Pattern]=None,
) -> Callable[[six.text_type], None]:
    ...


@overload
def validate_text(
    *, min_length: int=None, max_length: int=None,
    pattern: Union[str, Pattern]=None,
    required: bool,
) -> Callable[[Optional[six.text_type]], None]:
    ...


@overload
def validate_bytes(
    value: six.binary_type,
    *, min_length: int=None, max_length: int=None,
) -> None:
    ...


@overload
def validate_bytes(
    value: Optional[six.binary_type],
    *, min_length: int=None, max_length: int=None,
    required: bool,
) -> None:
    ...


@overload
def validate_bytes(
    *, min_length: int=None, max_length: int=None,
) -> Callable[[six.binary_type], None]:
    ...


@overload
def validate_bytes(
    *, min_length: int=None, max_length: int=None,
    required: bool,
) -> Callable[[Optional[six.binary_type]], None]:
    ...
