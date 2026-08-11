"""DRF serializers for the UoA Sensory Map API.

The data model is hierarchical:
    Location (a building / place on a campus)
      └── Space (a study/quiet/social area inside it)
Both Locations and Spaces carry facilities (with availability) and
sensory profiles (1-5 ratings against named SensoryAttributes).

The frontend uses two Location representations:
  * LocationListSerializer   -> lightweight, drives the map markers + list
  * LocationDetailSerializer -> everything needed for the detail panel
"""

from rest_framework import serializers
from django.utils.html import strip_tags

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
)


# --------------------------------------------------------------------------- #
# Shared / nested serializers
# --------------------------------------------------------------------------- #
class FacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = [
            "id",
            "external_id",
            "name",
            "icon_facility_available",
            "icon_facility_unavailable",
        ]


class _FacilityLinkSerializer(serializers.ModelSerializer):
    """Base for the through-models (LocationFacility / SpaceFacility)."""

    facility_id = serializers.IntegerField(source="facility.id", read_only=True)
    facility_external_id = serializers.IntegerField(
        source="facility.external_id", read_only=True
    )
    name = serializers.CharField(source="facility.name", read_only=True)
    icon_available = serializers.ImageField(
        source="facility.icon_facility_available", read_only=True
    )
    icon_unavailable = serializers.ImageField(
        source="facility.icon_facility_unavailable", read_only=True
    )

    class Meta:
        fields = [
            "facility_id",
            "facility_external_id",
            "name",
            "status",
            "notes",
            "icon_available",
            "icon_unavailable",
        ]


class LocationFacilityLinkSerializer(_FacilityLinkSerializer):
    class Meta(_FacilityLinkSerializer.Meta):
        model = LocationFacility


class SpaceFacilityLinkSerializer(_FacilityLinkSerializer):
    class Meta(_FacilityLinkSerializer.Meta):
        model = SpaceFacility


class LocationSensoryProfileSerializer(serializers.ModelSerializer):
    attribute = serializers.CharField(source="sensory_attribute.name", read_only=True)

    class Meta:
        model = LocationSensoryProfile
        fields = ["attribute", "rating", "notes"]


class SpaceSensoryProfileSerializer(serializers.ModelSerializer):
    attribute = serializers.CharField(source="sensory_attribute.name", read_only=True)

    class Meta:
        model = SpaceSensoryProfile
        fields = ["attribute", "rating", "notes"]


class GalleryImageSerializer(serializers.ModelSerializer):
    width = serializers.SerializerMethodField()
    height = serializers.SerializerMethodField()

    class Meta:
        model = LocationGalleryImage
        fields = ["id", "image", "caption", "width", "height"]

    def _dimensions(self, obj):
        try:
            from django.core.files.images import get_image_dimensions
            return get_image_dimensions(obj.image)
        except Exception:
            return (None, None)

    def get_width(self, obj):
        return self._dimensions(obj)[0]

    def get_height(self, obj):
        return self._dimensions(obj)[1]



class SpaceLocationSerializer(serializers.ModelSerializer):
    """Minimal location info for the /places space cards."""

    category_display = serializers.CharField(source="get_category_display", read_only=True)
    campus_display = serializers.CharField(source="get_campus_display", read_only=True)

    class Meta:
        model = Location
        fields = [
            "id",
            "name",
            "slug",
            "campus",
            "campus_display",
            "category",
            "category_display",
            "id_access_needed",
        ]


class SpaceSerializer(serializers.ModelSerializer):
    space_type_display = serializers.CharField(
        source="get_space_type_display", read_only=True
    )
    facilities = SpaceFacilityLinkSerializer(
        source="space_facilities", many=True, read_only=True
    )
    sensory_profiles = serializers.SerializerMethodField()
    location = SpaceLocationSerializer(read_only=True)

    class Meta:
        model = Space
        fields = [
            "id",
            "name",
            "space_type",
            "space_type_display",
            "description",
            "thumbnail_image",
            "weekday_open_time",
            "weekday_close_time",
            "saturday_open_time",
            "saturday_close_time",
            "sunday_holiday_open_time",
            "sunday_holiday_close_time",
            "opening_hrs_notes",
            "wayfinding",
            "is_quiet_zone",
            "is_safe_space_neurodivergent_students",
            "facilities",
            "sensory_profiles",
            "location",
        ]

    def get_sensory_profiles(self, obj):
        base = {}
        for p in obj.space_sensory_profiles.all():
            base[p.sensory_attribute.name] = {"rating": p.rating, "notes": p.notes}

        feedback = {}
        for r in obj.sensory_feedback.all():
            feedback.setdefault(r.sensory_attribute.name, []).append(r.rating)

        attrs = set(base.keys()) | set(feedback.keys())
        result = []
        for name in sorted(attrs):
            notes = base.get(name, {}).get("notes", "")
            if name in feedback:
                fb_avg = round(sum(feedback[name]) / len(feedback[name]))
                if name in base:
                    rating = round((base[name]["rating"] + fb_avg) / 2)
                else:
                    rating = fb_avg
            else:
                rating = base[name]["rating"]
            result.append({"attribute": name, "rating": rating, "notes": notes})
        return result


class QuietZoneSerializer(SpaceSerializer):
    """Nested representation of the quiet spaces inside a location."""

    class Meta(SpaceSerializer.Meta):
        fields = [
            "id",
            "name",
            "space_type",
            "space_type_display",
            "description",
            "is_quiet_zone",
            "is_safe_space_neurodivergent_students",
            "facilities",
            "sensory_profiles",
        ]


