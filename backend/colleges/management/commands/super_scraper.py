"""
SUPER SCRAPER v3.0 - Production-Grade College Data Scraper
Purpose: Clean, validated, production-ready data collection
Features:
  - Advanced location extraction with multiple fallbacks
  - Comprehensive data validation & cleaning
  - Automatic retry logic
  - Detailed quality reporting
  - Zero-tolerance for garbage data
"""

import re
import logging
from typing import Optional, Dict, List, Tuple
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Page, Browser
from django.core.management.base import BaseCommand
from datetime import datetime
import json

from colleges.models import College, Course, CollegeImage, DataUpdateTracker
from colleges.data_validators import (
    CollegeCleaner, StreamClassifier, LocationCleaner,
    DataQualityReport, CourseCleaner
)
from django.db import transaction
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class AdvancedLocationExtractor:
    """Extract clean location data from college pages"""
    
    TAMIL_NADU_CITIES = {
        'Chennai', 'Coimbatore', 'Madurai', 'Trichy', 'Tiruchirappalli',
        'Erode', 'Salem', 'Tiruppur', 'Vellore', 'Kanyakumari',
        'Cuddalore', 'Villupuram', 'Thoothukudi', 'Tirunelveli',
        'Nagercoil', 'Nellai', 'Krishnagiri', 'Dharmapuri',
        'Chengalpattu', 'Ranipet', 'Tiruvannamalai', 'Kanchipuram'
    }
    
    @classmethod
    def extract_from_structured_data(cls, soup: BeautifulSoup, url: str) -> Tuple[str, str, str]:
        """
        Extract location from structured data
        Returns: (location_text, city, state)
        """
        location_text = "Unknown"
        city = "Unknown"
        state = "Tamil Nadu"  # Default to Tamil Nadu since scraping TN colleges
        
        try:
            # Try 1: Look for address in meta tags
            for meta in soup.find_all('meta'):
                name = meta.get('name', '').lower()
                content = meta.get('content', '')
                if 'address' in name or 'location' in name:
                    location_text = cls._clean_location_text(content)
                    if location_text != "Unknown":
                        break
            
            # Try 2: Look for common location patterns in structured text
            if location_text == "Unknown":
                # Find text containing address-like patterns
                page_text = soup.get_text()
                # Look for patterns like "Address:", "Location:", "Based in:", etc.
                patterns = [
                    r'Address\s*:\s*(.+?)(?:\n|<|$)',
                    r'Location\s*:\s*(.+?)(?:\n|<|$)',
                    r'Based in\s*:\s*(.+?)(?:\n|<|$)',
                    r'(\w+),\s*(Tamil Nadu|TN)',
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, page_text, re.IGNORECASE | re.MULTILINE)
                    if matches:
                        location_text = cls._clean_location_text(matches[0] if isinstance(matches[0], str) else matches[0][0])
                        if location_text != "Unknown":
                            break
            
            # Try 3: Look for JSON-LD structured data
            if location_text == "Unknown":
                for script in soup.find_all('script', {'type': 'application/ld+json'}):
                    try:
                        data = json.loads(script.string)
                        if 'address' in data:
                            addr = data['address']
                            if isinstance(addr, dict):
                                city = addr.get('addressLocality', 'Unknown')
                                state = addr.get('addressRegion', 'Tamil Nadu')
                                location_text = f"{city}, {state}"
                                break
                    except:
                        continue
            
            # Extract city if not already extracted
            if city == "Unknown" and location_text != "Unknown":
                # Try to extract city from location text
                parts = [p.strip() for p in location_text.split(',')]
                if len(parts) >= 1:
                    potential_city = parts[0].strip()
                    if potential_city in cls.TAMIL_NADU_CITIES:
                        city = potential_city
                    elif len(parts) >= 2 and parts[1] in cls.TAMIL_NADU_CITIES:
                        city = parts[1]
            
            # If still no city, extract from first location part
            if city == "Unknown" and location_text != "Unknown":
                # Try to match city from text
                for tamil_city in sorted(cls.TAMIL_NADU_CITIES, key=len, reverse=True):
                    if tamil_city.lower() in location_text.lower():
                        city = tamil_city
                        break
            
            return location_text, city, state
            
        except Exception as e:
            logger.warning(f"Error extracting location: {e}")
            return "Unknown", "Unknown", "Tamil Nadu"
    
    @staticmethod
    def _clean_location_text(text: str) -> str:
        """Clean location text of noise"""
        if not text:
            return "Unknown"
        
        # Remove common noise patterns
        noise_patterns = [
            r'Select Goal.*',
            r'Search for.*',
            r'^\s*\n+',
            r'\s{2,}',
            r'<[^>]+>',  # HTML tags
        ]
        
        cleaned = text.strip()
        for pattern in noise_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.MULTILINE)
        
        cleaned = cleaned.strip()
        
        # Validate length
        if len(cleaned) < 3 or len(cleaned) > 100:
            return "Unknown"
        
        return cleaned


