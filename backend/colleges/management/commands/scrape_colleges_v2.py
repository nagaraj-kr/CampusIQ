"""
Advanced College Scraper v2.0
Collects clean, structured college data from CollegeDunia

Workflow:
1. Get college URLs from listing page (e.g., https://collegedunia.com/tamil-nadu-colleges)
2. For each URL:
   - Visit college page
   - Extract: name, location, university, established year
   - Extract: official website, images
   - Extract: courses (with stream classification)
   - Extract: fees, placement details
3. Validate ALL data
4. Store ONLY clean data
5. Report data quality

Run: python manage.py scrape_colleges_v2 --state=tamil-nadu --max=1000
"""

import time
import logging
import os
import re
from typing import List, Dict, Optional, Tuple
from django.core.management.base import BaseCommand
from django.utils import timezone
from playwright.sync_api import sync_playwright, Page, Browser
from bs4 import BeautifulSoup
from colleges.models import College, Course, CollegeImage
from colleges.data_validators import (
    CourseCleaner, CollegeCleaner, LocationCleaner,
    StreamClassifier, DataQualityReport
)

os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CollegeURLCollector:
    """
    Collects college URLs from CollegeDunia listing pages
    Handles dynamic loading by scrolling through the entire page
    """
    
    def __init__(self, page: Page, timeout_per_scroll: int = 2000):
        self.page = page
        self.timeout = timeout_per_scroll
        self.urls = []
        self.colleges_found = set()  # Track unique colleges
    
    def collect_urls(self, listing_url: str, max_colleges: int = 1000) -> List[str]:
        """
        Collect college URLs from listing page
        
        Strategy:
        1. Open listing page
        2. Scroll to load more colleges dynamically
        3. Extract URLs as they load
        4. Stop when enough collected or page ends
        """
        logger.info(f"\n📍 STARTING URL COLLECTION from {listing_url}")
        logger.info(f"   Target: {max_colleges} colleges")
        
        try:
            # Open listing page
            logger.info("   ⏳ Opening listing page...")
            self.page.goto(listing_url, wait_until="networkidle", timeout=60000)
            
            # Wait for content to fully load
            logger.info("   ⏳ Waiting for content to load...")
            self.page.wait_for_timeout(5000)  # Increased wait time
            
            # Try to wait for college elements to appear
            try:
                self.page.wait_for_selector('a[href*="/college/"]', timeout=10000)
            except:
                logger.warning("   ⚠️ College links selector timeout (might still have loaded)")
            
            # Get initial URLs
            self._extract_urls_from_page()
            logger.info(f"   ✅ Found {len(self.urls)} colleges in initial page")
            
            # If nothing found, try a few more waits
            if len(self.urls) == 0:
                logger.warning("   ⚠️ No colleges found on first extraction, trying again...")
                self.page.wait_for_timeout(3000)
                self._extract_urls_from_page()
                logger.info(f"   ✅ After retry: {len(self.urls)} colleges found")
            
            # Scroll and load more
            max_scrolls = 150
            scroll_count = 0
            previous_count = 0
            
            while len(self.urls) < max_colleges and scroll_count < max_scrolls:
                # Scroll down
                self.page.evaluate("window.scrollBy(0, window.innerHeight)")
                self.page.wait_for_timeout(self.timeout)
                
                # Extract newly visible URLs
                self._extract_urls_from_page()
                
                scroll_count += 1
                current_count = len(self.urls)
                
                # Log progress every 10 scrolls
                if scroll_count % 10 == 0:
                    new_colleges = current_count - previous_count
                    logger.info(f"   ✅ Scroll {scroll_count}/{max_scrolls} | Total: {current_count} | New in batch: {new_colleges}")
                    previous_count = current_count
                
                # Check if we've reached the end (no new colleges loaded)
                if current_count == previous_count and scroll_count > 50:
                    logger.info(f"   🔚 Reached end of listing (no new colleges loaded)")
                    break
            
            logger.info(f"\n✅ COLLECTION COMPLETE: {len(self.urls)} college URLs collected\n")
            return self.urls[:max_colleges]  # Return only up to max
        
        except Exception as e:
            logger.error(f"❌ Error collecting URLs: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self.urls
    
    def _extract_urls_from_page(self):
        """Extract all college URLs currently visible on page"""
        try:
            content = self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Primary selector: Find ALL links with /college/ in href
            # This is the most reliable selector for CollegeDunia
            college_links = soup.find_all('a', href=re.compile(r'/college/[^/]+$', re.I))
            
            if not college_links:
                logger.warning("⚠️ No college links found, trying alternative selectors...")
                # Fallback 1: Any /college/ link (might include course/review pages)
                college_links = soup.find_all('a', href=re.compile(r'/college/', re.I))
            
            if not college_links:
                logger.warning("⚠️ Still no links found. Page might not have loaded properly.")
                # Log page content size for debugging
                logger.warning(f"   Page content size: {len(content)} bytes")
                return
            
            logger.debug(f"   Found {len(college_links)} potential college links")
            
            for link in college_links:
                href = link.get('href', '')
                
                # Validate href format
                if not href or '/college/' not in href:
                    continue
                
                # Build full URL if relative
                if not href.startswith('http'):
                    href = 'https://collegedunia.com' + href
                
                # Ensure it's actually a collegedunia URL
                if 'collegedunia.com' not in href:
                    continue
                
                # Deduplicate
                if href not in self.colleges_found:
                    self.urls.append(href)
                    self.colleges_found.add(href)
        
        except Exception as e:
            logger.warning(f"⚠️ Error extracting URLs from page: {e}")
            import traceback
            logger.warning(traceback.format_exc())


class IndividualCollegeScraper:
    """
    Scrapes individual college pages
    Extracts comprehensive data: courses, fees, placement, etc.
    """
    
    def __init__(self, page: Page):
        self.page = page
        self.quality_report = DataQualityReport()
    
    def scrape_college(self, url: str) -> Optional[Dict]:
        """
        Scrape complete college data from individual page
        
        Returns: Dictionary with college data or None if invalid
        """
        try:
            logger.info(f"\n🔍 Scraping: {url}")
            self.page.goto(url, wait_until="networkidle", timeout=60000)
            self.page.wait_for_timeout(2000)
            
            content = self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract college basics
            college_data = self._extract_college_basics(soup)
            if not college_data:
                logger.warning("   ❌ Failed to extract college basics")
                return None
            
            # Extract courses
            courses = self._extract_courses(soup)
            if not courses:
                logger.warning("   ⚠️ No valid courses found")
                return None
            
            # Extract fees per course type
            fees_map = self._extract_fees(soup)
            
            # Classify courses by stream
            for course in courses:
                course['stream'] = StreamClassifier.classify(course['name'], course.get('degree_type'))
            
            # Determine college degree level from courses
            college_data['degree_level'] = self._determine_degree_level(courses)
            
            college_data['courses'] = courses
            college_data['fees_map'] = fees_map
            college_data['collegedunia_url'] = url
            
            logger.info(f"   ✅ Scraped successfully: {college_data['name']}")
            logger.info(f"      📚 Courses: {len(courses)} | 🎓 Streams: {self._get_stream_distribution(courses)}")
            
            return college_data
        
        except Exception as e:
            logger.error(f"   ❌ Error scraping: {e}")
            return None
    
    def _extract_college_basics(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Extract: name, location, university, established year, website, images"""
        try:
            # College name - try multiple sources
            name = None
            
            # Try 1: Page title
            title = self.page.title() or "Unknown"
            name = CollegeCleaner.clean_college_name(title)
            
            # Try 2: Look for h1 or main heading if title doesn't work
            if not name or not CollegeCleaner.is_valid_college_name(name):
                for heading in soup.find_all(['h1', 'h2'], limit=5):
                    heading_text = heading.get_text(strip=True)
                    potential_name = CollegeCleaner.clean_college_name(heading_text)
                    if potential_name and CollegeCleaner.is_valid_college_name(potential_name):
                        name = potential_name
                        break
            
            # Reject if still no valid name
            if not name or not CollegeCleaner.is_valid_college_name(name):
                logger.warning(f"   ❌ Could not extract valid college name (title: '{title}')")
                return None
            
            logger.info(f"   ✅ College: {name}")
            
            # Location
            location_text = "Unknown"
            for elem in soup.find_all(['p', 'span', 'div'], limit=100):
                text = elem.get_text(strip=True)
                if 'location' in text.lower() or 'address' in text.lower():
                    location_text = text.replace('Location:', '').replace('Location', '').strip()
                    break
            
            # Extract state and city
            state, city = LocationCleaner.extract_state_city(location_text)
            
            # University name
            university_name = "Unknown"
            for elem in soup.find_all(['p', 'span', 'div'], limit=100):
                text = elem.get_text(strip=True)
                if 'university' in text.lower() or 'affiliated' in text.lower():
                    university_name = text.replace('University:', '').replace('Affiliated to:', '').strip()
                    if len(university_name) > 200:
                        university_name = "Unknown"
                    break
            
            # Established year - IMPROVED EXTRACTION
            established = None
            
            # Try 1: Look in meta tags
            for meta in soup.find_all('meta'):
                content = meta.get('content', '').lower()
                meta_name = meta.get('name', '').lower()
                if 'establish' in meta_name or 'found' in meta_name:
                    matches = re.findall(r'(19\d\d|20\d\d)', content)
                    if matches:
                        year = int(matches[0])
                        if 1800 <= year <= 2025:
                            established = year
                            break
            
            # Try 2: Look in page text more broadly if not found
            if not established:
                page_text = soup.get_text()
                # Search for "established", "founded", "since", etc.
                patterns = [
                    r'established\s*:?\s*(19\d\d|20\d\d)',
                    r'founded\s*:?\s*(19\d\d|20\d\d)',
                    r'since\s*:?\s*(19\d\d|20\d\d)',
                    r'est\.\s*(19\d\d|20\d\d)',
                ]
                for pattern in patterns:
                    matches = re.findall(pattern, page_text, re.IGNORECASE)
                    if matches:
                        year = int(matches[0])
                        if 1800 <= year <= 2025:
                            established = year
                            break
            
            # Try 3: Search in divs/spans more thoroughly
            if not established:
                for elem in soup.find_all(['p', 'span', 'div', 'li'], limit=500):
                    text = elem.get_text(strip=True)
                    if any(kw in text.lower() for kw in ['establish', 'found', 'since', 'est']):
                        matches = re.findall(r'(19\d\d|20\d\d)', text)
                        if matches:
                            try:
                                year = int(matches[0])
                                if 1800 <= year <= 2025:
                                    established = year
                                    break
                            except:
                                pass
            
            # Fallback: set to None instead of 2000
            if not established:
                established = None
            
            # Official website
            official_website = ""
            for link in soup.find_all('a'):
                href = link.get('href', '')
                if href and any(x in href.lower() for x in ['college', 'university', 'edu', 'ac.in']):
                    if not href.startswith('http'):
                        continue
                    if 'collegedunia' not in href and 'facebook' not in href:
                        official_website = href
                        break
            
            # Images
            images = []
            for img in soup.find_all('img', limit=5):
                src = img.get('src', '')
                if src and ('college' in src.lower() or 'campus' in src.lower()):
                    if not src.startswith('http'):
                        if src.startswith('//'):
                            src = 'https:' + src
                        elif src.startswith('/'):
                            src = 'https://collegedunia.com' + src
                    images.append(src)
            
            # Placement percentage
            placement = 0.0
            page_text = soup.get_text()
            matches = re.findall(r'placement[:\s]+(\d+)\s*%', page_text, re.IGNORECASE)
            if matches:
                try:
                    placement = float(matches[0])
                except:
                    pass
            
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
            }
        
        except Exception as e:
            logger.error(f"   ❌ Error extracting college basics: {e}")
            return None
    
    def _extract_courses(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract course details with validation"""
        courses = []
        
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
                    
                    course_name = cell_texts[0].strip()
                    if not course_name or len(course_name) < 3:
                        continue
                    
                    # Clean course name
                    course_name = CourseCleaner.clean_course_name(course_name)
                    if not course_name:
                        continue
                    
                    # Validate
                    if not CourseCleaner.is_valid_course_name(course_name):
                        self.quality_report.add_rejected_course("Invalid course name")
                        continue
                    
                    # Extract degree type
                    degree_type = CourseCleaner.extract_degree_type(course_name)
                    
                    # Extract fees
                    fees_text = cell_texts[1] if len(cell_texts) > 1 else ""
                    fees_lakhs = self._extract_fees_value(fees_text)
                    
                    # Extract course code
                    code = self._extract_course_code(course_name)
                    
                    # Extract duration
                    duration = self._extract_duration(course_name)
                    
                    course_data = {
                        'name': course_name,
                        'code': code,
                        'degree_type': degree_type,
                        'fees_per_year_lakhs': fees_lakhs,
                        'duration_years': duration,
                        'placement_percentage': 0,  # Will be set from college
                    }
                    
                    courses.append(course_data)
                    self.quality_report.valid_courses += 1
            
            self.quality_report.total_courses_checked += len(courses)
            return courses
        
        except Exception as e:
            logger.warning(f"   ⚠️ Error extracting courses: {e}")
            return courses
    
    def _extract_fees(self, soup: BeautifulSoup) -> Dict[str, float]:
        """Extract fees per course type"""
        fees_map = {}
        
        try:
            page_text = soup.get_text()
            
            # Look for patterns like "B.Tech ₹9.39 Lakhs per year"
            patterns = [
                (r'B\.?Tech[:\s]+₹?([\d.]+)\s*[Ll]akh', 'B.Tech'),
                (r'M\.?Tech[:\s]+₹?([\d.]+)\s*[Ll]akh', 'M.Tech'),
                (r'B\.?Sc[:\s]+₹?([\d.]+)\s*[Ll]akh', 'B.Sc'),
                (r'MBA[:\s]+₹?([\d.]+)\s*[Ll]akh', 'MBA'),
            ]
            
            for pattern, degree in patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    try:
                        fees_value = float(matches[0])
                        if 0 < fees_value <= 200:
                            fees_map[degree] = fees_value
                    except:
                        pass
            
            return fees_map
        
        except Exception as e:
            logger.warning(f"   ⚠️ Error extracting fees: {e}")
            return fees_map
    
    def _extract_fees_value(self, fee_text: str) -> float:
        """Extract numeric fees value from text"""
        try:
            if not fee_text:
                return 0.0
            
            matches = re.findall(r'[\d.]+', fee_text)
            if matches:
                value = float(matches[0])
                if 0 <= value <= 200:  # Reasonable range in lakhs
                    return value
        except:
            pass
        
        return 0.0
    
    def _extract_course_code(self, course_name: str) -> str:
        """Extract course code like CSE, ME, EEE"""
        codes = {
            'computer science': 'CSE',
            'information technology': 'IT',
            'mechanical': 'ME',
            'civil': 'CE',
            'electrical': 'EEE',
            'electronics': 'ECE',
            'chemical': 'CHEM',
            'aerospace': 'AE',
            'automobile': 'AUTO',
            'production': 'PROD',
            'biotechnology': 'BT',
        }
        
        course_lower = course_name.lower()
        for key, code in codes.items():
            if key in course_lower:
                return code
        
        return 'UNKNOWN'
    
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
    
    def _determine_degree_level(self, courses: List[Dict]) -> str:
        """Determine overall college degree level from courses"""
        if not courses:
            return 'MIXED'
        
        streams = set(course.get('stream', 'UNKNOWN') for course in courses)
        
        if len(streams) == 1:
            stream = list(streams)[0]
            if stream == 'ENGINEERING':
                return 'ENGINEERING'
            elif stream == 'ARTS_SCIENCE':
                return 'ARTS_SCIENCE'
            elif stream == 'COMMERCE':
                return 'COMMERCE'
        
        return 'MIXED'
    
    def _get_stream_distribution(self, courses: List[Dict]) -> str:
        """Get distribution of streams in courses"""
        streams = {}
        for course in courses:
            stream = course.get('stream', 'UNKNOWN')
            streams[stream] = streams.get(stream, 0) + 1
        
        return ', '.join(f"{k}:{v}" for k, v in sorted(streams.items()))


class Command(BaseCommand):
    help = 'Scrape colleges from CollegeDunia with clean data validation'
    
    def add_arguments(self, parser):
        parser.add_argument('--state', default='tamil-nadu', help='State code (tamil-nadu, delhi, etc)')
        parser.add_argument('--max', type=int, default=100, help='Max colleges to scrape')
        parser.add_argument('--no-headless', action='store_true', help='Show browser window')
    
    def handle(self, *args, **options):
        state = options['state']
        max_colleges = options['max']
        headless = not options['no_headless']
        
        print("\n" + "="*70)
        print("🎓 COLLEGE SCRAPER v2.0 - ADVANCED URL + DATA COLLECTION")
        print("="*70)
        print(f"State: {state.upper()}")
        print(f"Target: {max_colleges} colleges")
        print(f"Mode: {'HEADLESS' if headless else 'VISIBLE'}")
        print("="*70 + "\n")
        
        listing_url = f"https://collegedunia.com/{state}-colleges"
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()
            
            try:
                # Step 1: Collect URLs
                url_collector = CollegeURLCollector(page)
                college_urls = url_collector.collect_urls(listing_url, max_colleges)
                
                if not college_urls:
                    logger.error("❌ No college URLs collected. Aborting.")
                    return
                
                # Step 2: Scrape individual colleges
                scraper = IndividualCollegeScraper(page)
                
                print(f"\n{'='*70}")
                print(f"📚 SCRAPING {len(college_urls)} COLLEGES")
                print(f"{'='*70}\n")
                
                scraped_count = 0
                for idx, url in enumerate(college_urls, 1):
                    college_data = scraper.scrape_college(url)
                    
                    if college_data and college_data['courses']:
                        self._save_college_to_db(college_data)
                        scraped_count += 1
                    
                    # Progress
                    if idx % 10 == 0:
                        print(f"   Progress: {idx}/{len(college_urls)} | Saved: {scraped_count}\n")
                
                # Report
                print(f"\n{'='*70}")
                print(f"✅ SCRAPING COMPLETE")
                print(f"   Colleges Processed: {len(college_urls)}")
                print(f"   Colleges Saved: {scraped_count}")
                print(f"   Success Rate: {(scraped_count/len(college_urls)*100):.1f}%")
                print(f"{'='*70}\n")
                
                scraper.quality_report.print_report()
            
            finally:
                browser.close()
    
    def _save_college_to_db(self, college_data: Dict):
        """Save college and courses to database"""
        try:
            # Validate college name before saving
            if not college_data.get('name') or len(college_data['name'].strip()) == 0:
                logger.error(f"❌ SKIPPING: College name is empty. URL: {college_data.get('collegedunia_url', 'Unknown')}")
                return
            
            # Create/update college using URL as unique key (not name)
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
            
            status = "✅ CREATED" if created else "🔄 UPDATED"
            logger.info(f"{status}: {college.name} with {len(college_data['courses'])} courses")
        
        except Exception as e:
            logger.error(f"❌ Error saving college: {e}")
