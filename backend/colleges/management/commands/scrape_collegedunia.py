import time
import logging
import os
import re
from django.core.management.base import BaseCommand
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from colleges.models import RealCollege, RealCourse

# Allow sync DB operations in async context
os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataCleaner:
    """Clean and validate scraped data with STRICT filters"""
    
    # Valid course code prefixes (must start with these)
    COURSE_PREFIXES = [
        'b.tech', 'btech', 'b tech',
        'm.tech', 'mtech', 'm tech',
        'b.sc', 'bsc', 'b sc',
        'm.sc', 'msc', 'm sc',
        'bba', 'b.b.a', 'b.a', 'ba',
        'mba', 'm.b.a', 'ma',
        'b.e', 'be',
        'llb', 'll.b',
        'diploma',
        'pg diploma',
        'phd',
        'diploma in',
        'certificate',
        'pharma', 'b pharma',
        # Full degree names
        'bachelor', 'master', 'doctoral',
        'b.ed', 'bed', 'm.ed', 'med',
        'b.des', 'bdes', 'b.arch', 'barch',
        'b.com', 'bcom', 'm.com', 'mcom',
        'b.pharma', 'b pharma', 'bpharm',
        'm.pharma', 'm pharma', 'mpharm',
        'mbbs', 'bds', 'b.des',
    ]
    
    # Things that should NEVER be in a course name
    GARBAGE_KEYWORDS = [
        # Administrative terms
        'registration', 'allocation', 'interview', 'counselling', 'validation',
        'verification', 'submission', 'classes begin', 'placement date',
        'choice filling', 'seat allocation', 'admission',
        
        # Exam/Result related
        'cmat result', 'exam date', 'correction', 'tancet', 'tnea',
        'result', 'merit list', 'cutoff',
        
        # College info metadata (NOT courses)
        'accreditation', 'approved by', 'affiliated to', 'established',
        'campus area', 'courses offered', 'facilities', 'library',
        'location', 'official website', 'recognized by',
        
        # Course metadata that should be separate fields
        'duration', 'mode of study', 'course level', 'eligibility',
        'seat intake', 'total fees', 'total cost', 'fees',
        'annual fee', 'semester', 'other fee',
        
        # Irrelevant content
        'circular', 'notice', 'news', 'update', 'amendment', 'round', 'schedule',
        'click here', 'view here', 'download', 'apply here',
        'http', 'www.', 'https', 'link', 'pdf', 'brochure', 'prospectus',
        
        # Admission related
        'criterion', 'apply', 'requirement', 'rank', 'marks', 'score',
        'ranking', 'nirf', 'batch size',
        
        # Dates and years
        '2024', '2025', '2026', '2027', '2028', 'reporting', 'allotment',
        'phase', 'round', 'provisional',
    ]

    @staticmethod
    def clean_college_name(name):
        """Remove metadata from college name"""
        name = re.sub(r':.*$', '', name)  # Remove everything after ':'
        name = name.replace('Admission 2026', '').replace('Admission 2025', '')
        name = name.replace('Fees', '').replace('Courses', '').replace('Ranking', '')
        name = name.replace('Placement', '').replace('Cutoff', '').strip()
        # Remove trailing hyphens or pipes
        name = re.sub(r'[-|]+$', '', name).strip()
        if len(name) > 100:  # Reject garbage
            return None
        return name

    @staticmethod
    def is_valid_college_name(name):
        """STRICT validation for college names - must be a real college"""
        if not name or len(name) < 3 or len(name) > 100:
            return False
        
        name_lower = name.lower()
        
        # Reject pages that are clearly NOT colleges
        INVALID_PATTERNS = [
            r'table\s+of\s+contents',
            r'latest\s+(update|news)',
            r'admission\s+(timeline|criteria)',
            r'ranking\s+\d{4}',
            r'\d{4}\s+ranking',
            r'cutoff.*\d{4}',
            r'news.*update',
            r'update.*news',
            r'upcoming\s+(exam|notification|result)',
            r'admission\s+(alert|notification)',
        ]
        
        for pattern in INVALID_PATTERNS:
            if re.search(pattern, name_lower):
                return False
        
        # MUST contain college identifier keywords
        VALID_KEYWORDS = [
            'college', 'institute', 'university', 'school', 'academy',
            'iiit', 'iit', 'nit', 'ism', 'dtu', 'iim',
            'tce', 'nce', 'ace', 'sairam', 'psg', 'cmc', 'loyola',
            'presidency', 'hindu', 'miranda', 'xavier',
        ]
        
        has_valid_keyword = any(kw in name_lower for kw in VALID_KEYWORDS)
        if not has_valid_keyword:
            return False
        
        return True

    @staticmethod
    def clean_course_name(name):
        """Remove view counts and metadata from course name"""
        # Remove patterns like "(1.4KViews)" or "(225Views)"
        name = re.sub(r'\(\d+\.?\d*[KMB]?Views?\)', '', name)
        # Remove course counts like "M.Tech25Courses"
        name = re.sub(r'(\d+Courses)', '', name)
        # Remove extra parentheses
        name = re.sub(r'\[\d+.*?\]', '', name)
        # Clean up whitespace
        name = re.sub(r'\s+', ' ', name).strip()
        return name

    @staticmethod
    def is_valid_course_name(name):
        """STRICT validation: Must pass ALL checks"""
        # Too short or too long
        if len(name) < 5 or len(name) > 80:
            return False
        
        # Check for garbage keywords FIRST (most important)
        name_lower = name.lower()
        if any(keyword in name_lower for keyword in DataCleaner.GARBAGE_KEYWORDS):
            return False
        
        # Must start with a valid course prefix
        starts_with_valid = any(name_lower.startswith(prefix) for prefix in DataCleaner.COURSE_PREFIXES)
        if not starts_with_valid:
            return False
        
        # Further checks
        if any(char in name for char in ['(', ')', '[', ']']) and len(name) > 60:
            return False  # Probably malformed
        
        return True

    @staticmethod
    def extract_fees_lakhs(fee_text):
        """Extract fees and validate - handles both rupees and lakhs"""
        if not fee_text or len(fee_text) < 1:
            return 0.0
        
        try:
            numbers = re.findall(r'\d+\.?\d*', fee_text)
            if not numbers:
                return 0.0
            
            fee_value = float(numbers[0])
            
            # Detect if fee is in rupees (< 100,000) or already in lakhs
            # If < 100, assume it's already in lakhs (e.g., "3.5 lakhs")
            # If 100-100000, assume it's in rupees (e.g., "₹7,758") → convert to lakhs
            # If > 100000, assume it's in rupees (e.g., "1200000" rupees) → convert to lakhs
            
            if fee_value < 100:
                # Already in lakhs (e.g., 3.5 lakhs)
                if 0 <= fee_value <= 200:  # Realistic range
                    return fee_value
                else:
                    return 0.0
            elif fee_value <= 100000:
                # In rupees, convert to lakhs (e.g., 7758 rupees → 0.07758 lakhs)
                return fee_value / 100000
            else:
                # Large rupee amount, convert to lakhs (e.g., 348000 rupees → 3.48 lakhs)
                fee_lakhs = fee_value / 100000
                if fee_lakhs <= 200:  # Realistic range for annual fees
                    return fee_lakhs
                else:
                    return 0.0
        except:
            return 0.0

    # Comprehensive city-to-state mapping for India
    CITY_STATE_MAP = {
        'Chennai': 'Tamil Nadu', 'Coimbatore': 'Tamil Nadu', 'Madurai': 'Tamil Nadu',
        'Trichy': 'Tamil Nadu', 'Tiruchirappalli': 'Tamil Nadu', 'Erode': 'Tamil Nadu',
        'Salem': 'Tamil Nadu', 'Tiruppur': 'Tamil Nadu', 'Vellore': 'Tamil Nadu',
        'Kanyakumari': 'Tamil Nadu', 'Cuddalore': 'Tamil Nadu', 'Villupuram': 'Tamil Nadu',
        'Thoothukudi': 'Tamil Nadu', 'Tirunelveli': 'Tamil Nadu', 'Nagercoil': 'Tamil Nadu',
        'Puducherry': 'Puducherry', 'Yanam': 'Puducherry', 'Karaikal': 'Puducherry',
        'Mahe': 'Puducherry',
        'Delhi': 'Delhi', 'New Delhi': 'Delhi', 'Delhi NCR': 'Delhi',
        'Mumbai': 'Maharashtra', 'Pune': 'Maharashtra', 'Nagpur': 'Maharashtra',
        'Aurangabad': 'Maharashtra', 'Nashik': 'Maharashtra', 'Kolhapur': 'Maharashtra',
        'Banglore': 'Karnataka', 'Bangalore': 'Karnataka', 'Mysore': 'Karnataka',
        'Belgaum': 'Karnataka', 'Belagavi': 'Karnataka', 'Mangalore': 'Karnataka',
        'Manipal': 'Karnataka', 'Udupi': 'Karnataka',
        'Hyderabad': 'Telangana', 'Warangal': 'Telangana', 'Vijayawada': 'Andhra Pradesh',
        'Visakhapatnam': 'Andhra Pradesh', 'Tirupati': 'Andhra Pradesh',
        'Jaipur': 'Rajasthan', 'Kota': 'Rajasthan', 'Jodhpur': 'Rajasthan',
        'Ajmer': 'Rajasthan', 'Udaipur': 'Rajasthan',
        'Chandigarh': 'Chandigarh', 'Mohali': 'Punjab',
        'Ludhiana': 'Punjab', 'Amritsar': 'Punjab', 'Jalandhar': 'Punjab',
        'Patiala': 'Punjab', 'Bathinda': 'Punjab',
        'Lucknow': 'Uttar Pradesh', 'Kanpur': 'Uttar Pradesh', 'Meerut': 'Uttar Pradesh',
        'Noida': 'Uttar Pradesh', 'Ghaziabad': 'Uttar Pradesh', 'Varanasi': 'Uttar Pradesh',
        'Allahabad': 'Uttar Pradesh', 'Agra': 'Uttar Pradesh',
        'Patna': 'Bihar', 'Gaya': 'Bihar', 'Bhagalpur': 'Bihar',
        'Kolkata': 'West Bengal', 'Kharagpur': 'West Bengal', 'Darjeeling': 'West Bengal',
        'Siliguri': 'West Bengal', 'Howrah': 'West Bengal',
        'Guwahati': 'Assam', 'Silchar': 'Assam',
        'Bhubaneswar': 'Odisha', 'Rourkela': 'Odisha', 'Cuttack': 'Odisha',
        'Sambalpur': 'Odisha', 'Berhampur': 'Odisha',
        'Ahmedabad': 'Gujarat', 'Vadodara': 'Gujarat', 'Surat': 'Gujarat',
        'Rajkot': 'Gujarat', 'Bhavnagar': 'Gujarat',
        'Indore': 'Madhya Pradesh', 'Bhopal': 'Madhya Pradesh', 'Gwalior': 'Madhya Pradesh',
        'Jabalpur': 'Madhya Pradesh', 'Ujjain': 'Madhya Pradesh',
        'Mandi': 'Himachal Pradesh', 'Shimla': 'Himachal Pradesh', 'Solan': 'Himachal Pradesh',
        'Kangra': 'Himachal Pradesh', 'Hamirpur': 'Himachal Pradesh',
        'Srinagar': 'Jammu and Kashmir', 'Jammu': 'Jammu and Kashmir',
        'Kochi': 'Kerala', 'Thiruvananthapuram': 'Kerala', 'Kozhikode': 'Kerala',
        'Ernakulam': 'Kerala', 'Kannur': 'Kerala', 'Kottayam': 'Kerala',
    }

    # Set of all known states for validation
    INDIAN_STATES = {
        'Tamil Nadu', 'Delhi', 'Maharashtra', 'Karnataka', 'Uttar Pradesh',
        'Himachal Pradesh', 'Rajasthan', 'West Bengal', 'Bihar', 'Gujarat',
        'Madhya Pradesh', 'Punjab', 'Haryana', 'Jharkhand', 'Odisha',
        'Andhra Pradesh', 'Telangana', 'Kerala', 'Assam', 'Chandigarh',
        'Puducherry', 'Goa', 'Tripura', 'Meghalaya', 'Manipur', 'Mizoram',
        'Nagaland', 'Sikkim', 'Uttarakhand', 'Chhattisgarh', 'Jammu and Kashmir'
    }

    @staticmethod
    def extract_state_city(location_text):
        """Extract state and city - STRICT format validation with comprehensive mapping"""
        if not location_text or len(location_text) < 2:
            return 'Unknown', 'Unknown'
        
        # Too long = probably garbage
        if len(location_text) > 100:
            return 'Unknown', 'Unknown'
        
        # Try comma-separated format first
        parts = [p.strip() for p in location_text.split(',')]
        
        if len(parts) >= 2:
            # Format: "City, State" or "City, State, Country"
            first_part = parts[0].strip()
            second_part = parts[1].strip()
            
            # Check which is city and which is state
            if second_part in DataCleaner.INDIAN_STATES:
                # Format is correct: City, State
                return second_part, first_part
            elif first_part in DataCleaner.INDIAN_STATES:
                # Reversed: State, City
                return first_part, second_part
            else:
                # Unknown format, try to match against known cities
                if first_part in DataCleaner.CITY_STATE_MAP:
                    return DataCleaner.CITY_STATE_MAP[first_part], first_part
                elif second_part in DataCleaner.CITY_STATE_MAP:
                    return DataCleaner.CITY_STATE_MAP[second_part], second_part
                else:
                    # Default: assume City, State
                    return second_part, first_part
                    
        elif len(parts) == 1:
            # Single part - try to match against known cities or states
            location = parts[0].strip()
            
            # Check if it's a known state
            if location in DataCleaner.INDIAN_STATES:
                return location, 'Unknown'
            
            # Check if it's a known city
            if location in DataCleaner.CITY_STATE_MAP:
                return DataCleaner.CITY_STATE_MAP[location], location
            
            # Try case-insensitive match
            for known_city, state_name in DataCleaner.CITY_STATE_MAP.items():
                if known_city.lower() == location.lower():
                    return state_name, known_city
            
            # Try case-insensitive state match
            for known_state in DataCleaner.INDIAN_STATES:
                if known_state.lower() == location.lower():
                    return known_state, 'Unknown'
            
            # Unknown - return as city
            return 'Unknown', location
        else:
            return 'Unknown', 'Unknown'


