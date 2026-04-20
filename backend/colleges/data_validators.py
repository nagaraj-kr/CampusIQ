"""
Data Validators and Cleaners for College Scraper
Ensures only high-quality, clean data is stored in database

Purpose:
- Validate course names, college names
- Clean messy data
- Detect and filter garbage data
- Classify courses by stream (Engineering, Arts, Science, Commerce)
- Extract meaningful data from HTML
"""

import re
import logging
from typing import Tuple, Dict, Optional, List

logger = logging.getLogger(__name__)


class StreamClassifier:
    """Classify courses by academic stream"""
    
    ENGINEERING_DEGREES = {
        'B.Tech', 'B.E.', 'B.E', 'M.Tech', 'Diploma', 
        'B.Tech (Hons)', 'B.E. (Hons)', 'PhD',
        'B.TECH', 'BE', 'BTECH', 'MTECH', 'M.TECH',
    }
    
    ENGINEERING_KEYWORDS = [
        'computer science engineering', 'cse', 'information technology',
        'mechanical engineering', 'civil engineering', 'electrical engineering',
        'electronics and communication', 'ece', 'automobile',
        'aerospace', 'production', 'biotechnology', 'chemical engineering',
        'petroleum engineering', 'mining', 'metallurgy', 'geology',
        'environmental engineering', 'marine engineering',
    ]
    
    ARTS_SCIENCE_DEGREES = {
        'B.Sc', 'B.A', 'M.Sc', 'M.A', 'BSc', 'BA', 'MSc', 'MA',
        'B.SC', 'B.A', 'M.SC', 'M.A',
    }
    
    ARTS_SCIENCE_KEYWORDS = [
        'computer science', 'information technology',
        'physics', 'chemistry', 'mathematics', 'biology',
        'microbiology', 'botany', 'zoology', 'geology',
        'psychology', 'economics', 'sociology', 'history',
        'english', 'hindi', 'literature', 'philosophy',
    ]
    
    COMMERCE_KEYWORDS = [
        'b.com', 'bcom', 'mba', 'commerce', 'accountancy',
        'business administration', 'ca', 'chartered accountant',
    ]
    
    LAW_KEYWORDS = [
        'llb', 'll.b', 'llm', 'll.m', 'law', 'jd',
    ]
    
    MEDICAL_KEYWORDS = [
        'mbbs', 'bds', 'nursing', 'physiotherapy', 'pharmacy',
        'ayurveda', 'homeopathy', 'medical',
    ]
    
    @classmethod
    def classify(cls, course_name: str, degree_type: str = None) -> str:
        """
        Classify course into stream
        
        Args:
            course_name: Full course name (e.g., "B.Tech Computer Science Engineering")
            degree_type: Explicit degree type (e.g., "B.Tech")
        
        Returns:
            Stream: 'ENGINEERING', 'ARTS_SCIENCE', 'COMMERCE', 'LAW', 'MEDICAL', 'UNKNOWN'
        """
        name_lower = course_name.lower()
        
        # Check explicit degree types first
        if degree_type:
            degree_lower = degree_type.lower()
            if any(eng_deg.lower() in degree_lower for eng_deg in cls.ENGINEERING_DEGREES):
                # Now check if it's engineering course within engineering degree
                if any(keyword in name_lower for keyword in cls.ENGINEERING_KEYWORDS):
                    return 'ENGINEERING'
                elif any(keyword in name_lower for keyword in cls.ARTS_SCIENCE_KEYWORDS):
                    return 'ARTS_SCIENCE'
                else:
                    # Default engineering degree to engineering stream
                    return 'ENGINEERING'
            
            elif any(arts_deg.lower() in degree_lower for arts_deg in cls.ARTS_SCIENCE_DEGREES):
                # Arts/Science degree - check course keywords
                if any(keyword in name_lower for keyword in cls.ENGINEERING_KEYWORDS):
                    # Engineering course in science degree = unlikely, skip
                    return 'UNKNOWN'
                elif any(keyword in name_lower for keyword in cls.ARTS_SCIENCE_KEYWORDS):
                    return 'ARTS_SCIENCE'
                else:
                    return 'ARTS_SCIENCE'
        
        # Check keywords
        if any(keyword in name_lower for keyword in cls.MEDICAL_KEYWORDS):
            return 'MEDICAL'
        elif any(keyword in name_lower for keyword in cls.LAW_KEYWORDS):
            return 'LAW'
        elif any(keyword in name_lower for keyword in cls.COMMERCE_KEYWORDS):
            return 'COMMERCE'
        elif any(keyword in name_lower for keyword in cls.ENGINEERING_KEYWORDS):
            return 'ENGINEERING'
        elif any(keyword in name_lower for keyword in cls.ARTS_SCIENCE_KEYWORDS):
            return 'ARTS_SCIENCE'
        
        return 'UNKNOWN'


