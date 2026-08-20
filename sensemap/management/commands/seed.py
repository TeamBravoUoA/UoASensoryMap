import csv
import json
import time as _time
import logging
from pathlib import Path
from decimal import Decimal, InvalidOperation
from datetime import datetime, time
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Max
from tqdm import tqdm
from sensemap.models import (
    Facility,
    SensoryAttribute,
    Location,
    Space,
    LocationFacility,
    SpaceFacility,
    LocationGalleryImage,
    LocationSensoryProfile, 
    SpaceSensoryProfile,
)

BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = BASE_DIR / "data"

# Mapping dictionaries which converts CSV values into model TextChoices values
CATEGORY_MAP = {
    "Library": "library",
    "Teaching building": "teaching_building",
    "Teaching Building": "teaching_building",
    "Conference / Events building": "conference_events",
    "Conference / Events Building": "conference_events",
    "Cultural Space": "cultural_space",
    "Social building": "social_building",
    "Social Building": "social_building",
    "Student Services": "student_services",
    "Student Accommodation": "student_accommodation",
    "Research / Laboratories": "research_laboratory",
    "Garden": "garden",
    "Gardens": "garden",
    "Sports Facility": "sports_facility",
    "Support Building": "support_building",
    "Cafe": "cafe",
    "cafe": "cafe",
    "Shop": "shop",
    "Nursery": "nursery",
}

CAMPUS_MAP = {
    "Old Aberdeen": "old_aberdeen",
    "Foresterhill": "foresterhill",
    "Hillhead": "hillhead",
}


MAX_RETRIES = 3
RETRY_DELAY = 1.5


logger = logging.getLogger("etl_seeder")
logger.setLevel(logging.INFO)
handler = logging.FileHandler(BASE_DIR / "etl_seed.log")
formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


def load_csv(file_name):
    """Load CSV file into list of dictionaries."""
    with open(DATA_DIR / file_name, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def parse_int(value):
    try:
        return int(value)
    except Exception:
        return None

def parse_rating(value):
    """Parse and validate a decimal sensory rating between 1 and 5."""
    if value is None or str(value).strip() == "":
        return None

    try:
        rating = Decimal(str(value).strip())
    except (InvalidOperation, TypeError, ValueError):
        return None

    if not Decimal("1.0") <= rating <= Decimal("5.0"):
        raise ValueError(
            f"Rating must be between 1 and 5, received: {value}"
        )

    return rating


def parse_float(value):
    try:
        return float(value)
    except Exception:
        return None


def parse_bool(value):
    return str(value).strip().lower() in ["true", "yes", "1"]


def parse_time(value):
    """Parse inconsistent CSV time formats into Python time objects."""
    if not value:
        return None

    value = value.strip().lower()

    if value in ["closed", "none", "na"]:
        return None

    value = value.replace("?", "").upper()
    formats = ["%I %p", "%I:%M %p", "%H:%M"]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).time()
        except Exception:
            continue

    return None