# --------------------------------------------------------------------------- #
# Location serializers
# --------------------------------------------------------------------------- #
class LocationListSerializer(serializers.ModelSerializer):
    """Lightweight payload for map markers and the places list."""

    category_display = serializers.CharField(source="get_category_display", read_only=True)
    campus_display = serializers.CharField(source="get_campus_display", read_only=True)
    space_types = serializers.SerializerMethodField()
    space_count = serializers.SerializerMethodField()
    has_quiet_zone = serializers.SerializerMethodField()
    has_neurodivergent_safe = serializers.SerializerMethodField()
    avg_sensory = serializers.SerializerMethodField()
    # Lightweight extras used by the full-page Places browser.
    sensory = serializers.SerializerMethodField()
    facilities_available = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = [
            "id",
            "name",
            "slug",
            "also_known_as",
            "category",
            "category_display",
            "campus",
            "campus_display",
            "description",
            "latitude",
            "longitude",
            "id_access_needed",
            "space_types",
            "space_count",
            "has_quiet_zone",
            "has_neurodivergent_safe",
            "avg_sensory",
            "sensory",
            "facilities_available",
            "thumbnail",
        ]

    def get_space_types(self, obj):
        return sorted({s.space_type for s in obj.spaces.all()})

    def get_sensory(self, obj):
        return [
            {"attribute": p.sensory_attribute.name, "rating": p.rating}
            for p in obj.location_sensory_profiles.all()
        ]

    def get_facilities_available(self, obj):
        return sorted(
            {lf.facility.name for lf in obj.location_facilities.all() if lf.status}
        )

    def get_thumbnail(self, obj):
        if not obj.thumbnail_image:
            return None
        request = self.context.get("request")
        url = obj.thumbnail_image.url
        return request.build_absolute_uri(url) if request else url

    def get_space_count(self, obj):
        return len(obj.spaces.all())

    def get_has_quiet_zone(self, obj):
        return any(s.is_quiet_zone for s in obj.spaces.all())

    def get_has_neurodivergent_safe(self, obj):
        return any(s.is_safe_space_neurodivergent_students for s in obj.spaces.all())

    def get_avg_sensory(self, obj):
        ratings = [p.rating for p in obj.location_sensory_profiles.all()]
        if not ratings:
            return None
        return round(sum(ratings) / len(ratings))


class LocationDetailSerializer(LocationListSerializer):
    """Full payload for the detail panel."""

    facilities = LocationFacilityLinkSerializer(
        source="location_facilities", many=True, read_only=True
    )
    sensory_profiles = serializers.SerializerMethodField()
    spaces = SpaceSerializer(many=True, read_only=True)
    quiet_zones = serializers.SerializerMethodField()
    gallery_images = GalleryImageSerializer(many=True, read_only=True)

    class Meta(LocationListSerializer.Meta):
        fields = LocationListSerializer.Meta.fields + [
            "weekday_open_time",
            "weekday_close_time",
            "saturday_open_time",
            "saturday_close_time",
            "sunday_holiday_open_time",
            "sunday_holiday_close_time",
            "opening_hrs_notes",
            "additional_access_notes",
            "uoa_map_link",
            "thumbnail_image",
            "facilities",
            "sensory_profiles",
            "spaces",
            "quiet_zones",
            "gallery_images",
            
        ]

    def get_quiet_zones(self, obj):
        quiet_spaces = [space for space in obj.spaces.all() if space.is_quiet_zone]
        return QuietZoneSerializer(quiet_spaces, many=True, context=self.context).data

    def get_sensory_profiles(self, obj):
        base = {}
        for p in obj.location_sensory_profiles.all():
            base[p.sensory_attribute.name] = {"rating": p.rating, "notes": p.notes}

        feedback = {}
        for r in obj.sensory_feedback.all():
            feedback.setdefault(r.sensory_attribute.name, []).append(r.rating)

        attrs = set(base.keys()) | set(feedback.keys())
        result = []
        for name in sorted(attrs):
            notes = base.get(name, {}).get("notes", "")
            if name in feedback:
                fb_avg = round(sum(feedback[name]) / len(feedback[name]))
                if name in base:
                    rating = round((base[name]["rating"] + fb_avg) / 2)
                else:
                    rating = fb_avg
            else:
                rating = base[name]["rating"]
            result.append({"attribute": name, "rating": rating, "notes": notes})
        return result




class FeedbackSensoryRatingBatchSerializer(serializers.Serializer):
    """Accept a batch of sensory ratings for a location or space."""

    location = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.all(), required=False
    )
    space = serializers.PrimaryKeyRelatedField(
        queryset=Space.objects.all(), required=False
    )
    is_anonymous = serializers.BooleanField(default=True)
    reporter_name = serializers.CharField(allow_blank=True, required=False)
    reporter_email = serializers.EmailField(allow_blank=True, required=False)
    ratings = serializers.DictField(
        child=serializers.IntegerField(min_value=1, max_value=5)
    )

    def validate(self, data):
        has_loc = bool(data.get("location"))
        has_space = bool(data.get("space"))
        if has_loc == has_space:
            raise serializers.ValidationError(
                "Provide exactly one of 'location' or 'space'."
            )
        return data

    def create(self, validated_data):
        location = validated_data.get("location")
        space = validated_data.get("space")
        is_anonymous = validated_data.get("is_anonymous", True)
        reporter_name = validated_data.get("reporter_name", "")
        reporter_email = validated_data.get("reporter_email", "")
        ratings = validated_data.get("ratings", {})

        created = []
        for attr_name, rating in ratings.items():
            attr = SensoryAttribute.objects.get(name__iexact=attr_name)
            created.append(
                FeedbackSensoryRating.objects.create(
                    location=location,
                    space=space,
                    sensory_attribute=attr,
                    rating=rating,
                    is_anonymous=is_anonymous,
                    reporter_name=reporter_name,
                    reporter_email=reporter_email,
                )
            )
        return created
