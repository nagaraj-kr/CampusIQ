"""
Integrated Recommendation Service with Scraper Data
Combines student profile, college database, and AI-powered recommendations

Data Flow:
1. User registers/logs in → StudentProfile created with initial preferences
2. User provides details → cutoff, budget, location, preferences
3. System retrieves scraped college data from database
4. Filters colleges based on student preferences
5. Uses Groq AI to generate personalized recommendations  
6. Returns top matched colleges with detailed reasons

API Endpoints:
- POST /api/recommendations/get-recommendations/ - Get college recommendations
- GET /api/recommendations/filter-colleges/ - Filter colleges by criteria
- POST /api/recommendations/save-preference/ - Save student preference
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from colleges.models import RealCollege, RealCourse
from students.models import StudentProfile
from django.contrib.auth.models import User
import math
import os
import logging
from groq import Groq

logger = logging.getLogger(__name__)

# Initialize Groq client
_groq_client = None

def get_groq_client():
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            _groq_client = Groq(api_key=api_key)
    return _groq_client


# ============================================================================
# SMART COURSE MATCHING - ENHANCED INPUT PARSING
# ============================================================================

def parse_course_input(user_input):
    """
    Parse user input to extract degree type and specialization.
    
    Handles:
    - "be cse" → degree='be', specialization='cse'
    - "cse" → specialization='cse', degree=None (match any degree)
    - "be" → degree='be', specialization=None (match all B.E. courses)
    - "btech" → degree='btech', specialization=None
    - "be eee" → degree='be', specialization='eee'
    - "mba" → degree='mba', specialization=None
    
    Returns: {'degree': str or None, 'specialization': str or None}
    """
    user_input = user_input.lower().strip()
    
    # Define degree types
    degree_keywords = {
        'btech': ['btech', 'b.tech', 'b tech'],
        'be': ['be', 'b.e', 'b.e.'],
        'bca': ['bca', 'b.ca', 'b ca'],
        'bsc': ['bsc', 'b.sc', 'b sc'],
        'bcom': ['bcom', 'b.com', 'b com'],
        'bba': ['bba', 'b.b.a'],
        'bed': ['bed', 'b.ed', 'b ed'],
        'barch': ['barch', 'b.arch', 'b arch'],
        'mtech': ['mtech', 'm.tech', 'm tech'],
        'mca': ['mca', 'm.ca', 'm ca'],
        'mba': ['mba', 'm.b.a'],
        'msc': ['msc', 'm.sc', 'm sc'],
        'mcom': ['mcom', 'm.com', 'm com'],
        'med': ['med', 'm.ed', 'm ed'],
        'diploma': ['diploma'],
        'certificate': ['certificate'],
    }
    
    # Define specialization types - NO ambiguous patterns like 'cs', 'it', 'me'!
    # NOTE: CSE keyword patterns work in context:
    #   - When degree='be' is specified: "computer science" is safe (B.E. filtered first)
    #   - When degree=None: We only match 'cse' exactly to avoid B.Sc matches
    specialization_keywords = [
        ('cse', ['cse', 'computer science', 'computer engineering']),
        ('mechanical', ['mechanical', 'mech']),
        ('civil', ['civil']),
        ('eee', ['eee', 'electrical engineering', 'electrical']),
        ('ece', ['ece', 'electronics communication', 'electronics and communication']),
        ('it', ['it', 'information technology', 'information tech']),
        ('ise', ['ise', 'information systems']),
        ('aiml', ['ai', 'aiml', 'artificial intelligence', 'machine learning']),
        ('ds', ['data science']),
        ('auto', ['automobile', 'automotive']),
        ('aero', ['aerospace', 'aeronautical']),
        ('mining', ['mining']),
        ('chemical', ['chemical']),
        ('biomedical', ['biomedical']),
        ('agriculture', ['agriculture']),
    ]
    
    # Parse the input
    parts = user_input.split()
    degree = None
    specialization = None
    remaining_parts = parts.copy()
    
    # Extract degree
    for degree_type, keywords in degree_keywords.items():
        for keyword in keywords:
            if keyword in remaining_parts:
                degree = degree_type
                # Remove degree from parts to isolate specialization
                remaining_parts = [p for p in remaining_parts if p not in keywords]
                break
        if degree:
            break
    
    # Check remaining parts for specialization (prioritized order)
    remaining_input = ' '.join(remaining_parts)
    for spec_type, keywords in specialization_keywords:
        for keyword in keywords:
            if keyword in remaining_input:
                specialization = spec_type
                break
        if specialization:
            break
    
    return {
        'degree': degree,
        'specialization': specialization,
        'parsed_from': user_input
    }


def get_degree_keywords(degree_type):
    """Get all keyword variations for a degree type."""
    patterns = {
        'btech': ['b.tech', 'btech'],  # ONLY B.Tech, NOT B.E.
        'be': ['b.e.', 'be/', 'b.e ', 'b.e,', 'be {', 'be '],  # ONLY B.E.
        'bca': ['bca', 'b.ca', 'computer application'],
        'bsc': ['b.sc', 'bsc', 'bachelor science'],
        'bcom': ['b.com', 'bcom', 'bachelor commerce'],
        'bba': ['bba', 'bachelor business'],
        'bed': ['b.ed', 'bed', 'bachelor education'],
        'barch': ['b.arch', 'barch', 'architecture'],
        'mtech': ['m.tech', 'mtech', 'master technology'],
        'mca': ['mca', 'm.ca', 'master computer'],
        'mba': ['mba', 'master business'],
        'msc': ['m.sc', 'msc', 'master science'],
        'mcom': ['m.com', 'mcom', 'master commerce'],
        'med': ['m.ed', 'med', 'master education'],
        'diploma': ['diploma'],
        'certificate': ['certificate'],
    }
    
    keywords = patterns.get(degree_type, [degree_type.lower()])
    if degree_type.lower() not in keywords:
        keywords.append(degree_type.lower())
    return keywords


def get_specialization_keywords(specialization):
    """Get all keyword variations for an engineering specialization."""
    # Prioritized list of specialization patterns (no ambiguous short patterns!)
    # NOTE: When used with degree filtering, "computer science" is safe
    patterns = [
        ('cse', ['cse', 'computer science', 'computer engineering']),
        ('mechanical', ['mechanical', 'mech']),
        ('civil', ['civil']),
        ('eee', ['eee', 'electrical engineering', 'electrical']),
        ('ece', ['ece', 'electronics communication', 'electronics and communication']),
        ('it', ['it', 'information technology', 'information tech']),
        ('ise', ['ise', 'information systems']),
        ('aiml', ['ai', 'aiml', 'artificial intelligence', 'machine learning']),
        ('ds', ['data science']),
        ('auto', ['automobile', 'automotive']),
        ('aero', ['aerospace', 'aeronautical']),
        ('mining', ['mining']),
        ('chemical', ['chemical']),
        ('biomedical', ['biomedical']),
        ('agriculture', ['agriculture']),
    ]
    
    # Find matching pattern
    for spec_name, keywords in patterns:
        if spec_name.lower() == specialization.lower():
            return keywords
    
    # Fallback
    return [specialization.lower()]


def get_course_matching_keywords(course_type):
    """
    LEGACY: Get all possible keywords for a course type.
    Now uses parse_course_input for better handling.
    """
    parsed = parse_course_input(course_type)
    keywords = []
    
    if parsed['degree']:
        keywords.extend(get_degree_keywords(parsed['degree']))
    
    if parsed['specialization']:
        keywords.extend(get_specialization_keywords(parsed['specialization']))
    
    # If nothing matched, try as a plain keyword
    if not keywords:
        keywords = [course_type.lower()]
    
    return keywords


def find_matching_courses(courses_queryset, course_type):
    """
    SMART COURSE MATCHING: Find courses matching user's desired course type.
    Handles:
    - "be cse" → Find B.E. CSE specifically
    - "cse" → Find any CSE (B.Tech CSE or B.E. CSE)
    - "be" → Find all B.E. courses
    - "btech" → Find all B.Tech courses
    - "mba" → Find all MBA courses
    
    Returns only courses that are relevant to the user's input.
    """
    if not courses_queryset.exists():
        return courses_queryset.none()
    
    # Parse input to extract degree and specialization
    parsed = parse_course_input(course_type)
    degree = parsed['degree']
    specialization = parsed['specialization']
    
    from django.db.models import Q
    q_objects = Q()
    
    # CASE 1: Degree + Specialization specified (e.g., "be cse")
    if degree and specialization:
        degree_keywords = get_degree_keywords(degree)
        specialization_keywords = get_specialization_keywords(specialization)
        
        # Combine: Match both degree AND specialization
        # E.g., "B.E. CSE" matches "B.E." AND "CSE"
        degree_q = Q()
        for kw in degree_keywords:
            degree_q |= Q(name__icontains=kw)
        
        specialization_q = Q()
        for kw in specialization_keywords:
            specialization_q |= Q(name__icontains=kw)
        
        # Filter by degree, then specialization
        matching = courses_queryset.filter(degree_q).filter(specialization_q)
        
        logger.info(f"  📚 Smart match: {degree.upper()} + {specialization.upper()} = {matching.count()} courses")
        return matching
    
    # CASE 2: Only degree specified (e.g., "be", "btech", "mba")
    elif degree:
        degree_keywords = get_degree_keywords(degree)
        for kw in degree_keywords:
            q_objects |= Q(name__icontains=kw)
        
        matching = courses_queryset.filter(q_objects)
        logger.info(f"  📚 Smart match: {degree.upper()} degree = {matching.count()} courses")
        return matching
    
    # CASE 3: Only specialization specified (e.g., "cse", "eee")
    # Use all keywords including CSE-related keywords like "computer science", "BCA", etc.
    elif specialization:
        specialization_keywords = get_specialization_keywords(specialization)
        for kw in specialization_keywords:
            q_objects |= Q(name__icontains=kw)
        
        matching = courses_queryset.filter(q_objects)
        logger.info(f"  📚 Smart match: {specialization.upper()} specialization = {matching.count()} courses")
        return matching
    
    # CASE 4: Fallback - try generic matching
    else:
        keywords = get_course_matching_keywords(course_type)
        for keyword in keywords:
            q_objects |= Q(name__icontains=keyword)
        
        matching = courses_queryset.filter(q_objects)
        logger.info(f"  📚 Generic match: {course_type} = {matching.count()} courses")
        return matching
    
    # If no matches, return empty (don't fall back to all courses)
    return matching


# ============================================================================
# FILTER COLLEGES
# ============================================================================


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates using Haversine formula."""
    if not all([lat1, lon1, lat2, lon2]):
        return float('inf')
    
    R = 6371  # Earth's radius in km
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def should_filter_college(student_profile, college, course, distance):
    """
    STRONG FILTERING: Remove colleges that don't match basic student needs.
    Returns True if college should be EXCLUDED.
    Checks: Cutoff qualification, Budget fit
    """
    # MUST-HAVE: Student qualifies for cutoff
    if course.cutoff and course.cutoff > 0 and student_profile.cutoff_marks:
        if student_profile.cutoff_marks < course.cutoff:
            # Allow small shortfall (±5 marks)
            shortfall = course.cutoff - student_profile.cutoff_marks
            if shortfall > 5:
                logger.debug(f"    → Filtered: Cutoff mismatch ({student_profile.cutoff_marks} < {course.cutoff})")
                return True  # Filter out - doesn't qualify
    
    # BUDGET CHECK: Soft check only (don't filter)
    # Budget is informational - let scoring handle trade-offs
    # Don't hard-filter based on fees - students can take loans/scholarships
    if course.fees_per_year_lakhs and course.fees_per_year_lakhs > 0:
        course_fees = course.fees_per_year_lakhs * 100000
        if student_profile.budget:
            # Only log for debugging - don't filter
            if course_fees > student_profile.budget * 2:
                logger.debug(f"    → Note: Fees high (₹{course_fees:,.0f} vs budget ₹{student_profile.budget:,})")
    
    # Distance check: Skip invalid locations only
    if distance > float('inf'):
        logger.debug(f"    → Filtered: Invalid location")
        return True  # Filter out - invalid location
    
    # If all checks pass, keep the college
    return False


