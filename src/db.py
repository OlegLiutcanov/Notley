from pathlib import Path
import os
from sqlmodel import SQLModel, Session, create_engine
from contextlib import contextmanager

_ENGINE = None
_ENGINE_URL = None  # track current engine's URL so we can switch when env changes

def _compute_url() -> str:
    env_path = os.getenv("NOTELY_DB_PATH")  # <-- exact spelling: NOTELY
    if env_path:
        db_path = Path(env_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{db_path}"
    else:
        db_path = Path.home() / ".notely" / "notely.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{db_path}"

def get_engine():
    global _ENGINE, _ENGINE_URL
    url = _compute_url()
    if _ENGINE is None or _ENGINE_URL != url:
        # swap engine if URL changed (common in tests)
        if _ENGINE is not None:
            _ENGINE.dispose()
        _ENGINE = create_engine(url, echo=False, future=True)
        _ENGINE_URL = url
    return _ENGINE

def reset_engine():
    """For tests: drop the cached engine so a new NOTELY_DB_PATH is picked up."""
    global _ENGINE, _ENGINE_URL
    if _ENGINE is not None:
        _ENGINE.dispose()
    _ENGINE = None
    _ENGINE_URL = None

def init_db():
    engine = get_engine()
    SQLModel.metadata.create_all(engine)

def get_session():
    # keep objects alive after commit so returned models retain values
    return Session(get_engine(), expire_on_commit=False)


@contextmanager
def session_scope():
    session = get_session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()

