"""Functional coverage for the public UoA Sensory Map REST API."""

from itertools import count

from django.test import TestCase

from sensemap.models import (
    Facility,
    FeedbackReport,
    Location,
    LocationFacility,
    LocationSensoryProfile,
    SensoryAttribute,
    Space,
)


external_ids = count(1)


def make_location(**kwargs):
    defaults = {
        "external_id": next(external_ids),
        "name": "Test Place",
        "category": "library",
        "campus": "old_aberdeen",
        "latitude": "57.160000",
        "longitude": "-2.100000",
    }
    defaults.update(kwargs)
    return Location.objects.create(**defaults)


def make_facility(name):
    return Facility.objects.create(external_id=next(external_ids), name=name)


def make_attribute(name):
    return SensoryAttribute.objects.create(external_id=next(external_ids), name=name)


class LocationModelTests(TestCase):
    def test_str_returns_name_and_generates_slug(self):
        location = make_location(name="Sir Duncan Rice Library")
        self.assertEqual(str(location), "Sir Duncan Rice Library")
        self.assertEqual(location.slug, "sir-duncan-rice-library")


class LocationListAPITests(TestCase):
    def setUp(self):
        self.library = make_location(name="The Library", category="library")
        self.hub = make_location(
            name="The Hub", category="social_building", campus="foresterhill"
        )
        self.garden = make_location(name="Botanical Garden", category="garden")

        Space.objects.create(
            external_id=next(external_ids),
            location=self.library,
            name="Silent Floor",
            space_type="quiet",
            is_quiet_zone=True,
            is_safe_space_neurodivergent_students=True,
        )
        Space.objects.create(
            external_id=next(external_ids),
            location=self.hub,
            name="Food Court",
            space_type="social",
        )

        self.auditory = make_attribute("Auditory")
        self.visual = make_attribute("Visual")
        LocationSensoryProfile.objects.create(
            location=self.library, sensory_attribute=self.auditory, rating=1
        )
        LocationSensoryProfile.objects.create(
            location=self.library, sensory_attribute=self.visual, rating=2
        )
        LocationSensoryProfile.objects.create(
            location=self.hub, sensory_attribute=self.auditory, rating=5
        )
        LocationSensoryProfile.objects.create(
            location=self.garden, sensory_attribute=self.auditory, rating=3
        )

        self.wifi = make_facility("Wi-Fi")
        self.step_free = make_facility("Step-free access")
        LocationFacility.objects.create(location=self.library, facility=self.wifi, status=True)
        LocationFacility.objects.create(
            location=self.library, facility=self.step_free, status=True
        )
        LocationFacility.objects.create(location=self.hub, facility=self.wifi, status=False)

    def test_list_returns_all_locations(self):
        response = self.client.get("/api/locations/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 3)

    def test_list_item_exposes_derived_fields(self):
        data = self.client.get("/api/locations/").json()
        library = next(item for item in data if item["name"] == "The Library")
        self.assertIn("quiet", library["space_types"])
        self.assertTrue(library["has_quiet_zone"])
        self.assertTrue(library["has_neurodivergent_safe"])
        self.assertEqual(library["category_display"], "Library")
        self.assertEqual(library["facilities_available"], ["Step-free access", "Wi-Fi"])

    def test_filter_by_category(self):
        data = self.client.get("/api/locations/?category=social_building").json()
        self.assertEqual([item["name"] for item in data], ["The Hub"])

    def test_filter_by_sensory_axis_and_maximum_rating(self):
        data = self.client.get("/api/locations/?axis=Auditory&max_rating=2").json()
        self.assertEqual([item["name"] for item in data], ["The Library"])

    def test_filter_by_sensory_axis_and_minimum_rating(self):
        data = self.client.get("/api/locations/?axis=Auditory&min_rating=3").json()
        self.assertEqual(
            {item["name"] for item in data}, {"The Hub", "Botanical Garden"}
        )

    def test_filter_by_sensory_axis_and_exact_rating(self):
        data = self.client.get("/api/locations/?axis=Auditory&rating=3").json()
        self.assertEqual([item["name"] for item in data], ["Botanical Garden"])

    def test_legacy_axis_rating_parameters_remain_supported(self):
        data = self.client.get("/api/locations/?axis=Auditory&level=5").json()
        self.assertEqual([item["name"] for item in data], ["The Hub"])

    def test_invalid_axis_rating_returns_400(self):
        response = self.client.get("/api/locations/?axis=Auditory&max_rating=6")
        self.assertEqual(response.status_code, 400)

    def test_rating_without_axis_returns_400(self):
        response = self.client.get("/api/locations/?rating=2")
        self.assertEqual(response.status_code, 400)

    def test_filter_quiet_only(self):
        data = self.client.get("/api/locations/?quiet=true").json()
        self.assertEqual([item["name"] for item in data], ["The Library"])

    def test_search_matches_name_and_description(self):
        self.garden.description = "A calm outdoor study destination."
        self.garden.save(update_fields=["description"])
        data = self.client.get("/api/locations/?search=outdoor").json()
        self.assertEqual([item["name"] for item in data], ["Botanical Garden"])

    def test_safe_ordering_is_applied(self):
        data = self.client.get("/api/locations/?ordering=-name").json()
        self.assertEqual(
            [item["name"] for item in data],
            ["The Library", "The Hub", "Botanical Garden"],
        )

    def test_unknown_ordering_is_ignored(self):
        response = self.client.get("/api/locations/?ordering=not_a_model_field")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 3)

    def test_filter_by_available_facility_name(self):
        data = self.client.get("/api/locations/?facility=Wi-Fi").json()
        self.assertEqual([item["name"] for item in data], ["The Library"])

    def test_filter_by_multiple_available_facilities(self):
        data = self.client.get("/api/locations/?facility=Wi-Fi,Step-free%20access").json()
        self.assertEqual([item["name"] for item in data], ["The Library"])

    def test_filter_by_available_facility_external_id(self):
        data = self.client.get(f"/api/locations/?facility={self.wifi.external_id}").json()
        self.assertEqual([item["name"] for item in data], ["The Library"])


