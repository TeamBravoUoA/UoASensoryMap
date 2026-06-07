from django.shortcuts import render
from rest_framework import viewsets

from .models import Location
from .serializers import LocationSerializer


class LocationViewSet(viewsets.ModelViewSet):
    """Full CRUD API for locations at /api/locations/.

    Supports listing, retrieving, creating, updating and deleting.
    Filtering/search will be added in later sprints.
    """

    queryset = Location.objects.all()
    serializer_class = LocationSerializer


def index(request):
    """Render the home page (map + list of locations)."""
    return render(request, "sensemap/index.html")
