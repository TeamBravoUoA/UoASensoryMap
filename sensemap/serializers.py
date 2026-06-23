from rest_framework import serializers

from .models import (
    Facility,
    Location,
    LocationFacility,
    LocationSensoryProfile,
    SensoryAttribute,
)


class FacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = [
            "id",
            "name",
            "description",
            "icon_facility_available",
            "icon_facility_unavailable",
        ]
        read_only_fields = ["id"]


class SensoryAttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensoryAttribute
        fields = ["id", "name", "description"]
        read_only_fields = ["id"]


class LocationFacilitySerializer(serializers.ModelSerializer):
    facility = FacilitySerializer(read_only=True)

    class Meta:
        model = LocationFacility
        fields = ["facility", "status", "notes"]


class LocationSensoryProfileSerializer(serializers.ModelSerializer):
    sensory_attribute = SensoryAttributeSerializer(read_only=True)

    class Meta:
        model = LocationSensoryProfile
        fields = ["sensory_attribute", "rating", "notes"]


class LocationSerializer(serializers.ModelSerializer):
    """Expose location data using Umama's database schema.

    Nested facility and sensory profile data is read-only for now, so the main
    location endpoint can safely list/create/update location records while still
    giving the frontend the related data it needs for display and filtering.
    """

    facilities_status = LocationFacilitySerializer(
        source="location_facilities",
        many=True,
        read_only=True,
    )
    sensory_profiles = LocationSensoryProfileSerializer(
        source="location_sensory_profiles",
        many=True,
        read_only=True,
    )

    class Meta:
        model = Location
        fields = [
            "id",
            "name",
            "also_known_as",
            "category",
            "campus",
            "description",
            "latitude",
            "longitude",
            "weekday_open_time",
            "weekday_close_time",
            "saturday_open_time",
            "saturday_close_time",
            "sunday_holiday_open_time",
            "sunday_holiday_close_time",
            "opening_hrs_notes",
            "id_access_needed",
            "additional_access_notes",
            "uoa_map_link",
            "thumbnail_image",
            "facilities_status",
            "sensory_profiles",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "facilities_status",
            "sensory_profiles",
            "created_at",
            "updated_at",
        ]
