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
    FeedbackSensoryRating
)


class ShowAllFieldsAdmin(admin.ModelAdmin):
    def get_list_display(self, request):
        excluded = ("ImageField", "FileField", "TextField")
        return [
            field.name
            for field in self.model._meta.fields
            if field.get_internal_type() not in excluded
        ]

@admin.register(Facility)
class FacilityAdmin(ShowAllFieldsAdmin):
    search_fields = ("name",)


@admin.register(SensoryAttribute)
class SensoryAttributeAdmin(ShowAllFieldsAdmin):
    search_fields = ("name",)


@admin.register(Location)
class LocationAdmin(ShowAllFieldsAdmin):
    search_fields = ("name", "also_known_as")
    list_filter = ("category", "campus")


class SpaceFacilityInline(admin.TabularInline):
    model = SpaceFacility
    extra = 1


@admin.register(Space)
class SpaceAdmin(ShowAllFieldsAdmin):
    search_fields = ("name",)
    list_filter = ("space_type", "is_quiet_zone", "floor")
    list_display = ("name", "location", "space_type", "floor", "latitude", "longitude", "is_quiet_zone")
    inlines = [SpaceFacilityInline]
    
    fieldsets = (
        ("Basic Info", {
            "fields": ("location", "name", "space_type", "description")
        }),
        ("Location & Navigation", {
            "fields": ("latitude", "longitude", "floor", "wayfinding")
        }),
        ("Hours", {
            "fields": (
                ("weekday_open_time", "weekday_close_time"),
                ("saturday_open_time", "saturday_close_time"),
                ("sunday_holiday_open_time", "sunday_holiday_close_time"),
                "opening_hrs_notes"
            )
        }),
        ("Sensory & Accessibility", {
            "fields": ("sensory_experience", "is_quiet_zone", "is_safe_space_neurodivergent_students", "thumbnail_image")
        }),
    )


@admin.register(LocationFacility)
class LocationFacilityAdmin(ShowAllFieldsAdmin):
    list_filter = ("status",)


@admin.register(SpaceFacility)
class SpaceFacilityAdmin(ShowAllFieldsAdmin):
    list_filter = ("status",)


@admin.register(LocationGalleryImage)
class LocationGalleryImageAdmin(ShowAllFieldsAdmin):
    pass


@admin.register(LocationSensoryProfile)
class LocationSensoryProfileAdmin(ShowAllFieldsAdmin):
    list_filter = ("sensory_attribute",)


@admin.register(SpaceSensoryProfile)
class SpaceSensoryProfileAdmin(ShowAllFieldsAdmin):
    list_filter = ("sensory_attribute",)
    
@admin.register(FeedbackSensoryRating)
class FeedbackSensoryRatingAdmin(ShowAllFieldsAdmin):
    pass