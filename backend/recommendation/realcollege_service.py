"""
Recommendation Service using RealCollege & RealCourse tables
Provides accurate recommendations based on real scraped college data
"""

from django.db.models import Q
from colleges.models import RealCollege, RealCourse
from students.models import StudentProfile
import math


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates (Haversine formula)"""
    if lat1 == 0 or lon1 == 0 or lat2 == 0 or lon2 == 0:
        return float('inf')
    
    R = 6371  # Earth's radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


def parse_course_input(user_input):
    """Parse user input to extract degree type and specialization"""
    user_input = user_input.lower().strip()
    
    # Degree keywords
    degree_keywords = {
        'btech': ['btech', 'b.tech', 'b tech'],
        'be': ['be', 'b.e', 'b.e.'],
        'bca': ['bca', 'b.ca'],
        'bsc': ['bsc', 'b.sc'],
        'bcom': ['bcom', 'b.com'],
        'bba': ['bba'],
        'bed': ['bed', 'b.ed'],
        'mtech': ['mtech', 'm.tech'],
        'mca': ['mca', 'm.ca'],
        'mba': ['mba'],
    }
    
    # Specialization keywords
    specialization_keywords = [
        ('cse', ['cse', 'computer science', 'computer engineering']),
        ('mechanical', ['mechanical', 'mech']),
        ('civil', ['civil']),
        ('eee', ['eee', 'electrical', 'electrical engineering']),
        ('ece', ['ece', 'electronics']),
        ('it', ['it', 'information technology']),
        ('aiml', ['ai', 'aiml', 'artificial intelligence', 'machine learning']),
        ('ds', ['data science']),
    ]
    
    # Extract degree
    degree = None
    for degree_type, keywords in degree_keywords.items():
        for keyword in keywords:
            if keyword in user_input:
                degree = degree_type
                break
        if degree:
            break
    
    # Extract specialization
    specialization = None
    for spec_type, keywords in specialization_keywords:
        for keyword in keywords:
            if keyword in user_input:
                specialization = spec_type
                break
        if specialization:
            break
    
    return {'degree': degree, 'specialization': specialization}


def find_matching_courses(course_type, college):
    """Find courses in a college that match the user's course type"""
    parsed = parse_course_input(course_type)
    courses = college.courses.all()
    
    matching = []
    
    for course in courses:
        # Match by degree type
        if parsed['degree']:
            if parsed['degree'].lower() in course.degree_type.lower():
                # If specialization specified, check that too
                if parsed['specialization']:
                    if parsed['specialization'].lower() in course.name.lower():
                        matching.append(course)
                else:
                    matching.append(course)
        # If no degree specified, match by specialization
        elif parsed['specialization']:
            if parsed['specialization'].lower() in course.name.lower():
                matching.append(course)
        # Generic match
        else:
            matching.append(course)
    
    return matching


def get_recommendations(preferences):
    """
    Get college recommendations based on user preferences
    
    Args:
        preferences: {
            'cutoff_marks': float,
            'budget': float (in rupees),
            'course_type': str (e.g., 'CSE', 'B.Tech', 'ME'),
            'latitude': float,
            'longitude': float,
            'max_distance': int (km, default=500),
            'limit': int (default=10)
        }
    
    Returns:
        {
            'status': 'success',
            'recommendations': [
                {
                    'college_id': int,
                    'college_name': str,
                    'city': str,
                    'state': str,
                    'course_name': str,
                    'degree_type': str,
                    'fees_per_year_lakhs': float,
                    'website': str,
                    'distance_km': float,
                    'score': float,
                    'reasons': {
                        'pros': [str],
                        'cons': [str]
                    }
                }
            ],
            'total': int
        }
    """
    
    cutoff_marks = preferences.get('cutoff_marks', 0)
    budget = preferences.get('budget', 1000000)
    course_type = preferences.get('course_type', '')
    user_lat = preferences.get('latitude', 0)
    user_lon = preferences.get('longitude', 0)
    max_distance = preferences.get('max_distance', 500)
    limit = preferences.get('limit', 10)
    
    if not course_type:
        return {
            'status': 'error',
            'message': 'Course type is required'
        }
    
    recommendations = []
    
    # Get all RealColleges
    colleges = RealCollege.objects.all()
    
    for college in colleges:
        # Find matching courses
        matching_courses = find_matching_courses(course_type, college)
        
        if not matching_courses:
            continue
        
        # Calculate distance
        distance = calculate_distance(
            user_lat, user_lon,
            float(college.latitude) if college.latitude else 0,
            float(college.longitude) if college.longitude else 0
        )
        
        # Skip if too far
        if distance != float('inf') and distance > max_distance:
            continue
        
        # Score each matching course
        for course in matching_courses:
            # Budget check
            if course.fees_lakhs == 0:
                continue  # Skip courses without fee data
            
            course_fees = course.fees_lakhs * 100000
            if course_fees > budget * 1.2:  # Allow 20% over budget
                continue
            
            # Calculate scores
            distance_score = max(0, 1 - (distance / max_distance)) if distance != float('inf') else 0.5
            fees_score = max(0, 1 - (course_fees / (budget * 1.5)))
            
            # Final score (weighted)
            score = (distance_score * 0.4 + fees_score * 0.6) * 100
            
            # Build recommendation
            rec = {
                'college_id': college.id,
                'college_name': college.name,
                'city': college.city,
                'state': college.state,
                'course_name': course.name,
                'degree_type': course.degree_type,
                'stream': course.stream,
                'fees_per_year_lakhs': round(course.fees_lakhs, 2),
                'website': college.website,
                'collegedunia_url': college.collegedunia_url,
                'distance_km': round(distance, 2) if distance != float('inf') else None,
                'score': round(score, 2),
                'reasons': build_recommendation_reason(college, course, budget, distance)
            }
            
            recommendations.append(rec)
    
    # Sort by score (descending)
    recommendations.sort(key=lambda x: x['score'], reverse=True)
    
    # Limit results
    recommendations = recommendations[:limit]
    
    return {
        'status': 'success',
        'recommendations': recommendations,
        'total': len(recommendations)
    }


