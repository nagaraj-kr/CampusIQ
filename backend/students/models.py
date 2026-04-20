from django.db import models
from django.contrib.auth.models import User

class StudentProfile(models.Model):
    """Extended student profile linked to Django User"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    phone = models.CharField(max_length=15, blank=True)
    education_level = models.CharField(max_length=50, default='12th')
    course_type = models.CharField(max_length=100, default='Engineering')
    group = models.CharField(max_length=50, default='PCM')
    cutoff_marks = models.FloatField(default=0.0)
    preferred_location = models.CharField(max_length=200, default='Any')
    budget = models.IntegerField(default=500000)
    hostel_required = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.education_level}"
    
    class Meta:
        verbose_name = "Student Profile"
        verbose_name_plural = "Student Profiles"
        ordering = ['-created_at']