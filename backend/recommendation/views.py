from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
from colleges.models import RealCollege
import math
import os
from groq import Groq
from difflib import SequenceMatcher

# Initialize Groq client lazily to avoid import errors when API key is not set
_client = None

def get_groq_client():
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            _client = Groq(api_key=api_key)
    return _client

# ============================================================================
# COURSE VALIDATION & FILTERING
# ============================================================================

def is_valid_course(course):
    """
    Check if a course is a legitimate degree program (not metadata/junk)
    Filters out entries like "Mastercard", "Major Recruiters", "B.Tech Entrances", etc.
    """
    # List of known metadata keywords to exclude
    metadata_keywords = [
        'recruiter', 'placement', 'package', 'salary', 'entrance',
        'seat intake', 'specialisation', 'specializations', 'compare',
        'median', 'offered', 'major domain', 'role', 'sector', 
        'company', 'industries', 'bank', 'mastercard', 'scholarship', 
        'loan', 'fee (first year)', 'admission', 'eligibility', 'merit',
        'cut off', 'application deadline', 'process', 'document',
        'hostel', 'infrastructure', 'library', 'laboratory',
        'teaching', 'faculty', 'alumni', 'batch', 'commencement',
        'best seller', 'berger', 'below tier', 'beyond 10 km',
        'maximum internship', 'maximum job', 'maximum salary',
        'marquee offers', 'maruti', 'marico', 'bain & co', 'bank of',
    ]
    
    course_name_lower = course.name.lower()
    
    # Check if course name contains metadata keywords
    for keyword in metadata_keywords:
        if keyword in course_name_lower:
            return False
    
    # Exclude single-word entries that look like company names
    if ' ' not in course.name and len(course.name) < 5:
        return False
    
    # Exclude entries that are ALL CAPS (likely company/brand names)
    if course.name.isupper() and len(course.name) > 3:
        return False
    
    # Must have actual degree keywords
    degree_keywords = [
        'b.', 'be', 'ba', 'bsc', 'bba', 'b.tech', 'diploma',
        'm.', 'master', 'ma', 'mba', 'msc', 'm.tech', 'mca',
        'llb', 'llm', 'mpharm', 'bds', 'mbbs', 'b.ed', 'b.ed.',
        'phd', 'b.arch', 'certificate', 'pg diploma', 'bachelor',
    ]
    
    if not any(keyword in course_name_lower for keyword in degree_keywords):
        return False
    
    return True

# ============================================================================
# FUZZY COURSE MATCHING
# ============================================================================

