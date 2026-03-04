from app.models.user import UserResponse


def test_user_response_model():
    user = UserResponse(id="u1", email="a@b.com", name="Test", avatar_url=None, provider="google")
    assert user.email == "a@b.com"
    assert user.provider == "google"
