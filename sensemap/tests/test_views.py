"""Smoke tests for rendered pages and public templates."""

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


class PublicPageTests(TestCase):
    def test_home_page_renders(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_places_page_renders(self):
        response = self.client.get("/places/")
        self.assertEqual(response.status_code, 200)


class PlaceDetailPageTests(TestCase):
    def setUp(self):
        self.location = make_location(name="The Library")

    def test_place_detail_renders_200(self):
        response = self.client.get(f"/place/{self.location.slug}/")
        self.assertEqual(response.status_code, 200)

    def test_place_detail_404_for_missing_slug(self):
        response = self.client.get("/place/no-such-place/")
        self.assertEqual(response.status_code, 404)

    def test_place_detail_includes_location_id_for_js(self):
        response = self.client.get(f"/place/{self.location.slug}/")
        self.assertContains(response, f'id="location-id"')
        self.assertContains(response, f"{self.location.id}")


class SpaceDetailPageTests(TestCase):
    def setUp(self):
        self.location = make_location(name="The Hub")
        self.space = make_space(location=self.location, name="Quiet Room")

    def test_space_detail_renders_200(self):
        response = self.client.get(f"/space/{self.space.id}/")
        self.assertEqual(response.status_code, 200)

    def test_space_detail_renders_for_missing_id(self):
        response = self.client.get("/space/999999/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="space-id"')

    def test_space_detail_includes_space_id_for_js(self):
        response = self.client.get(f"/space/{self.space.id}/")
        self.assertContains(response, 'id="space-id"')
        self.assertContains(response, f"{self.space.id}")


class MetaPageTests(TestCase):
    def test_meta_endpoint_renders(self):
        response = self.client.get("/api/meta/")
        self.assertEqual(response.status_code, 200)

    def test_meta_space_types_have_no_duplicate_labels(self):
        data = self.client.get("/api/meta/").json()
        labels = [item["label"] for item in data["space_types"]]
        self.assertEqual(len(labels), len(set(labels)))
