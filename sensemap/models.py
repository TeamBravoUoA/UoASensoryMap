from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.text import slugify


class ExternalIDModel(models.Model):
    """
    Abstract base model for entities imported from external datasets.
    Provides a consistent external_id across all imported models.
    """
    external_id = models.PositiveIntegerField(unique=True, db_index=True)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    """
    Abstract base model that adds created_at and updated_at fields.
    Used for consistent audit tracking across all models.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Facility(ExternalIDModel, TimeStampedModel):
    """
    A reusable amenity or feature available in Locations and Spaces.
    """

    name = models.CharField(max_length=100, unique=True, db_index=True)

    icon_facility_available = models.ImageField(
        upload_to="images/facilities/icons/",
        blank=True,
        null=True
    )

    icon_facility_unavailable = models.ImageField(
        upload_to="images/facilities/icons/",
        blank=True,
        null=True
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class SensoryAttribute(ExternalIDModel, TimeStampedModel):
    """
    Defines environmental sensory dimensions such as noise, lighting, or temperature.
    """

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Location(ExternalIDModel, TimeStampedModel):
    """
    A physical building or campus location containing multiple Spaces.
    """

    class Campus(models.TextChoices):
        OLD_ABERDEEN = "old_aberdeen", "Old Aberdeen"
        FORESTERHILL = "foresterhill", "Foresterhill"
        HILLHEAD = "hillhead", "Hillhead"

    class Category(models.TextChoices):
        TEACHING_BUILDING = "teaching_building", "Teaching Building"
        CULTURAL_SPACE = "cultural_space", "Cultural Space"
        CONFERENCE_EVENTS = "conference_events", "Conference / Events Building"
        LIBRARY = "library", "Library"
        SOCIAL_BUILDING = "social_building", "Social Building"
        STUDENT_SERVICES = "student_services", "Student Services"
        STUDENT_ACCOMMODATION = "student_accommodation", "Student Accommodation"
        RESEARCH_LABORATORY = "research_laboratory", "Research / Laboratories"
        GARDEN = "garden", "Garden"
        SPORTS_FACILITY = "sports_facility", "Sports Facility"
        SUPPORT_BUILDING = "support_building", "Support Building"
        NURSERY = "nursery", "Nursery"
        SHOP = "shop", "Shop"
        CAFE = "cafe", "Cafe"


    name = models.CharField(max_length=255, unique=True, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    also_known_as = models.CharField(max_length=255, blank=True)

    category = models.CharField(
        max_length=50,
        choices=Category.choices,
        db_index=True,
    )

    campus = models.CharField(
        max_length=50,
        choices=Campus.choices,
        db_index=True,
    )

    description = models.TextField(blank=True)
    sensory_experience = models.TextField(blank=True)
    wayfinding = models.TextField(blank=True)
    physical_access = models.TextField(blank=True)

    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)

    weekday_open_time = models.TimeField(null=True, blank=True)
    weekday_close_time = models.TimeField(null=True, blank=True)
    saturday_open_time = models.TimeField(null=True, blank=True)
    saturday_close_time = models.TimeField(null=True, blank=True)
    sunday_holiday_open_time = models.TimeField(null=True, blank=True)
    sunday_holiday_close_time = models.TimeField(null=True, blank=True)

    opening_hrs_notes = models.TextField(blank=True)

    id_access_needed = models.BooleanField(default=False)
    additional_access_notes = models.TextField(blank=True)

    uoa_map_link = models.URLField(blank=True)

    thumbnail_image = models.ImageField(
        upload_to="images/locations/thumbnail_images/",
        blank=True,
        null=True
    )

    facilities = models.ManyToManyField(
        "Facility",
        through="LocationFacility",
        related_name="locations",
        blank=True
    )

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        """
        Auto-generates a unique slug from the location name.
        Ensures slug uniqueness across the database.
        """
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1

            while self.__class__.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Space(ExternalIDModel, TimeStampedModel):
    """
    A specific functional area within a Location (e.g., study room, quiet zone).
    """

    class SpaceType(models.TextChoices):
        STUDY = "study", "Study Space"
        QUIET = "quiet", "Quiet Space"
        SOCIAL = "social", "Social Space"
        FOOD_DRINK = "food_drink", "Food & Drink"
        SPORT = "sport", "Sport / Fitness"
        OUTDOOR = "outdoor", "Outdoor"


    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="spaces"
    )

    name = models.CharField(max_length=255, db_index=True)
    
    space_type = models.CharField(
        max_length=50,
        choices=SpaceType.choices,
        db_index=True,
    )

    description = models.TextField(blank=True)

    thumbnail_image = models.ImageField(
        upload_to="images/spaces/thumbnail_images/",
        blank=True,
        null=True
    )

    weekday_open_time = models.TimeField(null=True, blank=True)
    weekday_close_time = models.TimeField(null=True, blank=True)
    saturday_open_time = models.TimeField(null=True, blank=True)
    saturday_close_time = models.TimeField(null=True, blank=True)
    sunday_holiday_open_time = models.TimeField(null=True, blank=True)
    sunday_holiday_close_time = models.TimeField(null=True, blank=True)

    opening_hrs_notes = models.TextField(blank=True)

    wayfinding = models.TextField(blank=True)
    sensory_experience = models.TextField(blank=True)

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    floor = models.CharField(
        max_length=50,
        blank=True,
    )

    is_quiet_zone = models.BooleanField(default=False)
    is_safe_space_neurodivergent_students = models.BooleanField(default=False)

    facilities = models.ManyToManyField(
        "Facility",
        through="SpaceFacility",
        related_name="spaces",
        blank=True
    )

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["location", "name"],
                name="unique_space_name_per_location"
            )
        ]

    def __str__(self):
        return self.name


class LocationFacility(TimeStampedModel):
    """
    Links Locations and Facilities with additional metadata.
    """

    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="location_facilities"
    )

    facility = models.ForeignKey(
        Facility,
        on_delete=models.CASCADE,
        related_name="location_facilities"
    )

    status = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["facility__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["location", "facility"],
                name="unique_location_facility"
            )
        ]

    def __str__(self):
        return f"{self.location.name} - {self.facility.name}"


class SpaceFacility(TimeStampedModel):
    """
    Links Spaces and Facilities with additional metadata.
    """

    space = models.ForeignKey(
        Space,
        on_delete=models.CASCADE,
        related_name="space_facilities"
    )

    facility = models.ForeignKey(
        Facility,
        on_delete=models.CASCADE,
        related_name="space_facilities"
    )

    status = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["facility__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["space", "facility"],
                name="unique_space_facility"
            )
        ]

    def __str__(self):
        return f"{self.space.name} - {self.facility.name}"


class LocationGalleryImage(TimeStampedModel):
    """
    Image gallery for Locations.
    """

    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="gallery_images"
    )

    image = models.ImageField(upload_to="images/locations/gallery/", blank=True, null=True)
    caption = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.location.name} Image"


class LocationSensoryProfile(TimeStampedModel):
    """
    Sensory rating profile for a Location.
    """

    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="location_sensory_profiles"
    )

    sensory_attribute = models.ForeignKey(
        SensoryAttribute,
        on_delete=models.CASCADE,
        related_name="location_sensory_profiles"
    )

    rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ],
        null=True,
        blank=True,
    )

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["sensory_attribute__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["location", "sensory_attribute"],
                name="unique_location_sensory_attribute"
            )
        ]

    def __str__(self):
        return f"{self.location.name} - {self.sensory_attribute.name}"


class SpaceSensoryProfile(TimeStampedModel):
    """
    Sensory rating profile for a Space.
    """

    space = models.ForeignKey(
        Space,
        on_delete=models.CASCADE,
        related_name="space_sensory_profiles"
    )

    sensory_attribute = models.ForeignKey(
        SensoryAttribute,
        on_delete=models.CASCADE,
        related_name="space_sensory_profiles"
    )

    rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ]
    )

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["sensory_attribute__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["space", "sensory_attribute"],
                name="unique_space_sensory_attribute"
            )
        ]

    def __str__(self):
        return f"{self.space.name} - {self.sensory_attribute.name}"



class FeedbackSensoryRating(TimeStampedModel):
    """
    User sensory rating feedback tied to either a Location OR a Space.
    """


    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="sensory_feedback"
    )

    space = models.ForeignKey(
        Space,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="sensory_feedback"
    )

    sensory_attribute = models.ForeignKey(
            SensoryAttribute,
            on_delete=models.CASCADE,
            related_name="sensory_feedback"
        )

    rating = models.PositiveSmallIntegerField(
            validators=[
                MinValueValidator(1),
                MaxValueValidator(5)
            ]
        )

    is_anonymous = models.BooleanField(default=True)

    reporter_name = models.CharField(max_length=255, blank=True)
    reporter_email = models.EmailField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        # Require identity only for non-anonymous feedback
        if not self.is_anonymous:
            if not self.reporter_name or not self.reporter_email:
                raise ValidationError(
                    "Name and email are required for non-anonymous feedback."
                )

    def __str__(self):
        if self.space:
            return f"Sensory Rating Feedback - {self.space.name}"
        return f"Sensory Rating Feedback - {self.location.name}"