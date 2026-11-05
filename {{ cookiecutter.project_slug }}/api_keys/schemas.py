from datetime import datetime

from ninja import Field, Schema

from api_keys.models import UserApiKey


class ApiKeyOut(Schema):
    id: int
    name: str
    prefix: str
    created_at: datetime
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None


class ApiKeyCreateIn(Schema):
    name: str = Field(
        max_length=UserApiKey.NAME_MAX_LENGTH,
        description=(
            "Label for the key, bounded at the model's column width of "
            f"{UserApiKey.NAME_MAX_LENGTH} characters."
        ),
    )


class ApiKeyMintOut(Schema):
    api_key: ApiKeyOut
    raw_token: str
