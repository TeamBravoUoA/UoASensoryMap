from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

class Facility(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name
    

class SensoryAttribute(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    

class Location(models.Model):

    CAMPUS_CHOICES = [
        ("old aberdeen", "Old Aberdeen"),
        ("foresterhill", "Foresterhill"),
        ("hillhead", "Hillhead"),
    ]

    name = models.CharField(max_length=255)
    also_known_as = models.CharField(max_length=255, blank=True)
    category = models.CharField(max_length=100)
    campus = models.CharField(max_length=50, choices=CAMPUS_CHOICES)
    description = models.TextField(blank=True)

    latitude = models.FloatField()
    longitude = models.FloatField()

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
        upload_to="locations/thumbnails/",
        blank=True
    )

    facilities = models.ManyToManyField(
        Facility,
        blank=True,
        related_name="locations"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
    
    
class Space(models.Model):
    SPACE_TYPE_CHOICES = [
        ("study", "Study Space"),
        ("quiet", "Quiet Space"),
        ("social", "Social Space"),
        ("sensory", "Sensory Room"),
        ("other", "Other"),
    ]

    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="spaces")

    name = models.CharField(max_length=255)

    space_type = models.CharField(max_length=50, choices=SPACE_TYPE_CHOICES)

    description = models.TextField(blank=True)

    thumbnail_image = models.ImageField(
        upload_to="spaces/thumbnails/",
        blank=True
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

    is_quiet_zone = models.BooleanField(default=False)
    is_safe_space_neurodivergent_students = models.BooleanField(default=False)

    facilities = models.ManyToManyField(
        Facility,
        blank=True,
        related_name="spaces"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
    
    
class LocationGalleryImage(models.Model):
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="gallery_images"
    )

    image = models.ImageField(upload_to="locations/gallery/")
    caption = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.location.name} Image"
    

class LocationSensoryProfile(models.Model):
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="sensory_profiles"
    )

    sensory_attribute = models.ForeignKey(
        SensoryAttribute,
        on_delete=models.CASCADE,
        related_name="location_profiles"
    )

    rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ]
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
    

class SpaceSensoryProfile(models.Model):
    space = models.ForeignKey(
        Space,
        on_delete=models.CASCADE,
        related_name="sensory_profiles"
    )

    sensory_attribute = models.ForeignKey(
        SensoryAttribute,
        on_delete=models.CASCADE,
        related_name="space_profiles"
    )

    rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ]
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
    


class FeedbackReport(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
    ]

    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="feedback_reports"
    )

    space = models.ForeignKey(
        Space,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="feedback_reports"
    )

    comment = models.TextField()

    is_anonymous = models.BooleanField(default=True)

    reporter_name = models.CharField(max_length=255, blank=True)
    reporter_email = models.EmailField(blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback #{self.pk}"
