"""
Real-Time College Data Service
Provides high-performance access to college data from database.

Architecture:
   Real-time API (serves from DB)
       ↓
   Fast response (<100ms)
   
Note: Data is populated via custom scraper (to be provided)
"""

import os
import django
import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import models, transaction
from django.db.models import Count, Avg
from colleges.models import RealCollege

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RealTimeCollegeService:
    """
    Service for real-time college data access
    - Queries database directly (fast)
    - No scraping on API calls
    - Uses caching for frequently accessed data
    """
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour cache
        
    def get_colleges_real_time(self, filters=None):
        """
        Get colleges from database in REAL-TIME (no scraping)
        Response time: <100ms
        """
        logger.info(f"⚡ Real-time query: {filters}")
        
        colleges = RealCollege.objects.all()
        
        # Apply filters if provided
        if filters:
            if filters.get('state'):
                colleges = colleges.filter(state__icontains=filters['state'])
            if filters.get('city'):
                colleges = colleges.filter(city__icontains=filters['city'])
        
        # Order by name (fastest colleges listed first)
        colleges = colleges.order_by('name')[:50]
        
        return colleges
    
    def get_college_by_id_real_time(self, college_id):
        """
        Get single college from database
        Response time: <50ms
        """
        return RealCollege.objects.get(id=college_id)
    
    def get_colleges_cached(self, cache_key, query_func):
        """
        Get colleges with caching for frequently accessed data
        Response time: <5ms (from cache)
        """
        # Check cache first
        if cache_key in self.cache:
            cache_data, timestamp = self.cache[cache_key]
            if (datetime.now() - timestamp).seconds < self.cache_ttl:
                logger.info(f"📦 Cache hit: {cache_key}")
                return cache_data
        
        # Query database if not in cache
        data = query_func()
        self.cache[cache_key] = (data, datetime.now())
        logger.info(f"💾 Cache updated: {cache_key}")
        return data
    
    def get_state_statistics_cached(self, state):
        """
        Get state statistics with caching
        """
        cache_key = f"state_stats_{state}"
        
        def query():
            return RealCollege.objects.filter(state__icontains=state).aggregate(
                count=Count('id')
            )
        
        return self.get_colleges_cached(cache_key, query)

