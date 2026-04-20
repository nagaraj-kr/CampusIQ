"""
URL Configuration for Students App - Authentication Routes
"""

from django.urls import path
from students import views

app_name = 'students'

urlpatterns = [
    # Authentication endpoints
    path('auth/register/', views.register, name='register'),
    path('auth/login/', views.login, name='login'),
    path('auth/logout/', views.logout, name='logout'),
    path('auth/current-user/', views.current_user, name='current_user'),
    path('auth/change-password/', views.change_password, name='change_password'),
    
    # Profile endpoints
    path('profile/', views.profile_view, name='profile'),
]
