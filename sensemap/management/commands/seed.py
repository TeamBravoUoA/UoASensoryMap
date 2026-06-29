import csv
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Avg
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
CHECKPOINT_FILE = BASE_DIR / "seed_checkpoint.json"

SAFE_SPACE_THRESHOLD = 2.5
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
    except:
        return None


def parse_float(value):
    try:
        return float(value)
    except:
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
        except:
            continue

    return None


def load_checkpoint():
    if CHECKPOINT_FILE.exists():
        return json.loads(CHECKPOINT_FILE.read_text())
    return {}


def save_checkpoint(data):
    CHECKPOINT_FILE.write_text(json.dumps(data, indent=2))


def retry(fn, *args, **kwargs):
    """Retry database operations on transient failures."""
    for attempt in range(MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except Exception:
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(RETRY_DELAY)


class Command(BaseCommand):
    """
    ETL pipeline for seeding the database from CSV datasets.
    Includes retry logic, logging, and optional error skipping.
    """

    help = "Production-grade ETL seeder"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--skip-errors", action="store_true")

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]
        self.skip_errors = options["skip_errors"]

        self.checkpoint = load_checkpoint()

        logger.info("ETL STARTED")

        with transaction.atomic():
            self.seed_facilities()
            self.seed_sensory_attributes()
            self.seed_locations()
            self.seed_spaces()
            self.seed_location_facilities()
            self.seed_space_facilities()         
            self.seed_location_sensory_profiles()
            self.seed_gallery()
            self.seed_space_sensory_profiles()
            self.update_space_safety()

        logger.info("ETL COMPLETED")

    def safe_execute(self, row_id, fn, *args, **kwargs):
        """Execute DB operation with retry and error handling."""
        try:
            return retry(fn, *args, **kwargs)

        except Exception as e:
            logger.error(f"FAILED ROW | id={row_id} | error={str(e)}")

            if self.skip_errors:
                return None

            raise

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

        for row in tqdm(rows, desc="Sensory Attributes"):
            self.safe_execute(
                row.get("sensory_attribute_id"),
                SensoryAttribute.objects.update_or_create,
                external_id=parse_int(row["sensory_attribute_id"]),
                defaults={
                    "name": row["name"].strip(),
                    "description": row.get("description", ""),
                },
            )

    def seed_locations(self):
        """Seed university locations."""
        rows = load_csv("Location.csv")

        for row in tqdm(rows, desc="Locations"):
            self.safe_execute(
                row.get("location_id"),
                Location.objects.update_or_create,
                external_id=parse_int(row["location_id"]),
                defaults={
                    "name": row["name"].strip(),
                    "category": row["Category"].strip().lower(),
                    "campus": row["campus"].strip().lower(),
                    "latitude": parse_float(row["latitude"]),
                    "longitude": parse_float(row["longitude"]),
                },
            )

    def seed_spaces(self):
        """Seed spaces within locations."""
        rows = load_csv("Space.csv")

        for row in tqdm(rows, desc="Spaces"):
            try:
                location = Location.objects.get(
                    external_id=parse_int(row["location_id"])
                )
            except:
                logger.error(f"Missing location for space {row['space_id']}")
                if self.skip_errors:
                    continue
                raise

            self.safe_execute(
                row.get("space_id"),
                Space.objects.update_or_create,
                external_id=parse_int(row["space_id"]),
                defaults={
                    "location": location,
                    "name": row["name"].strip(),
                    "space_type": row["space_type"],
                },
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
            except:
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
            except:
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
            except:
                continue

            self.safe_execute(
                f"{row['location_id']}-{row.get('image')}",
                LocationGalleryImage.objects.update_or_create,
                location=location,
                image=row.get("image"),
                defaults={"caption": row.get("caption", "")},
            )

    def seed_location_sensory_profiles(self):
        """Compute location-level sensory ratings from space data."""

        from django.db.models import Avg

        locations = Location.objects.all()

        for location in tqdm(locations, desc="Location Sensory Profiles"):

            aggregated = (
                SpaceSensoryProfile.objects
                .filter(space__location=location)
                .values("sensory_attribute")
                .annotate(avg_rating=Avg("rating"))
            )

            for row in aggregated:

                attr_id = row["sensory_attribute"]
                avg_rating = row["avg_rating"]

                self.safe_execute(
                    f"{location.id}-{attr_id}",
                    LocationSensoryProfile.objects.update_or_create,
                    location=location,
                    sensory_attribute_id=attr_id,
                    defaults={
                        "rating": avg_rating,   # ✔ computed value
                        "notes": "Auto-calculated from spaces"
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
            except:
                if self.skip_errors:
                    continue
                raise

            self.safe_execute(
                f"{row['space_id']}-{row['sensory_attribute_id']}",
                SpaceSensoryProfile.objects.update_or_create,
                space=space,
                sensory_attribute=attr,
                defaults={
                    "rating": int(row["space_ratings"]),
                    "notes": row.get("notes", ""),
                },
            )

    def update_space_safety(self):
        """Compute whether spaces are safe for neurodivergent users."""
        spaces = Space.objects.annotate(
            avg_rating=Avg("space_sensory_profiles__rating")
        )

        for space in tqdm(spaces, desc="Safety calc"):
            if space.avg_rating is not None:
                space.is_safe_space_neurodivergent_students = (
                    space.avg_rating <= SAFE_SPACE_THRESHOLD
                )
                space.save(update_fields=["is_safe_space_neurodivergent_students"])