class CourseCleaner:
    """Clean and validate course data"""
    
    # Valid course name prefixes
    VALID_PREFIXES = [
        'b.tech', 'btech', 'b tech',
        'm.tech', 'mtech', 'm tech',
        'b.e', 'be', 'b.e.',
        'b.sc', 'bsc', 'b sc',
        'm.sc', 'msc', 'm sc',
        'b.a', 'ba', 'b a',
        'm.a', 'ma', 'm a',
        'bba', 'b.b.a', 'b b a',
        'mba', 'm.b.a', 'm b a',
        'llb', 'll.b', 'diploma', 'pg diploma',
        'phd', 'ph.d', 'ph.d.',
        'mbbs', 'bds', 'pharmacy', 'b.pharm',
        'certificate', 'advanced', 'master',
        # Medical postgraduate degrees
        'm.ch', 'mch', 'm ch',
        'md', 'm.d', 'm d',
        'ms', 'm.s', 'm s',
        'dm', 'd.m', 'd m',
        'dgo', 'dip', 'dnb',
        # Other professional
        'ca', 'cs', 'icwa', 'b.com', 'bcom', 'b com',
        'm.com', 'mcom', 'm com',
        'b.arch', 'barch', 'b arch',
        'm.arch', 'march', 'm arch',
    ]
    
    # Garbage keywords - if present, course is invalid
    GARBAGE_KEYWORDS = {
        # Process-related
        'registration', 'allocation', 'interview', 'counselling',
        'validation', 'verification', 'submission', 'choice filling',
        'seat allocation', 'merit list',
        # Exam/Result related
        'cmat', 'exam date', 'result', 'cutoff score', 'merit',
        'ranking', 'nirf', 'exam',
        # Admin/News
        'amendment', 'circular', 'notice', 'announcement', 'news',
        'round', 'correction', 'schedule',
        # Action items
        'click here', 'view here', 'download', 'apply', 'link',
        # Time-specific
        '2025', '2026', '2027', 'batch', 'admission',
        # Other
        'http', 'www', 'pdf', 'brochure', 'prospectus',
    }
    
    @staticmethod
    def clean_course_name(name: str) -> str:
        """
        Clean course name by removing junk characters and metadata
        
        Examples:
        - "B.Tech Computer Science Engineering (1.2K Views)" → "B.Tech Computer Science Engineering"
        - "M.Tech CSE (25 Courses)" → "M.Tech CSE"
        """
        if not name or len(name) < 3:
            return None
        
        # Remove view counts: "(1.2K Views)", "(225Views)"
        name = re.sub(r'\(\d+\.?\d*[KMB]?\s*Views?\)', '', name, flags=re.IGNORECASE)
        
        # Remove course counts: "(25 Courses)"
        name = re.sub(r'\(\d+\s*Courses?\)', '', name, flags=re.IGNORECASE)
        
        # Remove extra brackets with numbers
        name = re.sub(r'\[\d+.*?\]', '', name)
        
        # Remove trailing numbers/symbols
        name = re.sub(r'[\d\(\)\[\]]*$', '', name)
        
        # Clean whitespace
        name = re.sub(r'\s+', ' ', name).strip()
        
        # Remove trailing hyphens/pipes
        name = re.sub(r'[-|]*$', '', name).strip()
        
        return name if len(name) >= 5 else None
    
    @staticmethod
    def is_valid_course_name(name: str) -> bool:
        """
        Strict validation - course name must pass ALL checks
        
        Returns True only if:
        1. Name length is reasonable (5-150 chars)
        2. Contains NO garbage keywords
        3. Starts with valid course prefix
        4. No excessive special characters
        """
        if not name or len(name) < 5 or len(name) > 150:
            return False
        
        name_lower = name.lower()
        
        # CRITICAL: Check for garbage keywords first
        if any(keyword in name_lower for keyword in CourseCleaner.GARBAGE_KEYWORDS):
            logger.warning(f"❌ Course rejected (garbage): {name}")
            return False
        
        # Must start with valid prefix
        has_valid_prefix = any(name_lower.startswith(prefix) for prefix in CourseCleaner.VALID_PREFIXES)
        if not has_valid_prefix:
            logger.warning(f"❌ Course rejected (invalid prefix): {name}")
            return False
        
        # Check for excessive special characters
        special_chars = len(re.findall(r'[^\w\s\.-]', name))
        if special_chars > 3:
            logger.warning(f"❌ Course rejected (too many special chars): {name}")
            return False
        
        return True
    
    @staticmethod
    def extract_degree_type(course_name: str) -> str:
        """
        Extract degree type from course name
        
        Examples:
        - "B.Tech Computer Science" → "B.Tech"
        - "M.Tech Data Science" → "M.Tech"
        - "B.Sc Physics" → "B.Sc"
        - "M.Ch General Surgery" → "M.Ch"
        """
        name_lower = course_name.lower()
        
        # Check each prefix in order of specificity
        degree_patterns = [
            (r'\bb\.tech\b', 'B.Tech'),
            (r'\bb\.e\.?\b', 'B.E.'),
            (r'\bb\.e\b', 'B.E.'),
            (r'\bm\.tech\b', 'M.Tech'),
            (r'\bb\.sc\b', 'B.Sc'),
            (r'\bm\.sc\b', 'M.Sc'),
            (r'\bb\.a\b', 'B.A'),
            (r'\bm\.a\b', 'M.A'),
            (r'\bbba\b', 'BBA'),
            (r'\bmba\b', 'MBA'),
            (r'\bllb\b', 'LLB'),
            (r'\bm\.ch\b', 'M.Ch'),
            (r'\bmd\b', 'MD'),
            (r'\bms\b', 'MS'),
            (r'\bdm\b', 'DM'),
            (r'\bphd\b', 'PhD'),
            (r'\bdiploma\b', 'Diploma'),
            (r'\bb\.com\b', 'B.Com'),
            (r'\bm\.com\b', 'M.Com'),
        ]
        
        for pattern, degree in degree_patterns:
            if re.search(pattern, name_lower):
                return degree
        
        return 'Unknown'


