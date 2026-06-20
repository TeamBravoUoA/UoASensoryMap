from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

# The router auto-generates the REST URLs for the viewset:
#   GET/POST        /api/locations/
#   GET/PUT/DELETE  /api/locations/<id>/
router = DefaultRouter()
router.register(r"locations", views.LocationViewSet, basename="location")

urlpatterns = [
    path("", views.index, name="index"),
    path("api/", include(router.urls)),
    path("list/", views.list, name="list")
]