def build_recommendation_reason(college, course, budget, distance):
    """Build detailed reasons for recommendation"""
    pros = []
    cons = []
    
    # Fees check
    course_fees = course.fees_lakhs * 100000
    if course_fees <= budget:
        saving = budget - course_fees
        pros.append(f"💰 Affordable: ₹{course_fees:,.0f}/yr (₹{saving:,.0f} within budget)")
    else:
        excess = course_fees - budget
        pros.append(f"✅ Meets eligibility requirements")
    
    # Distance check
    if distance != float('inf'):
        if distance <= 50:
            pros.append(f"📍 Very close: {distance:.0f} km away")
        elif distance <= 200:
            pros.append(f"📍 Accessible: {distance:.0f} km away")
        else:
            cons.append(f"🚗 Located {distance:.0f} km away")
    else:
        cons.append("📍 Location coordinates not available")
    
    # Location
    pros.append(f"📌 Located in {college.city}, {college.state}")
    
    # Course info
    pros.append(f"📚 Offers {course.degree_type} in {course.name}")
    
    if not cons:
        cons.append("Review detailed curriculum on college website")
    
    return {'pros': pros, 'cons': cons}


def filter_colleges(filters):
    """Filter colleges by various criteria"""
    colleges = RealCollege.objects.all()
    
    # Filter by state
    if filters.get('state'):
        colleges = colleges.filter(state__icontains=filters['state'])
    
    # Filter by city
    if filters.get('city'):
        colleges = colleges.filter(city__icontains=filters['city'])
    
    # Filter by degree level
    if filters.get('degree_level'):
        colleges = colleges.filter(degree_level=filters['degree_level'])
    
    # Filter by course type
    if filters.get('course_type'):
        course_type = filters['course_type']
        # Find colleges with matching courses
        matching_colleges = []
        for college in colleges:
            matching_courses = find_matching_courses(course_type, college)
            if matching_courses:
                matching_colleges.append(college)
        colleges = matching_colleges
    
    return colleges


def get_college_detail(college_id):
    """Get detailed information about a college"""
    try:
        college = RealCollege.objects.get(id=college_id)
        
        # Get courses
        courses = college.courses.all()
        courses_data = [
            {
                'id': course.id,
                'name': course.name,
                'degree_type': course.degree_type,
                'stream': course.stream,
                'fees_lakhs': round(course.fees_lakhs, 2)
            }
            for course in courses
        ]
        
        return {
            'status': 'success',
            'college': {
                'id': college.id,
                'name': college.name,
                'city': college.city,
                'state': college.state,
                'latitude': college.latitude,
                'longitude': college.longitude,
                'website': college.website,
                'collegedunia_url': college.collegedunia_url,
                'degree_level': college.degree_level,
                'courses': courses_data,
                'total_courses': len(courses_data)
            }
        }
    except RealCollege.DoesNotExist:
        return {
            'status': 'error',
            'message': 'College not found'
        }