def score_college(student_profile, college, course, distance):
    """
    Calculate match score AFTER filtering. Only called for qualified colleges.
    Score ranges from 0-100.
    **Student-centric scoring** - prioritize what students actually care about.
    """
    score = 0
    
    # ===== PLACEMENT (40% weight) - #1 student concern =====
    # This is the #1 factor students decide on (from college, not course)
    if college.placement_percentage:
        placement_score = (college.placement_percentage / 100) * 40
        score += placement_score
    
    # ===== BUDGET FIT (30% weight) - #2 concern =====
    # How well fees fit within budget
    if course.fees_per_year_lakhs and course.fees_per_year_lakhs > 0:
        course_fees = course.fees_per_year_lakhs * 100000
        
        if student_profile.budget and course_fees > 0:
            if course_fees <= student_profile.budget:
                # Within budget → full 30 points
                score += 30
            else:
                # Above budget but acceptable (already filtered weak cases)
                # Give declining credit: 20-30 points based on how much over
                budget_fit_ratio = student_profile.budget / course_fees
                score += max(20, budget_fit_ratio * 30)
    
    # ===== DISTANCE (20% weight) - #3 concern =====
    # Prioritize nearby colleges (more convenient)
    if distance < float('inf'):
        if distance <= 50:
            # Ideal: very close - best for daily travel
            score += 20
        elif distance <= 150:
            # Good: reasonable distance
            score += 15
        elif distance <= 300:
            # Acceptable: manageable with good infrastructure
            score += 10
        else:
            # Far: still possible with determination
            score += max(5, 20 - (distance / 200))
    
    # ===== CUTOFF MATCH (10% weight) - Nice to have =====
    # Bonus if marks are well above cutoff
    if course.cutoff and student_profile.cutoff_marks:
        cutoff_margin = student_profile.cutoff_marks - course.cutoff
        if cutoff_margin >= 10:
            score += 10  # Good margin
        elif cutoff_margin >= 0:
            score += 5   # Exactly qualifies
    
    return min(100, score)


