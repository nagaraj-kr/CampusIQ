# Migration to add missing fields to StudentProfile table

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('students', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentprofile',
            name='user',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='student_profile', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='studentprofile',
            name='phone',
            field=models.CharField(blank=True, default='', max_length=15),
        ),
        migrations.AddField(
            model_name='studentprofile',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='studentprofile',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='studentprofile',
            name='education_level',
            field=models.CharField(default='12th', max_length=50),
        ),
        migrations.AlterField(
            model_name='studentprofile',
            name='course_type',
            field=models.CharField(default='Engineering', max_length=100),
        ),
        migrations.AlterField(
            model_name='studentprofile',
            name='group',
            field=models.CharField(default='PCM', max_length=50),
        ),
        migrations.AlterField(
            model_name='studentprofile',
            name='cutoff_marks',
            field=models.FloatField(default=0.0),
        ),
        migrations.AlterField(
            model_name='studentprofile',
            name='preferred_location',
            field=models.CharField(default='Any', max_length=200),
        ),
        migrations.AlterField(
            model_name='studentprofile',
            name='budget',
            field=models.IntegerField(default=500000),
        ),
    ]

