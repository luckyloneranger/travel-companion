import pytest
from httpx import AsyncClient

from app.core.auth import create_access_token, decode_access_token
from app.models.user import UserResponse


def test_user_response_model():
    user = UserResponse(id="u1", email="a@b.com", name="Test", avatar_url=None, provider="google")
    assert user.email == "a@b.com"
    assert user.provider == "google"


def test_jwt_roundtrip():
    token = create_access_token({"sub": "user-123", "email": "a@b.com"})
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["email"] == "a@b.com"


def test_jwt_invalid_token():
    payload = decode_access_token("invalid-token")
    assert payload is None


def test_jwt_has_expiry():
    token = create_access_token({"sub": "user-123"})
    payload = decode_access_token(token)
    assert "exp" in payload


class TestAuthEndpoints:
    @pytest.mark.asyncio
    async def test_me_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/auth/me")
        assert response.status_code == 200
        assert response.json()["user"] is None

    @pytest.mark.asyncio
    async def test_logout(self, client: AsyncClient):
        response = await client.post("/api/auth/logout")
        assert response.status_code == 200
        assert response.json()["status"] == "logged_out"

    @pytest.mark.asyncio
    async def test_login_unknown_provider(self, client: AsyncClient):
        response = await client.get("/api/auth/login/facebook", follow_redirects=False)
        assert response.status_code == 400
