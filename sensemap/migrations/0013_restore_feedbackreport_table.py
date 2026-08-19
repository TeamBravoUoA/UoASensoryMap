from django.db import migrations


def create_feedback_report_table(apps, schema_editor):
    model = apps.get_model("sensemap", "FeedbackReport")
    if model._meta.db_table not in schema_editor.connection.introspection.table_names():
        schema_editor.create_model(model)


def drop_feedback_report_table(apps, schema_editor):
    model = apps.get_model("sensemap", "FeedbackReport")
    if model._meta.db_table in schema_editor.connection.introspection.table_names():
        schema_editor.delete_model(model)


class Migration(migrations.Migration):

    dependencies = [
        ("sensemap", "0012_merge_20260730_2357"),
    ]

    operations = [
        migrations.RunPython(create_feedback_report_table, drop_feedback_report_table),
    ]