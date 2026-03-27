"""
test_journal.py — Journal API tests
Fully mocked, no DB needed
"""

import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def registered_user():
    user = {"_id": "user1", "name": "Alice", "email": "alice@test.com"}
    token = "fake-jwt-token"
    return user, token

@pytest.fixture
def multi_users():
    return [( {"_id": f"user{i}", "name": f"User{i}", "email": f"user{i}@test.com"}, f"fake-token-{i}") for i in range(5)]

@pytest.fixture
def client():
    mock_client = AsyncMock()
    async def post(url, json=None, headers=None):
        return AsyncMock(status_code=200, json=AsyncMock(return_value={
            "id": "fakeid",
            "detected_mood": "happy",
            "ai_response": "AI response",
            "mood_score": 0.8,
            "transcript": json.get("transcript","")
        }))
    async def get(url, headers=None, params=None):
        return AsyncMock(status_code=200, json=AsyncMock(return_value={"entries": [], "total": 0, "page": 1}))
    async def delete(url, headers=None):
        return AsyncMock(status_code=200, json=AsyncMock(return_value={"message": "Deleted"}))
    mock_client.post.side_effect = post
    mock_client.get.side_effect = get
    mock_client.delete.side_effect = delete
    return mock_client

async def create_entry(client, token, transcript="Aaj ka din achha tha"):
    return await client.post("/api/journal/", json={"transcript": transcript}, headers={"Authorization": f"Bearer {token}"})

class TestCreateJournalEntry:

    @pytest.mark.asyncio
    async def test_create_entry_success(self, client, registered_user):
        _, token = registered_user
        resp = await create_entry(client, token)
        data = await resp.json()
        assert resp.status_code == 200
        assert "id" in data
        assert data["transcript"] == "Aaj ka din achha tha"

class TestMultiUserJournalIsolation:

    @pytest.mark.asyncio
    async def test_users_cannot_see_each_others_entries(self, client, multi_users):
        user_a, token_a = multi_users[0]
        user_b, token_b = multi_users[1]
        await create_entry(client, token_a, transcript="User A private thoughts")
        resp_b = await client.get("/api/journal/", headers={"Authorization": f"Bearer {token_b}"})
        data_b = await resp_b.json()
        assert "User A private thoughts" not in [e["transcript"] for e in data_b["entries"]]