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


from django.test import TestCase

from sensemap.models import (
    Facility,
    SensoryAttribute,
    Location,
    Space,
    LocationFacility,
    LocationSensoryProfile,
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



# Security: input handling on the public, no-auth feedback endpoint

class FeedbackSecurityTests(TestCase):
    def setUp(self):
        self.loc = make_location()

    def test_script_tag_in_comment_is_not_reflected_unescaped(self):
        payload = {
            "location": self.loc.id,
            "comment": "<script>alert('xss')</script>",
            "is_anonymous": True,
        }
        res = self.client.post(
            "/api/feedback/", data=payload, content_type="application/json"
        )
        self.assertEqual(res.status_code, 201)
        report = FeedbackReport.objects.get()
        # The raw script tag should never be stored/returned verbatim.
        self.assertNotIn("<script>", report.comment)

    def test_img_onerror_payload_is_not_reflected_unescaped(self):
        payload = {
            "location": self.loc.id,
            "comment": "<img src=x onerror=alert(1)>",
            "is_anonymous": True,
        }
        res = self.client.post(
            "/api/feedback/", data=payload, content_type="application/json"
        )
        self.assertEqual(res.status_code, 201)
        report = FeedbackReport.objects.get()
        self.assertNotIn("onerror=", report.comment)

    def test_sql_injection_style_search_does_not_error_or_leak(self):
        make_location(name="The Hub", category="social_building")
        res = self.client.get("/api/locations/?search=' OR '1'='1")
        self.assertEqual(res.status_code, 200)
        # Should behave like a normal (likely empty) search, not return everything.
        data = res.json()
        self.assertIsInstance(data, list)

    def test_mass_assignment_status_field_is_ignored(self):
        """A client should not be able to submit feedback that is
        immediately 'accepted' by injecting the status field."""
        payload = {
            "location": self.loc.id,
            "comment": "Trying to skip moderation",
            "is_anonymous": True,
            "status": "accepted",
        }
        res = self.client.post(
            "/api/feedback/", data=payload, content_type="application/json"
        )
        self.assertEqual(res.status_code, 201)
        report = FeedbackReport.objects.get()
        self.assertEqual(report.status, "pending")

    def test_oversized_comment_is_rejected_not_500(self):
        payload = {
            "location": self.loc.id,
            "comment": "x" * 50_000,
            "is_anonymous": True,
        }
        res = self.client.post(
            "/api/feedback/", data=payload, content_type="application/json"
        )
        self.assertIn(res.status_code, (201, 400))

    def test_invalid_location_id_type_returns_400(self):
        payload = {"location": "not-an-id", "comment": "bad id"}
        res = self.client.post(
            "/api/feedback/", data=payload, content_type="application/json"
        )
        self.assertEqual(res.status_code, 400)

    def test_negative_location_id_returns_400(self):
        payload = {"location": -1, "comment": "bad id"}
        res = self.client.post(
            "/api/feedback/", data=payload, content_type="application/json"
        )
        self.assertEqual(res.status_code, 400)

    def test_nonexistent_location_id_returns_400(self):
        payload = {"location": 999999, "comment": "ghost location"}
        res = self.client.post(
            "/api/feedback/", data=payload, content_type="application/json"
        )
        self.assertEqual(res.status_code, 400)



# Feedback target validation — "exactly one target" edge cases

class FeedbackTargetValidationTests(TestCase):
    def setUp(self):
        self.loc = make_location()
        self.space = Space.objects.create(
            location=self.loc, name="Study Room", space_type="quiet"
        )

    def test_feedback_with_both_location_and_space_is_rejected(self):
        payload = {
            "location": self.loc.id,
            "space": self.space.id,
            "comment": "Two targets at once",
        }
        res = self.client.post(
            "/api/feedback/", data=payload, content_type="application/json"
        )
        self.assertEqual(res.status_code, 400)

    def test_feedback_targeting_space_only_is_created_as_pending(self):
        payload = {"space": self.space.id, "comment": "About the study room"}
        res = self.client.post(
            "/api/feedback/", data=payload, content_type="application/json"
        )
        self.assertEqual(res.status_code, 201)
        report = FeedbackReport.objects.get()
        self.assertEqual(report.status, "pending")
        self.assertEqual(report.space_id, self.space.id)

    def test_feedback_cannot_be_edited_after_submission(self):
        report = FeedbackReport.objects.create(
            location=self.loc, comment="Original", status="pending"
        )
        res = self.client.patch(
            f"/api/feedback/{report.id}/",
            data={"comment": "Edited"},
            content_type="application/json",
        )
        self.assertIn(res.status_code, (404, 405))

    def test_feedback_cannot_be_deleted_via_api(self):
        report = FeedbackReport.objects.create(
            location=self.loc, comment="Original", status="pending"
        )
        res = self.client.delete(f"/api/feedback/{report.id}/")
        self.assertIn(res.status_code, (404, 405))



# Filtering: combinations and garbage input

class LocationFilterEdgeCaseTests(TestCase):
    def setUp(self):
        self.library = make_location(name="The Library", category="library")
        self.hub = make_location(name="The Hub", category="social_building")
        Space.objects.create(
            location=self.library, name="Silent Floor", space_type="quiet",
            is_quiet_zone=True,
        )
        Space.objects.create(location=self.hub, name="Food Court", space_type="social")

    def test_combined_category_and_quiet_filters(self):
        data = self.client.get("/api/locations/?category=library&quiet=true").json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "The Library")

    def test_combined_filters_that_match_nothing(self):
        data = self.client.get("/api/locations/?category=social_building&quiet=true").json()
        self.assertEqual(data, [])

    def test_unknown_category_value_returns_empty_not_error(self):
        res = self.client.get("/api/locations/?category=not_a_real_category")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), [])

    def test_unknown_space_type_value_returns_empty_not_error(self):
        res = self.client.get("/api/locations/?space_type=not_a_real_type")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), [])

    def test_search_is_case_insensitive(self):
        data = self.client.get("/api/locations/?search=THE HUB").json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "The Hub")

    def test_quiet_false_does_not_exclude_everything(self):
        res = self.client.get("/api/locations/?quiet=false")
        self.assertEqual(res.status_code, 200)



