"""Security-flavoured tests for the public API."""

from django.test import TestCase, Client

from sensemap.models import Location


class APISecurityTests(TestCase):
    def setUp(self):
        self.loc = Location.objects.create(
            name="Sec Place", category="library", campus="old_aberdeen",
            latitude=57.16, longitude=-2.10,
        )

    def test_locations_endpoint_is_read_only(self):
        # The public API must not allow mutating curated content.
        res = self.client.post(
            "/api/locations/",
            data={"name": "x", "latitude": 57.1, "longitude": -2.1},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 405)

    def test_post_without_csrf_token_rejected(self):
        response = self.csrf_client.post("/some-form-view/", data={...})
        self.assertEqual(response.status_code, 403)

#1. Authentication and Autherisation tests
# tests/test_authorization.py

import pytest
from django.urls import reverse

@pytest.mark.django_db
def test_non_authenticated_user_cannot_access_admin(client):
    response = client.get("/admin/")
    
    assert response.status_code in [302, 403]


@pytest.mark.django_db
def test_regular_user_cannot_edit_zone(client, regular_user):

    client.force_login(regular_user)

    response = client.get("/admin/zones/5/edit")

    assert response.status_code in [403, 302]

#session cookie security
@pytest.mark.django_db
def test_session_cookie_security(client):

    response = client.get("/")

    cookie = response.cookies.get("sessionid")

    assert cookie["httponly"]
    assert cookie["samesite"] in ["Lax", "Strict"]

#Logout Invalidates session 
@pytest.mark.django_db
def test_logout_invalidates_session(client, user):

    client.force_login(user)

    client.post("/logout/")

    response = client.get("/protected-route/")



#2. XSS testing 
@pytest.mark.django_db
def test_feedback_xss_payload(client):

    payload = "<script>alert('xss')</script>"

    response = client.post(
        "/api/feedback/",
        {
            "comment": payload
        }
    )

    assert response.status_code == 201

#Also verify the rendered output 
response = client.get("/feedback/")

assert "<script>" not in response.content.decode()
assert "&lt;script&gt;" in response.content.decode()


#CMS Content XSS
@pytest.mark.django_db
def test_zone_name_xss(client, admin_user):

    client.force_login(admin_user)

    payload = "<img src=x onerror=alert(1)>"

    client.post(
        "/cms/zones/create/",
        {"name": payload}
    )

    response = client.get("/zones/")

    assert "onerror=" not in response.content.decode()



#3. CSFR Protection 
from django.test import Client

def test_csrf_enabled():

    client = Client(enforce_csrf_checks=True)

    response = client.post(
        "/feedback/",
        {"comment": "test"}
    )

    assert response.status_code == 403



#4. Object-level authorisation 
@pytest.mark.django_db
def test_user_cannot_edit_other_users_zone(
    client,
    user_a,
    user_b,
    zone_owned_by_b
):

    client.force_login(user_a)

    response = client.patch(
        f"/api/zones/{zone_owned_by_b.id}/",
        {"name": "Hacked"},
        content_type="application/json"
    )

    assert response.status_code == 403




#5. Excessive Data Exposure
@pytest.mark.django_db
def test_api_does_not_expose_internal_fields(client):

    response = client.get("/api/zones/1/")

    data = response.json()

    assert "internal_notes" not in data
    assert "admin_flags" not in data
    assert "created_by_email" not in data




#6. File upload testing 
#Reject executables 
from django.core.files.uploadedfile import SimpleUploadedFile

@pytest.mark.django_db
def test_php_upload_rejected(client, admin_user):

    client.force_login(admin_user)

    malicious_file = SimpleUploadedFile(
        "shell.php",
        b"<?php system($_GET['cmd']); ?>"
    )

    response = client.post(
        "/cms/upload/",
        {"file": malicious_file}
    )

    assert response.status_code in [400, 415]


#oversized file
@pytest.mark.django_db
def test_large_file_rejected(client, admin_user):

    client.force_login(admin_user)

    large_file = SimpleUploadedFile(
        "huge.jpg",
        b"x" * (20 * 1024 * 1024)
    )

    response = client.post(
        "/cms/upload/",
        {"file": large_file}
    )

    assert response.status_code == 400



#7. security configuration tests
#Run: Bash
python manage.py check --deploy

#Automate in CI: YAML
- name: Django Security Check
  run: python manage.py check --deploy



#verify production settings 
from django.conf import settings

def test_security_settings():

    assert settings.DEBUG is False
    assert settings.SECURE_SSL_REDIRECT is True
    assert settings.SESSION_COOKIE_SECURE is True
    assert settings.CSRF_COOKIE_SECURE is True




#8. rate limiting test
@pytest.mark.django_db
def test_login_rate_limit(client):

    for _ in range(20):
        client.post(
            "/login/",
            {
                "username": "admin",
                "password": "wrong"
            }
        )

    response = client.post(
        "/login/",
        {
            "username": "admin",
            "password": "wrong"
        }
    )

    assert response.status_code == 429




#9. automated security pipeline: YAML
name: Security Checks

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pip-audit

      - name: Django deploy check
        run: python manage.py check --deploy

      - name: Dependency scan
        run: pip-audit

      - name: Run tests
        run: pytest
    def test_anonymous_feedback_allowed_without_csrf(self):
        # DRF does not enforce CSRF for unauthenticated requests, so anonymous
        # students can submit feedback. It is created as 'pending' (moderated).
        csrf_client = Client(enforce_csrf_checks=True)
        res = csrf_client.post(
            "/api/feedback/",
            data={"location": self.loc.id, "comment": "Calm", "is_anonymous": True},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 201)
