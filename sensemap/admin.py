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
    """
    Shared administration configuration for timestamped models.
    """

    readonly_fields = (
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    )

    def get_list_display(self, request):
        return [
            field.name
            for field in self.model._meta.concrete_fields
        ]

    def get_list_filter(self, request):
        existing_filters = tuple(super().get_list_filter(request))

        audit_filters = (
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        )

        return tuple(
            dict.fromkeys(existing_filters + audit_filters)
        )

    def get_search_fields(self, request):
        existing_fields = tuple(super().get_search_fields(request))

        audit_search_fields = (
            "created_by__username",
            "created_by__first_name",
            "created_by__last_name",
            "created_by__email",
            "updated_by__username",
            "updated_by__first_name",
            "updated_by__last_name",
            "updated_by__email",
        )

        return tuple(
            dict.fromkeys(existing_fields + audit_search_fields)
        )

    def save_model(self, request, obj, form, change):
        if not change or obj.created_by_id is None:
            obj.created_by = request.user

        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Facility)
class FacilityAdmin(ShowAllFieldsAdmin):
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(SensoryAttribute)
class SensoryAttributeAdmin(ShowAllFieldsAdmin):
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Location)
class LocationAdmin(ShowAllFieldsAdmin):
    search_fields = (
        "name",
        "also_known_as",
        "description",
    )

    list_filter = (
        "category",
        "campus",
        "id_access_needed",
        "created_at",
        "updated_at",
    )

    ordering = ("external_id",)


class SpaceFacilityInline(admin.TabularInline):
    model = SpaceFacility
    extra = 1
    autocomplete_fields = ("facility",)


@admin.register(Space)
class SpaceAdmin(ShowAllFieldsAdmin):
    search_fields = (
        "name",
        "location__name",
        "description",
        "floor",
    )

    list_filter = (
        "space_type",
        "is_quiet_zone",
        "is_safe_space_neurodivergent_students",
        "floor",
        "location",
        "created_at",
        "updated_at",
    )

    autocomplete_fields = ("location",)
    list_select_related = ("location",)
    ordering = ("location__name", "name")
    inlines = (SpaceFacilityInline,)

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "external_id",
                    "location",
                    "name",
                    "space_type",
                    "description",
                )
            },
        ),
        (
            "Location and Navigation",
            {
                "fields": (
                    "latitude",
                    "longitude",
                    "floor",
                    "wayfinding",
                )
            },
        ),
        (
            "Opening Hours",
            {
                "fields": (
                    ("weekday_open_time", "weekday_close_time"),
                    ("saturday_open_time", "saturday_close_time"),
                    (
                        "sunday_holiday_open_time",
                        "sunday_holiday_close_time",
                    ),
                    "opening_hrs_notes",
                )
            },
        ),
        (
            "Sensory and Accessibility",
            {
                "fields": (
                    "sensory_experience",
                    "is_quiet_zone",
                    "is_safe_space_neurodivergent_students",
                    "thumbnail_image",
                )
            },
        ),
    )

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)

        for deleted_object in formset.deleted_objects:
            deleted_object.delete()

        for instance in instances:
            if hasattr(instance, "created_by"):
                if instance.created_by_id is None:
                    instance.created_by = request.user

                instance.updated_by = request.user

            instance.save()

        formset.save_m2m()


@admin.register(LocationFacility)
class LocationFacilityAdmin(ShowAllFieldsAdmin):
    list_filter = (
        "facility",
        "status",
    )

    search_fields = (
        "location__name",
        "location__also_known_as",
        "facility__name",
        "created_by__username",
    )

    autocomplete_fields = (
        "location",
        "facility",
    )

    list_select_related = (
        "location",
        "facility",
        "created_at",
        "updated_at",
    )

    ordering = (
        "location__name",
        "facility__name",
    )


@admin.register(SpaceFacility)
class SpaceFacilityAdmin(ShowAllFieldsAdmin):
    list_filter = (
        "facility",
        "status",
        "space__location",
    )

    search_fields = (
        "space__name",
        "space__location__name",
        "facility__name",
    )

    autocomplete_fields = (
        "space",
        "facility",
    )

    list_select_related = (
        "space",
        "space__location",
        "facility",
    )

    ordering = (
        "space__location__name",
        "space__name",
        "facility__name",
    )


@admin.register(LocationGalleryImage)
class LocationGalleryImageAdmin(ShowAllFieldsAdmin):
    search_fields = (
        "location__name",
        "caption",
    )

    list_filter = ("location",)
    autocomplete_fields = ("location",)
    list_select_related = ("location",)


@admin.register(LocationSensoryProfile)
class LocationSensoryProfileAdmin(ShowAllFieldsAdmin):
    list_filter = (
        "sensory_attribute",
        "location",
        "rating",
    )

    search_fields = (
        "location__name",
        "location__also_known_as",
        "sensory_attribute__name",
    )

    autocomplete_fields = (
        "location",
        "sensory_attribute",
    )

    list_select_related = (
        "location",
        "sensory_attribute",
    )

    ordering = (
        "location__name",
        "sensory_attribute__name",
    )


@admin.register(SpaceSensoryProfile)
class SpaceSensoryProfileAdmin(ShowAllFieldsAdmin):
    list_filter = (
        "sensory_attribute",
        "space__location",
        "rating",
    )

    search_fields = (
        "space__name",
        "space__location__name",
        "sensory_attribute__name",
    )

    autocomplete_fields = (
        "space",
        "sensory_attribute",
    )

    list_select_related = (
        "space",
        "space__location",
        "sensory_attribute",
    )

    ordering = (
        "space__location__name",
        "space__name",
        "sensory_attribute__name",
    )


@admin.register(FeedbackSensoryRating)
class FeedbackSensoryRatingAdmin(ShowAllFieldsAdmin):
    list_filter = (
        "sensory_attribute",
        "rating",
        "is_anonymous",
        "created_at",
    )

    search_fields = (
        "location__name",
        "space__name",
        "space__location__name",
        "sensory_attribute__name",
        "reporter_name",
        "reporter_email",
    )

    autocomplete_fields = (
        "location",
        "space",
        "sensory_attribute",
    )

    list_select_related = (
        "location",
        "space",
        "sensory_attribute",
    )