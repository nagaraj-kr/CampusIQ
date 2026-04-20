from django.urls import path
from .views import recommend_colleges
from .realcollege_views import (
    get_college_recommendations,
    get_college_detail_view,
    filter_colleges_view
)

urlpatterns = [
    # Legacy endpoint
    path('recommend-colleges/', recommend_colleges),
    
    # New RealCollege endpoints (with real data)
    path('get-recommendations/', get_college_recommendations, name='get-recommendations'),
    path('filter-colleges/', filter_colleges_view, name='filter-colleges'),
    path('college-detail/<int:college_id>/', get_college_detail_view, name='college-detail'),
]