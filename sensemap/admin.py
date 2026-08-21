import csv
import json
from datetime import date, datetime, time
from decimal import Decimal
from django.contrib import admin
from django.db import models
from django.db.models.fields.files import FieldFile
from django.http import HttpResponse
from django.utils import timezone
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
    FeedbackSensoryRating,
    AuditLog,
)


# Audit helper functions
AUDIT_EXCLUDED_FIELDS = {
    "created_at",
    "updated_at",
    "created_by",
    "updated_by",
}


def serialise_audit_value(value):
    """Convert model values into JSON-compatible values."""
    if value is None:
        return None

    if isinstance(value, FieldFile):
        return value.name

    if isinstance(value, (datetime, date, time, Decimal)):
        return str(value)

    if isinstance(value, models.Model):
        return str(value)

    if isinstance(value, (str, int, float, bool)):
        return value

    return str(value)

def get_record_name(obj):
    """Return a readable name for an audited record."""
    return getattr(obj, "name", str(obj))


def get_catalogue_location(obj):
    """Return the Location associated with a record."""

    if isinstance(obj, Location):
        return obj

    location = getattr(obj, "location", None)

    if isinstance(location, Location):
        return location

    space = getattr(obj, "space", None)

    if space and getattr(space, "location", None):
        return space.location

    return None


def get_field_values(obj, field_names):
    """Return selected field values in a JSON-compatible dictionary."""
    values = {}

    for field_name in field_names:
        try:
            value = getattr(obj, field_name)
        except AttributeError:
            continue

        values[field_name] = serialise_audit_value(value)

    return values


def create_audit_log(
    *,
    obj,
    action,
    user,
    changed_fields=None,
    previous_values=None,
    new_values=None,
):
    """Create an audit-history record."""
    location = get_catalogue_location(obj)

    AuditLog.objects.create(
        app_label=obj._meta.app_label,
        model_name=obj._meta.verbose_name,
        record_id=str(obj.pk),
        record_name=get_record_name(obj),
        location_id_snapshot=(
            location.external_id if location else None
        ),
        location_name_snapshot=(
            location.name if location else ""
        ),
        action=action,
        changed_fields=changed_fields or [],
        previous_values=previous_values or {},
        new_values=new_values or {},
        changed_by=user if user.is_authenticated else None,
    )


