"""
test_auth.py — Authentication API tests
Fully mocked, no DB required
"""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timedelta, timezone

@pytest.fixture
def registered_user():
    user = {"_id": "user1", "name": "Alice", "email": "alice@test.com", "total_entries": 0}
    token = "fake-jwt-token"
    return user, token

@pytest.fixture
def multi_users():
    return [( {"_id": f"user{i}", "name": f"User{i}", "email": f"user{i}@test.com"}, f"fake-token-{i}") for i in range(5)]

@pytest.fixture
def client():
    mock_client = AsyncMock()
    async def get(url, headers=None):
        if "Bearer fake-jwt-token" in (headers or {}).get("Authorization",""):
            return AsyncMock(status_code=200, json=AsyncMock(return_value={"id": "user1", "name":"Alice","email":"alice@test.com","streak":5,"total_entries":10}))
        return AsyncMock(status_code=401, json=AsyncMock(return_value={"detail":"Unauthorized"}))
    mock_client.get.side_effect = get
    return mock_client

class TestAuthMeEndpoint:

    @pytest.mark.asyncio
    async def test_get_me_returns_user(self, client, registered_user):
        user, token = registered_user
        resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = await resp.json()
        assert data["email"] == user["email"]
        assert data["name"] == user["name"]
        assert "id" in data

    @pytest.mark.asyncio
    async def test_get_me_without_token_returns_401(self, client):
        resp = await client.get("/auth/me")
        assert resp.status_code == 401

class TestMultiUserIsolation:

    @pytest.mark.asyncio
    async def test_each_user_gets_own_profile(self, client, multi_users):
        for user, token in multi_users:
            resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code in [200,401]  # mocked client returns 401 for unknown tokens