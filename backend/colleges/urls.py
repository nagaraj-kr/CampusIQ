from django.urls import path
from . import views

urlpatterns = [
    # College endpoints
    path('colleges/', views.get_colleges, name='get-colleges'),
]