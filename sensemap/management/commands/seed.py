import csv
import json
import time
import logging
from pathlib import Path
from datetime import datetime, time
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

# Reference data
FACILITIES = [
    "Wi-Fi",
    "Power outlets",
    "Accessible toilet",
    "Step-free access",
    "Water fountain",
    "Gender-neutral toilet",
    "Hearing loop",
]

SENSORY_ATTRIBUTES = ["Auditory", "Visual", "Olfactory", "Thermal", "Crowding"]

WEEKDAY = (time(8, 0), time(22, 0))
SAT = (time(9, 0), time(17, 0))
SUN = (time(11, 0), time(16, 0))


def hours(loc_kwargs, weekday=WEEKDAY, sat=SAT, sun=SUN):
    loc_kwargs.update(
        weekday_open_time=weekday[0], weekday_close_time=weekday[1],
        saturday_open_time=sat[0], saturday_close_time=sat[1],
        sunday_holiday_open_time=sun[0], sunday_holiday_close_time=sun[1],
    )
    return loc_kwargs


LOCATIONS = [
    {
        "name": "Sir Duncan Rice Library",
        "also_known_as": "The New Library",
        "category": "library",
        "campus": "old_aberdeen",
        "description": "The University's flagship library, opened in 2011, spans seven floors of study, research and social space. The lower floors offer group seating and discussion areas, while the upper floors are increasingly silent, with Level 6 reserved for silent study. Lift and step-free access are available throughout, and the building is open to the public outside exam periods. Sensory environments vary by floor: higher floors are calm and softly lit, while the ground floor and café can be busy and noisy.",
        "sensory_experience": "",
        "wayfinding": "",
        "physical_access": "",
        "latitude": 57.165500, "longitude": -2.099600,
        "id_access_needed": False,
        "uoa_map_link": "https://www.abdn.ac.uk/library/",
        "facilities": {"Wi-Fi": True, "Power outlets": True, "Accessible toilet": True,
                        "Step-free access": True, "Water fountain": True, "Hearing loop": True},
        "sensory": {"Auditory": 2, "Visual": 3, "Olfactory": 1, "Thermal": 3, "Crowding": 3},
        "spaces": [
            {"name": "Level 6 Silent Study", "space_type": "quiet",
             "description": "The top floor of the library is reserved for silent, individual study. Large windows face south towards the city and sea, giving steady natural light and a sense of openness. Desks are spaced apart and conversation is not permitted.",
             "sensory_experience": "Very low noise; soft natural light from large windows; minimal movement and few distractions. A strong choice for people who need predictability and quiet.",
             "is_quiet_zone": True, "is_nd_safe": True,
             "facilities": {"Wi-Fi": True, "Power outlets": True},
             "sensory": {"Auditory": 1, "Visual": 2, "Crowding": 2}},
            {"name": "Ground Floor Group Study", "space_type": "social",
             "description": "A mix of bookable group rooms and open collaborative tables near the main entrance and café. Conversation is expected and the area is designed for teamwork and informal meetings.",
             "sensory_experience": "Chatter, chair movement and bright overhead lighting. Busy at most times of day, peaking during term-time afternoons.",
             "is_quiet_zone": False, "is_nd_safe": False,
             "facilities": {"Wi-Fi": True, "Power outlets": True, "Step-free access": True},
             "sensory": {"Auditory": 4, "Visual": 3, "Crowding": 4}},
            {"name": "Library Help Desk", "space_type": "facility",
             "description": "The main service desk for borrowing, returns, membership and access support. Staff are trained to help with disability-related access needs and can direct you to the nearest lift, accessible toilet or quiet space.",
             "sensory_experience": "Short queues, helpful staff and moderate background noise from the entrance lobby. Well-lit and clearly signed.",
             "is_quiet_zone": False, "is_nd_safe": False,
             "facilities": {"Step-free access": True, "Hearing loop": True},
             "sensory": {"Auditory": 3, "Visual": 3, "Crowding": 3}},
        ],
    },
    {
        "name": "The Hub",
        "also_known_as": "Students' Union Hub",
        "category": "social_building",
        "campus": "old_aberdeen",
        "description": "The Students' Union Hub is the busiest social building on the Old Aberdeen campus. It combines a large food court, bar, lounge seating, event spaces and the Union shop under one roof. It is a natural meeting point between lectures, but the noise and crowding can be intense, especially at lunch. A quieter screened-off lounge is available on the upper level for those who need a calmer space.",
        "sensory_experience": "",
        "wayfinding": "",
        "physical_access": "",
        "latitude": 57.164100, "longitude": -2.101000,
        "facilities": {"Wi-Fi": True, "Power outlets": True, "Accessible toilet": True,
                        "Step-free access": True, "Gender-neutral toilet": True},
        "sensory": {"Auditory": 5, "Visual": 4, "Olfactory": 4, "Thermal": 3, "Crowding": 5},
        "spaces": [
            {"name": "Food Court", "space_type": "food_drink",
             "description": "A large open-plan dining hall with high ceilings, hard surfaces and multiple food outlets. The space is designed for quick throughput, with long tables and bench seating.",
             "sensory_experience": "High noise from voices and kitchen equipment, strong food smells, bright lighting and dense crowds at peak lunch times. Can be overwhelming for people sensitive to noise, smell or crowding.",
             "is_quiet_zone": False, "is_nd_safe": False,
             "facilities": {"Wi-Fi": True, "Step-free access": True},
             "sensory": {"Auditory": 5, "Olfactory": 4, "Crowding": 5}},
            {"name": "Quiet Corner Lounge", "space_type": "quiet",
             "description": "A screened-off soft-seating area on the upper level, away from the main servery and food court. It is not a silent zone, but the screens, lower ceiling and soft furniture reduce the bustle of the rest of the building.",
             "sensory_experience": "Significantly calmer than the food court. Lower lighting, softer acoustics from upholstered seating and fewer people. A useful retreat when the rest of the Hub is too intense.",
             "is_quiet_zone": True, "is_nd_safe": True,
             "facilities": {"Wi-Fi": True, "Power outlets": True},
             "sensory": {"Auditory": 2, "Visual": 2, "Crowding": 2}},
        ],
    },
    {
        "name": "Taylor Building",
        "also_known_as": "",
        "category": "teaching_building",
        "campus": "old_aberdeen",
        "description": "Taylor Building is the main home of the Law School and School of Language, Literature, Music and Visual Culture. It contains a mix of large lecture theatres, medium seminar rooms, staff offices and a dedicated low-stimulation sensory room. The building is an older stone structure with some narrow corridors and stepped entrances, so step-free access is marked clearly at the main entrance.",
        "sensory_experience": "",
        "wayfinding": "",
        "physical_access": "",
        "latitude": 57.164800, "longitude": -2.102500,
        "facilities": {"Wi-Fi": True, "Power outlets": True, "Accessible toilet": True,
                        "Step-free access": True},
        "sensory": {"Auditory": 3, "Visual": 3, "Olfactory": 1, "Thermal": 3, "Crowding": 3},
        "spaces": [
            {"name": "Sensory / Quiet Room", "space_type": "sensory",
             "description": "A purpose-built low-stimulation room available for rest and sensory regulation. It contains soft seating, dimmable lighting, weighted blankets and a door that can be closed for privacy. The room is bookable through the School Office for students with a support plan, but can also be used on a drop-in basis when not booked.",
             "sensory_experience": "Dimmable lighting, soft furnishings, minimal visual clutter and near-silent conditions. Temperature is kept steady. One of the calmest spaces on the Old Aberdeen campus.",
             "is_quiet_zone": True, "is_nd_safe": True,
             "facilities": {"Step-free access": True, "Accessible toilet": True},
             "sensory": {"Auditory": 1, "Visual": 1, "Olfactory": 1, "Crowding": 1}},
        ],
    },
    {
        "name": "Cruickshank Botanic Garden",
        "also_known_as": "The Botanic Garden",
        "category": "garden",
        "campus": "old_aberdeen",
        "description": "Cruickshank Botanic Garden is an eleven-acre green space in the heart of the Old Aberdeen campus. It features mature trees, flower beds, a rock garden, a pond and open lawns. It is free to enter and is a popular place for walking, sitting, eating lunch or taking a break between classes. The sensory experience changes with the seasons and weather, with generally low noise and crowding.",
        "sensory_experience": "",
        "wayfinding": "",
        "physical_access": "",
        "latitude": 57.167500, "longitude": -2.101800,
        "facilities": {"Step-free access": True},
        "sensory": {"Auditory": 2, "Visual": 2, "Olfactory": 2, "Thermal": 4, "Crowding": 1},
        "spaces": [
            {"name": "Lawn & Pond Area", "space_type": "other",
             "description": "A gently sloping lawn with benches facing the central pond and mature trees around the edge. The path is tarmacked and suitable for mobility aids. It catches the afternoon sun and is sheltered from the wind by the surrounding planting.",
             "sensory_experience": "Birdsong, breeze across the water, occasional duck activity and very low crowding. The smell of grass and flowers varies with the season. An excellent low-stimulation outdoor option, though it can be cold or bright depending on the weather.",
             "is_quiet_zone": True, "is_nd_safe": True,
             "facilities": {"Step-free access": True},
             "sensory": {"Auditory": 2, "Visual": 2, "Crowding": 1}},
        ],
    },
    {
        "name": "Fraser Noble Building",
        "also_known_as": "",
        "category": "research_laboratory",
        "campus": "old_aberdeen",
        "description": "Fraser Noble Building houses engineering research labs, teaching labs, project rooms and computing clusters. The building is functional and busy during term, with a constant hum of equipment and frequent movement. The main computing cluster is accessible to engineering students and can be used when no classes are booked in.",
        "sensory_experience": "",
        "wayfinding": "",
        "physical_access": "",
        "latitude": 57.164400, "longitude": -2.103700,
        "facilities": {"Wi-Fi": True, "Power outlets": True, "Accessible toilet": True,
                        "Step-free access": True, "Water fountain": True},
        "sensory": {"Auditory": 3, "Visual": 4, "Olfactory": 2, "Thermal": 4, "Crowding": 3},
        "spaces": [
            {"name": "Computing Cluster", "space_type": "study",
             "description": "An open-access PC cluster with around sixty machines, used for classes, coursework and independent work. It is kept cool because of the equipment and has bright overhead lighting throughout.",
             "sensory_experience": "Steady fan and machine hum, bright fluorescent lighting and moderate visual stimulation from many screens. The temperature can feel cool. Good for focused work if you are comfortable with constant low-level noise.",
             "is_quiet_zone": False, "is_nd_safe": False,
             "facilities": {"Wi-Fi": True, "Power outlets": True},
             "sensory": {"Auditory": 3, "Visual": 4, "Thermal": 4, "Crowding": 3}},
        ],
    },
    {
        "name": "King's Museum",
        "also_known_as": "Old Aberdeen Town House Museum",
        "category": "cultural_space",
        "campus": "old_aberdeen",
        "description": "King's Museum is a small museum in the historic Old Aberdeen Town House on the High Street. It hosts regularly changing exhibitions drawn from the University's collections and is open to the public free of charge. The building is historic, with stone walls, smaller rooms and occasional background music during events, but the overall atmosphere is calm and visually interesting without being overwhelming.",
        "sensory_experience": "",
        "wayfinding": "",
        "physical_access": "",
        "latitude": 57.169000, "longitude": -2.101200,
        "facilities": {"Step-free access": True, "Accessible toilet": True},
        "sensory": {"Auditory": 2, "Visual": 3, "Olfactory": 1, "Thermal": 3, "Crowding": 2},
        "spaces": [
            {"name": "Reading Nook", "space_type": "quiet",
             "description": "A small seating area tucked between two display cases on the upper floor. It is not a formal study space but is suitable for reading, resting or taking a break while visiting the museum.",
             "sensory_experience": "Dim, hushed and very calm. Limited seating means very few people, and the thick walls keep street noise out. Lighting is focused on the displays rather than the seating area, creating a relaxed low-stimulation pocket.",
             "is_quiet_zone": True, "is_nd_safe": True,
             "facilities": {"Step-free access": True},
             "sensory": {"Auditory": 1, "Visual": 2, "Crowding": 1}},
        ],
    },
    {
        "name": "Foresterhill Student Hub",
        "also_known_as": "Medical School Hub",
        "category": "student_services",
        "campus": "foresterhill",
        "description": "Foresterhill Student Hub is the main student support and social space on the health campus. It sits close to the medical and dental schools and offers a blend of study seating, wellbeing services, peer support and a small social area. The environment is quieter than the Old Aberdeen social spaces, reflecting the clinical and placement-focused timetable of the students who use it.",
        "sensory_experience": "",
        "wayfinding": "",
        "physical_access": "",
        "latitude": 57.156400, "longitude": -2.131800,
        "facilities": {"Wi-Fi": True, "Power outlets": True, "Accessible toilet": True,
                        "Step-free access": True, "Gender-neutral toilet": True},
        "sensory": {"Auditory": 3, "Visual": 3, "Olfactory": 2, "Thermal": 3, "Crowding": 3},
        "spaces": [
            {"name": "Wellbeing Quiet Space", "space_type": "sensory",
             "description": "A small, calm room run by the Student Wellbeing team for students who need a break between lectures, labs or placements. The space is unstaffed during open hours but has clear guidelines on the door and an emergency contact number.",
             "sensory_experience": "Soft lighting, acoustic wall panels and a neutral, uncluttered layout. The room is warm and quiet, with curtains that can be drawn to reduce visual input. Suitable for rest, grounding or short decompression breaks.",
             "is_quiet_zone": True, "is_nd_safe": True,
             "facilities": {"Step-free access": True, "Accessible toilet": True},
             "sensory": {"Auditory": 1, "Visual": 1, "Crowding": 2}},
        ],
    },
    {
        "name": "Hillhead Student Village Common Room",
        "also_known_as": "Hillhead Hub",
        "category": "social_building",
        "campus": "hillhead",
        "description": "The Hillhead Common Room is the social hub for students living in the Hillhead Student Village. It is open to residents and their guests and includes a TV lounge, games area, group seating and a small kitchenette. The space is relaxed and can be lively in the evenings, but quieter study pods are available along the back wall for residents who need to work in their own accommodation block.",
        "sensory_experience": "",
        "wayfinding": "",
        "physical_access": "",
        "latitude": 57.146000, "longitude": -2.105000,
        "facilities": {"Wi-Fi": True, "Power outlets": True, "Step-free access": True},
        "sensory": {"Auditory": 4, "Visual": 3, "Olfactory": 2, "Thermal": 3, "Crowding": 4},
        "spaces": [
            {"name": "Games & Social Lounge", "space_type": "social",
             "description": "The main open-plan lounge with a large TV, games consoles, sofas and group tables. The kitchenette is nearby, so food smells and microwave noise are common. Designed for socialising and relaxation.",
             "sensory_experience": "Lively conversation, TV audio and games sounds. Music is sometimes played in the evenings. Lighting is warm and the space is often busiest between 18:00 and 22:00.",
             "is_quiet_zone": False, "is_nd_safe": False,
             "facilities": {"Wi-Fi": True, "Power outlets": True},
             "sensory": {"Auditory": 4, "Visual": 3, "Crowding": 4}},
            {"name": "Study Pods", "space_type": "study",
             "description": "A row of individual study booths along the back wall of the common room, separated from the main lounge by a low partition. Each pod has a desk, chair and power socket. They are not soundproof but offer a degree of visual enclosure.",
             "sensory_experience": "Quieter than the main lounge, with a more enclosed and focused feel. The partition reduces visual distractions and the background noise is muffled. A practical option for residents who need to study without leaving the building.",
             "is_quiet_zone": True, "is_nd_safe": True,
             "facilities": {"Wi-Fi": True, "Power outlets": True},
             "sensory": {"Auditory": 2, "Visual": 2, "Crowding": 2}},
        ],
    },
]
BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = BASE_DIR / "data"

