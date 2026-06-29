from django.contrib import admin
from .models import (
    Facility,
    SensoryAttribute,
    Location,
    Space,
    LocationFacility,
    SpaceFacility,
    LocationGalleryImage,
    LocationSensoryProfile,
    SpaceSensoryProfile,
    FeedbackReport,
)


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "icon_facility_available",
        "icon_facility_unavailable",
        "created_at",
        "updated_at",
    )
    search_fields = ("name",)


@admin.register(SensoryAttribute)
class SensoryAttributeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "description",
    )
    search_fields = ("name",)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "category",
        "campus",
        "latitude",
        "longitude",
        "id_access_needed",
    )
    search_fields = ("name", "also_known_as")
    list_filter = ("category", "campus")


@admin.register(Space)
class SpaceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "location",
        "space_type",
        "is_quiet_zone",
    )
    search_fields = ("name",)
    list_filter = ("space_type", "is_quiet_zone")


@admin.register(LocationFacility)
class LocationFacilityAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "location",
        "facility",
        "status",
        "notes",
    )
    list_filter = ("status",)


@admin.register(SpaceFacility)
class SpaceFacilityAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "space",
        "facility",
        "status",
        "notes",
    )
    list_filter = ("status",)


@admin.register(LocationGalleryImage)
class LocationGalleryImageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "location",
        "caption",
        "created_at",
    )


@admin.register(LocationSensoryProfile)
class LocationSensoryProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "location",
        "sensory_attribute",
        "rating",
    )
    list_filter = ("sensory_attribute",)


@admin.register(SpaceSensoryProfile)
class SpaceSensoryProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "space",
        "sensory_attribute",
        "rating",
    )
    list_filter = ("sensory_attribute",)


@admin.register(FeedbackReport)
class FeedbackReportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "location",
        "space",
        "status",
        "is_anonymous",
        "created_at",
    )
    list_filter = ("status", "is_anonymous")