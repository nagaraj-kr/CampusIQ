from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import RealCollege
from .serializers import RealCollegeSerializer


@api_view(['GET'])
def get_colleges(request):
    colleges = RealCollege.objects.all()
    serializer = RealCollegeSerializer(colleges, many=True)
    return Response(serializer.data)