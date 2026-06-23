from __future__ import annotations

import pytest

from docmesh_py_core.pagination import Page


pytestmark = [pytest.mark.unit]


def test_page_builds_standard_pagination_metadata_and_items():
    page = Page.from_items(
        items=[{"id": 1}, {"id": 2}],
        total=5,
        page=2,
        page_size=2,
    )

    assert page.items == [{"id": 1}, {"id": 2}]
    assert page.total == 5
    assert page.page == 2
    assert page.page_size == 2
    assert page.total_pages == 3
    assert page.has_next is True
    assert page.has_previous is True


def test_page_rejects_out_of_range_page_requests():
    with pytest.raises(ValueError) as exc_info:
        Page.from_items(items=[], total=5, page=4, page_size=2)

    assert "page" in str(exc_info.value)