class CollegeCleaner:
    """Clean and validate college data"""
    
    @staticmethod
    def clean_college_name(name: str) -> Optional[str]:
        """
        Clean college name by removing metadata
        
        Examples:
        - "IIT Madras - Fees, Courses, Ranking" → "IIT Madras"
        - "Anna University : Admission 2025" → "Anna University"
        """
        if not name or len(name) < 3:
            return None
        
        # Remove everything after colon (often metadata)
        name = re.sub(r':.*$', '', name)
        
        # Remove common suffixes
        suffixes = ['Admission 2025', 'Admission 2026', '- Fees', '- Courses', 
                   '- Ranking', '- Placement', '- Cutoff', 'Fees', 'Courses']
        for suffix in suffixes:
            name = name.replace(suffix, '')
        
        # Clean whitespace
        name = re.sub(r'\s+', ' ', name).strip()
        
        # Remove trailing hyphens/pipes
        name = re.sub(r'[-|]*$', '', name).strip()
        
        # Reject if too long (probably garbage)
        if len(name) > 200:
            return None
        
        return name if len(name) >= 3 else None
    
    @staticmethod
    def is_valid_college_name(name: str) -> bool:
        """Validate college name - reject metadata pollution"""
        if not name or len(name) < 3 or len(name) > 200:
            return False
        
        # Reject pure garbage patterns
        garbage_patterns = [
            r'^\d+$',  # Only numbers
            r'^[^a-z]*$',  # No letters
            r'registration|counselling|allocation|apply',  # Process words
        ]
        
        for pattern in garbage_patterns:
            if re.search(pattern, name, re.IGNORECASE):
                return False
        
        # REJECT if contains metadata keywords
        metadata_reject = [
            'ranking', 'comparison', 'vs ', 'vs-', 'reviews', 'ratings',
            'cutoff', 'placement stats', 'admission', 'apply now',
            'fees structure', 'entrance exam', 'counselling',
            '- b.sc', '- b.tech', '- bba', '- mba',  # Department pages
            '(nursing)', '(engineering)', '(commerce)',  # Degree suffix pollution
        ]
        
        name_lower = name.lower()
        for reject in metadata_reject:
            if reject in name_lower:
                return False
        
        return True


