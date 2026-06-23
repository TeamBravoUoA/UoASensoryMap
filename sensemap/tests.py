from django.test import TestCase
from django.urls import reverse

from .models import Location, LocationSensoryProfile, SensoryAttribute, Space


class LocationModelTests(TestCase):
    def test_str_returns_name(self):
        loc = Location.objects.create(
            name="Library",
            category="library",
            campus="old_aberdeen",
            latitude=57.160000,
            longitude=-2.100000,
        )
        self.assertEqual(str(loc), "Library")


class LocationAPITests(TestCase):
    def setUp(self):
        self.auditory = SensoryAttribute.objects.create(
            name="auditory",
            description="Noise level",
        )
        self.visual = SensoryAttribute.objects.create(
            name="visual",
            description="Lighting and visual stimulation",
        )

        self.quiet_room = Location.objects.create(
            name="Quiet Room",
            category="library",
            campus="old_aberdeen",
            latitude=57.160000,
            longitude=-2.100000,
            description="Low stimulation study room.",
        )
        self.busy_cafe = Location.objects.create(
            name="Busy Cafe",
            category="social_building",
            campus="old_aberdeen",
            latitude=57.170000,
            longitude=-2.110000,
            description="Cafe with background noise.",
        )

        Space.objects.create(
            location=self.quiet_room,
            name="Quiet Study Space",
            space_type="quiet",
            is_quiet_zone=True,
        )

        LocationSensoryProfile.objects.create(
            location=self.quiet_room,
            sensory_attribute=self.auditory,
            rating=1,
        )
        LocationSensoryProfile.objects.create(
            location=self.quiet_room,
            sensory_attribute=self.visual,
            rating=2,
        )
        LocationSensoryProfile.objects.create(
            location=self.busy_cafe,
            sensory_attribute=self.auditory,
            rating=5,
        )
        LocationSensoryProfile.objects.create(
            location=self.busy_cafe,
            sensory_attribute=self.visual,
            rating=4,
        )

    def test_list_locations_returns_data(self):
        response = self.client.get("/api/locations/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertIn("created_at", data[0])
        self.assertIn("updated_at", data[0])
        self.assertIn("sensory_profiles", data[0])

    def test_locations_route_is_registered(self):
        response = self.client.get(reverse("location-list"))
        self.assertEqual(response.status_code, 200)

    def test_create_location(self):
        payload = {
            "name": "New Teaching Building",
            "category": "teaching_building",
            "campus": "old_aberdeen",
            "latitude": "57.165000",
            "longitude": "-2.101000",
        }
        response = self.client.post(
            "/api/locations/", data=payload, content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Location.objects.count(), 3)

    def test_filter_locations_by_category(self):
        response = self.client.get("/api/locations/?category=library")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Quiet Room")

    def test_filter_locations_by_quiet_zone(self):
        response = self.client.get("/api/locations/?quiet=true")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Quiet Room")

    def test_filter_locations_by_axis_max_level(self):
        response = self.client.get("/api/locations/?axis=auditory&max_level=2")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Quiet Room")

    def test_filter_locations_by_axis_exact_level(self):
        response = self.client.get("/api/locations/?axis=auditory&level=5")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Busy Cafe")

    def test_filter_locations_by_axis_min_level(self):
        response = self.client.get("/api/locations/?axis=visual&min_level=4")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Busy Cafe")

    def test_filter_locations_by_category_and_axis(self):
        response = self.client.get(
            "/api/locations/?category=social_building&axis=auditory&min_level=4"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Busy Cafe")

    def test_invalid_axis_is_ignored(self):
        response = self.client.get("/api/locations/?axis=unknown&max_level=2")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)

    def test_invalid_axis_level_is_ignored(self):
        response = self.client.get("/api/locations/?axis=auditory&max_level=99")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)

    def test_search_locations_by_name_or_description(self):
        response = self.client.get("/api/locations/?search=study")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Quiet Room")

    def test_order_locations_by_name(self):
        response = self.client.get("/api/locations/?ordering=-name")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data[0]["name"], "Quiet Room")