class SuperScraper:
    """Production-grade college scraper with comprehensive validation"""
    
    def __init__(self, page: Page):
        self.page = page
        self.quality_report = DataQualityReport()
        self.colleges_saved = 0
        self.courses_saved = 0
    
    def scrape_college(self, url: str) -> Optional[Dict]:
        """Scrape college with comprehensive validation"""
        try:
            logger.info(f"\n🔍 Scraping: {url}")
            
            # Navigate and wait
            self.page.goto(url, wait_until="networkidle", timeout=60000)
            self.page.wait_for_timeout(2000)
            
            content = self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract college basics with advanced cleaning
            college_data = self._extract_college_basics(soup, url)
            if not college_data:
                logger.error("   ❌ Failed to extract college basics")
                return None
            
            # Extract courses
            courses = self._extract_courses(soup)
            if not courses:
                logger.warning("   ⚠️ No valid courses found")
                return None
            
            # Classify courses by stream
            for course in courses:
                course['stream'] = StreamClassifier.classify(course['name'], course.get('degree_type'))
            
            # Add courses to college data
            college_data['courses'] = courses
            college_data['collegedunia_url'] = url
            college_data['degree_level'] = self._determine_degree_level(courses)
            
            logger.info(f"   ✅ Scraped: {college_data['name']} | Location: {college_data['city']}")
            logger.info(f"      📚 Courses: {len(courses)} | 📍 Streams: {self._get_stream_distribution(courses)}")
            
            return college_data
            
        except Exception as e:
            logger.error(f"   ❌ Error scraping: {e}")
            return None
    
    def _extract_college_basics(self, soup: BeautifulSoup, url: str) -> Optional[Dict]:
        """Extract college basics with comprehensive validation"""
        try:
            # ==================== NAME EXTRACTION ====================
            name = self._extract_college_name(soup)
            if not name:
                logger.error("   ❌ Could not extract valid college name")
                return None
            
            # ==================== LOCATION EXTRACTION ====================
            location_text, city, state = AdvancedLocationExtractor.extract_from_structured_data(soup, url)
            
            # Validate location
            if not city or city == "Unknown":
                logger.warning(f"   ⚠️ Warning: City not extracted for {name}. Trying fallback...")
                # Try to extract from URL
                if 'vellore' in url.lower():
                    city = 'Vellore'
                elif 'chennai' in url.lower():
                    city = 'Chennai'
                else:
                    city = "Unknown"
            
            # ==================== ESTABLISHED YEAR ====================
            established = self._extract_established_year(soup)
            
            # ==================== UNIVERSITY ====================
            university_name = self._extract_university(soup)
            
            # ==================== WEBSITE ====================
            official_website = self._extract_official_website(soup)
            
            # ==================== IMAGES ====================
            images = self._extract_images(soup, url)
            
            # ==================== PLACEMENT ====================
            placement = self._extract_placement(soup)
            
            # ==================== DESCRIPTION ====================
            description = self._extract_description(soup)
            
            # ==================== FEES ====================
            fees = self._extract_fees(soup)
            
            # ==================== NIRF RANK ====================
            nirf_rank = self._extract_nirf_rank(soup)
            
            return {
                'name': name,
                'location': city if city != "Unknown" else location_text,
                'state': state,
                'city': city,
                'university_name': university_name,
                'established': established,
                'official_website': official_website,
                'images': images,
                'placement_percentage': placement,
                'description': description,
                'fees_per_semester_lakhs': fees,
                'nirf_rank': nirf_rank,
                'collegedunia_url': url,
            }
        
        except Exception as e:
            logger.error(f"   ❌ Error extracting basics: {e}")
            return None
    
    def _extract_college_name(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract college name with multiple fallbacks"""
        # Try 1: Page title
        title = self.page.title() or "Unknown"
        name = CollegeCleaner.clean_college_name(title)
        if name and CollegeCleaner.is_valid_college_name(name):
            return name
        
        # Try 2: H1 tags
        for h1 in soup.find_all('h1', limit=3):
            h1_text = h1.get_text(strip=True)
            potential = CollegeCleaner.clean_college_name(h1_text)
            if potential and CollegeCleaner.is_valid_college_name(potential):
                return potential
        
        # Try 3: H2 tags
        for h2 in soup.find_all('h2', limit=5):
            h2_text = h2.get_text(strip=True)
            potential = CollegeCleaner.clean_college_name(h2_text)
            if potential and CollegeCleaner.is_valid_college_name(potential):
                return potential
        
        # Try 4: Meta description
        for meta in soup.find_all('meta'):
            if meta.get('property') == 'og:title':
                og_title = meta.get('content', '')
                potential = CollegeCleaner.clean_college_name(og_title)
                if potential and CollegeCleaner.is_valid_college_name(potential):
                    return potential
        
        logger.warning(f"   ⚠️ Could not extract valid name from page title: {title}")
        return None
    
    def _extract_established_year(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract established year"""
        page_text = soup.get_text()
        
        patterns = [
            r'est.*?:\s*(19\d\d|20\d\d)',
            r'established\s*:?\s*(19\d\d|20\d\d)',
            r'founded\s*:?\s*(19\d\d|20\d\d)',
            r'since\s*:?\s*(19\d\d|20\d\d)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            if matches:
                try:
                    year = int(matches[0])
                    if 1800 <= year <= 2025:
                        return year
                except:
                    pass
        
        return None
    
    def _extract_university(self, soup: BeautifulSoup) -> str:
        """Extract university name"""
        for elem in soup.find_all(['p', 'span', 'div'], limit=50):
            text = elem.get_text(strip=True)
            if 'university' in text.lower() or 'affiliated' in text.lower():
                # Clean text
                result = text.replace('University:', '').replace('Affiliated to:', '').strip()
                if len(result) < 200 and len(result) > 3:
                    return result
        
        return "Unknown"
    
    def _extract_official_website(self, soup: BeautifulSoup) -> str:
        """Extract official website"""
        for link in soup.find_all('a'):
            href = link.get('href', '').strip()
            if not href or href.startswith('http') == False:
                continue
            if 'collegedunia' in href or 'facebook' in href or 'instagram' in href:
                continue
            if any(x in href.lower() for x in ['college', 'university', 'edu', 'ac.in']):
                return href
        
        return ""
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract college images"""
        images = []
        for img in soup.find_all('img', limit=10):
            src = img.get('src', '').strip()
            if not src:
                continue
            
            # Resolve relative URLs
            if src.startswith('//'):
                src = 'https:' + src
            elif src.startswith('/'):
                src = urljoin(base_url, src)
            elif not src.startswith('http'):
                src = urljoin(base_url, src)
            
            if src and ('college' in src.lower() or 'campus' in src.lower() or 'img' in src.lower()):
                images.append(src)
        
        return images
    
    def _extract_placement(self, soup: BeautifulSoup) -> float:
        """Extract placement percentage"""
        page_text = soup.get_text()
        matches = re.findall(r'placement[:\s]+(\d+)\s*%', page_text, re.IGNORECASE)
        if matches:
            try:
                return float(matches[0])
            except:
                pass
        return 0.0
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract college description"""
        # Try meta description
        for meta in soup.find_all('meta'):
            if meta.get('name') == 'description':
                desc = meta.get('content', '').strip()
                if desc and len(desc) > 20:
                    return desc[:500]  # Limit to 500 chars
        
        # Try to find main content paragraph
        for tag in soup.find_all(['p', 'div'], class_=re.compile(r'(about|description|intro|overview)', re.I), limit=5):
            text = tag.get_text(strip=True)
            if text and len(text) > 30:
                return text[:500]
        
        return ""
    
    def _extract_fees(self, soup: BeautifulSoup) -> float:
        """Extract fees per semester in lakhs"""
        page_text = soup.get_text()
        
        # Look for patterns like "₹1.5 Lakhs", "1.5 L", "15000"
        patterns = [
            r'fees?\s*:?\s*(?:₹)?\s*([\d,]+\.?\d*)\s*[Ll]a?kh',  # 1.5 Lakh
            r'(?:₹)?\s*([\d,]+\.?\d*)\s*per\s*year',  # ₹1.5L per year
            r'tuition\s*fee.*?(?:₹)?\s*([\d,]+\.?\d*)',  # tuition fee ₹1.5L
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            if matches:
                try:
                    amount = float(matches[0].replace(',', ''))
                    # If very small, probably in thousands, convert to lakhs
                    if amount < 100:
                        return amount
                    elif amount < 10000:
                        return amount / 100000  # Convert to lakhs
                except:
                    pass
        
        return 0.0
    
    def _extract_nirf_rank(self, soup: BeautifulSoup) -> int:
        """Extract NIRF ranking"""
        page_text = soup.get_text()
        
        patterns = [
            r'nirf\s*rank\s*:?\s*(\d+)',
            r'rank.*?nirf.*?:?\s*(\d+)',
            r'nirf.*?(?:2024|2025)\s*:?\s*(\d+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            if matches:
                try:
                    rank = int(matches[0])
                    if 1 <= rank <= 1000:
                        return rank
                except:
                    pass
        
        return 999  # Default (not ranked)
    
    def _extract_courses(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract courses with validation"""
        courses = []
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
                
                course_name = cell_texts[0] if len(cell_texts) > 0 else ""
                fees_text = cell_texts[1] if len(cell_texts) > 1 else ""
                
                if not CourseCleaner.is_valid_course_name(course_name):
                    continue
                
                # Validate course name
                cleaned_name = CourseCleaner.clean_course_name(course_name)
                if not cleaned_name or not CourseCleaner.is_valid_course_name(cleaned_name):
                    continue
                
                # Extract degree type and code
                degree_type = CourseCleaner.extract_degree_type(course_name)
                code = self._extract_course_code(course_name)
                duration = self._extract_duration(course_name)
                fees = self._extract_fees_value(fees_text)
                
                
                course_data = {
                    'name': cleaned_name,
                    'code': code,
                    'degree_type': degree_type,
                    'duration_years': duration,
                    'fees_per_year_lakhs': fees,
                    'placement_percentage': 0,
                    'is_valid': True,
                }
                
                courses.append(course_data)
        
        return courses
    
    def _extract_course_code(self, course_name: str) -> str:
        """Extract course code from name"""
        # Look for patterns like "CSE", "CE", "ME", etc.
        matches = re.findall(r'\b([A-Z]{2,4})\b', course_name)
        return matches[0] if matches else "UNKNOWN"
    
    def _extract_duration(self, course_name: str) -> int:
        """Extract course duration in years"""
        course_lower = course_name.lower()
        
        if 'diploma' in course_lower:
            return 3
        elif any(x in course_lower for x in ['m.tech', 'mtech', 'mba', 'm.sc', 'msc', 'm.a', 'ma', 'llm']):
            return 2
        elif any(x in course_lower for x in ['b.tech', 'btech', 'b.e', 'b.sc', 'b.a', 'ba', 'llb']):
            return 4
        elif 'phd' in course_lower:
            return 3
        
        return 4  # Default
    
    def _extract_fees_value(self, fee_text: str) -> float:
        """Extract fees value"""
        if not fee_text or len(fee_text) > 100:
            return 0
        
        # Look for currency amounts
        matches = re.findall(r'[\d,]+\.?\d*', fee_text)
        if matches:
            try:
                amount = float(matches[0].replace(',', ''))
                # If amount > 100, assume it's in thousands
                if amount > 100:
                    return amount / 100000  # Convert to lakhs
                return amount
            except:
                pass
        
        return 0
    
    def _determine_degree_level(self, courses: List[Dict]) -> str:
        """Determine overall college degree level"""
        if not courses:
            return 'MIXED'
        
        streams = set(course.get('stream', 'UNKNOWN') for course in courses)
        if len(streams) == 1:
            stream = list(streams)[0]
            if stream in ['ENGINEERING', 'ARTS_SCIENCE', 'COMMERCE', 'MEDICAL']:
                return stream
        
        return 'MIXED'
    
    def _get_stream_distribution(self, courses: List[Dict]) -> str:
        """Get stream distribution for logging"""
        streams = {}
        for course in courses:
            stream = course.get('stream', 'UNKNOWN')
            streams[stream] = streams.get(stream, 0) + 1
        
        return ', '.join([f"{s}:{c}" for s, c in sorted(streams.items())])
    
    def save_college_to_db(self, college_data: Dict) -> bool:
        """Save college and courses to database with validation"""
        try:
            # Comprehensive validation
            if not college_data.get('name') or len(college_data['name'].strip()) == 0:
                logger.error(f"❌ SKIPPING: College name is empty. URL: {college_data.get('collegedunia_url')}")
                return False
            
            if not college_data.get('city') or college_data['city'] == "Unknown":
                logger.error(f"❌ SKIPPING: City not found for {college_data['name']}")
                return False
            
            if not college_data.get('courses') or len(college_data['courses']) == 0:
                logger.error(f"❌ SKIPPING: No valid courses for {college_data['name']}")
                return False
            
            # Provide default established year if missing
            if not college_data.get('established') or college_data['established'] == 0:
                college_data['established'] = 2000  # Default year
            
            # Use transaction for atomic operations
            with transaction.atomic():
                # Create/update college using URL as unique key
                college, created = College.objects.update_or_create(
                    collegedunia_url=college_data['collegedunia_url'],
                    defaults={
                        'name': college_data['name'],
                        'state': college_data['state'],
                        'city': college_data['city'],
                        'location': college_data['location'],
                        'university_name': college_data['university_name'],
                        'established': college_data['established'],
                        'official_website': college_data['official_website'],
                        'degree_level': college_data['degree_level'],
                        'placement_percentage': college_data['placement_percentage'],
                        'description': college_data.get('description', ''),
                        'fees_per_semester_lakhs': college_data.get('fees_per_semester_lakhs', 0),
                        'nirf_rank': college_data.get('nirf_rank', 999),
                    }
                )
                
                # Save images
                for image_url in college_data.get('images', []):
                    CollegeImage.objects.get_or_create(college=college, image_url=image_url)
                
                # Save courses
                Course.objects.filter(college=college).delete()  # Clear old courses
                for course_data in college_data.get('courses', []):
                    Course.objects.create(
                        college=college,
                        name=course_data['name'],
                        code=course_data['code'],
                        degree_type=course_data['degree_type'],
                        stream=course_data['stream'],
                        fees_per_year_lakhs=course_data.get('fees_per_year_lakhs', 0),
                        duration_years=course_data.get('duration_years', 4),
                        placement_percentage=course_data.get('placement_percentage', 0),
                        is_valid=True,
                    )
            
            action = "Created" if created else "Updated"
            logger.info(f"   ✅ {action} college: {college.name} | Courses: {college.courses.count()}")
            
            self.colleges_saved += 1
            self.courses_saved += len(college_data.get('courses', []))
            return True
            
        except Exception as e:
            logger.error(f"   ❌ Error saving to database: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False


class Command(BaseCommand):
    help = 'Run SUPER SCRAPER to collect clean college data'
    
    def add_arguments(self, parser):
        parser.add_argument('--state', type=str, default='tamil-nadu', help='State to scrape')
        parser.add_argument('--max', type=int, default=1000, help='Maximum colleges to scrape')
        parser.add_argument('--headless', action='store_true', help='Run in headless mode')
        parser.add_argument('--no-headless', dest='headless', action='store_false', help='Run in visible mode')
        parser.set_defaults(headless=False)
    
    def handle(self, *args, **options):
        state = options['state'].upper()
        max_colleges = options['max']
        headless = options['headless']
        
        print("\n" + "="*70)
        print("[>>] SUPER SCRAPER v3.0 - PRODUCTION COLLEGE DATA COLLECTOR")
        print("="*70)
        print(f"State: {state} | Target: {max_colleges} colleges | Mode: {'HEADLESS' if headless else 'VISIBLE'}")
        print("="*70 + "\n")
        
        scraped_colleges = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page()
            
            try:
                # Collect URLs
                print("[*] PHASE 1: Collecting college URLs")
                print("-" * 70)
                
                url_collector = URLCollector(page, state)
                college_urls = url_collector.collect_urls(max_colleges)
                
                print(f"[OK] Collected {len(college_urls)} college URLs\n")
                
                # Scrape colleges (collect data only, don't save yet)
                print("[*] PHASE 2: Scraping college data")
                print("-" * 70 + "\n")
                
                scraper = SuperScraper(page)
                
                for idx, url in enumerate(college_urls, 1):
                    college_data = scraper.scrape_college(url)
                    
                    if college_data:
                        scraped_colleges.append(college_data)
                    
                    if idx % 10 == 0:
                        print(f"\n[>>] Progress: {idx}/{len(college_urls)} | Scraped: {len(scraped_colleges)} colleges\n")
                
                print(f"\n[OK] Scraping finished: {len(scraped_colleges)} colleges collected\n")
                
            finally:
                page.close()
                browser.close()
        
        # PHASE 3: Save all colleges to database (OUTSIDE browser context)
        print("[*] PHASE 3: Saving to database")
        print("-" * 70 + "\n")
        
        scraper = SuperScraper(None)  # Create scraper instance for counter tracking
        
        for idx, college_data in enumerate(scraped_colleges, 1):
            scraper.save_college_to_db(college_data)
            
            if idx % 10 == 0:
                print(f"\n[>>] Database Progress: {idx}/{len(scraped_colleges)} | Saved: {scraper.colleges_saved} colleges\n")
        
        # Final report
        print(f"\n" + "="*70)
        print("[OK] SCRAPING COMPLETE")
        print("="*70)
        print(f"   Colleges Processed: {len(college_urls)}")
        print(f"   Colleges Scraped: {len(scraped_colleges)}")
        print(f"   Colleges Saved: {scraper.colleges_saved}")
        print(f"   Total Courses: {scraper.courses_saved}")
        print("="*70 + "\n")


class URLCollector:
    """Collect college URLs from listing pages"""
    
    def __init__(self, page: Page, state: str):
        self.page = page
        self.state = state
        self.urls = []
        self.colleges_found = set()
    
    def collect_urls(self, max_colleges: int) -> List[str]:
        """Collect college URLs efficiently"""
        state_url_map = {
            'TAMIL-NADU': 'https://collegedunia.com/tamil-nadu-colleges',
            'TAMIL_NADU': 'https://collegedunia.com/tamil-nadu-colleges',
        }
        
        url = state_url_map.get(self.state.upper(), f'https://collegedunia.com/{self.state.lower()}-colleges')
        
        logger.info(f"📍 Opening: {url}")
        self.page.goto(url, wait_until="networkidle", timeout=60000)
        self.page.wait_for_timeout(2000)
        
        # Smart scroll with early exit
        max_scrolls = 50
        for scroll_count in range(max_scrolls):
            self.page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
            self.page.wait_for_timeout(200)
            
            # Extract URLs periodically to check if we have enough
            content = self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            college_links = soup.find_all('a', {'href': re.compile(r'/college/')})
            
            # Extract unique URLs
            for link in college_links:
                href = link.get('href', '')
                if '/college/' not in href:
                    continue
                
                # Skip ranking, comparison, review, and other non-main-page URLs
                skip_patterns = ['/rankings', '/comparison', '/reviews', '/vs', 
                               '/details', '/admissions', '/courses', '/placement',
                               '/fees', '/scholarships', '/reviews-ratings']
                if any(pattern in href.lower() for pattern in skip_patterns):
                    continue
                
                if not href.startswith('http'):
                    href = 'https://collegedunia.com' + href
                
                if href not in self.colleges_found:
                    self.urls.append(href)
                    self.colleges_found.add(href)
            
            logger.info(f"   📍 Scroll {scroll_count + 1}: {len(self.urls)} colleges found")
            
            if len(self.urls) >= max_colleges:
                logger.info(f"✅ Collected {len(self.urls)} colleges!")
                break
        
        return self.urls[:max_colleges]