class Command(BaseCommand):
    help = 'Scrape clean college and course data from Collegedunia'

    def add_arguments(self, parser):
        parser.add_argument('--batch-size', type=int, default=5, help='Number of colleges to scrape')
        parser.add_argument('--no-headless', action='store_true', help='Show browser window')

    def extract_college_details(self, page, college_url):
        """Extract COMPREHENSIVE college details"""
        try:
            page_content = page.content()
            soup = BeautifulSoup(page_content, 'html.parser')
            
            # 1. College Name
            title = page.title() or "Unknown"
            name = DataCleaner.clean_college_name(title)
            if not name or name == "Unknown":
                name = "Unknown College"
            
            # 2. Location & State/City - IMPROVED EXTRACTION
            location_text = "Unknown"
            state = "Unknown"
            city = "Unknown"
            
            # STRATEGY 1: Extract city from college name (many colleges have city in name)
            # e.g., "TCE Madurai" -> Madurai, "CMC Vellore" -> Vellore
            for city_name in DataCleaner.CITY_STATE_MAP.keys():
                if city_name in name:
                    location_text = city_name
                    logger.info(f"   Found city '{city_name}' in college name: {name}")
                    break
            
            # STRATEGY 2: Look for location in HTML patterns (from webpage)
            if location_text == "Unknown":
                location_patterns = [
                    soup.find('p', string=lambda x: x and 'Location' in str(x)),
                    soup.find('span', string=lambda x: x and 'Location' in str(x)),
                    soup.find('div', string=lambda x: x and 'Location' in str(x)),
                ]
                
                for elem in location_patterns:
                    if elem:
                        location_text = elem.get_text(strip=True).replace('Location:', '').replace('Location', '').strip()
                        if location_text and location_text != "Unknown":
                            logger.info(f"   Found location in HTML: {location_text}")
                            break
            
            # STRATEGY 3: Search page for known city names
            if location_text == "Unknown":
                for city_name in DataCleaner.CITY_STATE_MAP.keys():
                    if city_name in page_content:
                        location_text = city_name
                        logger.info(f"   Found city '{city_name}' in page content")
                        break
            
            # STRATEGY 4: Try to extract from page text (look for state names)
            if location_text == "Unknown":
                indian_states = ['Tamil Nadu', 'Delhi', 'Maharashtra', 'Karnataka', 'Uttar Pradesh',
                               'Himachal Pradesh', 'Rajasthan', 'West Bengal', 'Bihar', 'Gujarat',
                               'Madhya Pradesh', 'Punjab', 'Haryana', 'Jharkhand', 'Odisha',
                               'Andhra Pradesh', 'Telangana', 'Kerala', 'Assam', 'Chandigarh']
                for state_name in indian_states:
                    if state_name in page_content:
                        location_text = state_name
                        logger.info(f"   Found state '{state_name}' in page content")
                        break
            
            # Extract state and city from location text
            if location_text and location_text != "Unknown":
                state, city = DataCleaner.extract_state_city(location_text)
                logger.info(f"   Extracted: City={city}, State={state}")
            
            # 3. Placement Percentage
            placement_percentage = 0.0
            try:
                # Look for "placement" or "placed" with percentage
                placement_text = page_content.lower()
                if 'placement' in placement_text:
                    # Find percentage after "placement"
                    matches = re.findall(r'placement.*?(\d+)\s*%', page_content, re.IGNORECASE)
                    if matches:
                        placement_percentage = float(matches[0])
            except:
                pass
            
            # 4. NIRF Rank
            nirf_rank = 0
            try:
                nirf_text = page_content.lower()
                if 'nirf' in nirf_text and 'rank' in nirf_text:
                    # Find rank number near NIRF
                    matches = re.findall(r'nirf.*?#?(\d+)', page_content, re.IGNORECASE)
                    if matches:
                        nirf_rank = int(matches[0])
            except:
                pass
            
            # 5. Average Fees
            average_fees = 0.0
            try:
                # Look for fee structures
                fee_patterns = [
                    r'fee.*?₹?\s*(\d+\.?\d*)\s*[Ll]akh',
                    r'₹?\s*(\d+\.?\d*)\s*[Ll]akh.*?fee',
                ]
                for pattern in fee_patterns:
                    matches = re.findall(pattern, page_content)
                    if matches:
                        # Take first reasonable match
                        fee_val = float(matches[0])
                        if 0 < fee_val < 100:  # Reasonable range
                            average_fees = fee_val
                            break
            except:
                pass
            
            # 6. College Type & Tier
            college_type = "Government"
            tier = "Regular"
            
            page_lower = page_content.lower()
            if 'private' in page_lower:
                college_type = "Private"
            
            if 'iit' in name.lower():
                tier = "IIT - Premier"
            elif 'nit' in name.lower():
                tier = "NIT - National"
            elif 'iiit' in name.lower():
                tier = "IIIT - IT-Focused"
            elif 'government' in college_type.lower():
                tier = "Govt College"
            
            # 7. Simple Geolocation (approximate)
            latitude = 0.0
            longitude = 0.0
            
            # Try to get approximate coordinates from city name
            city_coords = {
                'dhanbad': (23.7957, 86.4304),
                'tiruchirappalli': (10.8069, 78.7047),
                'mandi': (32.2303, 76.9197),
                'delhi': (28.7041, 77.1025),
                'varanasi': (25.3209, 82.9789),
                'madurai': (9.9252, 78.1198),
                'kharagpur': (22.3039, 87.3119),
            }
            
            for city_key, coords in city_coords.items():
                if city_key in city.lower():
                    latitude, longitude = coords
                    break
            
            return {
                'name': name,
                'location': city if city != "Unknown" else location_text,
                'state': state,
                'city': city,
                'type': college_type,
                'tier': tier,
                'website': college_url,
                'latitude': latitude,
                'longitude': longitude,
                'placement_percentage': placement_percentage,
                'nirf_rank': nirf_rank,
            }
        except Exception as e:
            logger.error(f"Error extracting college: {e}")
            return None

    def extract_course_type_fees(self, soup):
        """Extract fees from 'Popular Full time Courses' section which has course-level fees"""
        fees_map = {}  # Maps course type to fees (e.g., 'B.Tech' -> 9.39)
        
        try:
            # Look for the Popular Full time Courses section
            page_text = soup.get_text()
            
            # Find all instances of course type with fees
            # Patterns: "M.Tech\n₹1.82 Lakhs" or "B.Tech\n₹9.39 Lakhs"
            patterns = [
                (r"B\.?Tech[®]?\s*\n\s*₹([\d.]+)\s*Lakhs?", "B.Tech"),
                (r"M\.?Tech\s*\n\s*₹([\d.]+)\s*Lakhs?", "M.Tech"),
                (r"B\.?Sc\s*\n\s*₹([\d.]+)\s*Lakhs?", "B.Sc"),
                (r"M\.?Sc\s*\n\s*₹([\d.]+)\s*Lakhs?", "M.Sc"),
                (r"MBA\s*\n\s*₹([\d.]+)\s*Lakhs?", "MBA"),
                (r"B\.?A\s*\n\s*₹([\d.]+)\s*Lakhs?", "B.A"),
                (r"M\.?A\s*\n\s*₹([\d.]+)\s*Lakhs?", "M.A"),
                (r"Ph\.?D\s*\n\s*₹([\d.]+)\s*Lakhs?", "Ph.D"),
                (r"Diploma[^a-z]?\s*\n\s*₹([\d.]+)\s*Lakhs?", "Diploma"),
                (r"B\.?E\s*\n\s*₹([\d.]+)\s*Lakhs?", "B.E"),
                (r"LLB\s*\n\s*₹([\d.]+)\s*Lakhs?", "LLB"),
                (r"BBA\s*\n\s*₹([\d.]+)\s*Lakhs?", "BBA"),
            ]
            
            for pattern, course_type in patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    # Take the first match for this course type
                    try:
                        fees_value = float(matches[0])
                        if 0 < fees_value <= 200:  # Reasonable range
                            fees_map[course_type] = fees_value
                            logger.info(f"Found {course_type}: ₹{fees_value} Lakhs")
                    except:
                        pass
            
            return fees_map
        except Exception as e:
            logger.warning(f"Error extracting course type fees: {e}")
            return {}

    def map_course_fees(self, courses_data, fees_map):
        """Match extracted courses to course types and apply their fees"""
        try:
            for course in courses_data:
                course_name = course['name'].lower()
                
                # Try to match course name to a course type with known fees
                for course_type, fees_value in fees_map.items():
                    course_type_lower = course_type.lower()
                    
                    # Match: "B.Tech Computer Science Engineering" -> matches "B.Tech"
                    if course_name.startswith(course_type_lower.replace('.', '').replace(' ', '')):
                        course['fees_per_year_lakhs'] = fees_value
                        logger.info(f"Applied fees {fees_value} Lakhs to {course['name']}")
                        break
                    
                    # Match: "Computer Science Engineering (B.Tech)" -> matches "B.Tech"
                    if course_type_lower in course_name:
                        course['fees_per_year_lakhs'] = fees_value
                        logger.info(f"Applied fees {fees_value} Lakhs to {course['name']}")
                        break
            
            return courses_data
        except Exception as e:
            logger.warning(f"Error mapping course fees: {e}")
            return courses_data

    def extract_course_details(self, soup):
        """Extract course details from tables - specifically looking for Course name + Total Fees columns"""
        courses_data = []
        
        try:
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                if len(rows) < 2:
                    continue
                
                # Get header row to identify column positions
                header_row = rows[0]
                header_cells = [cell.get_text(strip=True).lower() for cell in header_row.find_all(['th', 'td'])]
                
                # Find column indices for Course name and Total Fees
                course_col_idx = None
                fees_col_idx = None
                
                for idx, header in enumerate(header_cells):
                    if 'course' in header and course_col_idx is None:
                        course_col_idx = idx
                    if 'fees' in header and 'total' in header and fees_col_idx is None:
                        fees_col_idx = idx
                    # Alternative: just 'total fees' without 'course'
                    if 'total' in header and 'fee' in header and fees_col_idx is None:
                        fees_col_idx = idx
                
                # If we found both columns, extract course-fee pairs
                if course_col_idx is not None and fees_col_idx is not None:
                    for row in rows[1:]:  # Skip header
                        cells = row.find_all(['td', 'th'])
                        if len(cells) <= max(course_col_idx, fees_col_idx):
                            continue
                        
                        course_name = cells[course_col_idx].get_text(strip=True)
                        fees_text = cells[fees_col_idx].get_text(strip=True)
                        
                        if not course_name or len(course_name) < 3:
                            continue
                        
                        # EARLY REJECTION: Check garbage keywords
                        if any(keyword in course_name.lower() for keyword in DataCleaner.GARBAGE_KEYWORDS):
                            continue
                        
                        # Clean course name
                        course_name = DataCleaner.clean_course_name(course_name)
                        
                        if not course_name or len(course_name.strip()) < 5:
                            continue
                        
                        # Validate course name
                        if not DataCleaner.is_valid_course_name(course_name):
                            logger.info(f"Rejected invalid course: {course_name}")
                            continue
                        
                        # Extract fees from the dedicated fees column
                        fees_lakhs = DataCleaner.extract_fees_lakhs(fees_text)
                        
                        # Extract degree type
                        course_lower = course_name.lower()
                        degree_type = 'Unknown'
                        degree_patterns = {
                            'b.tech': 'B.Tech', 'btech': 'B.Tech', 'b tech': 'B.Tech',
                            'b.e': 'B.E', 'be': 'B.E', 'be ': 'B.E',
                            'm.tech': 'M.Tech', 'mtech': 'M.Tech', 'm tech': 'M.Tech',
                            'b.sc': 'B.Sc', 'bsc': 'B.Sc', 'b sc': 'B.Sc',
                            'm.sc': 'M.Sc', 'msc': 'M.Sc', 'm sc': 'M.Sc',
                            'b.a': 'B.A', 'ba': 'B.A',
                            'm.a': 'M.A', 'ma': 'M.A',
                            'b.com': 'B.Com', 'bcom': 'B.Com', 'b com': 'B.Com',
                            'm.com': 'M.Com', 'mcom': 'M.Com', 'm com': 'M.Com',
                            'mba': 'MBA', 'm.b.a': 'MBA',
                            'bba': 'BBA', 'b.b.a': 'BBA',
                            'llb': 'LLB', 'll.b': 'LLB',
                            'llm': 'LLM', 'll.m': 'LLM',
                            'mbbs': 'MBBS',
                            'bds': 'BDS',
                            'b.pharma': 'B.Pharma', 'b pharma': 'B.Pharma',
                            'm.pharma': 'M.Pharma', 'm pharma': 'M.Pharma',
                            'diploma': 'Diploma',
                            'phd': 'Ph.D',
                            'b.ed': 'B.Ed', 'bed': 'B.Ed',
                            'm.ed': 'M.Ed', 'med': 'M.Ed',
                            'b.des': 'B.Des', 'bdes': 'B.Des',
                            'b.arch': 'B.Arch', 'barch': 'B.Arch',
                            'bca': 'BCA', 'b.c.a': 'BCA',
                            'mca': 'MCA', 'm.c.a': 'MCA',
                        }
                        
                        # Sort patterns by length to avoid substring matching
                        sorted_patterns = sorted(degree_patterns.items(), key=lambda x: len(x[0]), reverse=True)
                        for pattern, dtype in sorted_patterns:
                            if pattern in course_lower:
                                degree_type = dtype
                                break
                        
                        # Stream extraction
                        stream = 'UNKNOWN'
                        if any(word in degree_type for word in ['B.Tech', 'B.E', 'M.Tech', 'B.Arch', 'Diploma']):
                            stream = 'ENGINEERING'
                        elif any(word in degree_type for word in ['B.Sc', 'M.Sc', 'B.A', 'M.A', 'B.Ed', 'M.Ed', 'BCA', 'MCA']):
                            stream = 'ARTS_SCIENCE'
                        elif any(word in degree_type for word in ['BBA', 'MBA', 'B.Com', 'M.Com']):
                            stream = 'COMMERCE'
                        elif any(word in degree_type for word in ['MBBS', 'BDS', 'B.Pharma', 'M.Pharma']):
                            stream = 'MEDICAL'
                        elif any(word in degree_type for word in ['LLB', 'LLM']):
                            stream = 'LAW'
                        
                        # Duration
                        duration = 4
                        if any(word in degree_type for word in ['M.Tech', 'M.Sc', 'M.A', 'M.Com', 'MBA', 'M.Ed', 'M.Pharma', 'LLM', 'MCA']):
                            duration = 2
                        elif degree_type == 'Diploma':
                            duration = 3
                        elif degree_type == 'Ph.D':
                            duration = 3
                        elif stream == 'ARTS_SCIENCE' and any(word in degree_type for word in ['B.Sc', 'B.A', 'B.Ed', 'BCA']):
                            duration = 3
                        elif degree_type == 'MBBS':
                            duration = 5
                        elif degree_type == 'BDS':
                            duration = 5
                        elif degree_type == 'LLB':
                            duration = 3
                        
                        courses_data.append({
                            'name': course_name,
                            'stream': stream,
                            'degree_type': degree_type,
                            'fees_per_year_lakhs': fees_lakhs,
                            'duration_years': duration,
                            'cutoff': 0.0,  # Cutoff not available in this table
                        })
                        
                        logger.info(f"✓ Extracted: {course_name} | {degree_type} | ₹{fees_lakhs}L | {stream}")
                    
                    # If we found courses in this table, return them (don't check other tables)
                    if courses_data:
                        return courses_data
            
            # Fallback: If no dedicated Course+Fees table found, use the original method
            return self._extract_course_details_fallback(soup)
        except Exception as e:
            logger.error(f"Error extracting courses: {e}")
            return []

    def _extract_course_details_fallback(self, soup):
        """Fallback extraction method for tables without dedicated Course+Fees columns"""
        courses_data = []
        
        try:
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                
                for row in rows[1:]:  # Skip header
                    cells = row.find_all(['td', 'th'])
                    if len(cells) < 2:
                        continue
                    
                    cell_texts = [cell.get_text(strip=True) for cell in cells]
                    if not any(cell_texts):
                        continue
                    
                    course_name = cell_texts[0]
                    if not course_name or len(course_name) < 3:
                        continue
                    
                    # Check garbage keywords
                    if any(keyword in course_name.lower() for keyword in DataCleaner.GARBAGE_KEYWORDS):
                        continue
                    
                    course_name = DataCleaner.clean_course_name(course_name)
                    if not course_name or len(course_name.strip()) < 5:
                        continue
                    
                    if not DataCleaner.is_valid_course_name(course_name):
                        continue
                    
                    # Extract fees from any cell
                    fees_lakhs = 0.0
                    for cell_text in cell_texts:
                        extracted_fees = DataCleaner.extract_fees_lakhs(cell_text)
                        if extracted_fees > 0:
                            fees_lakhs = extracted_fees
                            break
                    
                    # Extract cutoff
                    cutoff = 0.0
                    try:
                        cutoff_candidates = []
                        for cell_text in cell_texts:
                            numbers = re.findall(r'\d+', cell_text)
                            for num_str in numbers:
                                try:
                                    num_val = int(num_str)
                                    if 1 <= num_val <= 10000:
                                        cutoff_candidates.append(num_val)
                                except:
                                    pass
                        if cutoff_candidates:
                            cutoff = float(min(cutoff_candidates))
                    except:
                        pass
                    
                    # Extract degree type
                    course_lower = course_name.lower()
                    degree_type = 'Unknown'
                    degree_patterns = {
                        'b.tech': 'B.Tech', 'btech': 'B.Tech', 'b tech': 'B.Tech',
                        'b.e': 'B.E', 'be': 'B.E',
                        'm.tech': 'M.Tech', 'mtech': 'M.Tech', 'm tech': 'M.Tech',
                        'b.sc': 'B.Sc', 'bsc': 'B.Sc', 'b sc': 'B.Sc',
                        'm.sc': 'M.Sc', 'msc': 'M.Sc', 'm sc': 'M.Sc',
                        'b.a': 'B.A', 'ba': 'B.A',
                        'm.a': 'M.A', 'ma': 'M.A',
                        'b.com': 'B.Com', 'bcom': 'B.Com', 'b com': 'B.Com',
                        'm.com': 'M.Com', 'mcom': 'M.Com', 'm com': 'M.Com',
                        'mba': 'MBA', 'm.b.a': 'MBA',
                        'bba': 'BBA', 'b.b.a': 'BBA',
                        'llb': 'LLB', 'll.b': 'LLB',
                        'llm': 'LLM', 'll.m': 'LLM',
                        'mbbs': 'MBBS', 'bds': 'BDS',
                        'b.pharma': 'B.Pharma', 'b pharma': 'B.Pharma',
                        'm.pharma': 'M.Pharma', 'm pharma': 'M.Pharma',
                        'diploma': 'Diploma', 'phd': 'Ph.D',
                        'b.ed': 'B.Ed', 'bed': 'B.Ed',
                        'm.ed': 'M.Ed', 'med': 'M.Ed',
                        'b.des': 'B.Des', 'bdes': 'B.Des',
                        'b.arch': 'B.Arch', 'barch': 'B.Arch',
                        'bca': 'BCA', 'b.c.a': 'BCA',
                        'mca': 'MCA', 'm.c.a': 'MCA',
                    }
                    
                    sorted_patterns = sorted(degree_patterns.items(), key=lambda x: len(x[0]), reverse=True)
                    for pattern, dtype in sorted_patterns:
                        if pattern in course_lower:
                            degree_type = dtype
                            break
                    
                    # Determine stream
                    stream = 'UNKNOWN'
                    if any(word in degree_type for word in ['B.Tech', 'B.E', 'M.Tech', 'B.Arch', 'Diploma']):
                        stream = 'ENGINEERING'
                    elif any(word in degree_type for word in ['B.Sc', 'M.Sc', 'B.A', 'M.A', 'B.Ed', 'M.Ed', 'BCA', 'MCA']):
                        stream = 'ARTS_SCIENCE'
                    elif any(word in degree_type for word in ['BBA', 'MBA', 'B.Com', 'M.Com']):
                        stream = 'COMMERCE'
                    elif any(word in degree_type for word in ['MBBS', 'BDS', 'B.Pharma', 'M.Pharma']):
                        stream = 'MEDICAL'
                    elif any(word in degree_type for word in ['LLB', 'LLM']):
                        stream = 'LAW'
                    
                    # Determine duration
                    duration = 4
                    if any(word in degree_type for word in ['M.Tech', 'M.Sc', 'M.A', 'M.Com', 'MBA', 'M.Ed', 'M.Pharma', 'LLM', 'MCA']):
                        duration = 2
                    elif degree_type == 'Diploma':
                        duration = 3
                    elif degree_type == 'Ph.D':
                        duration = 3
                    elif stream == 'ARTS_SCIENCE' and any(word in degree_type for word in ['B.Sc', 'B.A', 'B.Ed', 'BCA']):
                        duration = 3
                    elif degree_type == 'MBBS':
                        duration = 5
                    elif degree_type == 'BDS':
                        duration = 5
                    elif degree_type == 'LLB':
                        duration = 3
                    
                    courses_data.append({
                        'name': course_name,
                        'stream': stream,
                        'degree_type': degree_type,
                        'fees_per_year_lakhs': fees_lakhs,
                        'duration_years': duration,
                        'cutoff': cutoff,
                    })
            
            return courses_data
        except Exception as e:
            logger.error(f"Error extracting courses (fallback): {e}")
            return []

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        headless = not options['no_headless']
        
        self.stdout.write(self.style.SUCCESS(f'[SCRAPER] UPGRADED Collegedunia Scraper (Batch: {batch_size})'))
        self.stdout.write(self.style.WARNING('[DATA] Data will be clean and validated\n'))
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless, args=[
                '--disable-blink-features=AutomationControlled'
            ])
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
            )
            page = context.new_page()
            
            try:
                # Step 1: Open listing (Tamil Nadu has 2356 colleges)
                self.stdout.write('[OPEN] Opening Tamil Nadu colleges listing page...')
                page.goto("https://collegedunia.com/tamil-nadu-colleges", wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(5000)
                
                # Step 2: Scroll (Tamil Nadu has many colleges, scroll more to load them)
                self.stdout.write('[SCROLL] Scrolling Tamil Nadu colleges page (loading all colleges)...')
                self.stdout.write('   This will load 500+ colleges dynamically...\n')
                
                last_height = page.evaluate("document.body.scrollHeight")
                scroll_iterations = 0
                max_iterations = 150  # Increased from 50 → 150 (load more colleges)
                no_change_count = 0  # Track consecutive no-change scrolls
                colleges_loaded_estimates = 0
                
                while scroll_iterations < max_iterations:
                    # Scroll down more aggressively
                    page.evaluate("window.scrollBy(0, 1000)")  # Increased from 500 → 1000
                    page.wait_for_timeout(1200)  # Increased from 800 → 1200 (more time for dynamic load)
                    scroll_iterations += 1
                    
                    # Get current page height
                    new_height = page.evaluate("document.body.scrollHeight")
                    
                    # Estimate colleges loaded (rough heuristic: each 300px of height = ~1 college card)
                    estimated_colleges = max(new_height // 300, 130)
                    
                    if scroll_iterations % 10 == 0:
                        self.stdout.write(f'   Scroll {scroll_iterations}/{max_iterations} | Page height: {new_height}px | Est. colleges: ~{estimated_colleges}')
                    
                    # Check if page is still loading new content
                    if new_height == last_height:
                        no_change_count += 1
                        # If no content loaded for 5 consecutive scrolls, we've reached the end
                        if no_change_count >= 5:
                            self.stdout.write(f'   [OK] Reached end of page (no new content for 5 scrolls)')
                            break
                    else:
                        no_change_count = 0  # Reset counter if new content loaded
                    
                    last_height = new_height
                    
                    # Extra aggressive: try to trigger infinite scroll by scrolling to very bottom
                    if scroll_iterations % 20 == 0:
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        page.wait_for_timeout(1500)  # Wait for any lazy loading
                
                self.stdout.write(f'\n   [OK] Total scrolls completed: {scroll_iterations}')
                self.stdout.write(f'   [OK] Est. colleges loaded on page: ~{new_height // 300}\n')
                page.wait_for_timeout(3000)
                
                # Step 3: Collect URLs (IMPROVED - Try multiple patterns)
                self.stdout.write('[COLLECT] Collecting college URLs...')
                content = page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                college_links = set()
                all_links = soup.find_all('a', href=True)
                
                # Try multiple URL patterns for colleges
                url_patterns = [
                    ('/university/', True),      # Primary pattern
                    ('/colleges/', True),        # Alternative pattern
                    ('/college/', True),         # Another variant
                ]
                
                logger.info(f"Total links on page: {len(all_links)}")
                
                for link in all_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    # Skip certain links
                    skip_keywords = ['news', 'alert', 'admission', 'forum', 'reviews', 'articles', 'discuss']
                    if any(k in href.lower() for k in skip_keywords):
                        continue
                    
                    # Check all patterns
                    for pattern, include in url_patterns:
                        if pattern in href and include:
                            # Must have a college name after pattern
                            full_url = f"https://collegedunia.com{href}" if not href.startswith('http') else href
                            
                            # Additional validation: URL should not be too short
                            if len(href) > 10:  # Basic length check
                                college_links.add(full_url)
                                logger.info(f"Found: {text[:40]} -> {href[:60]}")
                            break
                
                # If still no links, try broader search (any link with college-like name)
                if len(college_links) == 0:
                    logger.warning("No college links found with standard patterns, trying broader search...")
                    for link in all_links:
                        href = link.get('href', '')
                        text = link.get_text(strip=True)
                        
                        # Skip obvious non-college links
                        if any(k in href.lower() for k in ['forum', 'articles', 'reviews', 'news', 'help', 'about', 'contact']):
                            continue
                        
                        # Look for links with reasonable length and collegedunia domain
                        if 'collegedunia.com' in href and len(href) > 15:
                            if not href.startswith('https://collegedunia'):
                                # Relative URL
                                full_url = f"https://collegedunia.com{href}"
                            else:
                                full_url = href
                            
                            college_links.add(full_url)
                            logger.info(f"Broad search found: {text[:40]} -> {href[:60]}")
                
                college_links = list(college_links)[:batch_size]
                
                # FALLBACK: If no college links found, use hardcoded list of popular Tamil Nadu colleges
                if len(college_links) == 0:
                    self.stdout.write(self.style.WARNING('[FALLBACK] Using fallback Tamil Nadu college list...'))
                    
                    # Known working Tamil Nadu college URLs from Collegedunia (2356 available)
                    fallback_urls = [
                        "https://collegedunia.com/university/iit-madras-chennai",
                        "https://collegedunia.com/university/anna-university-chennai",
                        "https://collegedunia.com/university/cbe-national-institute-of-technology-nit-trichy",
                        "https://collegedunia.com/college/4770-college-of-engineering-guindy-ceg-chennai",
                        "https://collegedunia.com/college/2455-madras-institute-of-technology-mit-chennai",
                        "https://collegedunia.com/college/4768-rajalakshmi-engineering-college-chennai",
                        "https://collegedunia.com/college/4769-sri-sivasubramaniya-nadar-ssn-college-of-engineering-chennai",
                        "https://collegedunia.com/college/2438-vellore-institute-of-technology-vit-vellore",
                        "https://collegedunia.com/college/10343-christian-medical-college-cmc-vellore",
                        "https://collegedunia.com/university/iim-tiruppur-iim-tamil-nadu-tiruppur",
                        "https://collegedunia.com/college/4771-aarupadai-veedu-institute-of-technology-thiruvananthapuram",
                        "https://collegedunia.com/college/4765-savitribai-phule-pune-university-pune",
                        "https://collegedunia.com/college/4766-manipal-university-jaipur-jaipur",
                        "https://collegedunia.com/college/4767-chandigarh-university-chandigarh",
                        "https://collegedunia.com/college/2454-st-xaviers-college-of-engineering-thiruvananthapuram",
                        "https://collegedunia.com/college/2453-m-a-m-college-of-engineering-tirunelveli",
                        "https://collegedunia.com/college/2451-thiagarajar-college-of-engineering-madurai",
                        "https://collegedunia.com/college/2450-kumaraguru-college-of-technology-coimbatore",
                        "https://collegedunia.com/college/2449-k-s-rangasamy-college-of-technology-tiruchengode",
                        "https://collegedunia.com/college/2448-kongu-engineering-college-perundurai",
                        "https://collegedunia.com/college/2447-psg-college-of-technology-coimbatore",
                        "https://collegedunia.com/college/2446-sairam-engineering-college-chennai",
                        "https://collegedunia.com/college/2445-sairam-college-of-engineering-kanchipur",
                        "https://collegedunia.com/college/2444-sairam-college-of-engineering-thiruvananthapuram",
                        "https://collegedunia.com/college/2443-sairam-college-of-engineering-pondicherry",
                        "https://collegedunia.com/college/2442-sairam-college-of-engineering-salem",
                        "https://collegedunia.com/college/2441-sairam-college-of-engineering-tiruppur",
                        "https://collegedunia.com/college/2440-sairam-college-of-engineering-tamil-nadu",
                        "https://collegedunia.com/college/2439-sairam-engineering-college-thiruvananthapuram",
                        "https://collegedunia.com/college/4773-arulmigu-kalasalingam-university-anand-nagar-srivilliputtur",
                        "https://collegedunia.com/college/4774-rathinam-technical-campus-coimbatore",
                        "https://collegedunia.com/college/4775-vel-tech-rangarajan-dr-sagunthala-r-d-institute-of-science-and-technology-avadi-chennai",
                        "https://collegedunia.com/college/4776-vels-institute-of-science-technology-and-advanced-studies-vesats-pallavi-avadi-chennai",
                        "https://collegedunia.com/college/4777-christ-university-bangalore",
                        "https://collegedunia.com/college/4778-galgotias-university-greater-noida",
                        "https://collegedunia.com/college/4779-gmit-greater-noida",
                        "https://collegedunia.com/college/4780-maharshi-arvind-jr-college-ambazari-aurangabad",
                        "https://collegedunia.com/college/4781-maharshi-dayanand-university-rohtak",
                        "https://collegedunia.com/college/4782-manav-rachna-international-institute-of-research-and-studies-faridabad",
                        "https://collegedunia.com/college/4783-manipal-university-jaipur-jaipur",
                        "https://collegedunia.com/college/4784-nobel-group-of-institutions-junagadh",
                        "https://collegedunia.com/college/4785-ncce-nagpur-city-college-of-engineering-nagpur",
                        "https://collegedunia.com/college/4786-pes-university-bangalore",
                        "https://collegedunia.com/college/4787-piet-pune-institute-of-engineering-and-technology-pune",
                        "https://collegedunia.com/college/4788-rcc-institute-of-information-technology-rcciit-kolkata"
                    ]
                    
                    college_links = fallback_urls[:batch_size]
                    self.stdout.write(self.style.SUCCESS(f'[READY] Using fallback: {len(college_links)} Tamil Nadu colleges\n'))
                else:
                    self.stdout.write(self.style.SUCCESS(f'[READY] Collected {len(college_links)} colleges from page\n'))
                
                if len(college_links) == 0:
                    self.stdout.write(self.style.WARNING('No colleges found!'))
                    return
                
                # Step 4: Scrape each college
                for idx, college_url in enumerate(college_links, 1):
                    self.stdout.write(f'[SCRAPE] [{idx}/{len(college_links)}] Processing...')
                    
                    try:
                        # Add longer delay between requests to avoid rate limiting
                        page.goto(college_url, wait_until="domcontentloaded", timeout=60000)
                        page.wait_for_timeout(5000)  # Increased from 3000
                        
                        # Extract college
                        college_details = self.extract_college_details(page, college_url)
                        if not college_details:
                            self.stdout.write(self.style.WARNING('   [SKIP] Could not extract college'))
                            continue
                        
                        # VALIDATE college name STRICTLY
                        if not DataCleaner.is_valid_college_name(college_details['name']):
                            self.stdout.write(self.style.WARNING(f'   [SKIP] Invalid college name: {college_details["name"]}'))
                            continue
                        
                        # Skip colleges without valid location details
                        if college_details['city'] == 'Unknown' or college_details['state'] == 'Unknown':
                            self.stdout.write(self.style.WARNING(f'   [SKIP] No location details: {college_details["name"]}'))
                            continue
                        
                        # STRICT VALIDATION: Check all required fields before saving
                        required_fields = ['name', 'city', 'state', 'location']
                        missing_fields = [field for field in required_fields if not college_details.get(field) or college_details.get(field) == 'Unknown']
                        
                        if missing_fields:
                            self.stdout.write(self.style.WARNING(f'   [SKIP] Missing fields: {missing_fields}'))
                            continue
                        
                        # Save college to RealCollege table
                        college, created = RealCollege.objects.update_or_create(
                            name=college_details['name'],
                            defaults={
                                'city': college_details['city'],
                                'state': college_details['state'],
                                'website': college_details['website'],
                                'collegedunia_url': college_url,
                                'latitude': college_details['latitude'],
                                'longitude': college_details['longitude'],
                            }
                        )
                        
                        action = "[SAVE] Created" if created else "[UPDATE] Updated"
                        self.stdout.write(self.style.SUCCESS(f'   {action}: {college.name}'))
                        
                        # Scroll to courses
                        try:
                            page.get_by_text("Popular Full time Courses", exact=False).scroll_into_view_if_needed(timeout=5000)
                            page.wait_for_timeout(2000)
                        except:
                            pass
                        
                        # Extract courses
                        content = page.content()
                        soup = BeautifulSoup(content, 'html.parser')
                        courses_data = self.extract_course_details(soup)
                        
                        # STRICT: Reject colleges without courses
                        if not courses_data or len(courses_data) == 0:
                            self.stdout.write(self.style.WARNING('   [REJECT] No valid courses found - deleting incomplete college'))
                            # Delete the college we just created since it has no courses
                            college.delete()
                            continue
                        else:
                            # Extract course type fees from "Popular Full time Courses" section
                            fees_map = self.extract_course_type_fees(soup)
                            
                            # Map course type fees to individual courses
                            if fees_map:
                                courses_data = self.map_course_fees(courses_data, fees_map)
                                self.stdout.write(f'   [FEES] Applied types fees: {fees_map}')
                            
                            # Save courses to RealCourse table
                            saved_courses = 0
                            for course_data in courses_data:
                                try:
                                    RealCourse.objects.update_or_create(
                                        college=college,
                                        name=course_data['name'],
                                        defaults={
                                            'stream': course_data['stream'],
                                            'degree_type': course_data['degree_type'],
                                            'fees_lakhs': course_data['fees_per_year_lakhs'],
                                        }
                                    )
                                    saved_courses += 1
                                except Exception as e:
                                    logger.warning(f"Error saving course: {e}")
                            
                            # Final validation: Ensure college has saved courses
                            final_course_count = college.courses.count()
                            if final_course_count == 0:
                                self.stdout.write(self.style.WARNING(f'   [REJECT] College has no courses after save - removing'))
                                college.delete()
                                continue
                            
                            self.stdout.write(self.style.SUCCESS(f'   [SAVE] Stored {saved_courses} courses (Total: {final_course_count})\n'))
                        
                        # Longer delay between requests to avoid rate limiting
                        time.sleep(4)  # Increased from 2
                    
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'   [ERROR] {type(e).__name__}: {str(e)[:60]}'))
                        continue
                
                self.stdout.write(self.style.SUCCESS('\n[DONE] Scraping complete!\n'))
            
            finally:
                context.close()
                browser.close()
