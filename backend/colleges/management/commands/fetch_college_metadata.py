"""
Management command to populate college official websites and images from registry.

Usage:
    python manage.py fetch_college_metadata
    python manage.py fetch_college_metadata --college-id=<id>
"""

from django.core.management.base import BaseCommand
from colleges.models import College
from colleges.college_registry import get_college_metadata
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Populate college websites and images from verified registry"

    def add_arguments(self, parser):
        parser.add_argument(
            '--college-id',
            type=int,
            help='Populate metadata for specific college ID',
        )

    def handle(self, *args, **options):
        college_id = options.get('college_id')

        if college_id:
            colleges = College.objects.filter(id=college_id)
        else:
            colleges = College.objects.all()

        total = colleges.count()
        self.stdout.write(self.style.SUCCESS(f"Processing {total} colleges..."))

        updated = 0

        for college in colleges:
            try:
                metadata = get_college_metadata(college.name)
                
                if metadata.get('website') and not college.website.endswith('example.com'):
                    if college.website != metadata['website']:
                        college.website = metadata['website']
                        self.stdout.write(f"✅ {college.name}: Website updated")
                elif metadata.get('website'):
                    college.website = metadata['website']
                    self.stdout.write(f"✅ {college.name}: Website added")
                
                if metadata.get('image_url'):
                    college.image_url = metadata['image_url']
                    self.stdout.write(f"✅ {college.name}: Image added")
                
                college.save()
                updated += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ {college.name}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"\n✅ Updated {updated}/{total} colleges"))