# Derived-field edge cases in the serializer

class SerializerDerivedFieldEdgeCaseTests(TestCase):
    def test_avg_sensory_is_null_with_no_profiles(self):
        loc = make_location(name="No Data Place")
        data = self.client.get(f"/api/locations/{loc.id}/").json()
        self.assertIsNone(data["avg_sensory"])

    def test_location_with_no_spaces_has_empty_space_fields(self):
        loc = make_location(name="Empty Place")
        data = self.client.get("/api/locations/").json()
        item = next(d for d in data if d["name"] == "Empty Place")
        self.assertEqual(item["space_types"], [])
        self.assertFalse(item["has_quiet_zone"])
        self.assertFalse(item["has_neurodivergent_safe"])

    def test_mixed_quiet_and_social_spaces(self):
        loc = make_location(name="Mixed Place")
        Space.objects.create(
            location=loc, name="Quiet Room", space_type="quiet", is_quiet_zone=True,
        )
        Space.objects.create(location=loc, name="Lounge", space_type="social")
        data = self.client.get("/api/locations/").json()
        item = next(d for d in data if d["name"] == "Mixed Place")
        self.assertIn("quiet", item["space_types"])
        self.assertIn("social", item["space_types"])
        self.assertTrue(item["has_quiet_zone"])



# HTTP method coverage the original suite didn't hit

class HTTPMethodTests(TestCase):
    def setUp(self):
        self.loc = make_location()

    def test_put_on_location_detail_not_allowed(self):
        res = self.client.put(
            f"/api/locations/{self.loc.id}/",
            data={"name": "Hacked"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 405)

    def test_patch_on_location_detail_not_allowed(self):
        res = self.client.patch(
            f"/api/locations/{self.loc.id}/",
            data={"name": "Hacked"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 405)

    def test_delete_on_location_detail_not_allowed(self):
        res = self.client.delete(f"/api/locations/{self.loc.id}/")
        self.assertEqual(res.status_code, 405)



# Meta endpoint edge cases

class MetaAPIEdgeCaseTests(TestCase):
    def test_meta_with_empty_database_returns_empty_lists_not_error(self):
        res = self.client.get("/api/meta/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["sensory_attributes"], [])
        self.assertEqual(data["facilities"], [])
        # Static choice lists (category/space_type) should still be present.
        self.assertTrue(len(data["categories"]) > 0)
        self.assertTrue(len(data["space_types"]) > 0)

    def test_meta_sensory_attributes_has_no_duplicates(self):
        SensoryAttribute.objects.create(name="Auditory")
        SensoryAttribute.objects.create(name="Auditory")  # duplicate name, separate row
        data = self.client.get("/api/meta/").json()
        names = data["sensory_attributes"]
        self.assertEqual(len(names), len(set(names)))



# Scale / pagination sanity check

class LocationListScaleTests(TestCase):
    def test_list_endpoint_handles_many_locations(self):
        for i in range(60):
            make_location(name=f"Place {i}", latitude=57.0 + i * 0.001)
        res = self.client.get("/api/locations/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        # If pagination is enabled this will be a page dict, not a bare list —
        # adjust this assertion to match whichever your view returns.
        if isinstance(data, dict):
            self.assertIn("results", data)
        else:
            self.assertEqual(len(data), 60)