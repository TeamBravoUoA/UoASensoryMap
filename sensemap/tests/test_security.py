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