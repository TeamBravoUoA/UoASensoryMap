# Neutralised migration.
#
# This migration originally added a set of flat fields to ``Location``
# (building, opening_hours, wifi, etc.) and created a ``SensoryReport`` model.
# Those belonged to an earlier, flat schema that has since been replaced by the
# current rich schema in ``0001_initial`` (Location -> Space -> profiles /
# facilities / FeedbackReport). The models no longer exist, so the operations
# here have been emptied to keep the migration history consistent without
# re-introducing the obsolete columns/table.
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sensemap', '0001_initial'),
    ]

    operations = []