def build_recommendation_reason(student_profile, college, course, distance):
    """
    Build detailed reason for recommendation - STUDENT PERSPECTIVE.
    Answer: "Why should I pick this college?"
    """
    pros = []
    cons = []
    
    # ===== PRO 1: PLACEMENT (Most important for students) =====
    if college.placement_percentage:
        if college.placement_percentage >= 80:
            pros.append(f"🎯 Excellent placement: {college.placement_percentage}% students placed")
        elif college.placement_percentage >= 60:
            pros.append(f"📊 Good placement: {college.placement_percentage}% students placed")
        else:
            cons.append(f"⚠️ Placement: {college.placement_percentage}%")
    
    # ===== PRO/CON 2: AFFORDABILITY (Second most important) =====
    course_fees = None
    if course.fees_per_year_lakhs and course.fees_per_year_lakhs > 0:
        course_fees = course.fees_per_year_lakhs * 100000
    
    if student_profile.budget and course_fees:
        budget_excess = course_fees - student_profile.budget
        if budget_excess <= 0:
            # Within budget
            savings = student_profile.budget - course_fees
            pros.append(f"💰 Affordable: ₹{course_fees:,.0f}/yr (₹{savings:,.0f} within budget)")
        else:
            # Slightly over budget (but passed filter, so acceptable)
            percentage_over = (budget_excess / student_profile.budget) * 100
            cons.append(f"💸 Costs ₹{budget_excess:,.0f} more than budget ({percentage_over:.0f}% over)")
    
    # ===== PRO/CON 3: LOCATION & COMMUTE =====
    if distance < float('inf'):
        if distance <= 30:
            pros.append(f"📍 Very close location ({distance:.0f} km) - easy commute")
        elif distance <= 100:
            pros.append(f"📍 Reasonable distance ({distance:.0f} km) - manageable")
        elif distance <= 300:
            pros.append(f"📍 Located at {distance:.0f} km - accessible")
        else:
            cons.append(f"🚗 Far location ({distance:.0f} km) - long commute")
    
    # ===== PRO/CON 4: ACADEMIC ELIGIBILITY =====
    if course.cutoff and student_profile.cutoff_marks:
        margin = student_profile.cutoff_marks - course.cutoff
        if margin > 10:
            pros.append(f"✅ Strong qualification: Your marks ({student_profile.cutoff_marks}) are {margin} points above cutoff")
        elif margin >= 0:
            pros.append(f"✅ You qualify: Your marks ({student_profile.cutoff_marks}) meet cutoff ({course.cutoff})")
        else:
            # Should not happen due to filtering, but add as fallback
            shortfall = abs(margin)
            cons.append(f"⚠️ Close call: Cutoff is {shortfall} points higher than your marks")
    
    # ===== BONUS: COLLEGE PRESTIGE =====
    if college.tier in ['IIT', 'NIT', 'IIIT']:
        pros.append(f"🏆 Prestigious {college.tier} institution with strong industry connections")
    elif college.tier in ['Category-1', 'Govt College']:
        pros.append("🏅 Recognized government college with good reputation")
    
    # Ensure we have meaningful content
    if not pros:
        pros.append("Meets your academic requirements")
    if not cons:
        cons.append("Review detailed facilities and curriculum on their official website")
    
    return pros, cons


# ============================================================================
# API ENDPOINTS
# ============================================================================

@csrf_exempt
@permission_classes([AllowAny])
@api_view(['POST'])
def get_recommendations(request):
    """
    Get college recommendations based on student profile.
    
    Request body:
    {
        "user_id": int (optional - for authentication),
        "cutoff_marks": float,
        "budget": int,
        "course_type": str (e.g., "CSE", "ME", "ECE"),
        "latitude": float,
        "longitude": float,
        "location": str (optional - city/state),
        "max_distance": int (default: 1000 km),
        "limit": int (default: 10)
    }
    
    Response:
    {
        "status": "success",
        "recommendations": [
            {
                "college": {...},
                "course": {...},
                "distance_km": float,
                "score": int (0-100),
                "pros": [...],
                "cons": [...],
                "ai_reason": str
            }
        ]
    }
    """
    try:
        data = request.data
        
        # Extract parameters
        cutoff_marks = float(data.get('cutoff_marks', 0))
        budget = float(data.get('budget', 1000000))
        course_type = data.get('course_type', 'CSE')
        user_lat = float(data.get('latitude', 28.7041))  # Default: Delhi
        user_lon = float(data.get('longitude', 77.1025))
        max_distance = int(data.get('max_distance', 1000))  # Max 1000 km
        limit = int(data.get('limit', 10))
        
        logger.info(f"Getting recommendations for cutoff={cutoff_marks}, budget=₹{budget}, course={course_type}")
        logger.info(f"DEBUG: Budget = ₹{budget}, Max acceptable fees = ₹{budget * 1.2}")
        
        # Create or get student profile
        student_profile = StudentProfile(
            cutoff_marks=cutoff_marks,
            budget=budget,
            course_type=course_type,
            preferred_location=data.get('location', 'Any'),
            hostel_required=False  # Hostel not filtered (no hostel data available)
        )
        
        # Query colleges
        colleges = RealCollege.objects.all()
        logger.info(f"DEBUG: Total colleges in database: {colleges.count()}")
        
        # Filter by state if provided
        if data.get('location'):
            colleges = colleges.filter(
                Q(state__icontains=data.get('location')) |
                Q(city__icontains=data.get('location'))
            )
        
        recommendations = []
        filtered_count = 0
        courses_count = 0
        
        # Score and rank colleges
        for college in colleges:
            # Get courses for this college
            courses = college.courses.all()
            
            if not courses.exists():
                logger.debug(f"  ❌ {college.name}: No courses")
                filtered_count += 1
                continue
            
            courses_count += courses.count()
            
            # Filter courses by type/name - SMART MATCHING FOR ALL VARIATIONS
            matching_courses = find_matching_courses(courses, course_type)
            
            if not matching_courses.exists():
                # NO FALLBACK: Skip college if course doesn't match
                # User asked for specific course, don't suggest unrelated programs
                logger.debug(f"  ❌ {college.name}: No courses matching '{course_type}'")
                filtered_count += 1
                continue
            
            if not matching_courses.exists():
                # Skip college if no courses available
                logger.debug(f"  ❌ {college.name}: No matching courses")
                filtered_count += 1
                continue
            
            # Select BEST course from matching_courses (one per college)
            # Since all courses from same college have same placement %, prioritize by fees
            best_course = matching_courses.order_by('fees_per_year_lakhs').first()
            
            if not best_course:
                logger.debug(f"  ❌ {college.name}: No best course")
                filtered_count += 1
                continue
            
            # Calculate distance
            distance = calculate_distance(user_lat, user_lon, college.latitude, college.longitude)
            
            # ===== STRONG FILTERING: Skip colleges that don't match student needs =====
            if should_filter_college(student_profile, college, best_course, distance):
                logger.debug(f"  ❌ {college.name}: Filtered out - Cutoff: {best_course.cutoff}, Fees: ₹{best_course.fees_per_year_lakhs * 100000 if best_course.fees_per_year_lakhs else 0}")
                filtered_count += 1
                continue
            
            # Skip if too far (after filtering check)
            if distance > max_distance:
                logger.debug(f"  ❌ {college.name}: Too far ({distance} km)")
                filtered_count += 1
                continue
            
            # ===== SMART SCORING: Only score colleges that passed filtering =====
            score = score_college(student_profile, college, best_course, distance)
            
            # Build recommendation
            pros, cons = build_recommendation_reason(student_profile, college, best_course, distance)
            
            # Calculate actual fees in rupees (convert from lakhs)
            fees_in_rupees = None
            if best_course.fees_per_year_lakhs and best_course.fees_per_year_lakhs > 0:
                fees_in_rupees = int(best_course.fees_per_year_lakhs * 100000)
            
            rec = {
                'college_id': college.id,
                'college_name': college.name,
                'college_tier': college.tier,
                'college_type': college.type,
                'location': college.location,
                'website': college.website or '',
                'image_url': college.image_url or '',
                'course_name': best_course.name,
                'cutoff': best_course.cutoff,  # Include cutoff for frontend
                'fees': fees_in_rupees,  # Convert from lakhs to rupees
                'duration_years': best_course.duration_years or 0,  # Add duration
                'placement_percentage': college.placement_percentage,
                'distance_km': round(distance, 2),
                'score': int(score),
                'ai_reasoning': {
                    'summary': f"Strong match at {college.name}",
                    'pros': pros,
                    'cons': cons,
                    'verdict': f"{len(pros)} advantages and {len(cons)} considerations make this a good option for your profile."
                }
            }
            
            recommendations.append(rec)
        
        # Sort by score (descending) and get top N
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        recommendations = recommendations[:limit]
        
        logger.info(f"Recommended {len(recommendations)} colleges")
        logger.info(f"DEBUG: Processed {colleges.count()} colleges, {courses_count} total courses, {filtered_count} filtered out")
        
        return Response({
            'status': 'success',
            'count': len(recommendations),
            'recommendations': recommendations
        })
        
    except Exception as e:
        logger.error(f"Error in recommendations: {e}", exc_info=True)
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=400)