# Mapping dictionaries which converts CSV values into model TextChoices values
CATEGORY_MAP = {
    "Library": "library",
    "Teaching building": "teaching_building",
    "Conference / Events building": "conference_events",
    "Conference / Events Building": "conference_events",
    "Cultural Space": "cultural_space",
    "Social building": "social_building",
    "Student Services": "student_services",
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
    except Exception:
        return None


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

            thumbnail = row.get("thumbnails_image", "").replace("\\", "/")

            self.safe_execute(
                row.get("location_id"),
                Location.objects.update_or_create,
                external_id=parse_int(row["location_id"]),
                defaults={
                    "name": row["name"].strip(),
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
            except Exception:
                logger.error(f"Missing location for space {row['space_id']}")
                if self.skip_errors:
                    continue
                raise

            thumbnail = row.get("thumbnail_image", "").replace("\\", "/")

            self.safe_execute(
                row.get("space_id"),
                Space.objects.update_or_create,
                external_id=parse_int(row["space_id"]),
                defaults={
                    "location": location,
                    "name": row["name"].strip(),
                    "space_type": row["space_type"],
                    "description": row.get("description", ""),
                    "thumbnail_image": thumbnail,
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
            except Exception:
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
            except Exception:
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
            except Exception:
                continue

            image = row.get("image", "").replace("\\", "/")

            self.safe_execute(
                f"{row['location_id']}-{row.get('image')}",
                LocationGalleryImage.objects.update_or_create,
                location=location,
                image=image,
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
            except Exception:
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