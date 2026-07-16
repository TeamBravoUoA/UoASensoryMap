"""Functional tests for the UoA Sensory Map REST API (rich schema)."""

from django.test import TestCase

from sensemap.models import (
    Facility,
    SensoryAttribute,
    Location,
    Space,
    LocationFacility,
    LocationSensoryProfile,
    SpaceSensoryProfile,
    FeedbackReport,
)


def make_location(**kwargs):
    defaults = {
        "name": "Test Place",
        "category": "library",
        "campus": "old_aberdeen",
        "latitude": 57.16,
        "longitude": -2.10,
    }
    defaults.update(kwargs)
    return Location.objects.create(**defaults)


class LocationModelTests(TestCase):
    def test_str_returns_name(self):
        loc = make_location(name="Library")
        self.assertEqual(str(loc), "Library")


class LocationListAPITests(TestCase):
    def setUp(self):
        self.library = make_location(name="The Library", category="library")
        self.hub = make_location(name="The Hub", category="social_building")
        # A quiet space inside the library.
        Space.objects.create(
            location=self.library, name="Silent Floor", space_type="quiet",
            is_quiet_zone=True, is_safe_space_neurodivergent_students=True,
        )
        # A social space inside the hub.
        Space.objects.create(location=self.hub, name="Food Court", space_type="social")

    def test_list_returns_all_locations(self):
        res = self.client.get("/api/locations/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 2)

    def test_list_item_exposes_derived_fields(self):
        data = self.client.get("/api/locations/").json()
        lib = next(d for d in data if d["name"] == "The Library")
        self.assertIn("quiet", lib["space_types"])
        self.assertTrue(lib["has_quiet_zone"])
        self.assertTrue(lib["has_neurodivergent_safe"])
        self.assertEqual(lib["category_display"], "Library")

    def test_filter_by_category(self):
        data = self.client.get("/api/locations/?category=social_building").json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "The Hub")

    def test_filter_by_space_type(self):
        data = self.client.get("/api/locations/?space_type=quiet").json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "The Library")

    def test_filter_quiet_only(self):
        data = self.client.get("/api/locations/?quiet=true").json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "The Library")

    def test_search(self):
        data = self.client.get("/api/locations/?search=hub").json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "The Hub")


class LocationDetailAPITests(TestCase):
    def setUp(self):
        self.loc = make_location(name="Detail Place")
        wifi = Facility.objects.create(name="Wi-Fi")
        LocationFacility.objects.create(location=self.loc, facility=wifi, status=True)
        for attr in ("Auditory", "Visual", "Crowding"):
            a = SensoryAttribute.objects.create(name=attr)
            LocationSensoryProfile.objects.create(
                location=self.loc, sensory_attribute=a, rating=2
            )

    def test_detail_includes_nested_data(self):
        data = self.client.get(f"/api/locations/{self.loc.id}/").json()
        self.assertEqual(data["name"], "Detail Place")
        self.assertEqual(len(data["facilities"]), 1)
        self.assertEqual(data["facilities"][0]["name"], "Wi-Fi")
        self.assertEqual(len(data["sensory_profiles"]), 3)
        self.assertEqual(data["avg_sensory"], 2.0)

    def test_detail_404_for_missing(self):
        res = self.client.get("/api/locations/999999/")
        self.assertEqual(res.status_code, 404)

    def test_only_accepted_feedback_is_nested(self):
        FeedbackReport.objects.create(location=self.loc, comment="Pending", status="pending")
        FeedbackReport.objects.create(location=self.loc, comment="Yay", status="accepted")
        data = self.client.get(f"/api/locations/{self.loc.id}/").json()
        self.assertEqual(len(data["feedback"]), 1)
        self.assertEqual(data["feedback"][0]["comment"], "Yay")


class LocationReadOnlyTests(TestCase):
    def test_create_via_api_is_not_allowed(self):
        res = self.client.post(
            "/api/locations/",
            data={"name": "Nope", "latitude": 57.1, "longitude": -2.1},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 405)


class FeedbackPageTests(TestCase):
    def test_feedback_page_is_available_without_trailing_slash(self):
        res = self.client.get("/feedback")
        self.assertEqual(res.status_code, 200)


class FeedbackAPITests(TestCase):
    def setUp(self):
        self.loc = make_location()

    def test_anonymous_feedback_created_as_pending(self):
        payload = {"location": self.loc.id, "comment": "Quiet today", "is_anonymous": True}
        res = self.client.post(
            "/api/feedback/", data=payload, content_type="application/json"
        )
        self.assertEqual(res.status_code, 201)
        report = FeedbackReport.objects.get()
        self.assertEqual(report.status, "pending")

    def test_feedback_requires_exactly_one_target(self):
        payload = {"comment": "No target"}
        res = self.client.post(
            "/api/feedback/", data=payload, content_type="application/json"
        )
        self.assertEqual(res.status_code, 400)


class MetaAPITests(TestCase):
    def test_meta_returns_choice_lists(self):
        SensoryAttribute.objects.create(name="Auditory")
        Facility.objects.create(name="Wi-Fi")
        data = self.client.get("/api/meta/").json()
        self.assertTrue(any(c["key"] == "library" for c in data["categories"]))
        self.assertTrue(any(c["key"] == "quiet" for c in data["space_types"]))
        self.assertIn("Auditory", data["sensory_attributes"])
        self.assertIn("Wi-Fi", data["facilities"])