from django.test import TestCase


class APIValidationTests(TestCase):
    def test_create_location_missing_required_fields_is_rejected(self):
        response = self.client.post(
            "/api/locations/",
            data={"name": "Incomplete Location"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
