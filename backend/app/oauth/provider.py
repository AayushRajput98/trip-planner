"""Minimal OAuth 2.1 authorization server for the MCP endpoint.

There's no real per-person account system here — three family members share
one secret (config.AUTH_TOKEN, the same one already used for page edits).
"Login" at the /authorize step is a plain HTML form asking for that secret;
a correct submission is what makes this authorization server issue a code.

Everything else — PKCE verification, the DCR request/response shaping, the
actual HTTP plumbing for /authorize, /token, /register, /revoke, and the
/.well-known/oauth-authorization-server discovery document — is handled by
the mcp SDK (see mcp/server/auth/routes.py, verified by reading it directly).
This module supplies only the storage and decisions behind those routes.
"""
import secrets
import time
from html import escape
from typing import Any

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

from .. import storage
from ..auth import check_token

CLIENTS_FILE = "oauth_clients.json"
ACCESS_TOKENS_FILE = "oauth_tokens.json"
REFRESH_TOKENS_FILE = "oauth_refresh_tokens.json"

ACCESS_TOKEN_TTL_SECONDS = 3600
AUTH_CODE_TTL_SECONDS = 300
SUBJECT = "family"

# Pending /authorize -> /consent handoffs, and issued-but-not-yet-exchanged
# authorization codes. Both are short-lived (a browser redirect round-trip,
# seconds to a few minutes) and low-value if lost, so in-memory is fine —
# losing one on a mid-flow redeploy just means the user retries that step.
_pending: dict[str, dict[str, Any]] = {}
_codes: dict[str, dict[str, Any]] = {}


def _now() -> float:
    return time.time()


class TripOAuthProvider(OAuthAuthorizationServerProvider[AuthorizationCode, RefreshToken, AccessToken]):
    def __init__(self, base_url: str, resource_url: str):
        self.base_url = base_url.rstrip("/")
        # This authorization server only ever protects one resource, so a
        # request that omits the RFC 8707 `resource` indicator still gets a
        # token scoped to it — with AuthSettings.validate_token_resource=True,
        # a token with no resource claim would otherwise be rejected outright.
        self.resource_url = resource_url

    # ---- clients (RFC 7591 dynamic client registration) --------------------
    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        raw = storage.load_json(CLIENTS_FILE, {}).get(client_id)
        return OAuthClientInformationFull.model_validate(raw) if raw else None

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        clients = storage.load_json(CLIENTS_FILE, {})
        clients[client_info.client_id] = client_info.model_dump(mode="json")
        storage.save_json(CLIENTS_FILE, clients)

    # ---- authorize: hand off to our own /consent page, not a third party --
    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        txn = secrets.token_urlsafe(24)
        _pending[txn] = {
            "client_id": client.client_id,
            "client_name": client.client_name or client.client_id,
            "state": params.state,
            "scopes": params.scopes or [],
            "code_challenge": params.code_challenge,
            "redirect_uri": str(params.redirect_uri),
            "redirect_uri_provided_explicitly": params.redirect_uri_provided_explicitly,
            "resource": params.resource or self.resource_url,
            "created_at": _now(),
        }
        return f"{self.base_url}/consent?txn={txn}"

    # ---- authorization codes ------------------------------------------------
    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        entry = _codes.get(authorization_code)
        if not entry or entry["client_id"] != client.client_id:
            return None
        if entry["expires_at"] < _now():
            _codes.pop(authorization_code, None)
            return None
        return AuthorizationCode(
            code=authorization_code,
            scopes=entry["scopes"],
            expires_at=entry["expires_at"],
            client_id=entry["client_id"],
            code_challenge=entry["code_challenge"],
            redirect_uri=entry["redirect_uri"],
            redirect_uri_provided_explicitly=entry["redirect_uri_provided_explicitly"],
            resource=entry.get("resource"),
            subject=SUBJECT,
        )

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        _codes.pop(authorization_code.code, None)  # single-use
        return self._issue_tokens(client.client_id, authorization_code.scopes, authorization_code.resource)

    # ---- refresh tokens -------------------------------------------------------
    async def load_refresh_token(self, client: OAuthClientInformationFull, refresh_token: str) -> RefreshToken | None:
        entry = storage.load_json(REFRESH_TOKENS_FILE, {}).get(refresh_token)
        if not entry or entry["client_id"] != client.client_id:
            return None
        return RefreshToken(
            token=refresh_token,
            client_id=entry["client_id"],
            scopes=entry["scopes"],
            expires_at=entry.get("expires_at"),
            resource=entry.get("resource"),
            subject=entry.get("subject"),
        )

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        refresh_tokens = storage.load_json(REFRESH_TOKENS_FILE, {})
        refresh_tokens.pop(refresh_token.token, None)  # rotate: old one dies here
        storage.save_json(REFRESH_TOKENS_FILE, refresh_tokens)
        return self._issue_tokens(client.client_id, scopes or refresh_token.scopes, refresh_token.resource)

    # ---- access tokens -------------------------------------------------------
    async def load_access_token(self, token: str) -> AccessToken | None:
        entry = storage.load_json(ACCESS_TOKENS_FILE, {}).get(token)
        if not entry:
            return None
        if entry.get("expires_at") and entry["expires_at"] < _now():
            return None
        return AccessToken(
            token=token,
            client_id=entry["client_id"],
            scopes=entry["scopes"],
            expires_at=entry.get("expires_at"),
            resource=entry.get("resource"),
            subject=entry.get("subject"),
        )

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        access_tokens = storage.load_json(ACCESS_TOKENS_FILE, {})
        if token.token in access_tokens:
            access_tokens.pop(token.token)
            storage.save_json(ACCESS_TOKENS_FILE, access_tokens)
        refresh_tokens = storage.load_json(REFRESH_TOKENS_FILE, {})
        if token.token in refresh_tokens:
            refresh_tokens.pop(token.token)
            storage.save_json(REFRESH_TOKENS_FILE, refresh_tokens)

    # ---- internal --------------------------------------------------------------
    def _issue_tokens(self, client_id: str, scopes: list[str], resource: str | None) -> OAuthToken:
        access_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)
        expires_at = int(_now()) + ACCESS_TOKEN_TTL_SECONDS

        access_tokens = storage.load_json(ACCESS_TOKENS_FILE, {})
        access_tokens[access_token] = {
            "client_id": client_id,
            "scopes": scopes,
            "expires_at": expires_at,
            "resource": resource,
            "subject": SUBJECT,
        }
        storage.save_json(ACCESS_TOKENS_FILE, access_tokens)

        refresh_tokens = storage.load_json(REFRESH_TOKENS_FILE, {})
        refresh_tokens[refresh_token] = {
            "client_id": client_id,
            "scopes": scopes,
            "expires_at": None,  # long-lived; this is a trusted personal app. /revoke exists.
            "resource": resource,
            "subject": SUBJECT,
        }
        storage.save_json(REFRESH_TOKENS_FILE, refresh_tokens)

        return OAuthToken(
            access_token=access_token,
            token_type="Bearer",
            expires_in=ACCESS_TOKEN_TTL_SECONDS,
            scope=" ".join(scopes) if scopes else None,
            refresh_token=refresh_token,
        )


