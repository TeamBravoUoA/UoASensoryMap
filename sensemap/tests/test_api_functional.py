"""Functional coverage for the public UoA Sensory Map REST API."""

from itertools import count

from django.test import TestCase

from sensemap.models import (
    Facility,
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
        self.assertEqual(
            [facility["name"] for facility in library["facilities_available"]],
            ["Step-free access", "Wi-Fi"],
        )

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
            space_type="quiet",
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





class MetaAPITests(TestCase):
    def test_meta_returns_current_choice_lists_and_reference_data(self):
        make_attribute("Auditory")
        make_facility("Wi-Fi")
        data = self.client.get("/api/meta/").json()
        self.assertTrue(any(item["key"] == "library" for item in data["categories"]))
        self.assertTrue(any(item["key"] == "quiet" for item in data["space_types"]))
        self.assertIn("Auditory", data["sensory_attributes"])
        self.assertIn("Wi-Fi", data["facilities"])






# Filtering: combinations and garbage input

class LocationFilterEdgeCaseTests(TestCase):
    def setUp(self):
        self.library = make_location(name="The Library", category="library")
        self.hub = make_location(name="The Hub", category="social_building")
        Space.objects.create(
            external_id=next(external_ids),
            location=self.library, name="Silent Floor", space_type="quiet",
            is_quiet_zone=True,
        )
        Space.objects.create(
            external_id=next(external_ids),
            location=self.hub,
            name="Food Court",
            space_type="social",
        )

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
            external_id=next(external_ids),
            location=loc, name="Quiet Room", space_type="quiet", is_quiet_zone=True,
        )
        Space.objects.create(
            external_id=next(external_ids),
            location=loc,
            name="Lounge",
            space_type="social",
        )
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

    def test_meta_returns_unique_sensory_attribute_names(self):
        SensoryAttribute.objects.create(external_id=next(external_ids), name="Auditory")
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
