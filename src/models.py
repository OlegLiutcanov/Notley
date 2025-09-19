from __future__ import annotations
from datetime import datetime, UTC
from typing import Optional
from sqlmodel import Field, SQLModel

class Note(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    content: str = ""
    # store tags as CSV for MVP
    tags_csv: str = Field(default="", index=True)

    # ✅ these two were missing
    pinned: bool = Field(default=False, index=True)
    archived: bool = Field(default=False, index=True)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def tags(self) -> list[str]:
        if not self.tags_csv:
            return []
        return [t for t in self.tags_csv.split(",") if t]

    def set_tags(self, tags: list[str] | None) -> None:
        if not tags:
            self.tags_csv = ""
            return
        norm = sorted({t.strip().lower() for t in tags if t and t.strip()})
        self.tags_csv = ",".join(norm)

    def touch(self) -> None:
        self.updated_at = datetime.now(UTC)
