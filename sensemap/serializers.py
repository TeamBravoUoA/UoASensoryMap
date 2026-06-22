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
        ]
