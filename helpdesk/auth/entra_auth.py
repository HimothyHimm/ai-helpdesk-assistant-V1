"""Sign in with Microsoft Entra ID and read the signed-in user's profile.

FLOW: device code flow (via MSAL). The app prints a short code; the user opens
https://microsoft.com/devicelogin in any browser, enters the code, and signs in
with their Microsoft work account. No client secret is involved (this is a
PUBLIC client app), so there is nothing sensitive to store, paste, or leak.

TOKEN CACHE: tokens are cached to a gitignored file at the project root. On each
launch we first try a SILENT sign-in from the cache (no browser); only if there
is no usable cached token do we fall back to the device code flow. So you sign
in once, and subsequent launches sign you in silently until the token expires.

After sign-in we call Microsoft Graph (/me) for the user's own profile.

Graceful degradation, same as the rest of the app: if Entra isn't configured
(missing client/tenant id), or the 'msal'/'requests' packages aren't installed,
sign_in() returns None and the app simply continues unauthenticated.
"""

from dataclasses import dataclass
from pathlib import Path

from config import settings

# Token cache lives at the project root. It holds access/refresh tokens, so it
# MUST stay gitignored (.token_cache.json is added to .gitignore).
_CACHE_PATH = Path(__file__).resolve().parents[2] / ".token_cache.json"


@dataclass
class UserProfile:
    name: str
    email: str
    job_title: str
    department: str


class EntraAuth:
    """Device-code sign-in (with silent token cache) + a Graph profile lookup."""

    def __init__(self):
        self.client_id = settings.AZURE_AUTH_CLIENT_ID
        self.tenant_id = settings.AZURE_AUTH_TENANT_ID
        self.scopes = settings.AZURE_AUTH_SCOPES
        self.configured = settings.entra_auth_configured()

    def _load_cache(self, msal):
        cache = msal.SerializableTokenCache()
        if _CACHE_PATH.exists():
            try:
                cache.deserialize(_CACHE_PATH.read_text())
            except Exception:
                pass  # corrupt/old cache -> ignore it and just sign in again
        return cache

    def _save_cache(self, cache):
        if cache.has_state_changed:
            try:
                _CACHE_PATH.write_text(cache.serialize())
            except Exception:
                pass  # not fatal: worst case we sign in again next launch

    def sign_in(self, prompt=print):
        """Return a UserProfile, or None. Tries silent sign-in, then device code.

        `prompt` is how the device-code instructions get shown (defaults to
        print). Returning None means "carry on unauthenticated".
        """
        if not self.configured:
            return None

        try:
            import msal
        except ImportError:
            prompt("[Sign-in unavailable] the 'msal' package isn't installed.")
            return None

        authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        cache = self._load_cache(msal)
        app = msal.PublicClientApplication(
            self.client_id, authority=authority, token_cache=cache
        )

        result = None
        # 1. Try a SILENT sign-in from a previously cached account (no browser).
        accounts = app.get_accounts()
        if accounts:
            result = app.acquire_token_silent(self.scopes, account=accounts[0])

        # 2. Fall back to the device code flow only if there's no cached token.
        if not result or "access_token" not in result:
            flow = app.initiate_device_flow(scopes=self.scopes)
            if "user_code" not in flow:
                prompt("[Sign-in failed] couldn't start the device code flow.")
                return None
            prompt("\n" + flow["message"] + "\n")
            result = app.acquire_token_by_device_flow(flow)  # blocks until done

        # Persist any new/refreshed tokens for next time.
        self._save_cache(cache)

        if not result or "access_token" not in result:
            err = (
                (result or {}).get("error_description")
                or (result or {}).get("error")
                or "unknown error"
            )
            prompt(f"[Sign-in failed] {err}")
            return None

        return self._fetch_profile(result["access_token"], prompt)

    def _fetch_profile(self, token, prompt):
        """Call Graph /me with the access token and map it to a UserProfile."""
        try:
            import requests
        except ImportError:
            prompt("[Profile unavailable] the 'requests' package isn't installed.")
            return None

        try:
            resp = requests.get(
                settings.GRAPH_ME_ENDPOINT,
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:  # network error, bad token, etc.
            prompt(f"[Profile lookup failed] {exc}")
            return None

        return UserProfile(
            name=data.get("displayName") or "",
            # work accounts often expose the address as userPrincipalName, not mail
            email=data.get("mail") or data.get("userPrincipalName") or "",
            job_title=data.get("jobTitle") or "",
            department=data.get("department") or "",
        )
