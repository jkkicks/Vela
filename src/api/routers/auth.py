"""Authentication router with Discord OAuth"""

from fastapi import APIRouter, Request, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from httpx import AsyncClient
from urllib.parse import urlencode
from jose import jwt, JWTError
from datetime import datetime, timedelta
from pathlib import Path
import secrets
import logging

from src.shared.database import get_session
from src.shared.models import AdminUser
from src.shared.config import settings

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "templates"))

router = APIRouter()

# Store CSRF tokens (in production, use Redis or similar)
csrf_tokens = {}


def create_jwt_token(data: dict, expires_delta: timedelta = timedelta(hours=24)):
    """Create a JWT token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.api_secret_key, algorithm="HS256")
    return encoded_jwt


def decode_jwt_token(token: str):
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, settings.api_secret_key, algorithms=["HS256"])
        return payload
    except JWTError:
        raise HTTPException(401, "Invalid authentication token")


async def get_current_user(request: Request):
    """Get current user from JWT cookie"""
    token = request.cookies.get("auth_token")
    if not token:
        raise HTTPException(401, "Not authenticated")

    try:
        payload = decode_jwt_token(token)
        return payload
    except Exception:
        raise HTTPException(401, "Invalid authentication")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Display login page"""
    # Check if Discord OAuth is configured
    if not settings.discord_client_id or not settings.discord_client_secret:
        return templates.TemplateResponse(
            "pages/login.html",
            {"request": request, "title": "Login", "oauth_configured": False},
        )

    return templates.TemplateResponse(
        "pages/login.html",
        {"request": request, "title": "Login", "oauth_configured": True},
    )


@router.get("/discord")
async def discord_login():
    """Initiate Discord OAuth flow"""
    if not settings.discord_client_id:
        raise HTTPException(500, "Discord OAuth not configured")

    # Generate CSRF token
    state = secrets.token_urlsafe(32)
    csrf_tokens[state] = datetime.utcnow()

    # Clean old tokens (older than 10 minutes)
    cutoff = datetime.utcnow() - timedelta(minutes=10)
    csrf_tokens_copy = csrf_tokens.copy()
    for token, timestamp in csrf_tokens_copy.items():
        if timestamp < cutoff:
            del csrf_tokens[token]

    params = {
        "client_id": settings.discord_client_id,
        "redirect_uri": settings.discord_redirect_uri,
        "response_type": "code",
        "scope": "identify guilds",
        "state": state,
    }

    discord_url = f"https://discord.com/api/oauth2/authorize?{urlencode(params)}"
    return RedirectResponse(discord_url)


@router.get("/callback")
async def discord_callback(
    code: str, state: str, response: Response, session: Session = Depends(get_session)
):
    """Handle Discord OAuth callback for both regular login and setup"""
    # Check if this is a setup flow (state starts with "setup:")
    is_setup_flow = state.startswith("setup:")

    # Verify CSRF token (check both regular and setup token stores)
    if is_setup_flow:
        # Import setup tokens
        from src.api.routers.setup import setup_csrf_tokens, setup_oauth_sessions

        if state not in setup_csrf_tokens:
            raise HTTPException(400, "Invalid state token")
        del setup_csrf_tokens[state]
    else:
        if state not in csrf_tokens:
            raise HTTPException(400, "Invalid state token")
        del csrf_tokens[state]

    if not settings.discord_client_id or not settings.discord_client_secret:
        raise HTTPException(500, "Discord OAuth not configured")

    async with AsyncClient() as client:
        # Exchange code for token
        token_response = await client.post(
            "https://discord.com/api/oauth2/token",
            data={
                "client_id": settings.discord_client_id,
                "client_secret": settings.discord_client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.discord_redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if token_response.status_code != 200:
            logger.error(f"Token exchange failed: {token_response.text}")
            raise HTTPException(400, "Failed to authenticate with Discord")

        tokens = token_response.json()

        # Get user info
        user_response = await client.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        if user_response.status_code != 200:
            raise HTTPException(400, "Failed to get user info from Discord")

        discord_user = user_response.json()

        # Handle setup flow differently
        if is_setup_flow:
            # Create a temporary setup session
            import secrets
            from src.api.routers.setup import setup_oauth_sessions

            session_id = secrets.token_urlsafe(32)
            setup_oauth_sessions[session_id] = {
                "discord_id": discord_user["id"],
                "username": discord_user["username"],
                "avatar": discord_user.get("avatar"),
                "created_at": datetime.utcnow(),
            }

            # Clean old sessions (older than 1 hour)
            cutoff = datetime.utcnow() - timedelta(hours=1)
            sessions_copy = setup_oauth_sessions.copy()
            for sess_id, sess_data in sessions_copy.items():
                if sess_data.get("created_at", datetime.min) < cutoff:
                    del setup_oauth_sessions[sess_id]

            # Set setup session cookie and redirect back to setup page
            redirect = RedirectResponse(url="/setup", status_code=302)
            redirect.set_cookie(
                key="setup_session",
                value=session_id,
                httponly=True,
                secure=False,  # Set to True in production with HTTPS
                samesite="lax",
                max_age=3600,  # 1 hour
            )

            logger.info(f"User {discord_user['username']} authenticated for setup")
            return redirect

        # Regular login flow
        # Check if user is admin in database
        admin = session.exec(
            select(AdminUser).where(AdminUser.discord_id == int(discord_user["id"]))
        ).first()

        if not admin:
            # Not an admin, deny access
            logger.warning(
                f"Non-admin user attempted login: {discord_user['username']}"
            )
            raise HTTPException(403, "You are not authorized to access this panel")

        # Update last login
        admin.last_login = datetime.utcnow()
        session.commit()

        # Create JWT token
        jwt_token = create_jwt_token(
            {
                "discord_id": discord_user["id"],
                "username": discord_user["username"],
                "avatar": discord_user.get("avatar"),
                "guild_id": admin.guild_id,
                "is_super_admin": admin.is_super_admin,
            }
        )

        # Set cookie and redirect to dashboard
        redirect = RedirectResponse(url="/dashboard", status_code=302)
        redirect.set_cookie(
            key="auth_token",
            value=jwt_token,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
            max_age=86400,  # 24 hours
        )

        logger.info(f"User {discord_user['username']} logged in successfully")
        return redirect


@router.get("/logout")
async def logout(response: Response):
    """Logout user"""
    redirect = RedirectResponse(url="/", status_code=302)
    redirect.delete_cookie("auth_token")
    return redirect


@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    """Get current user info"""
    return current_user
