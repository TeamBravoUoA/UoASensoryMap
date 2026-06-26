import csv
from pathlib import Path
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction

from sensemap.models import (
    Facility,
    SensoryAttribute,
    Location,
    Space,
    LocationFacility,
    SpaceFacility,
    LocationGalleryImage,
    SpaceSensoryProfile,
)

BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = BASE_DIR / "data"


# ----------------------------
# Helpers
# ----------------------------

def parse_time(value):
    if not value:
        return None

    value = value.strip().lower()

    if value in ["closed", "none", "na"]:
        return None

    value = value.replace("?", "").replace(".", "").strip().upper()

    formats = ["%I %p", "%I:%M %p", "%H:%M"]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue

    return None


def parse_bool(value):
    return str(value).strip().lower() in ["true", "yes", "1"]


def get_int(value):
    try:
        return int(value)
    except:
        return None


def get_float(value):
    try:
        return float(value)
    except:
        return None


def normalize_category(category):
    mapping = {
        "Library": "library",
        "Teaching building": "teaching_building",
        "Conference / Events building": "conference_events",
        "Cultural Space": "cultural_space",
        "Social building": "social_building",
        "Student Services": "student_services",
        "Research / Laboratories": "research_laboratory",
        "Garden": "garden",
    }
    return mapping.get(category.strip(), category.strip().lower())


def load_csv(file_name):
    with open(DATA_DIR / file_name, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


# ----------------------------
# Command
# ----------------------------

class Command(BaseCommand):
    help = "Seed database (clean version)"

    def handle(self, *args, **kwargs):
        with transaction.atomic():
            self.seed_facilities()
            self.seed_sensory_attributes()
            self.seed_locations()
            self.seed_spaces()
            self.seed_location_facilities()
            self.seed_space_facilities()
            self.seed_gallery()
            self.seed_space_sensory_profiles()

        self.stdout.write(self.style.SUCCESS("Database seeded successfully."))

    # ----------------------------
    # Facilities
    # ----------------------------

    def seed_facilities(self):
        rows = load_csv("Facility.csv")

        for row in rows:
            Facility.objects.update_or_create(
                external_id=get_int(row["facility_id"]),
                defaults={
                    "name": row["name"].strip(),
                },
            )

    # ----------------------------
    # Sensory Attributes
    # ----------------------------

    def seed_sensory_attributes(self):
        rows = load_csv("SensoryAttributes.csv")

        for row in rows:
            SensoryAttribute.objects.update_or_create(
                external_id=get_int(row["sensory_attribute_id"]),
                defaults={
                    "name": row["name"].strip(),
                    "description": row.get("description", "").strip(),
                },
            )

    # ----------------------------
    # Locations
    # ----------------------------

    def seed_locations(self):
        rows = load_csv("Location.csv")

        for row in rows:
            Location.objects.update_or_create(
                external_id=get_int(row["location_id"]),
                defaults={
                    "name": row["name"].strip(),
                    "also_known_as": row.get("also_known_as", ""),
                    "category": normalize_category(row["Category"]),
                    "campus": row["campus"].strip().lower().replace(" ", "_"),
                    "description": row.get("location_description", ""),
                    "latitude": get_float(row["latitude"]),
                    "longitude": get_float(row["longitude"]),

                    "weekday_open_time": parse_time(row.get("week_days_opentime")),
                    "weekday_close_time": parse_time(row.get("weekdays_close_time")),
                    "saturday_open_time": parse_time(row.get("Saturday_open_time")),
                    "saturday_close_time": parse_time(row.get("saturday_close_time")),
                    "sunday_holiday_open_time": parse_time(row.get("sunday_holidays_open_time")),
                    "sunday_holiday_close_time": parse_time(row.get("Sunday_holidays_close_time")),

                    "opening_hrs_notes": row.get("opening_hours_note", ""),
                    "id_access_needed": parse_bool(row.get("id_access_needed")),
                    "additional_access_notes": row.get("additional_access_notes", ""),
                    "uoa_map_link": row.get("uoa_map_link", ""),
                },
            )

    # ----------------------------
    # Spaces
    # ----------------------------

    def seed_spaces(self):
        rows = load_csv("Space.csv")

        for row in rows:
            location = Location.objects.get(
                external_id=get_int(row["location_id"])
            )

            Space.objects.update_or_create(
                external_id=get_int(row["space_id"]),
                defaults={
                    "location": location,
                    "name": row["name"].strip(),
                    "space_type": row["space_type"],
                    "description": row.get("description", ""),

                    "weekday_open_time": parse_time(row.get("week_days_opentime")),
                    "weekday_close_time": parse_time(row.get("weekdays_close_time")),
                    "saturday_open_time": parse_time(row.get("Saturday_open_time")),
                    "saturday_close_time": parse_time(row.get("saturday_close_time")),
                    "sunday_holiday_open_time": parse_time(row.get("sunday_holidays_open_time")),
                    "sunday_holiday_close_time": parse_time(row.get("Sunday_holidays_close_time")),

                    "opening_hrs_notes": row.get("opening_hours_note", ""),
                    "sensory_experience": row.get("sensory_experience", ""),
                    "wayfinding": row.get("wayfinding", ""),
                    "is_quiet_zone": parse_bool(row.get("is_quiet_zone")),
                },
            )

    # ----------------------------
    # Location Facilities (FIXED FK)
    # ----------------------------

    def seed_location_facilities(self):
        rows = load_csv("LocationFacility.csv")

        for row in rows:
            location = Location.objects.get(
                external_id=get_int(row["location_id"])
            )
            facility = Facility.objects.get(
                external_id=get_int(row["facility_id"])
            )

            LocationFacility.objects.update_or_create(
                location=location,
                facility=facility,
                defaults={
                    "status": parse_bool(row.get("status")),
                    "notes": row.get("description", ""),
                },
            )

    # ----------------------------
    # Space Facilities (FIXED FK)
    # ----------------------------

    def seed_space_facilities(self):
        rows = load_csv("SpaceFacility.csv")

        for row in rows:
            space = Space.objects.get(
                external_id=get_int(row["space_id"])
            )
            facility = Facility.objects.get(
                external_id=get_int(row["facility_id"])
            )

            SpaceFacility.objects.update_or_create(
                space=space,
                facility=facility,
                defaults={
                    "status": parse_bool(row.get("status")),
                    "notes": row.get("description", ""),
                },
            )

    # ----------------------------
    # Gallery
    # ----------------------------

    def seed_gallery(self):
        rows = load_csv("LocationGalleryImage.csv")

        for row in rows:
            location = Location.objects.get(
                external_id=get_int(row["location_id"])
            )

            LocationGalleryImage.objects.update_or_create(
                location=location,
                image=row.get("image"),
                defaults={
                    "caption": row.get("caption", ""),
                },
            )

    # ----------------------------
    # Space Sensory Profiles (FIXED FK)
    # ----------------------------

    def seed_space_sensory_profiles(self):
        rows = load_csv("SpaceSensoryProfile.csv")

        for row in rows:
            space = Space.objects.get(
                external_id=get_int(row["space_id"])
            )
            attr = SensoryAttribute.objects.get(
                external_id=get_int(row["sensory_attribute_id"])
            )

            SpaceSensoryProfile.objects.update_or_create(
                space=space,
                sensory_attribute=attr,
                defaults={
                    "rating": int(row["space_ratings"]),
                    "notes": row.get("notes", ""),
                },
            )