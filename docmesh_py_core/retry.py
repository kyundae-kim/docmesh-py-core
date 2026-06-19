from __future__ import annotations

from collections.abc import Callable
import time
from typing import ParamSpec, TypeVar


P = ParamSpec("P")
T = TypeVar("T")


class RetryExhaustedError(RuntimeError):
    pass


def retry_call(
    operation: Callable[P, T],
    *args: P.args,
    retry_on: tuple[type[BaseException], ...],
    max_attempts: int,
    base_delay_seconds: float = 0.5,
    sleep: Callable[[float], None] = time.sleep,
    **kwargs: P.kwargs,
) -> T:
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    attempt = 0
    while True:
        attempt += 1
        try:
            return operation(*args, **kwargs)
        except retry_on:
            if attempt >= max_attempts:
                raise
            sleep(base_delay_seconds * (2 ** (attempt - 1)))
