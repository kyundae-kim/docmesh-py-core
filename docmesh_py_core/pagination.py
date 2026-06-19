from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class Page(Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool

    @classmethod
    def from_items(cls, *, items: list[T], total: int, page: int, page_size: int) -> "Page[T]":
        if page < 1:
            raise ValueError("page must be >= 1")
        if page_size < 1:
            raise ValueError("page_size must be >= 1")
        if total < 0:
            raise ValueError("total must be >= 0")

        total_pages = max(1, ceil(total / page_size)) if total else 1
        if total > 0 and page > total_pages:
            raise ValueError(f"page {page} exceeds total_pages {total_pages}")

        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )
