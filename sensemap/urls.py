from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

"""
API router.

The router automatically generates standard REST endpoints for each ViewSet.

Examples:
    GET    /api/locations/          List locations
    GET    /api/locations/<id>/     Retrieve a location
    GET    /api/spaces/             List spaces
    GET    /api/facilities/         List facilities
    
"""
router = DefaultRouter()
router.register(r"locations", views.LocationViewSet, basename="location")
router.register(r"spaces", views.SpaceViewSet, basename="space")
router.register(r"facilities", views.FacilityViewSet, basename="facility")


urlpatterns = [
    # Template views
    path("", views.index, name="index"),
    path("places/", views.places, name="places"),
    path("place/<slug:slug>/", views.place_detail, name="place_detail"),
    path("space/<int:space_id>/", views.space_detail, name="space_detail"),
    path("feedback/", views.feedback, name="feedback"),

    # API endpoints
    path("api/meta/", views.meta, name="meta"),
    path("api/sensory-feedback/", views.sensory_feedback, name="sensory_feedback"),
    path("api/", include(router.urls)),
]
