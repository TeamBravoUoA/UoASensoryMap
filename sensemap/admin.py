from django.contrib import admin

from .models import Location


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "is_quiet_zone", "auditory", "visual")
    list_filter = ("category", "is_quiet_zone")
    search_fields = ("name", "description")
