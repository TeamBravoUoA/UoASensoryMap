"""Add a slug field to Location and populate it from existing names."""

from django.db import migrations, models
from django.utils.text import slugify


def populate_slugs(apps, schema_editor):
    """Generate URL-friendly slugs for every existing location."""
    Location = apps.get_model("sensemap", "Location")
    for location in Location.objects.all():
        location.slug = slugify(location.name)
        location.save()


def reverse_populate_slugs(apps, schema_editor):
    """No reverse data migration needed: the field is removed anyway."""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("sensemap", "0003_alter_space_space_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="location",
            name="slug",
            field=models.SlugField(
                max_length=255, unique=True, db_index=True, blank=True, null=True
            ),
        ),
        migrations.RunPython(populate_slugs, reverse_populate_slugs),
        migrations.AlterField(
            model_name="location",
            name="slug",
            field=models.SlugField(
                max_length=255, unique=True, db_index=True, blank=True
            ),
        ),
    ]
