from django.contrib import admin
from .models import RealCollege, RealCourse

# Register RealCollege and RealCourse models
admin.site.register(RealCollege)
admin.site.register(RealCourse)