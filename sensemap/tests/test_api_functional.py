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

#API Tests 
    #Retrieve single object
def test_retrieve_single_location(self):
    loc = Location.objects.create(name="Park", latitude=57.1, longitude=-2.1)
    response = self.client.get(f"/api/locations/{loc.id}/")
    self.assertEqual(response.status_code, 200)

    #Update (PUT/PATCH)
def test_update_location(self):
    loc = Location.objects.create(name="Cafe", latitude=57.1, longitude=-2.1)
    response = self.client.patch(
        f"/api/locations/{loc.id}/",
        data={"name": "Cafe Updated"},
        content_type="application/json",
    )
    self.assertEqual(response.status_code, 200)
    loc.refresh_from_db()
    self.assertEqual(loc.name, "Cafe Updated")


    #Delete
def test_delete_location(self):
    loc = Location.objects.create(name="Temp", latitude=57.1, longitude=-2.1)
    response = self.client.delete(f"/api/locations/{loc.id}/")
    self.assertEqual(response.status_code, 204)
    self.assertFalse(Location.objects.filter(id=loc.id).exists())


    #404 for non-existent object
def test_retrieve_nonexistent_location_returns_404(self):
    response = self.client.get("/api/locations/9999/")
    self.assertEqual(response.status_code, 404)


#Negative / invalid-input tests
def test_create_location_missing_required_field_fails(self):
    payload = {"category": "food", "latitude": 57.1, "longitude": -2.1}  # no name
    response = self.client.post("/api/locations/", data=payload, content_type="application/json")
    self.assertEqual(response.status_code, 400)

def test_create_location_invalid_latitude_fails(self):
    payload = {"name": "Bad Place", "latitude": 999, "longitude": -2.1}
    response = self.client.post("/api/locations/", data=payload, content_type="application/json")
    self.assertEqual(response.status_code, 400)

def test_create_location_invalid_sensory_value_fails(self):
    payload = {"name": "Bad Sensory", "latitude": 57.1, "longitude": -2.1, "auditory": 50}
    response = self.client.post("/api/locations/", data=payload, content_type="application/json")
    self.assertEqual(response.status_code, 400)



#Filtering / querying
def test_filter_by_quiet_zone(self):
    response = self.client.get("/api/locations/?is_quiet_zone=true")
    self.assertEqual(response.status_code, 200)
    data = response.json()
    self.assertTrue(all(loc["is_quiet_zone"] for loc in data))

def test_filter_by_category(self):
    response = self.client.get("/api/locations/?category=quiet")



#Auth / permissions
def test_unauthenticated_create_is_rejected(self):
    payload = {"name": "Sneaky", "latitude": 57.1, "longitude": -2.1}
    response = self.client.post("/api/locations/", data=payload, content_type="application/json")
    self.assertIn(response.status_code, [401, 403])