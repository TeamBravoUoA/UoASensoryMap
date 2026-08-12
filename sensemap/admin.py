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


@admin.register(Space)
class SpaceAdmin(ShowAllFieldsAdmin):
    search_fields = ("name",)
    list_filter = ("space_type", "is_quiet_zone", "floor")


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