class LocationCleaner:
    """Clean and validate location data"""
    
    CITY_STATE_MAP = {
        'Chennai': 'Tamil Nadu', 'Coimbatore': 'Tamil Nadu', 'Madurai': 'Tamil Nadu',
        'Trichy': 'Tamil Nadu', 'Tiruchirappalli': 'Tamil Nadu', 'Erode': 'Tamil Nadu',
        'Salem': 'Tamil Nadu', 'Tiruppur': 'Tamil Nadu', 'Vellore': 'Tamil Nadu',
        'Kanyakumari': 'Tamil Nadu', 'Cuddalore': 'Tamil Nadu', 'Villupuram': 'Tamil Nadu',
        'Thoothukudi': 'Tamil Nadu', 'Tirunelveli': 'Tamil Nadu', 'Nagercoil': 'Tamil Nadu',
        'Puducherry': 'Puducherry', 'Yanam': 'Puducherry', 'Karaikal': 'Puducherry', 'Mahe': 'Puducherry',
        'Delhi': 'Delhi', 'New Delhi': 'Delhi', 'Delhi NCR': 'Delhi',
        'Mumbai': 'Maharashtra', 'Pune': 'Maharashtra', 'Nagpur': 'Maharashtra',
        'Aurangabad': 'Maharashtra', 'Nashik': 'Maharashtra', 'Kolhapur': 'Maharashtra',
        'Bangalore': 'Karnataka', 'Banglore': 'Karnataka', 'Mysore': 'Karnataka',
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
    
    INDIAN_STATES = {
        'Tamil Nadu', 'Delhi', 'Maharashtra', 'Karnataka', 'Uttar Pradesh',
        'Himachal Pradesh', 'Rajasthan', 'West Bengal', 'Bihar', 'Gujarat',
        'Madhya Pradesh', 'Punjab', 'Haryana', 'Jharkhand', 'Odisha',
        'Andhra Pradesh', 'Telangana', 'Kerala', 'Assam', 'Chandigarh',
        'Puducherry', 'Goa', 'Tripura', 'Meghalaya', 'Manipur', 'Mizoram',
        'Nagaland', 'Sikkim', 'Uttarakhand', 'Chhattisgarh', 'Jammu and Kashmir'
    }
    
    @staticmethod
    def extract_state_city(location_text: str) -> Tuple[str, str]:
        """
        Extract state and city from location string
        
        Returns: (state, city)
        """
        if not location_text or len(location_text) < 2 or len(location_text) > 100:
            return 'Unknown', 'Unknown'
        
        # Try comma-separated format
        parts = [p.strip() for p in location_text.split(',')]
        
        if len(parts) >= 2:
            first, second = parts[0].strip(), parts[1].strip()
            
            # Check which is state and which is city
            if second in LocationCleaner.INDIAN_STATES:
                return second, first
            elif first in LocationCleaner.INDIAN_STATES:
                return first, second
            elif first in LocationCleaner.CITY_STATE_MAP:
                return LocationCleaner.CITY_STATE_MAP[first], first
            elif second in LocationCleaner.CITY_STATE_MAP:
                return LocationCleaner.CITY_STATE_MAP[second], second
            else:
                return second, first
        
        elif len(parts) == 1:
            location = parts[0].strip()
            
            if location in LocationCleaner.INDIAN_STATES:
                return location, 'Unknown'
            elif location in LocationCleaner.CITY_STATE_MAP:
                return LocationCleaner.CITY_STATE_MAP[location], location
            
            # Try case-insensitive
            for city, state in LocationCleaner.CITY_STATE_MAP.items():
                if city.lower() == location.lower():
                    return state, city
            
            for state in LocationCleaner.INDIAN_STATES:
                if state.lower() == location.lower():
                    return state, 'Unknown'
            
            return 'Unknown', location
        
        return 'Unknown', 'Unknown'


class DataQualityReport:
    """Generate data quality reports"""
    
    def __init__(self):
        self.total_colleges_checked = 0
        self.valid_colleges = 0
        self.invalid_colleges = 0
        self.total_courses_checked = 0
        self.valid_courses = 0
        self.invalid_courses = 0
        self.rejected_reasons = {}
    
    def add_rejected_course(self, reason: str):
        """Track rejection reasons"""
        if reason not in self.rejected_reasons:
            self.rejected_reasons[reason] = 0
        self.rejected_reasons[reason] += 1
    
    def print_report(self):
        """Print quality report"""
        print("\n" + "="*60)
        print("📊 DATA QUALITY REPORT")
        print("="*60)
        print(f"\nColleges: {self.valid_colleges}/{self.total_colleges_checked} valid")
        print(f"Courses: {self.valid_courses}/{self.total_courses_checked} valid")
        
        if self.rejected_reasons:
            print("\n❌ Top Rejection Reasons:")
            for reason, count in sorted(self.rejected_reasons.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"   {reason}: {count}")
        
        print("="*60 + "\n")
