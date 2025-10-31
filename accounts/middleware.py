# accounts/middleware.py

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from django.http import JsonResponse
from .models import UserSession, User
import logging

logger = logging.getLogger(__name__)


class SingleDeviceMiddleware:
    """
    Middleware to enforce single-device login by checking if the access token's
    session still exists in the database.
    
    For non-SITE_OWNER users, if the session doesn't exist, the token is invalidated.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Skip for non-authenticated endpoints
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if auth_header.startswith('Bearer '):
            try:
                # Extract and validate the token
                jwt_auth = JWTAuthentication()
                validated_token = jwt_auth.get_validated_token(auth_header.split(' ')[1])
                user = jwt_auth.get_user(validated_token)
                
                # Skip check for SITE_OWNERs (they can have multiple sessions)
                if user.role == User.Role.SITE_OWNER:
                    return self.get_response(request)
                
                # Get the access token JTI
                access_jti = str(validated_token.get('jti', ''))
                
                if access_jti:
                    # Check if this session exists in the database
                    session_exists = UserSession.objects.filter(
                        user=user,
                        jti=access_jti
                    ).exists()
                    
                    if not session_exists:
                        # Session was deleted (user logged in from another device)
                        logger.warning(
                            f"Invalid session for user {user.username}. "
                            f"Token JTI {access_jti[:10]}... not found in active sessions."
                        )
                        return JsonResponse(
                            {
                                'detail': 'Your session has ended. You may have logged in from another device.',
                                'code': 'session_ended'
                            },
                            status=401
                        )
                        
            except InvalidToken:
                # Token is invalid/expired, let DRF handle it normally
                pass
            except Exception as e:
                # Log but don't block the request
                logger.error(f"Error in SingleDeviceMiddleware: {str(e)}")
        
        return self.get_response(request)
