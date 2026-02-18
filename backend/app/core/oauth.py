from authlib.integrations.httpx_client import AsyncOAuth2Session
from app.core.config import settings


GOOGLE_CLIENT_ID = settings.google_client_id
GOOGLE_CLIENT_SECRET = settings.google_client_secret
GITHUB_CLIENT_ID = settings.github_client_id
GITHUB_CLIENT_SECRET = settings.github_client_secret


async def get_oauth_session(provider: str) -> AsyncOAuth2Session:
    """Get AsyncOAuth2Session for the specified provider."""
    if provider == "google":
        return AsyncOAuth2Session(
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            redirect_uri=f"{settings.backend_url}/auth/oauth/callback/google",
        )
    elif provider == "github":
        return AsyncOAuth2Session(
            client_id=GITHUB_CLIENT_ID,
            client_secret=GITHUB_CLIENT_SECRET,
            redirect_uri=f"{settings.backend_url}/auth/oauth/callback/github",
        )
    else:
        raise ValueError(f"Unknown OAuth provider: {provider}")


GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USERINFO_URL = "https://api.github.com/user"
