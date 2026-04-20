from django.contrib import admin
from .models import StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    """Admin for StudentProfile model"""
    
    list_display = [
        'user', 'phone', 'education_level', 'course_type',
        'group', 'budget', 'hostel_required', 'created_at'
    ]
    
    list_filter = [
        'education_level', 'course_type', 'group',
        'hostel_required', 'created_at'
    ]
    
    search_fields = [
        'user__username', 'user__email', 'user__first_name',
        'user__last_name', 'phone'
    ]
    
    readonly_fields = ['created_at', 'updated_at', 'user']
    
    fieldsets = (
        ('User Info', {
            'fields': ('user', 'phone')
        }),
        ('Academic Info', {
            'fields': ('education_level', 'course_type', 'group', 'cutoff_marks')
        }),
        ('Preferences', {
            'fields': ('preferred_location', 'budget', 'hostel_required')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['-created_at']
