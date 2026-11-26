import pytest
from httpx import ASGITransport, AsyncClient

from app import db
from app.config import get_settings
from app.main import create_app


@pytest.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setenv("FITFINDER_DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path}/t.db")
    monkeypatch.setenv("FITFINDER_API_KEYS", "")
    get_settings.cache_clear()
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
    get_settings.cache_clear()
    assert db._engine is not None