def find_matching_courses(user_input, college):
    """
    Find courses matching user input using smart fuzzy matching
    Returns list of matching courses sorted by relevance
    Only returns valid degree programs, filters out metadata
    """
    user_input = user_input.lower().strip()
    matching_courses = []
    
    # Filter to only valid courses first
    valid_courses = [c for c in college.courses.all() if is_valid_course(c)]
    
    if not valid_courses:
        return []
    
    # Try exact match first
    for course in valid_courses:
        if course.name.lower() == user_input:
            matching_courses.append(course)
    
    if matching_courses:
        return matching_courses
    
    # Define keyword patterns for smart matching
    search_patterns = {
        # Master's programs
        'mca': {
            'must_have': ['mca', 'master', 'computer'],
            'should_have': ['application'],
            'boost': ['mca'],
            'avoid': ['bachelor', 'b.', 'b.tech', 'engineering'],
            'min_score': 5,
        },
        'mtech': {
            'must_have': ['m.tech', 'master', 'technology'],
            'should_have': ['engineering'],
            'boost': ['m.tech', 'engineering'],
            'avoid': ['bachelor', 'b.', 'b.tech', 'diploma'],
            'min_score': 5,
        },
        'msc': {
            'must_have': ['m.sc', 'master', 'science'],
            'should_have': ['science'],
            'boost': ['m.sc'],
            'avoid': ['bachelor', 'b.', 'b.tech', 'commerce'],
            'min_score': 5,
        },
        'mcom': {
            'must_have': ['m.com', 'master', 'commerce'],
            'should_have': ['commerce'],
            'boost': ['m.com'],
            'avoid': ['bachelor', 'b.', 'b.tech'],
            'min_score': 5,
        },
        'mba': {
            'must_have': ['mba', 'master', 'business', 'administration'],
            'should_have': ['management'],
            'boost': ['mba'],
            'avoid': ['bachelor', 'b.', 'b.tech', 'diploma'],
            'min_score': 5,
        },
        'med': {
            'must_have': ['m.ed', 'master', 'education'],
            'should_have': ['education'],
            'boost': ['m.ed'],
            'avoid': ['bachelor', 'b.', 'b.tech'],
            'min_score': 5,
        },
        'mpharm': {
            'must_have': ['m.pharm', 'master', 'pharmacy'],
            'should_have': ['pharmacy'],
            'boost': ['m.pharm'],
            'avoid': ['bachelor', 'b.', 'diploma'],
            'min_score': 4,
        },
        # Bachelor's programs
        'btech': {
            'must_have': ['b.tech', 'b.e.', 'be ', 'btech'],
            'should_have': ['technology', 'engineering'],
            'boost': ['b.tech', 'engineering'],
            'avoid': ['master', 'm.', 'mtech', 'mca', 'diploma', 'certificate', 'commerce', 'business administration', 'education', 'pharmacy', 'law'],
            'min_score': 5,
        },
        'bca': {
            'must_have': ['bca', 'computer'],
            'should_have': ['application'],
            'boost': ['bca'],
            'avoid': ['master', 'm.', 'mca', 'engineering', 'technology', 'commerce', 'business administration', 'education'],
            'min_score': 5,
        },
        'bsc': {
            'must_have': ['b.sc', 'bsc'],
            'should_have': ['science'],
            'boost': ['b.sc'],
            'avoid': ['master', 'm.', 'msc', 'commerce', 'business', 'engineering', 'technology'],
            'min_score': 5,
        },
        'bcom': {
            'must_have': ['b.com', 'bcom', 'commerce'],
            'should_have': ['commerce'],
            'boost': ['b.com'],
            'avoid': ['master', 'm.', 'mcom', 'technology', 'engineering', 'business administration'],
            'min_score': 5,
        },
        'bba': {
            'must_have': ['bba'],
            'should_have': ['business', 'administration'],
            'boost': ['bba'],
            'avoid': ['master', 'm.', 'mba', 'technology', 'engineering', 'commerce', 'science'],
            'min_score': 5,
        },
        'bed': {
            'must_have': ['b.ed', 'bed'],
            'should_have': ['education'],
            'boost': ['b.ed'],
            'avoid': ['master', 'm.', 'med', 'technology', 'engineering', 'commerce'],
            'min_score': 5,
        },
        'diploma': {
            'must_have': ['diploma'],
            'should_have': [],
            'boost': [],
            'avoid': ['bachelor', 'master', 'b.', 'm.', 'degree'],
            'min_score': 4,
        },
    }
    
    # Get search pattern for input
    pattern = search_patterns.get(user_input, {
        'must_have': [user_input],
        'should_have': [],
        'boost': [],
        'avoid': [],
        'min_score': 2,
    })
    
    # Try fuzzy matching if no exact pattern
    if user_input not in search_patterns:
        # Split input into keywords
        keywords = user_input.lower().split()
        # If we have keywords like "Computer Science Engineering", use them
        if len(keywords) > 1:
            pattern = {
                'must_have': keywords[:1],  # First keyword is required
                'should_have': keywords[1:],  # Rest are nice to have
                'boost': [],
                'avoid': [],
                'min_score': len(keywords) - 1,  # Need at least 1 keyword
            }
    
    scored_courses = []
    
    for course in valid_courses:
        course_name = course.name.lower()
        
        # Check if REQUIRED keywords are present (must have at least one)
        must_have_count = sum(1 for kw in pattern['must_have'] if kw in course_name)
        if must_have_count == 0:
            continue
        
        # Check should_have keywords (optional but good to have)
        should_have_count = sum(1 for kw in pattern['should_have'] if kw in course_name)
        
        # Calculate boost score
        boost_count = sum(2 for kw in pattern['boost'] if kw in course_name)
        
        # Check for avoid keywords (penalize)
        avoid_count = sum(1 for kw in pattern.get('avoid', []) if kw in course_name)
        
        # String similarity
        similarity = SequenceMatcher(None, user_input, course_name).ratio()
        
        # Total score (higher is better)
        total_score = (must_have_count * 3) + (should_have_count * 1.5) + boost_count + (similarity * 0.5) - (avoid_count * 3)
        
        # Only include if meets minimum threshold
        if total_score >= pattern.get('min_score', 3):
            scored_courses.append((course, total_score))
    
    # Sort by score (highest first)
    scored_courses.sort(key=lambda x: x[1], reverse=True)
    
    # Return top matches (limit to 5)
    return [c[0] for c in scored_courses[:5]]

