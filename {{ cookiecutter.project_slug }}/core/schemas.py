from ninja import Schema


class MeOut(Schema):
    """The current user, for the SPA boot payload and headless ``whoami``.

    Per-user boot data travels through the typed API rather than an untyped
    ``window`` global; build-time constants (e.g. project name) are
    server-rendered instead. See ADR-0006. Grow as the SPA needs it
    (email, is_staff, …) — each field stays inside the OpenAPI contract.
    """

    username: str