@csrf_exempt
@permission_classes([AllowAny])
@api_view(['GET'])
def filter_colleges(request):
    """
    Filter colleges by various criteria.
    
    Query parameters:
    - state: str
    - tier: str (IIT, NIT, IIIT, etc.)
    - type: str (Government, Private, Autonomous)
    - min_placement: int
    - max_fees: int
    - course: str (CSE, ME, ECE, etc.)
    - limit: int (default: 20)
    """
    try:
        colleges = RealCollege.objects.all()
        
        # Apply filters
        if request.GET.get('state'):
            colleges = colleges.filter(state__icontains=request.GET.get('state'))
        
        if request.GET.get('tier'):
            colleges = colleges.filter(tier=request.GET.get('tier'))
        
        if request.GET.get('type'):
            colleges = colleges.filter(type=request.GET.get('type'))
        
        if request.GET.get('min_placement'):
            min_placement = int(request.GET.get('min_placement'))
            colleges = colleges.filter(placement_percentage__gte=min_placement)
        
        if request.GET.get('max_fees'):
            max_fees = int(request.GET.get('max_fees'))
            colleges = colleges.filter(courses__fees__lte=max_fees)
        
        limit = int(request.GET.get('limit', 20))
        
        colleges = colleges[:limit]
        
        data = []
        for college in colleges:
            data.append({
                'id': college.id,
                'name': college.name,
                'location': college.location,
                'tier': college.tier,
                'type': college.type,
                'placement_percentage': college.placement_percentage,
                'average_package_lpa': college.average_package_lpa,
                'courses_count': college.courses.count(),
            })
        
        return Response({
            'status': 'success',
            'count': len(data),
            'colleges': data
        })
        
    except Exception as e:
        logger.error(f"Error in filter_colleges: {e}", exc_info=True)
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=400)


