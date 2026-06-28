from __future__ import annotations

from functools import wraps
import inspect
import logging
from typing import Any, Callable, ParamSpec, TypeVar, cast

P = ParamSpec("P")
T = TypeVar("T")


def log_function_boundary(event: str | None = None) -> Callable[[Callable[P, T]], Callable[P, T]]:
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        logger = logging.getLogger(func.__module__)
        event_name = event or f"{func.__module__}.{func.__qualname__}"

        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                logger.info("function_start", extra={"function_event": event_name})
                try:
                    result = await cast(Callable[P, Any], func)(*args, **kwargs)
                except Exception:
                    logger.exception("function_error", extra={"function_event": event_name})
                    raise
                logger.info("function_end", extra={"function_event": event_name})
                return cast(T, result)

            return cast(Callable[P, T], async_wrapper)

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            logger.info("function_start", extra={"function_event": event_name})
            try:
                result = func(*args, **kwargs)
            except Exception:
                logger.exception("function_error", extra={"function_event": event_name})
                raise
            logger.info("function_end", extra={"function_event": event_name})
            return result

        return cast(Callable[P, T], wrapper)

    return decorator
