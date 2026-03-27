"""
test_journal.py — Journal API tests
Tests: create, read, delete, pagination, search, mood filter, multi-user isolation
"""

import pytest
from unittest.mock import patch, AsyncMock


# ── helpers ───────────────────────────────────────────────────────────────────

SAMPLE_TRANSCRIPTS = [
    ("happy",    "Aaj bahut achha din tha! Maine apna project complete kiya aur sab khush the."),
    ("sad",      "Aaj bahut bura feel ho raha hai. Mera dost naraaz ho gaya mujhse, bahut dukh hua."),
    ("anxious",  "Kal exam hai aur main bahut stressed aur worried hoon. Tension ho rahi hai mujhe."),
    ("grateful", "Main bahut grateful aur thankful hoon apni family ke liye. Sach mein blessed feel karta hoon."),
    ("excited",  "Mujhe kal job offer mila! Bahut excited hoon, can't wait to start!"),
    ("tired",    "Bahut tired hoon aaj. Kaam bahut zyada tha, exhausted feel ho raha hai."),
    ("angry",    "Office mein bahut gussa aaya aaj. Boss ne galat baat kahi, frustrated hoon."),
    ("neutral",  "Aaj ka din theek tha. Sab normal raha, kuch khaas nahi hua."),
]


async def create_entry(client, token, transcript="Aaj ka din achha tha", **kwargs):
    return await client.post(
        "/api/journal/",
        json={"transcript": transcript, **kwargs},
        headers={"Authorization": f"Bearer {token}"}
    )


# ── create entry ──────────────────────────────────────────────────────────────

