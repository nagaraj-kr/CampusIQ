# Generated migration for new College and Course fields

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('colleges', '0003_remove_college_accreditation_and_more'),
    ]

    operations = [
        # Add new fields to College model
        migrations.AddField(
            model_name='college',
            name='degree_level',
            field=models.CharField(
                choices=[
                    ('ENGINEERING', 'Engineering (B.Tech, B.E, M.Tech, etc)'),
                    ('ARTS_SCIENCE', 'Arts & Science (B.Sc, B.A, M.Sc, etc)'),
                    ('COMMERCE', 'Commerce (B.Com, MBA, M.Com, etc)'),
                    ('LAW', 'Law (LLB, LLM, etc)'),
                    ('MEDICAL', 'Medical (MBBS, BDS, etc)'),
                    ('MIXED', 'Mixed (Multiple degree levels)'),
                ],
                default='MIXED',
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name='college',
            name='university_name',
            field=models.CharField(blank=True, default='Unknown', max_length=200),
        ),
        migrations.AddField(
            model_name='college',
            name='collegedunia_url',
            field=models.URLField(blank=True, null=True, default=''),
        ),
        migrations.AddField(
            model_name='college',
            name='official_website',
            field=models.URLField(blank=True, null=True, default=''),
        ),
        
        # Update Course model
        migrations.AddField(
            model_name='course',
            name='stream',
            field=models.CharField(
                choices=[
                    ('ENGINEERING', 'Engineering'),
                    ('ARTS_SCIENCE', 'Arts & Science'),
                    ('COMMERCE', 'Commerce'),
                    ('LAW', 'Law'),
                    ('MEDICAL', 'Medical'),
                    ('UNKNOWN', 'Unknown'),
                ],
                default='UNKNOWN',
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name='course',
            name='degree_type',
            field=models.CharField(default='B.Tech', max_length=50),
        ),
        migrations.AddField(
            model_name='course',
            name='is_valid',
            field=models.BooleanField(default=True),
        ),
        
        # Update College latitude/longitude - remove NOT NULL constraint
        migrations.AlterField(
            model_name='college',
            name='latitude',
            field=models.FloatField(default=0.0),
        ),
        migrations.AlterField(
            model_name='college',
            name='longitude',
            field=models.FloatField(default=0.0),
        ),
        
        # Add indexes for new fields
        migrations.AddIndex(
            model_name='course',
            index=models.Index(fields=['stream'], name='colleges_co_stream_idx'),
        ),
        migrations.AddIndex(
            model_name='course',
            index=models.Index(fields=['code'], name='colleges_co_code_idx'),
        ),
        migrations.AddIndex(
            model_name='course',
            index=models.Index(fields=['degree_type'], name='colleges_co_degree_idx'),
        ),
        migrations.AddIndex(
            model_name='course',
            index=models.Index(fields=['is_valid'], name='colleges_co_valid_idx'),
        ),
    ]
