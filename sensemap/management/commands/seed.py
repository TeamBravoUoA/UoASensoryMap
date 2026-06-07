"""Seed the database with a few sample campus locations.

Run with:  python manage.py seed
Re-running is safe: it clears existing locations first.
"""

from django.core.management.base import BaseCommand

from sensemap.models import Location

SAMPLE_LOCATIONS = [
    {
        "name": "Sir Duncan Rice Library",
        "description": "Main university library with study floors.",
        "category": "study",
        "latitude": 57.1655,
        "longitude": -2.0996,
        "auditory": 2, "visual": 3, "olfactory": 1, "thermal": 3, "vestibular": 2,
        "is_quiet_zone": True,
    },
    {
        "name": "Hub Food Court",
        "description": "Busy central food court at peak times.",
        "category": "food",
        "latitude": 57.1641,
        "longitude": -2.1010,
        "auditory": 5, "visual": 4, "olfactory": 4, "thermal": 3, "vestibular": 5,
        "is_quiet_zone": False,
    },
    {
        "name": "Taylor Building Quiet Room",
        "description": "Small low-stimulation room for decompression.",
        "category": "quiet",
        "latitude": 57.1648,
        "longitude": -2.1025,
        "auditory": 1, "visual": 1, "olfactory": 1, "thermal": 2, "vestibular": 1,
        "is_quiet_zone": True,
    },
    {
        "name": "Students' Union Lounge",
        "description": "Social space with seating and events.",
        "category": "social",
        "latitude": 57.1639,
        "longitude": -2.0998,
        "auditory": 4, "visual": 4, "olfactory": 2, "thermal": 3, "vestibular": 3,
        "is_quiet_zone": False,
    },
    {
        "name": "Meston Walk Cafe",
        "description": "Quiet cafe with mild background noise.",
        "category": "food",
        "latitude": 57.1652,
        "longitude": -2.1018,
        "auditory": 3, "visual": 2, "olfactory": 3, "thermal": 3, "vestibular": 2,
        "is_quiet_zone": False,
    },
]


class Command(BaseCommand):
    help = "Seed the database with sample campus locations."

    def handle(self, *args, **options):
        Location.objects.all().delete()
        for data in SAMPLE_LOCATIONS:
            Location.objects.create(**data)
        self.stdout.write(
            self.style.SUCCESS(f"Seeded {len(SAMPLE_LOCATIONS)} locations.")
        )
