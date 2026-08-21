"""Model-level unit tests for the UoA Sensory Map app."""

from itertools import count

from django.test import TestCase

from sensemap.models import Facility, Location, Space

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


def make_space(location, **kwargs):
    defaults = {
        "external_id": next(external_ids),
        "location": location,
        "name": "Test Space",
        "space_type": "study",
    }
    defaults.update(kwargs)
    return Space.objects.create(**defaults)


def make_facility(name="Wi-Fi"):
    return Facility.objects.create(external_id=next(external_ids), name=name)


class LocationModelTests(TestCase):
    def test_str_returns_name(self):
        location = make_location(name="Sir Duncan Rice Library")
        self.assertEqual(str(location), "Sir Duncan Rice Library")

    def test_slug_is_auto_generated_on_save(self):
        location = make_location(name="New Library Block")
        self.assertEqual(location.slug, "new-library-block")

    def test_slug_is_unique_forced(self):
        first = make_location(name="Library")
        second = make_location(name="library")
        self.assertNotEqual(first.slug, second.slug)
        self.assertTrue(second.slug.startswith("library-"))


class SpaceModelTests(TestCase):
    def test_str_returns_name(self):
        location = make_location(name="The Hub")
        space = make_space(location=location, name="Silent Floor")
        self.assertEqual(str(space), "Silent Floor")

    def test_space_type_choices_are_unique_labels(self):
        labels = [label for _, label in Space.SpaceType.choices]
        self.assertEqual(len(labels), len(set(labels)))

    def test_food_drink_space_type_label_is_cafeteria(self):
        self.assertEqual(Space.SpaceType.FOOD_DRINK.label, "Cafeteria")


class FacilityModelTests(TestCase):
    def test_str_returns_name(self):
        facility = make_facility("Hearing loop")
        self.assertEqual(str(facility), "Hearing loop")

    def test_name_is_unique(self):
        make_facility("Wi-Fi")
        with self.assertRaises(Exception):
            Facility.objects.create(external_id=next(external_ids), name="Wi-Fi")