class LocationDetailAPITests(TestCase):
    def setUp(self):
        self.location = make_location(name="Detail Place")
        facility = make_facility("Hearing loop")
        LocationFacility.objects.create(location=self.location, facility=facility, status=True)
        auditory = make_attribute("Auditory")
        LocationSensoryProfile.objects.create(
            location=self.location, sensory_attribute=auditory, rating=2
        )
        Space.objects.create(
            external_id=next(external_ids),
            location=self.location,
            name="Low stimulation room",
            space_type="sensory",
            is_quiet_zone=True,
        )

    def test_detail_includes_facilities_profiles_and_quiet_zones(self):
        data = self.client.get(f"/api/locations/{self.location.id}/").json()
        self.assertEqual(data["name"], "Detail Place")
        self.assertEqual(data["facilities"][0]["name"], "Hearing loop")
        self.assertEqual(data["sensory_profiles"][0]["attribute"], "Auditory")
        self.assertEqual(data["quiet_zones"][0]["name"], "Low stimulation room")

    def test_detail_404_for_missing_location(self):
        response = self.client.get("/api/locations/999999/")
        self.assertEqual(response.status_code, 404)

    def test_location_api_is_read_only(self):
        response = self.client.post("/api/locations/", data={}, content_type="application/json")
        self.assertEqual(response.status_code, 405)


class FeedbackReportAPITests(TestCase):
    def setUp(self):
        self.location = make_location()
        self.space = Space.objects.create(
            external_id=next(external_ids),
            location=self.location,
            name="Test Space",
            space_type="study",
        )

    def test_report_endpoint_creates_pending_anonymous_report(self):
        response = self.client.post(
            "/api/reports/",
            data={"location": self.location.id, "comment": "Quiet today", "is_anonymous": True},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        report = FeedbackReport.objects.get()
        self.assertEqual(report.status, FeedbackReport.Status.PENDING)

    def test_legacy_feedback_endpoint_is_kept_for_the_existing_frontend(self):
        response = self.client.post(
            "/api/feedback/",
            data={"location": self.location.id, "comment": "Works too"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

    def test_report_requires_exactly_one_target(self):
        response = self.client.post(
            "/api/reports/",
            data={"location": self.location.id, "space": self.space.id, "comment": "Both"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_non_anonymous_report_requires_name_and_email(self):
        response = self.client.post(
            "/api/reports/",
            data={"location": self.location.id, "comment": "Hello", "is_anonymous": False},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_blank_report_comment_is_rejected(self):
        response = self.client.post(
            "/api/reports/",
            data={"location": self.location.id, "comment": "   "},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_client_cannot_set_accepted_status(self):
        response = self.client.post(
            "/api/reports/",
            data={"location": self.location.id, "comment": "Please review", "status": "accepted"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(FeedbackReport.objects.get().status, FeedbackReport.Status.PENDING)


class MetaAPITests(TestCase):
    def test_meta_returns_current_choice_lists_and_reference_data(self):
        make_attribute("Auditory")
        make_facility("Wi-Fi")
        data = self.client.get("/api/meta/").json()
        self.assertTrue(any(item["key"] == "library" for item in data["categories"]))
        self.assertTrue(any(item["key"] == "quiet" for item in data["space_types"]))
        self.assertIn("Auditory", data["sensory_attributes"])
        self.assertIn("Wi-Fi", data["facilities"])