def retry(fn, *args, **kwargs):
    """Retry database operations on transient failures."""
    for attempt in range(MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except Exception:
            if attempt == MAX_RETRIES - 1:
                raise
            _time.sleep(RETRY_DELAY)


class Command(BaseCommand):
    """
    ETL pipeline for seeding the database from CSV datasets.
    Includes retry logic, logging, and optional error skipping.
    """

    help = "Seed the sensory map database from CSV datasets"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--skip-errors", action="store_true")

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]
        self.skip_errors = options["skip_errors"]

        logger.info("ETL STARTED")

        with transaction.atomic():
            self.seed_facilities()
            self.seed_sensory_attributes()
            self.seed_locations()
            self.seed_spaces()
            self.seed_location_facilities()
            self.seed_space_facilities()
            self.seed_gallery()
            self.seed_space_sensory_profiles()
            self.seed_location_sensory_profiles()

            if self.dry_run:
                transaction.set_rollback(True)
                logger.info("DRY RUN COMPLETED — CHANGES ROLLED BACK")
                self.stdout.write(
                    self.style.WARNING(
                        "Dry run completed; all changes were rolled back."
                    )
                )


        logger.info("ETL COMPLETED")

    def safe_execute(self, row_id, fn, *args, **kwargs):
        """Execute DB operation with retry and error handling inside a savepoint."""
        for attempt in range(MAX_RETRIES):
            try:
                with transaction.atomic():
                    return fn(*args, **kwargs)
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    logger.error(f"FAILED ROW | id={row_id} | error={str(e)}")
                    if self.skip_errors:
                        return None
                    raise
                _time.sleep(RETRY_DELAY)

    def seed_facilities(self):
        """Seed Facility reference data."""
        rows = load_csv("Facility.csv")

        for row in tqdm(rows, desc="Facilities"):
            self.safe_execute(
                row.get("facility_id"),
                Facility.objects.update_or_create,
                external_id=parse_int(row["facility_id"]),
                defaults={"name": row["name"].strip()},
            )

    def seed_sensory_attributes(self):
        """Seed sensory attributes used for evaluation."""
        rows = load_csv("SensoryAttributes.csv")

        """Wipe and rebuild: attribute IDs/names can be remapped in the CSV, and the name field has a UNIQUE constraint, so updates alone can fail when names move between external_ids."""
        SensoryAttribute.objects.all().delete()

        for row in tqdm(rows, desc="Sensory Attributes"):
            self.safe_execute(
                row.get("sensory_attribute_id"),
                SensoryAttribute.objects.update_or_create,
                external_id=parse_int(row["sensory_attribute_id"]),
                defaults={
                    "name": row["name"].strip(),
                    "description": row.get("description", ""),
                    "icon": (
                        row.get("icon", "")
                        .replace("\\", "/")
                        .strip()
                        .lstrip("/")
                    ),
                },
            )

    def _seed_location(self, row):
        """Create or update a Location row, handling external_id and name changes."""
        name = row["name"].strip()
        external_id = parse_int(row["location_id"])
        thumbnail = row.get("thumbnails_image", "").replace("\\", "/").strip().strip("/")

        defaults = {
            "also_known_as": row.get("also_known_as", ""),
            "category": CATEGORY_MAP[row["Category"].strip()],
            "campus": CAMPUS_MAP[row["campus"].strip()],
            "description": row.get("location_description", ""),
            "latitude": parse_float(row["latitude"]),
            "longitude": parse_float(row["longitude"]),
            "weekday_open_time": parse_time(row.get("week_days_opentime")),
            "weekday_close_time": parse_time(row.get("weekdays_close_time")),
            "saturday_open_time": parse_time(row.get("Saturday_open_time")),
            "saturday_close_time": parse_time(row.get("saturday_close_time")),
            "sunday_holiday_open_time": parse_time(row.get("sunday_holidays_open_time")),
            "sunday_holiday_close_time": parse_time(row.get("Sunday_holidays_close_time")),
            "opening_hrs_notes": row.get("opening_hours_note", ""),
            "id_access_needed": parse_bool(row.get("id_access_needed")),
            "additional_access_notes": row.get("additional_access_notes", ""),
            "thumbnail_image": thumbnail,
            "uoa_map_link": row.get("uoa_map_link", ""),
        }

        loc_by_external = Location.objects.filter(external_id=external_id).first()
        loc_by_name = Location.objects.filter(name=name).first()

        if loc_by_external and loc_by_name and loc_by_external.pk == loc_by_name.pk:
            loc = loc_by_external
        elif loc_by_external and loc_by_name:
            # Both the name and the new external_id point to different records.
            # Use a temporary external_id to swap values without hitting
            # the unique constraint.
            old_external_id = loc_by_name.external_id
            temp_id = (Location.objects.aggregate(m=Max('external_id'))['m'] or 0) + 1

            loc_by_external.external_id = temp_id
            loc_by_external.save()

            loc = loc_by_name
            loc.external_id = external_id
            loc.save()

            loc_by_external.external_id = old_external_id
            loc_by_external.save()
        elif loc_by_name:
            loc = loc_by_name
            loc.external_id = external_id
        elif loc_by_external:
            loc = loc_by_external
            loc.name = name
        else:
            loc = Location(name=name, external_id=external_id)

        for attr, value in defaults.items():
            setattr(loc, attr, value)

        loc.save()

    def seed_locations(self):
        """Seed university locations."""
        rows = load_csv("Location.csv")

        for row in tqdm(rows, desc="Locations"):
            self.safe_execute(
                row.get("location_id"),
                self._seed_location,
                row,
            )

    def _seed_space(self, row, location):
        """Create or update a Space row, handling external_id and location/name changes."""
        name = row["name"].strip()
        external_id = parse_int(row["space_id"])
        thumbnail = (
            row.get("thumbnail_image", "")
            .replace("\\", "/")
            .replace("thumnail_images", "thumbnail_images")
            .strip()
            .strip("/")
        )

        defaults = {
            "space_type": row["space_type"],
            "description": row.get("description", ""),
            "latitude": parse_float(row.get("latitude")),
            "longitude": parse_float(row.get("longitude")),
            "floor": row.get("floor", "").strip(),
            "thumbnail_image": thumbnail,
            "weekday_open_time": parse_time(row.get("week_days_opentime")),
            "weekday_close_time": parse_time(row.get("weekdays_close_time")),
            "saturday_open_time": parse_time(row.get("Saturday_open_time")),
            "saturday_close_time": parse_time(row.get("saturday_close_time")),
            "sunday_holiday_open_time": parse_time(row.get("sunday_holidays_open_time")),
            "sunday_holiday_close_time": parse_time(row.get("Sunday_holidays_close_time")),
            "opening_hrs_notes": row.get("opening_hours_note", ""),
            "wayfinding": row.get("wayfinding", ""),
            "is_quiet_zone": parse_bool(row.get("is_quiet_zone")),
            "is_safe_space_neurodivergent_students": parse_bool(row.get("is_safety_space_neurodivergent_students")),
        }

        loc_by_external = Space.objects.filter(external_id=external_id).first()
        loc_by_unique = Space.objects.filter(location=location, name=name).first()

        if loc_by_external and loc_by_unique and loc_by_external.pk == loc_by_unique.pk:
            loc = loc_by_external
        elif loc_by_external and loc_by_unique:
            # Both the (location, name) key and the new external_id point to
            # different records. Use a temporary external_id to swap values
            # without hitting the unique constraint.
            old_external_id = loc_by_unique.external_id
            temp_id = (Space.objects.aggregate(m=Max('external_id'))['m'] or 0) + 1

            loc_by_external.external_id = temp_id
            loc_by_external.save()

            loc = loc_by_unique
            loc.external_id = external_id
            loc.save()

            loc_by_external.external_id = old_external_id
            loc_by_external.save()
        elif loc_by_unique:
            loc = loc_by_unique
            loc.external_id = external_id
        elif loc_by_external:
            loc = loc_by_external
            loc.location = location
            loc.name = name
        else:
            loc = Space(location=location, name=name, external_id=external_id)

        for attr, value in defaults.items():
            setattr(loc, attr, value)

        loc.save()

    def seed_spaces(self):
        """Seed spaces within locations."""
        rows = load_csv("Space.csv")

        for row in tqdm(rows, desc="Spaces"):
            try:
                location = Location.objects.get(
                    external_id=parse_int(row["location_id"])
                )
            except Location.DoesNotExist:
                logger.error(
                    f"Missing location {row.get('location_id')} "
                    f"for space {row.get('space_id')}"
                )
                if self.skip_errors:
                    continue
                raise

            thumbnail = (
                row.get("thumbnail_image", "")
                .replace("\\", "/")
                .replace("thumnail_images", "thumbnail_images")
                .strip()
                .strip("/")
            )

            self.safe_execute(
                row.get("space_id"),
                self._seed_space,
                row,
                location,
            )
    

    def seed_location_facilities(self):
        """Seed facility availability for each location."""
        rows = load_csv("LocationFacility.csv")

        for row in tqdm(rows, desc="Location Facilities"):
            try:
                location = Location.objects.get(
                    external_id=parse_int(row["location_id"])
                )
                facility = Facility.objects.get(
                    external_id=parse_int(row["facility_id"])
                )
            except (Location.DoesNotExist, Facility.DoesNotExist) as exc:
                logger.error(
                    f"Missing relationship object for location "
                    f"{row.get('location_id')} and facility "
                    f"{row.get('facility_id')}: {exc}"
                )
                if self.skip_errors:
                    continue
                raise

            self.safe_execute(
                f"{row['location_id']}-{row['facility_id']}",
                LocationFacility.objects.update_or_create,
                location=location,
                facility=facility,
                defaults={
                    "status": parse_bool(row.get("status")),
                    "notes": row.get("notes", ""),
                },
            )


    def seed_space_facilities(self):
        """Seed facility availability for each space."""
        rows = load_csv("SpaceFacility.csv")

        for row in tqdm(rows, desc="Space Facilities"):
            try:
                space = Space.objects.get(
                    external_id=parse_int(row["space_id"])
                )
                facility = Facility.objects.get(
                    external_id=parse_int(row["facility_id"])
                )
            except (Space.DoesNotExist, Facility.DoesNotExist) as exc:
                logger.error(
                    f"Missing relationship object for space "
                    f"{row.get('space_id')} and facility "
                    f"{row.get('facility_id')}: {exc}"
                )
                if self.skip_errors:
                    continue
                raise

            self.safe_execute(
                f"{row['space_id']}-{row['facility_id']}",
                SpaceFacility.objects.update_or_create,
                space=space,
                facility=facility,
                defaults={
                    "status": parse_bool(row.get("status")),
                    "notes": row.get("notes", ""),
                },
            )

    def seed_gallery(self):
        """Seed location gallery images."""
        rows = load_csv("LocationGalleryImage.csv")

        for row in tqdm(rows, desc="Gallery"):
            try:
                location = Location.objects.get(
                    external_id=parse_int(row["location_id"])
                )
            except Location.DoesNotExist:
                logger.error(
                    f"Missing location {row.get('location_id')} for gallery image "
                    f"{row.get('image')}"
                )
                if self.skip_errors:
                    continue
                raise

            image = row.get("image", "").replace("\\", "/")

            self.safe_execute(
                f"{row['location_id']}-{row.get('image')}",
                LocationGalleryImage.objects.update_or_create,
                location=location,
                image=image,
                defaults={"caption": row.get("caption", "") or ""},
            )

    def seed_location_sensory_profiles(self):
        """Seed sensory ratings for locations from CSV."""
        rows = load_csv("LocationSensoryProfile.csv")

        for row in tqdm(rows, desc="Location Sensory Profiles"):
            try:
                location = Location.objects.get(
                    external_id=parse_int(row["location_id"])
                )
                attr = SensoryAttribute.objects.get(
                    external_id=parse_int(row["sensory_attribute_id"])
                )
            except (
                Location.DoesNotExist,
                SensoryAttribute.DoesNotExist
            ) as exc:
                logger.error(
                    f"Missing relationship object for location "
                    f"{row.get('location_id')} and sensory attribute "
                    f"{row.get('sensory_attribute_id')}: {exc}"
                )
                if self.skip_errors:
                    continue
                raise

            # Skip rows with missing ratings
            rating = parse_rating(row.get("location_rating"))
            if rating is None:
                continue

            self.safe_execute(
                f"{row['location_id']}-{row['sensory_attribute_id']}",
                LocationSensoryProfile.objects.update_or_create,
                location=location,
                sensory_attribute=attr,
                defaults={
                    "rating": rating,
                    "notes": row.get("notes", ""),
                },
            )


    def seed_space_sensory_profiles(self):
        """Seed sensory ratings for spaces."""
        rows = load_csv("SpaceSensoryProfile.csv")

        for row in tqdm(rows, desc="Space Sensory Profiles"):
            try:
                space = Space.objects.get(
                    external_id=parse_int(row["space_id"])
                )
                attr = SensoryAttribute.objects.get(
                    external_id=parse_int(row["sensory_attribute_id"])
                )
            except (
                Space.DoesNotExist,
                SensoryAttribute.DoesNotExist
            ) as exc:
                logger.error(
                    f"Missing relationship object for space "
                    f"{row.get('space_id')} and sensory attribute "
                    f"{row.get('sensory_attribute_id')}: {exc}"
                )
                if self.skip_errors:
                    continue
                raise

            #Skip rows with missing ratings
            rating = parse_rating(row.get("space_rating"))
            if rating is None:
                continue

            self.safe_execute(
                f"{row['space_id']}-{row['sensory_attribute_id']}",
                SpaceSensoryProfile.objects.update_or_create,
                space=space,
                sensory_attribute=attr,
                defaults={
                    "rating": rating,
                    "notes": row.get("notes", ""),
                },
            )