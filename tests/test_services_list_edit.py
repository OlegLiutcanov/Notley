from src.db import init_db, reset_engine
from src.services import create_note, list_notes, edit_note

def test_list_filters_and_sorting(tmp_path, monkeypatch):
    monkeypatch.setenv("NOTELY_DB_PATH", str(tmp_path / "db1.sqlite"))
    reset_engine()   # ✅
    init_db()

    n1 = create_note("alpha", "first body", tags=["work", "ideas"])
    n2 = create_note("beta", "second body with keyword", tags=["personal"])
    n3 = create_note("gamma", "third body", tags=["work"])

    # default list (no archived) returns all 3
    all_notes = list_notes()
    ids = [n.id for n in all_notes]
    assert set(ids) == {n1.id, n2.id, n3.id}

    # tag filter
    work_notes = list_notes(tag="work")
    assert {n.title for n in work_notes} == {"alpha", "gamma"}

    # text search
    kw = list_notes(search="keyword")
    assert [n.title for n in kw] == ["beta"]

    # sort by title
    by_title = list_notes(sort="title")
    assert [n.title for n in by_title] == ["alpha", "beta", "gamma"]

def test_edit_updates_fields_and_timestamp(tmp_path, monkeypatch):
    monkeypatch.setenv("NOTELY_DB_PATH", str(tmp_path / "db2.sqlite"))
    reset_engine()
    init_db()

    n = create_note("draft", "hello", tags=["temp"])
    updated = edit_note(n.id, title="final", content="world", tags=["Work", "ideas"], pinned=True)
    assert updated.title == "final"
    assert updated.content == "world"
    assert updated.pinned is True
    assert updated.tags == ["ideas", "work"]  # normalized
    assert updated.updated_at >= n.updated_at
