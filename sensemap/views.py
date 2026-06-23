from django.shortcuts import render
from django.db.models import Q
from rest_framework import viewsets

from .models import Location, SensoryAttribute
from .serializers import LocationSerializer


class LocationViewSet(viewsets.ModelViewSet):
    """Full CRUD API for locations at /api/locations/.

    Supports listing, retrieving, creating, updating and deleting.
    Supports simple filtering with query parameters:
      /api/locations/?category=quiet
      /api/locations/?quiet=true
      /api/locations/?axis=auditory&level=1
      /api/locations/?axis=auditory&max_level=2
      /api/locations/?axis=visual&min_level=3
      /api/locations/?search=library
      /api/locations/?ordering=-auditory
    """

    queryset = Location.objects.all()
    serializer_class = LocationSerializer

    ordering_fields = {
        "name",
        "category",
        "campus",
        "created_at",
        "updated_at",
    }

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .prefetch_related(
                "location_facilities__facility",
                "location_sensory_profiles__sensory_attribute",
            )
        )
        category = self.request.query_params.get("category")
        quiet = self.request.query_params.get("quiet")
        axis = self.request.query_params.get("axis")
        level = self.request.query_params.get("level")
        min_level = self.request.query_params.get("min_level")
        max_level = self.request.query_params.get("max_level")
        search = self.request.query_params.get("search")
        ordering = self.request.query_params.get("ordering")

        if category:
            queryset = queryset.filter(category=category)

        if quiet in {"true", "1", "yes"}:
            queryset = queryset.filter(spaces__is_quiet_zone=True)
        elif quiet in {"false", "0", "no"}:
            queryset = queryset.exclude(spaces__is_quiet_zone=True)

        if axis:
            exact_level = self._parse_sensory_level(level)
            lower_bound = self._parse_sensory_level(min_level)
            upper_bound = self._parse_sensory_level(max_level)
            sensory_filter = {
                "location_sensory_profiles__sensory_attribute__name__iexact": axis
            }

            axis_exists = SensoryAttribute.objects.filter(name__iexact=axis).exists()
            has_level_filter = any(
                value is not None for value in [exact_level, lower_bound, upper_bound]
            )

            if axis_exists and not has_level_filter:
                queryset = queryset.filter(**sensory_filter)
            if axis_exists and exact_level is not None:
                queryset = queryset.filter(
                    **sensory_filter,
                    location_sensory_profiles__rating=exact_level,
                )
            if axis_exists and lower_bound is not None:
                queryset = queryset.filter(
                    **sensory_filter,
                    location_sensory_profiles__rating__gte=lower_bound,
                )
            if axis_exists and upper_bound is not None:
                queryset = queryset.filter(
                    **sensory_filter,
                    location_sensory_profiles__rating__lte=upper_bound,
                )

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(also_known_as__icontains=search)
                | Q(description__icontains=search)
            )

        if ordering:
            field = ordering.lstrip("-")
            if field in self.ordering_fields:
                queryset = queryset.order_by(ordering)

        return queryset.distinct()

    def _parse_sensory_level(self, value):
        if value is None or not value.isdigit():
            return None

        level = int(value)
        if 1 <= level <= 5:
            return level

        return None


def index(request):
    """Render the home page (map + list of locations)."""
    return render(request, "sensemap/index.html")
