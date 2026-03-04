"""Authentication router — OAuth login/callback, logout, current user."""

import logging
import uuid

from authlib.integrations.httpx_client import AsyncOAuth2Client
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select

from app.config import get_settings
from app.core.auth import create_access_token
from app.db.engine import get_session
from app.db.models import User
from app.dependencies import get_current_user
from app.models.user import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# OAuth provider configs
PROVIDERS = {
    "google": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "scopes": "openid email profile",
    },
    "github": {
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "scopes": "read:user user:email",
    },
}


@router.get("/login/{provider}")
async def login(provider: str, request: Request):
    """Redirect to OAuth provider consent screen."""
    if provider not in PROVIDERS:
        raise HTTPException(400, f"Unknown provider: {provider}")

    settings = get_settings()
    config = PROVIDERS[provider]

    client_id = getattr(settings, f"{provider}_oauth_client_id")
    client_secret = getattr(settings, f"{provider}_oauth_client_secret")

    if not client_id:
        raise HTTPException(400, f"{provider} OAuth not configured")

    # In development, use app_url (frontend) to route through Vite proxy
    # so cookies are set on the same origin. In production, use the backend URL.
    if settings.is_development:
        redirect_uri = f"{settings.app_url}/api/auth/callback/{provider}"
    else:
        redirect_uri = str(request.base_url).rstrip("/") + f"/api/auth/callback/{provider}"

    client = AsyncOAuth2Client(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
    )

    uri, state = client.create_authorization_url(
        config["authorize_url"],
        scope=config["scopes"],
        prompt="select_account",
    )

    # Store state in cookie for CSRF protection
    response = Response(status_code=307, headers={"Location": uri})
    response.set_cookie("oauth_state", state, httponly=True, max_age=600, samesite="lax")
    return response


@router.get("/callback/{provider}")
async def callback(provider: str, request: Request, response: Response):
    """Handle OAuth callback, create/find user, issue JWT."""
    if provider not in PROVIDERS:
        raise HTTPException(400, f"Unknown provider: {provider}")

    settings = get_settings()
    config = PROVIDERS[provider]

    client_id = getattr(settings, f"{provider}_oauth_client_id")
    client_secret = getattr(settings, f"{provider}_oauth_client_secret")

    if settings.is_development:
        redirect_uri = f"{settings.app_url}/api/auth/callback/{provider}"
    else:
        redirect_uri = str(request.base_url).rstrip("/") + f"/api/auth/callback/{provider}"

    client = AsyncOAuth2Client(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
    )

    # Exchange code for token
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(400, "Missing authorization code")

    # Validate CSRF state
    stored_state = request.cookies.get("oauth_state")
    callback_state = request.query_params.get("state")
    if not stored_state or stored_state != callback_state:
        raise HTTPException(403, "Invalid OAuth state — possible CSRF attack")

    try:
        token = await client.fetch_token(
            config["token_url"],
            code=code,
            grant_type="authorization_code",
        )
    except Exception as exc:
        logger.error("OAuth token exchange failed: %s", exc)
        raise HTTPException(400, "OAuth token exchange failed")

    # Fetch user info
    try:
        resp = await client.get(config["userinfo_url"])
        userinfo = resp.json()
    except Exception as exc:
        logger.error("Failed to fetch user info: %s", exc)
        raise HTTPException(400, "Failed to fetch user info")

    # Extract user details (different per provider)
    if provider == "google":
        email = userinfo.get("email", "")
        name = userinfo.get("name", "")
        avatar = userinfo.get("picture")
    elif provider == "github":
        email = userinfo.get("email", "")
        name = userinfo.get("name") or userinfo.get("login", "")
        avatar = userinfo.get("avatar_url")
        # GitHub may not return email in profile, need separate API call
        if not email:
            try:
                email_resp = await client.get("https://api.github.com/user/emails")
                emails = email_resp.json()
                primary = next((e for e in emails if e.get("primary")), None)
                email = primary["email"] if primary else ""
            except Exception:
                pass
    else:
        raise HTTPException(400, f"Unknown provider: {provider}")

    if not email:
        raise HTTPException(400, "Could not get email from provider")

    # Find or create user in DB
    async for session in get_session(settings):
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                id=str(uuid.uuid4()),
                email=email,
                name=name,
                avatar_url=avatar,
                provider=provider,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        # Create JWT
        jwt_token = create_access_token({
            "sub": user.id,
            "email": user.email,
            "name": user.name,
        })

        # Redirect to frontend with JWT cookie + token in URL for cross-origin
        separator = "&" if "?" in settings.app_url else "?"
        redirect_url = f"{settings.app_url}{separator}token={jwt_token}"
        redirect_response = Response(
            status_code=307,
            headers={"Location": redirect_url},
        )
        cookie_kwargs: dict[str, object] = {
            "httponly": True,
            "max_age": settings.jwt_expire_minutes * 60,
            "samesite": "lax",
            "secure": not settings.is_development,
        }
        if settings.cookie_domain:
            cookie_kwargs["domain"] = settings.cookie_domain
        redirect_response.set_cookie("access_token", jwt_token, **cookie_kwargs)
        redirect_response.delete_cookie("oauth_state")
        return redirect_response


@router.post("/logout")
async def logout(response: Response):
    """Clear the JWT cookie."""
    settings = get_settings()
    if settings.cookie_domain:
        response.delete_cookie("access_token", domain=settings.cookie_domain)
    else:
        response.delete_cookie("access_token")
    return {"status": "logged_out"}


@router.get("/me")
async def me(user: dict | None = Depends(get_current_user)):
    """Return the current authenticated user, or null if not logged in."""
    if not user:
        return {"user": None}
    return {
        "user": {
            "id": user.get("sub"),
            "email": user.get("email"),
            "name": user.get("name"),
        }
    }
