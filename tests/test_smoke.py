import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from src.db import init_db, get_session, reset_engine
from src.models import Note

def test_create_note(tmp_path, monkeypatch):
    monkeypatch.setenv("NOTELY_DB_PATH", str(tmp_path / "smoke.sqlite"))
    reset_engine()   # ✅
    init_db()

    s = get_session()
    note = Note(title="hello", content="world")
    s.add(note)
    s.commit()
    s.refresh(note)
    assert note.id is not None