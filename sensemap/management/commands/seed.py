"""Seed the database with sample University of Aberdeen campus data.

Run with:  python manage.py seed
Re-running is safe: it clears the seeded models first, then recreates
Facilities, SensoryAttributes, Locations, Spaces, their profiles/facility
links and a couple of accepted feedback reports.
"""

from datetime import time

from django.core.management.base import BaseCommand
from django.db import transaction

from sensemap.models import (
    Facility,
    SensoryAttribute,
    Location,
    Space,
    LocationFacility,
    SpaceFacility,
    LocationSensoryProfile,
    SpaceSensoryProfile,
    FeedbackReport,
)

# Reference data ------------------------------------------------------------ #
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


class Command(BaseCommand):
    help = "Seed the database with sample UoA campus locations, spaces and reference data."

    @transaction.atomic
    def handle(self, *args, **options):
        # Clear previously seeded rows (order respects FKs).
        FeedbackReport.objects.all().delete()
        SpaceSensoryProfile.objects.all().delete()
        SpaceFacility.objects.all().delete()
        Space.objects.all().delete()
        LocationSensoryProfile.objects.all().delete()
        LocationFacility.objects.all().delete()
        Location.objects.all().delete()
        SensoryAttribute.objects.all().delete()
        Facility.objects.all().delete()

        facilities = {name: Facility.objects.create(name=name) for name in FACILITIES}
        attributes = {
            name: SensoryAttribute.objects.create(name=name) for name in SENSORY_ATTRIBUTES
        }

        space_total = 0
        for entry in LOCATIONS:
            loc = Location.objects.create(
                **hours({
                    "name": entry["name"],
                    "also_known_as": entry.get("also_known_as", ""),
                    "category": entry["category"],
                    "campus": entry["campus"],
                    "description": entry["description"],
                    "latitude": entry["latitude"],
                    "longitude": entry["longitude"],
                    "id_access_needed": entry.get("id_access_needed", False),
                    "uoa_map_link": entry.get("uoa_map_link", ""),
                })
            )

            for fname, status in entry.get("facilities", {}).items():
                LocationFacility.objects.create(
                    location=loc, facility=facilities[fname], status=status
                )

            for attr, rating in entry.get("sensory", {}).items():
                LocationSensoryProfile.objects.create(
                    location=loc, sensory_attribute=attributes[attr], rating=rating
                )

            for sp in entry.get("spaces", []):
                space = Space.objects.create(
                    **hours({
                        "location": loc,
                        "name": sp["name"],
                        "space_type": sp["space_type"],
                        "description": sp.get("description", ""),
                        "sensory_experience": sp.get("sensory_experience", ""),
                        "is_quiet_zone": sp.get("is_quiet_zone", False),
                        "is_safe_space_neurodivergent_students": sp.get("is_nd_safe", False),
                    })
                )
                space_total += 1
                for fname, status in sp.get("facilities", {}).items():
                    SpaceFacility.objects.create(
                        space=space, facility=facilities[fname], status=status
                    )
                for attr, rating in sp.get("sensory", {}).items():
                    SpaceSensoryProfile.objects.create(
                        space=space, sensory_attribute=attributes[attr], rating=rating
                    )

        # A couple of accepted community feedback reports for the detail panel.
        library = Location.objects.get(name="Sir Duncan Rice Library")
        FeedbackReport.objects.create(
            location=library, comment="Level 6 is wonderfully calm in the mornings.",
            is_anonymous=True, status="accepted",
        )
        hub = Location.objects.get(name="The Hub")
        FeedbackReport.objects.create(
            location=hub, comment="Very loud at lunch - try just before noon.",
            is_anonymous=False, reporter_name="A. Student",
            reporter_email="student@abdn.ac.uk", status="accepted",
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(facilities)} facilities, {len(attributes)} sensory attributes, "
                f"{len(LOCATIONS)} locations and {space_total} spaces."
            )
        )