class TestCreateJournalEntry:

    @pytest.mark.asyncio
    async def test_create_entry_success(self, client, registered_user):
        _, token = registered_user
        resp = await create_entry(client, token)
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "detected_mood" in data
        assert "ai_response" in data
        assert "mood_score" in data
        assert data["transcript"] == "Aaj ka din achha tha"

    @pytest.mark.asyncio
    async def test_create_entry_requires_auth(self, client):
        resp = await client.post("/api/journal/", json={"transcript": "test"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_create_entry_empty_transcript_returns_400(self, client, registered_user):
        _, token = registered_user
        resp = await create_entry(client, token, transcript="")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_create_entry_whitespace_transcript_returns_400(self, client, registered_user):
        _, token = registered_user
        resp = await create_entry(client, token, transcript="   ")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_create_entry_missing_transcript_returns_400(self, client, registered_user):
        _, token = registered_user
        resp = await client.post(
            "/api/journal/",
            json={},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_create_entry_returns_auto_title(self, client, registered_user):
        _, token = registered_user
        long_text = "A" * 100
        resp = await create_entry(client, token, transcript=long_text)
        assert resp.status_code == 200
        title = resp.json()["title"]
        assert len(title) <= 63  # 60 chars + "..."

    @pytest.mark.asyncio
    async def test_create_entry_custom_title(self, client, registered_user):
        _, token = registered_user
        resp = await create_entry(client, token, title="My Custom Title")
        assert resp.json()["title"] == "My Custom Title"

    @pytest.mark.asyncio
    async def test_create_entry_has_tags(self, client, registered_user):
        _, token = registered_user
        resp = await create_entry(client, token)
        assert "tags" in resp.json()
        assert isinstance(resp.json()["tags"], list)

    @pytest.mark.asyncio
    async def test_create_entry_has_created_at(self, client, registered_user):
        _, token = registered_user
        resp = await create_entry(client, token)
        assert "created_at" in resp.json()

    @pytest.mark.asyncio
    async def test_create_entry_increments_user_total(self, client, registered_user, mock_db):
        user, token = registered_user
        before = (await mock_db.users.find_one({"_id": user["_id"]}))["total_entries"]
        await create_entry(client, token)
        after = (await mock_db.users.find_one({"_id": user["_id"]}))["total_entries"]
        assert after == before + 1


# ── read entries ──────────────────────────────────────────────────────────────

class TestGetJournalEntries:

    @pytest.mark.asyncio
    async def test_get_entries_empty(self, client, registered_user):
        _, token = registered_user
        resp = await client.get(
            "/api/journal/",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "entries" in data
        assert "total" in data
        assert "page" in data

    @pytest.mark.asyncio
    async def test_get_entries_returns_created_entries(self, client, registered_user):
        _, token = registered_user
        await create_entry(client, token, transcript="Entry one about my day")
        await create_entry(client, token, transcript="Entry two about my evening")
        resp = await client.get(
            "/api/journal/",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 2

    @pytest.mark.asyncio
    async def test_pagination_limit(self, client, registered_user):
        _, token = registered_user
        for i in range(5):
            await create_entry(client, token, transcript=f"Entry number {i} today was good")
        resp = await client.get(
            "/api/journal/?limit=2",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert len(resp.json()["entries"]) <= 2

    @pytest.mark.asyncio
    async def test_pagination_page_2(self, client, registered_user):
        _, token = registered_user
        resp_p1 = await client.get(
            "/api/journal/?limit=2&page=1",
            headers={"Authorization": f"Bearer {token}"}
        )
        resp_p2 = await client.get(
            "/api/journal/?limit=2&page=2",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp_p1.status_code == 200
        assert resp_p2.status_code == 200
        # Pages should differ
        ids_p1 = {e["id"] for e in resp_p1.json()["entries"]}
        ids_p2 = {e["id"] for e in resp_p2.json()["entries"]}
        assert ids_p1.isdisjoint(ids_p2) or len(ids_p2) == 0

    @pytest.mark.asyncio
    async def test_search_by_keyword(self, client, registered_user):
        _, token = registered_user
        await create_entry(client, token, transcript="Mujhe aaj cricket match dekhna tha")
        resp = await client.get(
            "/api/journal/?search=cricket",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        entries = resp.json()["entries"]
        assert any("cricket" in e["transcript"].lower() for e in entries)

    @pytest.mark.asyncio
    async def test_get_entries_requires_auth(self, client):
        resp = await client.get("/api/journal/")
        assert resp.status_code == 401


# ── delete entry ──────────────────────────────────────────────────────────────

class TestDeleteJournalEntry:

    @pytest.mark.asyncio
    async def test_delete_own_entry_success(self, client, registered_user):
        _, token = registered_user
        create_resp = await create_entry(client, token)
        entry_id = create_resp.json()["id"]
        del_resp = await client.delete(
            f"/api/journal/{entry_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert del_resp.status_code == 200
        assert "deleted" in del_resp.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_entry_returns_404(self, client, registered_user):
        _, token = registered_user
        resp = await client.delete(
            "/api/journal/507f1f77bcf86cd799439011",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_with_invalid_id_returns_400(self, client, registered_user):
        _, token = registered_user
        resp = await client.delete(
            "/api/journal/not-a-valid-id",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_requires_auth(self, client):
        resp = await client.delete("/api/journal/507f1f77bcf86cd799439011")
        assert resp.status_code == 401


# ── multi-user isolation ──────────────────────────────────────────────────────

class TestMultiUserJournalIsolation:

    @pytest.mark.asyncio
    async def test_users_cannot_see_each_others_entries(self, client, multi_users):
        """Each user's entries should be invisible to other users."""
        user_a, token_a = multi_users[0]
        user_b, token_b = multi_users[1]

        # User A creates an entry
        await create_entry(client, token_a, transcript="User A private thoughts today")

        # User B's entries list should NOT contain User A's entry
        resp_b = await client.get(
            "/api/journal/",
            headers={"Authorization": f"Bearer {token_b}"}
        )
        entries_b = resp_b.json()["entries"]
        transcripts_b = [e["transcript"] for e in entries_b]
        assert "User A private thoughts today" not in transcripts_b

    @pytest.mark.asyncio
    async def test_five_users_create_entries_independently(self, client, multi_users):
        """5 users each create 3 entries — totals stay separate."""
        for user, token in multi_users:
            for i in range(3):
                await create_entry(client, token, transcript=f"Entry {i} by {user['name']}")

        for user, token in multi_users:
            resp = await client.get(
                "/api/journal/",
                headers={"Authorization": f"Bearer {token}"}
            )
            total = resp.json()["total"]
            assert total >= 3

    @pytest.mark.asyncio
    async def test_user_cannot_delete_another_users_entry(self, client, multi_users):
        user_a, token_a = multi_users[0]
        user_b, token_b = multi_users[1]

        # User A creates entry
        create_resp = await create_entry(client, token_a, transcript="User A confidential entry")
        entry_id = create_resp.json()["id"]

        # User B tries to delete it
        resp = await client.delete(
            f"/api/journal/{entry_id}",
            headers={"Authorization": f"Bearer {token_b}"}
        )
        assert resp.status_code == 404  # not found for user B

    @pytest.mark.asyncio
    async def test_concurrent_entries_from_multiple_users(self, client, multi_users):
        import asyncio
        tasks = [
            create_entry(client, token, transcript=f"Concurrent entry from {user['name']}")
            for user, token in multi_users
        ]
        responses = await asyncio.gather(*tasks)
        assert all(r.status_code == 200 for r in responses)
        ids = [r.json()["id"] for r in responses]
        assert len(set(ids)) == len(ids)  # all unique IDs


# ── insights endpoint ─────────────────────────────────────────────────────────

class TestInsightsEndpoint:

    @pytest.mark.asyncio
    async def test_insights_returns_correct_structure(self, client, registered_user):
        _, token = registered_user
        resp = await client.get(
            "/api/journal/insights",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        required_keys = [
            "total_entries", "streak", "mood_distribution",
            "average_mood_score", "most_common_mood",
            "weekly_entries", "recent_tags", "positive_days_percentage"
        ]
        for key in required_keys:
            assert key in data, f"Missing key: {key}"

    @pytest.mark.asyncio
    async def test_insights_requires_auth(self, client):
        resp = await client.get("/api/journal/insights")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_insights_total_entries_accurate(self, client, registered_user):
        _, token = registered_user
        before = (await client.get(
            "/api/journal/insights",
            headers={"Authorization": f"Bearer {token}"}
        )).json()["total_entries"]

        await create_entry(client, token, transcript="New entry for insights test today")

        after = (await client.get(
            "/api/journal/insights",
            headers={"Authorization": f"Bearer {token}"}
        )).json()["total_entries"]

        assert after == before + 1

    @pytest.mark.asyncio
    async def test_insights_mood_score_in_valid_range(self, client, registered_user):
        _, token = registered_user
        await create_entry(client, token, transcript="Testing mood score range today")
        data = (await client.get(
            "/api/journal/insights",
            headers={"Authorization": f"Bearer {token}"}
        )).json()
        assert 0.0 <= data["average_mood_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_insights_positive_percentage_in_range(self, client, registered_user):
        _, token = registered_user
        data = (await client.get(
            "/api/journal/insights",
            headers={"Authorization": f"Bearer {token}"}
        )).json()
        assert 0.0 <= data["positive_days_percentage"] <= 100.0