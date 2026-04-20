from rest_framework import serializers
from .models import RealCollege, RealCourse


class RealCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = RealCourse
        fields = ['id', 'name', 'stream', 'degree_type', 'fees_lakhs']


class RealCollegeSerializer(serializers.ModelSerializer):
    courses = RealCourseSerializer(many=True, read_only=True)

    class Meta:
        model = RealCollege
        fields = ['id', 'name', 'city', 'state', 'latitude', 'longitude', 'website', 'collegedunia_url', 'courses']