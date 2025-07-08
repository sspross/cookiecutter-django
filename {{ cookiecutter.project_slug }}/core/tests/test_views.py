# ABOUTME: Tests for Django views
# ABOUTME: Ensures views are accessible and render correct templates

import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestHomeView:
    def test_home_url_accessible(self, client):
        """Test that home URL is accessible and returns 200 status."""
        url = reverse("home")
        response = client.get(url)
        assert response.status_code == 200

    def test_home_template_used(self, client):
        """Test that home view uses the correct template."""
        url = reverse("home")
        response = client.get(url)
        # With Jinja2, we can't directly check template_name
        # Instead, we verify the response contains expected template content
        assert response.status_code == 200
        # Check for unique content from home.jinja template
        assert b"This is the home page" in response.content

    def test_home_content(self, client):
        """Test that home page contains expected content."""
        url = reverse("home")
        response = client.get(url)
        content = response.content.decode("utf-8")
        # Check for content from the template
        assert "This is the home page" in content
        # Check for base template elements
        assert "<title>" in content
        assert "</html>" in content
