#security-flavoured tests
from django.test import TestCase, Client

class CSRFEnforcementTests(TestCase):
    def setUp(self):
        self.csrf_client = Client(enforce_csrf_checks=True)

    def test_post_without_csrf_token_rejected(self):
        response = self.csrf_client.post("/some-form-view/", data={...})
        self.assertEqual(response.status_code, 403)