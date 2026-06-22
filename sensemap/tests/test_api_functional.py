from django.test import TestCase

from .models import Location

# Test class for Location model
class LocationModelTests(TestCase):
    def test_str_returns_name(self):
        loc = Location.objects.create(name="Library", latitude=57.16, longitude=-2.10)
        self.assertEqual(str(loc), "Library")


# Test class for Location API
class LocationAPITests(TestCase):
    def setUp(self):
        Location.objects.create(
            name="Quiet Room", category="quiet", latitude=57.16, longitude=-2.10,
            auditory=1, is_quiet_zone=True,
        )

    def test_list_locations_returns_data(self):
        response = self.client.get("/api/locations/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Quiet Room")

    def test_create_location(self):
        payload = {
            "name": "New Cafe", "category": "food",
            "latitude": 57.165, "longitude": -2.101,
            "auditory": 3, "visual": 2, "olfactory": 3,
            "thermal": 3, "vestibular": 2, "is_quiet_zone": False,
        }
        response = self.client.post(
            "/api/locations/", data=payload, content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Location.objects.count(), 2)
