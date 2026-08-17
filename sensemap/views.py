from django.db.models import Avg, Q
from django.shortcuts import get_object_or_404, render
from rest_framework import mixins, viewsets
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import (
    Facility,
    SensoryAttribute,
    Location,
    Space,
)
from .serializers import (
    FacilitySerializer,
    SensoryAttributeSerializer,
    LocationListSerializer,
    LocationDetailSerializer,
    SpaceSerializer,
    FeedbackSensoryRatingBatchSerializer,
)


class LocationViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only public API for locations at /api/locations/.

    Content is curated through the Django admin; the API is read-only for
    the public site. Supports the following query parameters:

      ?search=<text>            name / also_known_as / description
      ?category=<key>           Location.CATEGORY_CHOICES key
      ?campus=<key>             Location.CAMPUS_CHOICES key
      ?space_type=<key>         only locations containing that space type
      ?quiet=true               only locations with a quiet-zone space
      ?neurodivergent=true      only locations with a neurodivergent-safe space
      ?axis=<name>              sensory attribute name (for example, Auditory)
      ?rating=<1-5>             exact rating for the selected sensory attribute
      ?min_rating=<1-5>         minimum rating for the selected sensory attribute
      ?max_rating=<1-5>         maximum rating for the selected sensory attribute
      ?facility=<name>          available location facility; comma-separated values use AND
      ?ordering=name,-name,...  safe ordering by name, category, campus, created_at,
                                updated_at, or avg_sensory
    """

    ORDERING_FIELDS = {
        "name": "name",
        "category": "category",
        "campus": "campus",
        "created_at": "created_at",
        "updated_at": "updated_at",
        "avg_sensory": "avg_sensory",
    }

    def get_serializer_class(self):
        if self.action == "retrieve":
            return LocationDetailSerializer
        return LocationListSerializer

    def get_queryset(self):
        qs = (
            Location.objects.all()
            .prefetch_related(
                "spaces",
                "location_sensory_profiles__sensory_attribute",
                "location_facilities__facility",
                "gallery_images",
                "sensory_feedback__sensory_attribute",
                "spaces__space_facilities__facility",
                "spaces__space_sensory_profiles__sensory_attribute",
                "spaces__sensory_feedback__sensory_attribute",
            )
        )
        params = self.request.query_params

        search = params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(also_known_as__icontains=search)
                | Q(description__icontains=search)
            )

        category = params.get("category")
        if category:
            qs = qs.filter(category=category)

        campus = params.get("campus")
        if campus:
            qs = qs.filter(campus=campus)

        space_type = params.get("space_type")
        if space_type:
            qs = qs.filter(spaces__space_type=space_type)

        if params.get("quiet") in ("true", "1"):
            qs = qs.filter(spaces__is_quiet_zone=True)

        if params.get("neurodivergent") in ("true", "1"):
            qs = qs.filter(spaces__is_safe_space_neurodivergent_students=True)

        qs = self._filter_sensory_axis(qs, params)
        qs = self._filter_facilities(qs, params)
        qs = self._apply_ordering(qs, params)

        return qs.distinct()

    def _filter_sensory_axis(self, queryset, params):
        axis = params.get("axis", "").strip()
        rating = self._rating_param(params, "rating", "level")
        min_rating = self._rating_param(params, "min_rating", "min_level")
        max_rating = self._rating_param(params, "max_rating", "max_level")

        if not axis:
            if any(value is not None for value in (rating, min_rating, max_rating)):
                raise ValidationError({"axis": "An axis is required when filtering by rating."})
            return queryset

        axis_filter = Q(
            location_sensory_profiles__sensory_attribute__name__iexact=axis
        )
        if axis.isdigit():
            axis_filter |= Q(
                location_sensory_profiles__sensory_attribute__external_id=int(axis)
            )

        profile_filter = axis_filter
        if rating is not None:
            profile_filter &= Q(location_sensory_profiles__rating=rating)
        if min_rating is not None:
            profile_filter &= Q(location_sensory_profiles__rating__gte=min_rating)
        if max_rating is not None:
            profile_filter &= Q(location_sensory_profiles__rating__lte=max_rating)
        return queryset.filter(profile_filter)

    def _filter_facilities(self, queryset, params):
        values = params.getlist("facility") + params.getlist("facilities")
        facility_names = [
            name.strip()
            for value in values
            for name in value.split(",")
            if name.strip()
        ]
        for facility_name in facility_names:
            facility_filter = Q(
                location_facilities__status=True,
                location_facilities__facility__name__iexact=facility_name,
            )
            if facility_name.isdigit():
                facility_filter |= Q(
                    location_facilities__status=True,
                    location_facilities__facility__external_id=int(facility_name),
                )
            queryset = queryset.filter(facility_filter)
        return queryset

    def _apply_ordering(self, queryset, params):
        requested_fields = [
            field.strip()
            for field in params.get("ordering", "").split(",")
            if field.strip()
        ]
        ordering = []
        needs_average = False
        for requested in requested_fields:
            descending = requested.startswith("-")
            field_name = requested[1:] if descending else requested
            mapped = self.ORDERING_FIELDS.get(field_name)
            if not mapped:
                continue
            if mapped == "avg_sensory":
                needs_average = True
            ordering.append(f"-{mapped}" if descending else mapped)

        if needs_average:
            queryset = queryset.annotate(avg_sensory=Avg("location_sensory_profiles__rating"))
        return queryset.order_by(*ordering) if ordering else queryset

    @staticmethod
    def _rating_param(params, *names):
        raw_value = next((params.get(name) for name in names if params.get(name) is not None), None)
        if raw_value is None or raw_value == "":
            return None
        try:
            value = int(raw_value)
        except (TypeError, ValueError) as exc:
            raise ValidationError({names[0]: "Rating must be an integer from 1 to 5."}) from exc
        if value not in range(1, 6):
            raise ValidationError({names[0]: "Rating must be between 1 and 5."})
        return value


class SpaceViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to individual spaces at /api/spaces/."""

    serializer_class = SpaceSerializer

    def get_queryset(self):
        qs = Space.objects.all().select_related("location").prefetch_related(
            "space_facilities__facility",
            "space_sensory_profiles__sensory_attribute",
            "sensory_feedback__sensory_attribute",
        )
        location = self.request.query_params.get("location")
        if location:
            qs = qs.filter(location_id=location)
        space_type = self.request.query_params.get("space_type")
        if space_type:
            qs = qs.filter(space_type=space_type)
        return qs


class FacilityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Facility.objects.all()
    serializer_class = FacilitySerializer


@api_view(["GET"])
def meta(request):
    """Choices + reference data the frontend uses to build filters/legends."""
    return Response(
        {
            "categories": [
                {"key": key, "label": label} for key, label in Location.Category.choices
            ],
            "campuses": [
                {"key": key, "label": label} for key, label in Location.Campus.choices
            ],
            "space_types": [
                {"key": key, "label": label} for key, label in Space.SpaceType.choices
            ],
            "sensory_attributes": list(
                SensoryAttribute.objects.values_list("name", flat=True)
            ),
            "facilities": list(Facility.objects.values_list("name", flat=True)),
        }
    )


def index(request):
    """Render the home page (map + list of locations)."""
    return render(request, "sensemap/index.html")


def places(request):
    """Render the full-page browser listing every location as cards."""
    return render(request, "sensemap/places.html")


def place_detail(request, slug):
    """Render a dedicated detail page for a single location.

    The URL is human-readable (/place/<slug>/) while the template still
    receives the numeric ID so the client can fetch /api/locations/<id>/.
    """
    location = get_object_or_404(Location, slug=slug)
    return render(request, "sensemap/place_detail.html", {"location_id": location.id})


def space_detail(request, space_id):
    """Render a dedicated detail page for a single space."""
    return render(request, "sensemap/space_detail.html", {"space_id": space_id})


def feedback(request):
    """Render the feedback form page."""
    return render(request, "sensemap/feedback.html")


@api_view(["POST"])
def sensory_feedback(request):
    """Public endpoint to submit a batch of sensory ratings."""
    serializer = FeedbackSensoryRatingBatchSerializer(data=request.data)
    if serializer.is_valid():
        created = serializer.save()
        return Response({"ok": True, "count": len(created)}, status=201)
    return Response(serializer.errors, status=400)