"""
Student Authentication and Profile Views
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from django.contrib.auth import logout as django_logout
from django.views.decorators.csrf import csrf_exempt

from students.models import StudentProfile
from students.serializers import (
    RegisterSerializer, LoginSerializer, LogoutSerializer,
    StudentProfileSerializer, ChangePasswordSerializer, UserSerializer
)


@csrf_exempt
@permission_classes([AllowAny])
@api_view(['POST'])
def register(request):
    """
    Register a new student account
    POST /api/auth/register/
    """
    serializer = RegisterSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.save()
        return Response({
            'status': 'success',
            'message': 'Account created successfully',
            'user': UserSerializer(user).data,
            'profile': StudentProfileSerializer(user.student_profile).data
        }, status=status.HTTP_201_CREATED)
    
    return Response({
        'status': 'error',
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@permission_classes([AllowAny])
@api_view(['POST'])
def login(request):
    """
    Login with username and password
    POST /api/auth/login/
    """
    serializer = LoginSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.validated_data['user']
        
        # Create session
        from django.contrib.auth import login as django_login
        django_login(request, user)
        
        return Response({
            'status': 'success',
            'message': 'Login successful',
            'user': UserSerializer(user).data,
            'profile': StudentProfileSerializer(user.student_profile).data
        }, status=status.HTTP_200_OK)
    
    return Response({
        'status': 'error',
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@permission_classes([IsAuthenticated])
@api_view(['POST'])
def logout(request):
    """
    Logout current user
    POST /api/auth/logout/
    """
    django_logout(request)
    
    return Response({
        'status': 'success',
        'message': 'Logout successful'
    }, status=status.HTTP_200_OK)


@csrf_exempt
@permission_classes([AllowAny])
@api_view(['GET'])
def current_user(request):
    """
    Get current authenticated user profile
    GET /api/auth/current-user/
    Returns 401 if not authenticated
    """
    try:
        if not request.user or not request.user.is_authenticated:
            return Response({
                'status': 'error',
                'message': 'Not authenticated'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Ensure StudentProfile exists
        profile, created = StudentProfile.objects.get_or_create(user=request.user)
        
        return Response({
            'status': 'success',
            'user': UserSerializer(request.user).data,
            'profile': StudentProfileSerializer(profile).data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        import traceback
        print(f"Error in current_user: {str(e)}")
        traceback.print_exc()
        return Response({
            'status': 'error',
            'message': f'Server error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@permission_classes([IsAuthenticated])
@api_view(['POST'])
def change_password(request):
    """
    Change user password
    POST /api/auth/change-password/
    """
    serializer = ChangePasswordSerializer(data=request.data)
    
    if serializer.is_valid():
        user = request.user
        
        # Verify old password
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({
                'status': 'error',
                'message': 'Old password is incorrect'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Set new password
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({
            'status': 'success',
            'message': 'Password changed successfully'
        }, status=status.HTTP_200_OK)
    
    return Response({
        'status': 'error',
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@permission_classes([IsAuthenticated])
@api_view(['GET', 'PUT'])
def profile_view(request):
    """
    Get or update student profile
    GET /api/profile/
    PUT /api/profile/
    """
    try:
        profile = request.user.student_profile
    except StudentProfile.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'Student profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = StudentProfileSerializer(profile)
        return Response({
            'status': 'success',
            'profile': serializer.data
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'PUT':
        serializer = StudentProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'status': 'success',
                'message': 'Profile updated successfully',
                'profile': serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