# ---------------- DISTANCE FUNCTION ----------------
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# ---------------- BUILD REASON DATA ----------------
def build_reason_data(college, course, distance, budget):
    pros = []
    cons = []

    # Placement (from college)
    if college.placement_percentage > 85:
        pros.append("Excellent placement opportunities")
    elif college.placement_percentage > 70:
        pros.append("Good placement support")
    else:
        cons.append("Average placement rate")

    # Distance
    if distance < 50:
        pros.append("Very close to your location")
    elif distance > 300:
        cons.append("Far from your location")

    # Fees (convert lakhs to rupees for comparison)
    course_fees_rupees = course.fees_per_year_lakhs * 100000
    if course_fees_rupees <= budget:
        pros.append(f"Fits within your budget (₹{course_fees_rupees:,.0f})")
    else:
        cons.append(f"Higher than your budget (₹{course_fees_rupees:,.0f})")

    return pros, cons

# ---------------- CLEAN AI OUTPUT ----------------
def clean_reason_output(reason):
    # Capitalize summary
    if reason.get("summary"):
        reason["summary"] = reason["summary"].capitalize()

    # Remove "none" from cons
    reason["cons"] = [c for c in reason.get("cons", []) if c.lower() != "none"]

    # Improve final verdict
    if "consider" in reason.get("final_verdict", "").lower():
        if any("far" in c.lower() for c in reason["cons"]):
            reason["final_verdict"] = "Good option, but distance may be a concern."
        elif len(reason.get("pros", [])) >= 2:
            reason["final_verdict"] = "Strong choice based on your preferences."
        else:
            reason["final_verdict"] = "Decent option depending on your priorities."

    return reason

# ---------------- PARSE AI RESPONSE ----------------
def parse_ai_response(ai_text):
    try:
        lines = ai_text.split("\n")
        summary = ""
        pros = []
        cons = []
        verdict = ""
        section = None

        for line in lines:
            line = line.strip()
            lower_line = line.lower()

            if "summary" in lower_line:
                section = "summary"
                summary += " " + line.split(":", 1)[-1].strip()
            elif "pros" in lower_line:
                section = "pros"
            elif "cons" in lower_line:
                section = "cons"
            elif "verdict" in lower_line or "conclusion" in lower_line:
                section = "verdict"
                verdict += " " + line.split(":", 1)[-1].strip()
            elif line.startswith("-"):
                content = line.replace("-", "").strip()
                if section == "pros":
                    pros.append(content)
                elif section == "cons":
                    cons.append(content)
            else:
                if section == "summary":
                    summary += " " + line
                elif section == "verdict":
                    verdict += " " + line

        # Defaults if empty
        summary = summary.strip() or "This college is a suitable option based on your profile."
        verdict = verdict.strip() or "Consider this college based on your priorities."
        if not pros:
            pros = ["Good academic environment"]
        if not cons:
            cons = []

        return clean_reason_output({
            "summary": summary,
            "pros": pros,
            "cons": cons,
            "final_verdict": verdict
        })

    except Exception as e:
        print("PARSE ERROR:", e)
        return None