@csrf_exempt
@permission_classes([AllowAny])
@api_view(['GET'])
def get_college_detail(request, college_id):
    """
    Get detailed information about a specific college.
    """
    try:
        college = RealCollege.objects.get(id=college_id)
        courses = college.courses.all()
        
        return Response({
            'status': 'success',
            'college': {
                'id': college.id,
                'name': college.name,
                'short_name': college.short_name,
                'location': college.location,
                'state': college.state,
                'city': college.city,
                'website': college.website,
                'type': college.type,
                'tier': college.tier,
                'established': college.established,
                'placement_percentage': college.placement_percentage,
                'average_package_lpa': college.average_package_lpa,
                'highest_package_lpa': college.highest_package_lpa,
                'fees_per_semester_lakhs': college.fees_per_semester_lakhs,
                'nirf_rank': college.nirf_rank,
                'total_students': college.total_students,
                'faculty_count': college.faculty_count,
                'latitude': college.latitude,
                'longitude': college.longitude,
            },
            'courses': [
                {
                    'id': c.id,
                    'name': c.name,
                    'degree_type': c.degree_type,
                    'stream': c.stream,
                    'fees_per_year_lakhs': c.fees_per_year_lakhs,
                    'cutoff': c.cutoff,
                    'duration_years': c.duration_years,
                }
                for c in courses
            ]
        })
        
    except RealCollege.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'College not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error in get_college_detail: {e}", exc_info=True)
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=400)
