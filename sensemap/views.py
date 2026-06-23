from django.shortcuts import render
from django.db.models import Q
from rest_framework import viewsets

from .models import Location
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

    sensory_axes = {"auditory", "visual", "olfactory", "thermal", "vestibular"}
    ordering_fields = {
        "name",
        "category",
        "auditory",
        "visual",
        "olfactory",
        "thermal",
        "vestibular",
    }

    def get_queryset(self):
        queryset = super().get_queryset()
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
            queryset = queryset.filter(is_quiet_zone=True)
        elif quiet in {"false", "0", "no"}:
            queryset = queryset.filter(is_quiet_zone=False)

        if axis in self.sensory_axes:
            exact_level = self._parse_sensory_level(level)
            lower_bound = self._parse_sensory_level(min_level)
            upper_bound = self._parse_sensory_level(max_level)

            if exact_level is not None:
                queryset = queryset.filter(**{axis: exact_level})
            if lower_bound is not None:
                queryset = queryset.filter(**{f"{axis}__gte": lower_bound})
            if upper_bound is not None:
                queryset = queryset.filter(**{f"{axis}__lte": upper_bound})

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )

        if ordering:
            field = ordering.lstrip("-")
            if field in self.ordering_fields:
                queryset = queryset.order_by(ordering)

        return queryset

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
