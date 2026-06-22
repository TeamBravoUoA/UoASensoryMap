from django.contrib import admin
from .models import (
    Facility,
    SensoryAttribute,
    Location,
    Space,
    LocationGalleryImage,
    LocationSensoryProfile,
    SpaceSensoryProfile,
    FeedbackReport,
)

admin.site.register(Facility)
admin.site.register(SensoryAttribute)
admin.site.register(Location)
admin.site.register(Space)
admin.site.register(LocationGalleryImage)
admin.site.register(LocationSensoryProfile)
admin.site.register(SpaceSensoryProfile)
admin.site.register(FeedbackReport)