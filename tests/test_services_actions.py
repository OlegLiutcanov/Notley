from src.db import init_db, reset_engine
from src.services import (
    create_note, pin_note, archive_note, restore_note, purge_note,
    backlinks_for, get_note,
)

def test_pin_archive_restore_purge_and_backlinks(tmp_path, monkeypatch):
    monkeypatch.setenv("NOTELY_DB_PATH", str(tmp_path / "actions.sqlite"))
    reset_engine()
    init_db()

    a = create_note("A", "hello [[B]]", tags=["alpha"])
    b = create_note("B", "world", tags=["beta"])

    # pin / unpin
    a1 = pin_note(a.id, True)
    assert a1.pinned is True
    a2 = pin_note(a.id, False)
    assert a2.pinned is False

    # archive / restore
    a3 = archive_note(a.id, True)
    assert a3.archived is True
    a4 = restore_note(a.id)
    assert a4.archived is False

    # backlinks: A links to B, so B has backlink from A
    bl = backlinks_for("B")
    assert {n.id for n in bl} == {a.id}

    # purge removes permanently
    purge_note(a.id)
    assert get_note(a.id) is None