# ---------------- AI FUNCTION ----------------
def generate_ai_reason(college, course, distance, cutoff, budget):
    try:
        pros, cons = build_reason_data(college, course, distance, budget)
        prompt = f"""
You are a career advisor.

Student Profile:
Cutoff: {cutoff}
Budget: {budget}

College Details:
Name: {college.name}
Course: {course.name}
Placement: {college.placement_percentage}%
Fees: ₹{course.fees_per_year_lakhs}L/year
Distance: {round(distance,1)} km

Pros:
{pros}

Cons:
{cons}

Generate structured output:

Summary:
Pros:
- point 1
- point 2
Cons:
- point 1 (if any)
Final Verdict:

Keep it clear and useful.
"""
        client = get_groq_client()
        if not client:
            return None
        
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.6
        )
        ai_text = chat_completion.choices[0].message.content.strip()
        return ai_text if ai_text else None

    except Exception as e:
        print("AI ERROR:", e)
        return None

# ============================================================================
# MAIN RECOMMENDATION API
# ============================================================================

@csrf_exempt
@permission_classes([AllowAny])
@api_view(['POST'])
def recommend_colleges(request):
    """
    Recommendation API that finds best colleges for a course
    Filters invalid courses and returns only relevant recommendations
    """
    try:
        cutoff = float(request.data.get('cutoff', 0))
        budget = float(request.data.get('budget', 500000))
        course_name = request.data.get('course', '').strip()
        user_lat = float(request.data.get('latitude', 0))
        user_lon = float(request.data.get('longitude', 0))
    except (ValueError, TypeError):
        return Response({"error": "Invalid input parameters"}, status=400)
    
    if not course_name:
        return Response({"error": "Course name is required"}, status=400)

    result = []
    colleges = RealCollege.objects.all()
    max_distance = 500  # km
    max_fees = 500000   # rupees
    
    # Debug: Print request data
    print(f"DEBUG: Recommendation request - Cutoff: {cutoff}, Course: {course_name}, Budget: {budget}, Lat/Lon: ({user_lat}, {user_lon})")

    # -------- STEP 1: FILTER + SCORE --------
    for college in colleges:
        # Find matching courses using improved fuzzy logic
        # This now filters out invalid/metadata courses
        matching_courses = find_matching_courses(course_name, college)
        print(f"DEBUG: {college.name} - Found {len(matching_courses)} matching courses")
        
        for course in matching_courses:
            # Skip if course has 0 fees (not properly configured)
            if course.fees_lakhs == 0:
                print(f"DEBUG:   Skipping {course.name} - fees data missing")
                continue
            
            print(f"DEBUG:   Processing {course.name} - Fees: {course.fees_lakhs}L")
            
            # Calculate distance-based score
            distance = calculate_distance(user_lat, user_lon, float(college.latitude), float(college.longitude))
            
            # Score components
            distance_score = max(0, 1 - (distance / max_distance))  # 0-1, higher is closer
            placement_score = 0.7  # Default placement for RealCollege data
            fees_rupees = course.fees_lakhs * 100000
            fees_score = max(0, 1 - (fees_rupees / max_fees))  # 0-1, higher is cheaper
            
            # Cutoff score: 1.0 if user qualifies, decreases if user below cutoff
            course_cutoff = getattr(course, 'cutoff', 0)
            if course_cutoff > 0:
                if cutoff >= course_cutoff:
                    cutoff_score = 1.0
                else:
                    shortfall = course_cutoff - cutoff
                    cutoff_score = max(0, 1 - (shortfall / 50))  # Penalize if below cutoff
            else:
                cutoff_score = 0.8  # Default for courses without cutoff data
            
            # Combined weighted score
            # Placement (40%) + Distance (25%) + Fees (20%) + Cutoff (15%)
            score = ((placement_score * 0.40) + 
                    (distance_score * 0.25) + 
                    (fees_score * 0.20) + 
                    (cutoff_score * 0.15)) * 100
            
            print(f"DEBUG:     Distance: {distance:.2f}km, Score breakdown - Placement: {placement_score:.2f}, Distance: {distance_score:.2f}, Fees: {fees_score:.2f}, Cutoff: {cutoff_score:.2f}, Final: {score:.2f}")
            
            result.append({
                "college_name": college.name,
                "location": college.city,
                "course_name": course.name,
                "cutoff": getattr(course, 'cutoff', 0),
                "fees_per_year_lakhs": round(course.fees_lakhs, 2),
                "placement_percentage": 0,
                "distance_km": round(distance, 2),
                "score": round(score, 2),
                "relevance": "HIGH" if score >= 70 else "MEDIUM" if score >= 50 else "LOW",
                "website": college.website,
                "state": college.state,
                "city": college.city,
                "degree_type": course.degree_type,
                "college_id": college.id
            })

    # -------- STEP 2: FILTER LOW-RELEVANCE RESULTS --------
    # Remove results with very low scores (likely bad matches)
    print(f"DEBUG: Total results before filtering: {len(result)}")
    for r in result:
        print(f"DEBUG:   {r['college_name']} - {r['course_name']}: Score {r['score']}")
    
    result = [r for r in result if r['score'] >= 30]
    print(f"DEBUG: Results after score >= 30 filter: {len(result)}")
    
    if not result:
        print(f"DEBUG: No results passed filter")
        return Response({
            "message": "No colleges found matching your criteria",
            "suggestions": "Try different course, location, or budget parameters"
        }, status=200)

    # -------- STEP 3: SORT BY SCORE --------
    result = sorted(result, key=lambda x: x['score'], reverse=True)

    # -------- STEP 4: LIMIT TOP RESULTS --------
    top_results = result[:3]  # Return top 3 instead of 2

    # -------- STEP 5: ADD AI REASONING (Optional) --------
    try:
        for item in top_results:
            try:
                college = RealCollege.objects.get(name=item["college_name"])
                course = college.courses.get(name=item["course_name"])

                # Only call AI for high-relevance results
                if item["relevance"] == "HIGH":
                    ai_text = generate_ai_reason(college, course, item["distance_km"], cutoff, budget)
                    parsed = parse_ai_response(ai_text) if ai_text else None
                else:
                    parsed = None

                if parsed:
                    item["ai_reasoning"] = parsed
                else:
                    # Fallback to basic reasoning
                    pros, cons = build_reason_data(college, course, item["distance_km"], budget)
                    item["ai_reasoning"] = clean_reason_output({
                        "summary": f"{college.name} offers {course.name} with {course.placement_percentage}% placement.",
                        "pros": pros,
                        "cons": cons,
                        "final_verdict": "Consider this option based on your profile."
                    })

            except Exception as e:
                print(f"ERROR generating reasoning for item: {e}")
                import traceback
                traceback.print_exc()
                item["ai_reasoning"] = {
                    "summary": "College recommendation based on your search criteria",
                    "pros": ["Good academic program"],
                    "cons": [],
                    "final_verdict": "Review the college details for more information"
                }
    except Exception as e:
        print(f"ERROR in Step 5: {e}")
        import traceback
        traceback.print_exc()

    # -------- STEP 6: RETURN RESULTS --------
    try:
        print(f"DEBUG: Returning {len(top_results)} recommendations")
        
        # Add missing fields to response items
        for item in top_results:
            try:
                college = RealCollege.objects.get(name=item["college_name"])
                course = college.courses.get(name=item["course_name"])
                item["website"] = college.website
                item["duration_years"] = 4
                item["fees"] = round(course.fees_lakhs * 100000, 2)  # Convert to rupees
            except Exception as e:
                print(f"ERROR adding fields to item: {e}")
                item["website"] = "N/A"
                item["duration_years"] = 0
                item["fees"] = 0
        
        response_data = {
            "status": "success",
            "count": len(top_results),
            "recommendations": top_results,  # Use "recommendations" key for frontend
            "total_matches": len(result),
            "search_criteria": {
                "course": course_name,
                "cutoff": cutoff,
                "budget": budget,
                "location": {"latitude": user_lat, "longitude": user_lon}
            }
        }
        print(f"DEBUG: Response ready with {len(top_results)} items")
        return Response(response_data)
    except Exception as e:
        print(f"ERROR in Step 6: {e}")
        import traceback
        traceback.print_exc()
        return Response({
            "status": "error",
            "message": "Error preparing response",
            "error": str(e)
        }, status=500)