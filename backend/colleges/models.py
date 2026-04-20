from django.db import models

# Only keep RealCollege and RealCourse (with real data from CollegeDunia)


class RealCollege(models.Model):
    """
    New table for storing REAL college data scraped from CollegeDunia.
    This keeps the scraped data separate from the old/hardcoded data.
    """
    DEGREE_LEVEL_CHOICES = [
        ('ENGINEERING', 'Engineering (B.Tech, B.E, M.Tech, etc)'),
        ('ARTS_SCIENCE', 'Arts & Science (B.Sc, B.A, M.Sc, etc)'),
        ('COMMERCE', 'Commerce (B.Com, MBA, M.Com, etc)'),
        ('LAW', 'Law (LLB, LLM, etc)'),
        ('MEDICAL', 'Medical (MBBS, BDS, etc)'),
        ('UNKNOWN', 'Unknown'),
    ]
    
    # Basic information
    name = models.CharField(max_length=300, unique=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, default='Tamil Nadu')
    
    # Location coordinates
    latitude = models.FloatField(default=0.0)
    longitude = models.FloatField(default=0.0)
    
    # College URLs
    website = models.URLField(default='', blank=True)
    collegedunia_url = models.URLField(default='', blank=True)
    
    # Metadata
    degree_level = models.CharField(max_length=30, choices=DEGREE_LEVEL_CHOICES, default='UNKNOWN')
    
    # Tracking
    scraped_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_validated = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['city']),
            models.Index(fields=['state']),
            models.Index(fields=['degree_level']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.city})"


class RealCourse(models.Model):
    """
    Courses for RealCollege - stores actual course data from CollegeDunia
    """
    STREAM_CHOICES = [
        ('ENGINEERING', 'Engineering'),
        ('ARTS_SCIENCE', 'Arts & Science'),
        ('COMMERCE', 'Commerce'),
        ('LAW', 'Law'),
        ('MEDICAL', 'Medical'),
        ('UNKNOWN', 'Unknown'),
    ]
    
    college = models.ForeignKey(RealCollege, on_delete=models.CASCADE, related_name='courses')
    name = models.CharField(max_length=200)
    stream = models.CharField(max_length=30, choices=STREAM_CHOICES, default='UNKNOWN')
    degree_type = models.CharField(max_length=50, default='Unknown')  # B.Tech, B.Sc, M.Tech, etc.
    fees_lakhs = models.FloatField(default=0)  # Annual fees in lakhs
    scraped_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['college']),
            models.Index(fields=['stream']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.college.name})"