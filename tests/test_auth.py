"""
test_auth.py — Authentication API tests
Tests: JWT creation, /auth/me, token validation, invalid tokens
"""

import pytest
from datetime import datetime, timezone


class TestJWTTokenCreation:

    def test_create_access_token_returns_string(self):
        from backend.auth_utils import create_access_token
        token = create_access_token("507f1f77bcf86cd799439011", "test@example.com")
        assert isinstance(token, str)
        assert len(token) > 20

    def test_token_has_three_parts(self):
        """JWT format: header.payload.signature"""
        from backend.auth_utils import create_access_token
        token = create_access_token("507f1f77bcf86cd799439011", "test@example.com")
        parts = token.split(".")
        assert len(parts) == 3

    def test_decode_valid_token(self):
        from backend.auth_utils import create_access_token, decode_token
        user_id = "507f1f77bcf86cd799439011"
        email = "decode_test@example.com"
        token = create_access_token(user_id, email)
        payload = decode_token(token)
        assert payload["sub"] == user_id
        assert payload["email"] == email

    def test_decode_invalid_token_raises(self):
        from backend.auth_utils import decode_token
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            decode_token("this.is.not.valid")
        assert exc.value.status_code == 401

    def test_decode_tampered_token_raises(self):
        from backend.auth_utils import create_access_token, decode_token
        from fastapi import HTTPException
        token = create_access_token("abc123", "test@test.com")
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(HTTPException):
            decode_token(tampered)

    def test_different_users_get_different_tokens(self):
        from backend.auth_utils import create_access_token
        t1 = create_access_token("user1", "a@test.com")
        t2 = create_access_token("user2", "b@test.com")
        assert t1 != t2

    def test_same_user_tokens_are_unique_over_time(self):
        """Tokens include iat (issued-at) so they differ even for same user."""
        import time
        from backend.auth_utils import create_access_token
        t1 = create_access_token("user1", "a@test.com")
        time.sleep(1)
        t2 = create_access_token("user1", "a@test.com")
        # payload differs due to iat
        assert t1 != t2


class TestAuthMeEndpoint:

    @pytest.mark.asyncio
    async def test_get_me_returns_user(self, client, registered_user):
        user, token = registered_user
        resp = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == user["email"]
        assert data["name"]  == user["name"]
        assert "id" in data

    @pytest.mark.asyncio
    async def test_get_me_without_token_returns_401(self, client):
        resp = await client.get("/auth/me")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_with_bad_token_returns_401(self, client):
        resp = await client.get(
            "/auth/me",
            headers={"Authorization": "Bearer totally.fake.token"}
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_with_expired_token_returns_401(self, client):
        from jose import jwt
        from datetime import timedelta
        payload = {
            "sub": "507f1f77bcf86cd799439011",
            "email": "expired@test.com",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # already expired
            "iat": datetime.now(timezone.utc) - timedelta(hours=2)
        }
        expired_token = jwt.encode(payload, "test-secret-key-for-testing-only", algorithm="HS256")
        resp = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_returns_streak_and_entries(self, client, registered_user):
        user, token = registered_user
        resp = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        data = resp.json()
        assert "streak" in data
        assert "total_entries" in data
        assert isinstance(data["streak"], int)
        assert isinstance(data["total_entries"], int)


class TestMultiUserIsolation:

    @pytest.mark.asyncio
    async def test_five_users_have_unique_tokens(self, multi_users):
        tokens = [token for _, token in multi_users]
        assert len(set(tokens)) == 5  # all unique

    @pytest.mark.asyncio
    async def test_each_user_gets_own_profile(self, client, multi_users):
        for user, token in multi_users:
            resp = await client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert resp.status_code == 200
            assert resp.json()["email"] == user["email"]

    @pytest.mark.asyncio
    async def test_user_a_token_cannot_access_user_b_data(self, multi_users):
        """Decode user A token — should get user A's ID, not user B's."""
        from backend.auth_utils import decode_token
        (user_a, token_a), (user_b, token_b) = multi_users[0], multi_users[1]
        payload_a = decode_token(token_a)
        payload_b = decode_token(token_b)
        assert payload_a["sub"] != payload_b["sub"]
        assert payload_a["email"] != payload_b["email"]