from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Location(models.Model):
    """A place on campus with its sensory ratings.

    This is the core model of the app. Each sensory axis is rated 1 (calm/low)
    to 5 (intense/high). Keep new fields documented so the team stays in sync.
    """

    CATEGORY_CHOICES = [
        ("study", "Study space"),
        ("social", "Social space"),
        ("quiet", "Quiet zone"),
        ("food", "Food & drink"),
        ("facility", "Facility"),
        ("other", "Other"),
    ]

    # 1 = calm/low stimulation, 5 = intense/high stimulation
    SENSORY_VALIDATORS = [MinValueValidator(1), MaxValueValidator(5)]

    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="other")

    # Location on the map
    latitude = models.FloatField()
    longitude = models.FloatField()

    # Sensory profile (1-5 on each axis)
    auditory = models.PositiveSmallIntegerField(default=3, validators=SENSORY_VALIDATORS)
    visual = models.PositiveSmallIntegerField(default=3, validators=SENSORY_VALIDATORS)
    olfactory = models.PositiveSmallIntegerField(default=3, validators=SENSORY_VALIDATORS)
    thermal = models.PositiveSmallIntegerField(default=3, validators=SENSORY_VALIDATORS)
    vestibular = models.PositiveSmallIntegerField(default=3, validators=SENSORY_VALIDATORS)

    is_quiet_zone = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
