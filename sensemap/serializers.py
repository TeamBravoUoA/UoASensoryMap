from rest_framework import serializers

from .models import Location


class LocationSerializer(serializers.ModelSerializer):
    """Turns a Location into JSON (and validates incoming JSON).

    Add new fields to `fields` when you add them to the model.
    """

    class Meta:
        model = Location
        fields = [
            "id",
            "name",
            "description",
            "category",
            "latitude",
            "longitude",
            "auditory",
            "visual",
            "olfactory",
            "thermal",
            "vestibular",
            "is_quiet_zone",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
