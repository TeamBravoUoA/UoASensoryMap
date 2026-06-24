from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

# The router auto-generates the REST URLs for each viewset, e.g.:
#   GET  /api/locations/            list (lightweight)
#   GET  /api/locations/<id>/       detail (full)
#   GET  /api/spaces/               list spaces (?location= / ?space_type=)
#   GET  /api/facilities/           list facilities
#   POST /api/feedback/             submit feedback (created as 'pending')
router = DefaultRouter()
router.register(r"locations", views.LocationViewSet, basename="location")
router.register(r"spaces", views.SpaceViewSet, basename="space")
router.register(r"facilities", views.FacilityViewSet, basename="facility")
router.register(r"feedback", views.FeedbackReportViewSet, basename="feedback")

urlpatterns = [
    path("", views.index, name="index"),
    path("places/", views.places, name="places"),
    path("place/<slug:slug>/", views.place_detail, name="place_detail"),
    path("api/meta/", views.meta, name="meta"),
    path("api/", include(router.urls)),
]
