from django.shortcuts import render
from rest_framework import viewsets

from .models import Location
from .serializers import LocationSerializer


class LocationViewSet(viewsets.ModelViewSet):
    """Full CRUD API for locations at /api/locations/.

    Supports listing, retrieving, creating, updating and deleting.
    Supports simple filtering with query parameters:
      /api/locations/?category=quiet
      /api/locations/?axis=auditory&max_level=2
      /api/locations/?axis=visual&min_level=3
    """

    queryset = Location.objects.all()
    serializer_class = LocationSerializer

    sensory_axes = {"auditory", "visual", "olfactory", "thermal", "vestibular"}

    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get("category")
        axis = self.request.query_params.get("axis")
        min_level = self.request.query_params.get("min_level")
        max_level = self.request.query_params.get("max_level")

        if category:
            queryset = queryset.filter(category=category)

        if axis in self.sensory_axes:
            if min_level and min_level.isdigit():
                queryset = queryset.filter(**{f"{axis}__gte": int(min_level)})
            if max_level and max_level.isdigit():
                queryset = queryset.filter(**{f"{axis}__lte": int(max_level)})

        return queryset


def index(request):
    """Render the home page (map + list of locations)."""
    return render(request, "sensemap/index.html")
