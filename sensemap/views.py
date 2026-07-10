from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404, render
from rest_framework import mixins, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import (
    Facility,
    SensoryAttribute,
    Location,
    Space,
    FeedbackReport,
)
from .serializers import (
    FacilitySerializer,
    LocationListSerializer,
    LocationDetailSerializer,
    SpaceSerializer,
    FeedbackReportSerializer,
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
    """

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
                "feedback_reports",
                "spaces__space_facilities__facility",
                "spaces__space_sensory_profiles__sensory_attribute",
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

        return qs.distinct()


class SpaceViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to individual spaces at /api/spaces/."""

    serializer_class = SpaceSerializer

    def get_queryset(self):
        qs = Space.objects.all().prefetch_related(
            "space_facilities__facility",
            "space_sensory_profiles__sensory_attribute",
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


class FeedbackReportViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """Public can submit feedback (always created as 'pending')."""

    queryset = FeedbackReport.objects.all()
    serializer_class = FeedbackReportSerializer


@api_view(["GET"])
def meta(request):
    """Choices + reference data the frontend uses to build filters/legends."""
    return Response(
        {
            "categories": [
                {"key": key, "label": label} for key, label in Location.CATEGORY_CHOICES
            ],
            "campuses": [
                {"key": key, "label": label} for key, label in Location.CAMPUS_CHOICES
            ],
            "space_types": [
                {"key": key, "label": label} for key, label in Space.SPACE_TYPE_CHOICES
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

def feedback(request):
    """Render the feedback submission page."""
    return render(request, "sensemap/feedback.html")