# ---- the /consent page itself ------------------------------------------------
def _consent_html(client_name: str, txn: str, error: str | None = None) -> str:
    error_html = f'<p style="color:#b3541e">{escape(error)}</p>' if error else ""
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Approve access</title>
<style>
body{{font-family:-apple-system,Segoe UI,sans-serif;max-width:420px;margin:80px auto;padding:0 20px;color:#22201d}}
input{{width:100%;padding:8px;margin:8px 0 16px;box-sizing:border-box;font-size:1rem}}
button{{padding:8px 20px;font-size:1rem;background:#6b1d1d;color:#fff;border:none;border-radius:6px;cursor:pointer}}
</style></head><body>
<h2>Approve access for {escape(client_name)}?</h2>
<p>This lets it read and edit the trip planner, the same as editing the page directly.</p>
{error_html}
<form method="post">
<input type="hidden" name="txn" value="{escape(txn)}">
<label>Shared secret<input type="password" name="secret" autofocus></label>
<button type="submit">Approve</button>
</form>
</body></html>"""


async def handle_consent(request: Request) -> Response:
    """@mcp.custom_route("/consent", methods=["GET", "POST"]) target — see mcp_server.py."""
    if request.method == "GET":
        txn = request.query_params.get("txn")
    else:
        form = await request.form()
        txn_value = form.get("txn")
        txn = txn_value if isinstance(txn_value, str) else None

    entry = _pending.get(txn) if txn else None
    if not entry or entry["created_at"] + AUTH_CODE_TTL_SECONDS < _now():
        return HTMLResponse(
            "<p>This approval link has expired. Please retry connecting from the app.</p>",
            status_code=400,
        )

    if request.method == "GET":
        return HTMLResponse(_consent_html(entry["client_name"], txn))

    form = await request.form()
    secret = form.get("secret")
    if not check_token(secret if isinstance(secret, str) else None):
        return HTMLResponse(
            _consent_html(entry["client_name"], txn, error="Incorrect secret — try again."),
            status_code=401,
        )

    _pending.pop(txn, None)
    code = secrets.token_urlsafe(32)
    _codes[code] = {
        "client_id": entry["client_id"],
        "scopes": entry["scopes"],
        "expires_at": _now() + AUTH_CODE_TTL_SECONDS,
        "code_challenge": entry["code_challenge"],
        "redirect_uri": entry["redirect_uri"],
        "redirect_uri_provided_explicitly": entry["redirect_uri_provided_explicitly"],
        "resource": entry.get("resource"),
    }
    redirect_url = construct_redirect_uri(entry["redirect_uri"], code=code, state=entry.get("state"))
    return RedirectResponse(url=redirect_url, status_code=302)