class ShowAllFieldsAdmin(admin.ModelAdmin):
    """
    Shared admin configuration with audit logging.
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
        existing_filters = tuple(
            super().get_list_filter(request)
        )

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
        existing_fields = tuple(
            super().get_search_fields(request)
        )

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
            dict.fromkeys(
                existing_fields + audit_search_fields
            )
        )

    def save_model(self, request, obj, form, change):
        changed_fields = [
            field_name
            for field_name in form.changed_data
            if field_name not in AUDIT_EXCLUDED_FIELDS
        ]

        previous_values = {}

        if change and obj.pk:
            original = self.model.objects.get(pk=obj.pk)
            previous_values = get_field_values(
                original,
                changed_fields
            )

        if not change or obj.created_by_id is None:
            obj.created_by = request.user

        obj.updated_by = request.user

        super().save_model(request, obj, form, change)

        if change:
            if changed_fields:
                create_audit_log(
                    obj=obj,
                    action=AuditLog.Action.UPDATED,
                    user=request.user,
                    changed_fields=changed_fields,
                    previous_values=previous_values,
                    new_values=get_field_values(
                        obj,
                        changed_fields
                    ),
                )
        else:
            created_fields = [
                field.name
                for field in obj._meta.concrete_fields
                if field.name not in AUDIT_EXCLUDED_FIELDS
            ]

            create_audit_log(
                obj=obj,
                action=AuditLog.Action.CREATED,
                user=request.user,
                changed_fields=created_fields,
                new_values=get_field_values(
                    obj,
                    created_fields
                ),
            )

    def delete_model(self, request, obj):
        create_audit_log(
            obj=obj,
            action=AuditLog.Action.DELETED,
            user=request.user,
            changed_fields=[],
            previous_values=get_field_values(
                obj,
                [
                    field.name
                    for field in obj._meta.concrete_fields
                    if field.name not in AUDIT_EXCLUDED_FIELDS
                ],
            ),
        )

        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            create_audit_log(
                obj=obj,
                action=AuditLog.Action.DELETED,
                user=request.user,
                previous_values=get_field_values(
                    obj,
                    [
                        field.name
                        for field in obj._meta.concrete_fields
                        if field.name not in AUDIT_EXCLUDED_FIELDS
                    ],
                ),
            )

        queryset.delete()

# Audit report filters and export action
class ThisMonthFilter(admin.SimpleListFilter):
    title = "reporting period"
    parameter_name = "reporting_period"

    def lookups(self, request, model_admin):
        return [
            ("this_month", "This month"),
            ("last_month", "Last month"),
        ]

    def queryset(self, request, queryset):
        today = timezone.localdate()

        if self.value() == "this_month":
            return queryset.filter(
                changed_at__year=today.year,
                changed_at__month=today.month,
            )

        if self.value() == "last_month":
            if today.month == 1:
                year = today.year - 1
                month = 12
            else:
                year = today.year
                month = today.month - 1

            return queryset.filter(
                changed_at__year=year,
                changed_at__month=month,
            )

        return queryset


class CatalogueAreaFilter(admin.SimpleListFilter):
    """
    Group audit records by the main catalogue area they affect.
    """

    title = "catalogue area"
    parameter_name = "catalogue_area"

    def lookups(self, request, model_admin):
        return [
            ("locations", "Locations"),
            ("spaces", "Spaces"),
            ("facilities", "Facilities"),
            ("sensory_attributes", "Sensory attributes"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "locations":
            return queryset.filter(
                model_name__in=[
                    "location",
                    "location facility",
                    "location gallery image",
                    "location sensory profile",
                ]
            )

        if self.value() == "spaces":
            return queryset.filter(
                model_name__in=[
                    "space",
                    "space facility",
                    "space sensory profile",
                ]
            )

        if self.value() == "facilities":
            return queryset.filter(
                model_name__in=[
                    "facility",
                    "location facility",
                    "space facility",
                ]
            )

        if self.value() == "sensory_attributes":
            return queryset.filter(
                model_name__in=[
                    "sensory attribute",
                    "location sensory profile",
                    "space sensory profile",
                    "feedback sensory rating",
                ]
            )

        return queryset


@admin.action(
    description="Export selected audit records as CSV",
    permissions=["view"],
)
def export_audit_report_csv(modeladmin, request, queryset):
    response = HttpResponse(
        content_type="text/csv; charset=utf-8"
    )

    filename = (
        f"catalogue-change-report-"
        f"{timezone.localdate().isoformat()}.csv"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="{filename}"'
    )

    # Helps Excel recognise UTF-8 correctly.
    response.write("\ufeff")

    writer = csv.writer(response)

    writer.writerow([
        "Date and time",
        "Action",
        "Table/model",
        "Record ID",
        "Record name",
        "Location ID",
        "Building/location",
        "Changed fields",
        "Previous values",
        "New values",
        "Changed by",
    ])

    for audit in queryset.select_related("changed_by"):
        writer.writerow([
            timezone.localtime(audit.changed_at).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            audit.get_action_display(),
            audit.model_name,
            audit.record_id,
            audit.record_name,
            audit.location_id_snapshot or "",
            audit.location_name_snapshot,
            ", ".join(audit.changed_fields),
            json.dumps(
                audit.previous_values,
                ensure_ascii=False
            ),
            json.dumps(
                audit.new_values,
                ensure_ascii=False
            ),
            (
                audit.changed_by.get_username()
                if audit.changed_by
                else ""
            ),
        ])

    return response
    

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
        """
        Save and audit SpaceFacility records edited through the Space inline.
        """
        instances = formset.save(commit=False)

        # Record inline deletions before deleting the database records.
        for deleted_object in formset.deleted_objects:
            create_audit_log(
                obj=deleted_object,
                action=AuditLog.Action.DELETED,
                user=request.user,
                previous_values=get_field_values(
                    deleted_object,
                    [
                        field.name
                        for field
                        in deleted_object._meta.concrete_fields
                        if field.name not in AUDIT_EXCLUDED_FIELDS
                    ],
                ),
            )
            deleted_object.delete()

        for instance in instances:
            is_created = instance.pk is None

            matching_form = next(
                (
                    inline_form
                    for inline_form in formset.forms
                    if inline_form.instance is instance
                ),
                None,
            )

            changed_fields = []

            if matching_form:
                changed_fields = [
                    field_name
                    for field_name in matching_form.changed_data
                    if field_name not in AUDIT_EXCLUDED_FIELDS
                ]

            previous_values = {}

            # Retrieve the database values before saving an update.
            if not is_created:
                original = instance.__class__.objects.get(
                    pk=instance.pk
                )
                previous_values = get_field_values(
                    original,
                    changed_fields,
                )

            if instance.created_by_id is None:
                instance.created_by = request.user

            instance.updated_by = request.user
            instance.save()

            if is_created:
                created_fields = [
                    field.name
                    for field in instance._meta.concrete_fields
                    if field.name not in AUDIT_EXCLUDED_FIELDS
                ]

                create_audit_log(
                    obj=instance,
                    action=AuditLog.Action.CREATED,
                    user=request.user,
                    changed_fields=created_fields,
                    new_values=get_field_values(
                        instance,
                        created_fields,
                    ),
                )

            elif changed_fields:
                create_audit_log(
                    obj=instance,
                    action=AuditLog.Action.UPDATED,
                    user=request.user,
                    changed_fields=changed_fields,
                    previous_values=previous_values,
                    new_values=get_field_values(
                        instance,
                        changed_fields,
                    ),
                )

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
        "created_by",
        "updated_by",
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


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "changed_at",
        "action",
        "model_name",
        "record_id",
        "record_name",
        "location_name_snapshot",
        "changed_by",
    )

    list_filter = (
        ThisMonthFilter,
        CatalogueAreaFilter,
        "action",
        "model_name",
        "changed_by",
        "changed_at",
    )

    search_fields = (
        "record_id",
        "record_name",
        "location_name_snapshot",
        "changed_by__username",
        "changed_by__first_name",
        "changed_by__last_name",
        "changed_by__email",
    )

    date_hierarchy = "changed_at"

    readonly_fields = (
        "app_label",
        "model_name",
        "record_id",
        "record_name",
        "location_id_snapshot",
        "location_name_snapshot",
        "action",
        "changed_fields",
        "previous_values",
        "new_values",
        "changed_by",
        "changed_at",
    )

    actions = [export_audit_report_csv]

    ordering = ("-changed_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(
        self,
        request,
        obj=None
    ):
        return False

    def has_delete_permission(
        self,
        request,
        obj=None
    ):
        return False