from __future__ import annotations

import asyncio
import logging

import pytest

from docmesh_py_core.function_logging import log_function_boundary


pytestmark = [pytest.mark.unit]


def test_log_function_boundary_logs_start_and_end_for_sync_functions(caplog: pytest.LogCaptureFixture):
    @log_function_boundary("sync-test")
    def sample(value: int) -> int:
        return value + 1

    with caplog.at_level(logging.INFO, logger=__name__):
        result = sample(41)

    assert result == 42
    assert [record.message for record in caplog.records] == ["function_start", "function_end"]
    assert [record.function_event for record in caplog.records] == ["sync-test", "sync-test"]


def test_log_function_boundary_logs_errors_for_failing_functions(caplog: pytest.LogCaptureFixture):
    @log_function_boundary("failing-test")
    def sample() -> None:
        raise RuntimeError("boom")

    with caplog.at_level(logging.INFO, logger=__name__):
        with pytest.raises(RuntimeError, match="boom"):
            sample()

    assert [record.message for record in caplog.records] == ["function_start", "function_error"]
    assert [record.function_event for record in caplog.records] == ["failing-test", "failing-test"]


def test_log_function_boundary_logs_start_and_end_for_async_functions(caplog: pytest.LogCaptureFixture):
    @log_function_boundary("async-test")
    async def sample(value: int) -> int:
        await asyncio.sleep(0)
        return value + 1

    with caplog.at_level(logging.INFO, logger=__name__):
        result = asyncio.run(sample(41))

    assert result == 42
    assert [record.message for record in caplog.records] == ["function_start", "function_end"]
    assert [record.function_event for record in caplog.records] == ["async-test", "async-test"]
