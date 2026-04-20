# Generated migration to remove old College, Course, and CollegeImage models

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('colleges', '0002_dataupdatetracker'),
    ]

    operations = [
        # Drop old tables - remove foreign key dependencies first
        migrations.DeleteModel(
            name='CollegeImage',
        ),
        migrations.DeleteModel(
            name='Course',
        ),
        migrations.DeleteModel(
            name='College',
        ),
        migrations.DeleteModel(
            name='DataUpdateTracker',
        ),
    ]
