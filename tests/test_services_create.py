from src.db import init_db, reset_engine
from src.services import create_note

def test_create_note_service_and_return_id(tmp_path, monkeypatch):
    test_db = tmp_path / "test.db"
    monkeypatch.setenv("NOTELY_DB_PATH", str(test_db))  # ✅ correct name
    reset_engine()                                      # ✅ pick up new path
    init_db()

    note = create_note("hello", "world", tags=["Work", "ideas", "work"])
    assert note.id is not None
    assert note.title == "hello"
    assert note.content == "world"
    assert note.tags == ["ideas", "work"]
