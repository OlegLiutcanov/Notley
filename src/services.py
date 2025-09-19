from __future__ import annotations
from datetime import UTC,datetime
from typing import Iterable, Optional
from sqlmodel import select
import re

from .db import session_scope
from .models import Note


BACKLINK_RE = re.compile(r"\[\[([^\]]+)\]\]")

def _normal_tags(tags: Optional[Iterable[str]]) -> list[str]:
    if not tags:
        return []
    return sorted({t.strip().lower() for t in tags if t and t.strip()})


def create_note(title: str, content: str = "", tags: Optional[Iterable[str]] = None) -> Note:

    tags_list = _normal_tags(tags)
    with session_scope() as s:
        note = Note(title=title, content=content)
        note.set_tags(tags_list)
        s.add(note)
        s.flush()  # get the ID assigned
        s.refresh(note)  # get any defaults set by DB
        return note
    
def list_notes(
    tag: Optional[str] = None,
    search: Optional[str] = None,
    include_archived: bool = False,
    sort: str = "updated",  # "updated" | "created" | "title"
) -> list[Note]:
    """
    Return notes with optional filtering and sorting.
    - tag: match within normalized tags (simple LIKE for MVP)
    - search: substring in title or content
    - include_archived: include archived notes
    - sort: updated|created|title
    """
    with session_scope() as s:
        stmt = select(Note)
        if not include_archived:
            stmt = stmt.where(Note.archived == False)  # type: ignore[comparison-overlap]  # noqa: E712
        if tag:
            tag = tag.strip().lower()
            stmt = stmt.where(Note.tags_csv.like(f"%{tag}%"))
        if search:
            like = f"%{search}%"
            stmt = stmt.where((Note.title.like(like)) | (Note.content.like(like)))

        if sort == "created":
            stmt = stmt.order_by(Note.created_at.desc())
        elif sort == "title":
            stmt = stmt.order_by(Note.title.asc())
        else:
            stmt = stmt.order_by(Note.updated_at.desc())

        return list(s.exec(stmt))
    

def get_note(identifier: int | str) -> Optional[Note]:
    """Fetch by id (int/str digits) or exact title."""
    with session_scope() as s:
        if isinstance(identifier, int) or str(identifier).isdigit():
            obj = s.get(Note, int(identifier))
            if obj:
                return obj
        stmt = select(Note).where(Note.title == str(identifier))
        return s.exec(stmt).first()


def edit_note(
    identifier: int | str,
    *,
    title: Optional[str] = None,
    content: Optional[str] = None,
    tags: Optional[Iterable[str]] = None,
    archived: Optional[bool] = None,
    pinned: Optional[bool] = None,
) -> Note:
    """
    Update fields and bump updated_at. Returns the updated note.
    """
    tags_list = None if tags is None else _normal_tags(tags)
    with session_scope() as s:
        note = get_note(identifier)
        if not note:
            raise ValueError(f"Note '{identifier}' not found")
        note = s.merge(note)  # attach to this session

        if title is not None:
            note.title = title
        if content is not None:
            note.content = content
        if tags_list is not None:
            note.set_tags(tags_list)
        if archived is not None:
            note.archived = archived
        if pinned is not None:
            note.pinned = pinned

        note.updated_at = datetime.now(UTC)
        s.add(note)
        s.flush()
        s.refresh(note)
        return note
    

def delete_note(identifier: int | str, hard: bool = False) -> None:
    """Soft delete by default (archive). Hard delete removes the row."""
    with session_scope() as s:
        note = get_note(identifier)
        if not note:
            return
        note = s.merge(note)
        if hard:
            s.delete(note)
        else:
            note.archived = True
            note.updated_at = datetime.now(UTC)
            s.add(note)

def pin_note(identifier: int | str, value: bool = True) -> Note:
    with session_scope() as s:
        note = get_note(identifier)
        if not note:
            raise ValueError(f"Note '{identifier}' not found")
        note = s.merge(note)
        note.pinned = value
        note.updated_at = datetime.now(UTC)
        s.add(note)
        s.flush()          # <-- make sure changes hit the DB
        s.refresh(note)    # <-- now safe to reload
        return note

def archive_note(identifier: int | str, value: bool = True) -> Note:
    with session_scope() as s:
        note = get_note(identifier)
        if not note:
            raise ValueError(f"Note '{identifier}' not found")
        note = s.merge(note)
        note.archived = value
        note.updated_at = datetime.now(UTC)
        s.add(note)
        s.flush()          # <-- flush before refresh
        s.refresh(note)
        return note

def restore_note(identifier: int | str) -> Note:
    return archive_note(identifier, value=False)

def purge_note(identifier: int | str) -> None:
    delete_note(identifier, hard=True)

def extract_links(content: str | None) -> list[str]:
    if not content:
        return []
    return sorted({m.group(1).strip() for m in BACKLINK_RE.finditer(content)})

def backlinks_for(identifier: int | str, include_archived: bool = False) -> list[Note]:
    """Return notes that link to the given note via [[Title]]."""
    target = get_note(identifier)
    if not target:
        return []
    title = target.title
    with session_scope() as s:
        stmt = select(Note).where(Note.content.like(f"%[[{title}]]%"))
        if not include_archived:
            stmt = stmt.where(Note.archived == False)  # noqa: E712
        return list(s.exec(stmt))