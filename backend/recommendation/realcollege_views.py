"""
Updated API endpoints for recommendation system
Uses RealCollege & RealCourse tables for accurate data
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
from recommendation.realcollege_service import (
    get_recommendations,
    get_college_detail,
    filter_colleges
)
import logging

logger = logging.getLogger(__name__)


@csrf_exempt
@permission_classes([AllowAny])
@api_view(['POST'])
def get_college_recommendations(request):
    """
    Get personalized college recommendations based on student preferences
    
    Request:
    {
        "cutoff_marks": float,
        "budget": float (rupees),
        "course_type": str ("CSE", "B.Tech", "Mechanical", etc),
        "latitude": float,
        "longitude": float,
        "max_distance": int (default: 500),
        "limit": int (default: 10)
    }
    
    Response:
    {
        "status": "success",
        "recommendations": [
            {
                "college_id": int,
                "college_name": str,
                "city": str,
                "state": str,
                "course_name": str,
                "degree_type": str,
                "fees_per_year_lakhs": float,
                "website": str,
                "collegedunia_url": str,
                "distance_km": float,
                "score": float,
                "reasons": {
                    "pros": [str],
                    "cons": [str]
                }
            }
        ],
        "total": int
    }
    """
    try:
        # Get preferences from request
        preferences = {
            'cutoff_marks': request.data.get('cutoff_marks', 0),
            'budget': request.data.get('budget', 1000000),
            'course_type': request.data.get('course_type', ''),
            'latitude': request.data.get('latitude', 0),
            'longitude': request.data.get('longitude', 0),
            'max_distance': request.data.get('max_distance', 500),
            'limit': request.data.get('limit', 10),
        }
        
        # Get recommendations
        result = get_recommendations(preferences)
        
        if result['status'] == 'success':
            return Response({
                'status': 'success',
                'recommendations': result['recommendations'],
                'total': result['total']
            })
        else:
            return Response({
                'status': 'error',
                'message': result.get('message', 'No recommendations found')
            }, status=400)
            
    except Exception as e:
        logger.error(f"Recommendation error: {str(e)}")
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=500)


@csrf_exempt
@permission_classes([AllowAny])
@api_view(['GET'])
def get_college_detail_view(request, college_id):
    """
    Get detailed information about a specific college
    
    Response:
    {
        "status": "success",
        "college": {
            "id": int,
            "name": str,
            "city": str,
            "state": str,
            "latitude": float,
            "longitude": float,
            "website": str,
            "collegedunia_url": str,
            "degree_level": str,
            "courses": [
                {
                    "id": int,
                    "name": str,
                    "degree_type": str,
                    "stream": str,
                    "fees_lakhs": float
                }
            ],
            "total_courses": int
        }
    }
    """
    try:
        result = get_college_detail(college_id)
        
        if result['status'] == 'success':
            return Response(result)
        else:
            return Response(result, status=404)
            
    except Exception as e:
        logger.error(f"College detail error: {str(e)}")
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=500)


@csrf_exempt
@permission_classes([AllowAny])
@api_view(['GET'])
def filter_colleges_view(request):
    """
    Filter colleges by various criteria
    
    Query Parameters:
    - state: str
    - city: str
    - degree_level: str
    - course_type: str
    
    Response:
    {
        "status": "success",
        "colleges": [
            {
                "id": int,
                "name": str,
                "city": str,
                "state": str,
                "website": str,
                "degree_level": str
            }
        ],
        "total": int
    }
    """
    try:
        filters = {
            'state': request.query_params.get('state'),
            'city': request.query_params.get('city'),
            'degree_level': request.query_params.get('degree_level'),
            'course_type': request.query_params.get('course_type'),
        }
        
        colleges = filter_colleges(filters)
        
        colleges_data = [
            {
                'id': college.id,
                'name': college.name,
                'city': college.city,
                'state': college.state,
                'website': college.website,
                'collegedunia_url': college.collegedunia_url,
                'degree_level': college.degree_level,
                'latitude': college.latitude,
                'longitude': college.longitude,
            }
            for college in colleges
        ]
        
        return Response({
            'status': 'success',
            'colleges': colleges_data,
            'total': len(colleges_data)
        })
        
    except Exception as e:
        logger.error(f"Filter error: {str(e)}")
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=500)
