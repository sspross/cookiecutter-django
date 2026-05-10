from datetime import datetime

from ninja import Schema


class ApiKeyOut(Schema):
    """Wire shape for a UserApiKey row.

    Deliberately omits ``hash`` — the persisted token digest is never
    surfaced to clients, since the only legitimate consumer of the live
    credential is the user who minted it (via the one-shot mint response).
    """

    id: int
    name: str
    prefix: str
    created_at: datetime
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None


class ApiKeyCreateIn(Schema):
    """Body for ``POST /api/api-keys/``."""

    name: str


class ApiKeyMintOut(Schema):
    """Response for ``POST /api/api-keys/`` — the only place the raw token
    is ever returned by the server."""

    api_key: ApiKeyOut
    raw_token: str
