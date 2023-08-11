import pytest
from httpx import AsyncClient

from horoscoper.api.main import app, lifespan


@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        async with lifespan(app):
            yield client


@pytest.mark.anyio
async def test_healthcheck(client):
    response = await client.get("/healthcheck")
    assert response.status_code == 200
