# Tests for the SPA shell catch-all view used by the WhiteNoise/Appliku
# deploy path.

import pytest


@pytest.mark.django_db
class TestSpaShell:
    def test_root_returns_spa_index(self, client):
        response = client.get("/")
        assert response.status_code == 200
        # The SPA index.html contains the root mount point.
        body = (
            b"".join(response.streaming_content)
            if hasattr(response, "streaming_content")
            else response.content
        )
        assert b'id="root"' in body

    def test_unknown_path_returns_spa_index(self, client):
        response = client.get("/some/client/route")
        assert response.status_code == 200

    def test_admin_is_not_swallowed_by_shell(self, client):
        # The admin should redirect to login, not return the SPA shell.
        response = client.get("/admin/")
        assert response.status_code in (200, 302)
        body = b""
        if hasattr(response, "streaming_content"):
            body = b"".join(response.streaming_content)
        else:
            body = response.content
        assert b'id="root"' not in body
