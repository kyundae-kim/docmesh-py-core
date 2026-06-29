from __future__ import annotations

from functools import wraps
import inspect
import logging
import os
from pathlib import Path
import sys
from typing import Any, Callable, Mapping, ParamSpec, TypeVar, cast

P = ParamSpec("P")
T = TypeVar("T")


@wraps(logging.basicConfig)
def configure_logging(*, level: int | str | None = None, log_path: str | Path | None = None, force: bool = False, env: Mapping[str, str] | None = None, env_key: str = 'DOCMESH_LOG_LEVEL') -> logging.Logger:
    root_logger = logging.getLogger()
    effective_level = _resolve_log_level(level=level, env=env, env_key=env_key)
    formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s %(function_event)s', defaults={'function_event': '-'})
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    if log_path is not None:
        file_path = Path(log_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(file_path, encoding='utf-8'))
    for handler in handlers:
        handler.setFormatter(formatter)
    logging.basicConfig(level=effective_level, handlers=handlers, force=force)
    root_logger.setLevel(effective_level)
    return root_logger


def _resolve_log_level(*, level: int | str | None, env: Mapping[str, str] | None, env_key: str) -> int | str:
    if level is not None:
        return level
    source_env = env if env is not None else os.environ
    resolved = source_env.get(env_key)
    if resolved is None:
        return logging.INFO
    normalized = resolved.strip().upper()
    if not normalized:
        return logging.INFO
    if normalized not in logging.getLevelNamesMapping():
        raise ValueError(f'{env_key} must be one of: {", ".join(sorted(logging.getLevelNamesMapping()))}')
    return normalized


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
