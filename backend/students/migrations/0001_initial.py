# Generated migration to add User FK and auth fields to StudentProfile

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone', models.CharField(blank=True, max_length=15)),
                ('education_level', models.CharField(default='12th', max_length=50)),
                ('course_type', models.CharField(default='Engineering', max_length=100)),
                ('group', models.CharField(default='PCM', max_length=50)),
                ('cutoff_marks', models.FloatField(default=0.0)),
                ('preferred_location', models.CharField(default='Any', max_length=200)),
                ('budget', models.IntegerField(default=500000)),
                ('hostel_required', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='student_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Student Profile',
                'verbose_name_plural': 'Student Profiles',
                'ordering': ['-created_at'],
            },
        ),
    ]
