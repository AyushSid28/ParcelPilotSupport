import pytest

from app.db import rebuild


@pytest.fixture()
def db(tmp_path):
    path = tmp_path / "test.db"
    conn = rebuild(path)
    yield conn
    conn.close()
